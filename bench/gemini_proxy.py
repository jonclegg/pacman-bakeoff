"""Anthropic Messages to Gemini API translation proxy, so Claude Code can drive Gemini models directly.

Usage: python3 bench/gemini_proxy.py <port> <usage_log.jsonl>

Claude Code's ANTHROPIC_AUTH_TOKEN (the Gemini API key) arrives as a bearer token and goes upstream as x-goog-api-key.
Google doesn't stream function-call arguments, so a big Write is silent upstream for minutes. The upstream socket gets
the cell's full hour before it times out, and Claude Code gets an Anthropic `ping` event every 10 s of silence.
Gemini thought signatures must come back with each function call; they stay here, keyed by the tool_use id.
Every /v1/messages response appends Gemini's own usageMetadata to the usage log, which is the basis for cost.
"""
import hashlib
import http.client
import http.server
import json
import queue
import sys
import threading
import time
import uuid

UPSTREAM_HOST = "generativelanguage.googleapis.com"
UPSTREAM_PREFIX = "/v1beta/models/"
UPSTREAM_TIMEOUT_SECONDS = 3600
PING_SECONDS = 10
THINKING_LEVELS = {"low": "low", "medium": "medium", "high": "high"}
STOP_REASONS = {"STOP": "end_turn", "MAX_TOKENS": "max_tokens"}
ERROR_TYPES = {400: "invalid_request_error", 401: "authentication_error", 403: "permission_error",
               404: "not_found_error", 429: "rate_limit_error", 503: "overloaded_error"}
TOOL_CALLS = {}
TEXT_SIGNATURES = {}
LOG_LOCK = threading.Lock()
USAGE_LOG = None


###############################################################################
def text_key(text):
    return hashlib.sha256(text.encode()).hexdigest()


###############################################################################
def media_part(block):
    source = block["source"]
    if source["type"] != "base64":
        raise ValueError("unsupported %s source type %s" % (block["type"], source["type"]))
    return {"inlineData": {"mimeType": source["media_type"], "data": source["data"]}}


###############################################################################
def user_parts(content):
    if isinstance(content, str):
        return [{"text": content}]
    parts = []
    for block in content:
        kind = block["type"]
        if kind == "text":
            parts.append({"text": block["text"]})
        elif kind in ("image", "document"):
            parts.append(media_part(block))
        elif kind == "tool_result":
            call = TOOL_CALLS[block["tool_use_id"]]
            result = block.get("content", "")
            blocks = [{"type": "text", "text": result}] if isinstance(result, str) else result
            text = "\n".join(b["text"] for b in blocks if b["type"] == "text")
            function_response = {"name": call["name"], "response": {"error" if block.get("is_error") else "output": text}}
            if call["id"]:
                function_response["id"] = call["id"]
            parts.append({"functionResponse": function_response})
            parts.extend(media_part(b) for b in blocks if b["type"] == "image")
        else:
            raise ValueError("unsupported user block type %s" % kind)
    return parts


###############################################################################
def model_parts(content):
    if isinstance(content, str):
        return [{"text": content}] if content else []
    parts = []
    for block in content:
        kind = block["type"]
        if kind in ("thinking", "redacted_thinking"):
            continue
        if kind == "text":
            if not block["text"]:
                continue
            part = {"text": block["text"]}
            signature = TEXT_SIGNATURES.get(text_key(block["text"]))
        elif kind == "tool_use":
            call = TOOL_CALLS[block["id"]]
            function_call = {"name": block["name"], "args": block["input"]}
            if call["id"]:
                function_call["id"] = call["id"]
            part = {"functionCall": function_call}
            signature = call["signature"]
        else:
            raise ValueError("unsupported assistant block type %s" % kind)
        if signature:
            part["thoughtSignature"] = signature
        parts.append(part)
    return parts


###############################################################################
def system_text(system):
    if isinstance(system, str):
        return system
    return "\n\n".join(block["text"] for block in system)


###############################################################################
def thinking_config(body):
    config = {"includeThoughts": True}
    effort = (body.get("output_config") or {}).get("effort")
    if effort:
        config["thinkingLevel"] = THINKING_LEVELS[effort]
    return config


###############################################################################
def tool_config(tool_choice):
    kind = tool_choice["type"]
    if kind == "auto":
        return None
    if kind == "none":
        return {"functionCallingConfig": {"mode": "NONE"}}
    if kind == "any":
        return {"functionCallingConfig": {"mode": "ANY"}}
    if kind == "tool":
        return {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": [tool_choice["name"]]}}
    raise ValueError("unsupported tool_choice %s" % kind)


###############################################################################
def gemini_request(body):
    contents = []
    for message in body["messages"]:
        role = "model" if message["role"] == "assistant" else "user"
        parts = model_parts(message["content"]) if role == "model" else user_parts(message["content"])
        if not parts:
            continue
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"].extend(parts)
        else:
            contents.append({"role": role, "parts": parts})
    request = {"contents": contents}
    if body.get("system"):
        request["systemInstruction"] = {"parts": [{"text": system_text(body["system"])}]}
    if body.get("tools"):
        request["tools"] = [{"functionDeclarations": [
            {"name": tool["name"], "description": tool.get("description", ""), "parametersJsonSchema": tool["input_schema"]}
            for tool in body["tools"]]}]
        config = tool_config(body.get("tool_choice") or {"type": "auto"})
        if config:
            request["toolConfig"] = config
    if "max_tokens" in body:
        request["generationConfig"] = {"maxOutputTokens": body["max_tokens"], "thinkingConfig": thinking_config(body)}
    return request


###############################################################################
def anthropic_usage(metadata):
    cached = metadata.get("cachedContentTokenCount", 0)
    return {"input_tokens": metadata.get("promptTokenCount", 0) - cached,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": cached,
            "output_tokens": metadata.get("candidatesTokenCount", 0) + metadata.get("thoughtsTokenCount", 0)}


###############################################################################
class Translator:
    """Turns Gemini response parts into Anthropic content-block events, passed to emit(event_type, data)."""

    def __init__(self, emit):
        self.emit = emit
        self.index = -1
        self.open = None
        self.text = ""
        self.text_signature = None
        self.last_tool_id = None
        self.tool_calls = 0
        self.orphan_signatures = 0

    def start(self, kind, block):
        self.stop()
        self.index += 1
        self.open = kind
        self.emit("content_block_start", {"type": "content_block_start", "index": self.index, "content_block": block})

    def delta(self, delta):
        self.emit("content_block_delta", {"type": "content_block_delta", "index": self.index, "delta": delta})

    def stop(self):
        if self.open is None:
            return
        if self.open == "text" and self.text_signature:
            TEXT_SIGNATURES[text_key(self.text)] = self.text_signature
        self.emit("content_block_stop", {"type": "content_block_stop", "index": self.index})
        self.open = None

    def attach_signature(self, signature):
        if self.open == "text":
            self.text_signature = signature
        elif self.last_tool_id and TOOL_CALLS[self.last_tool_id]["signature"] is None:
            TOOL_CALLS[self.last_tool_id]["signature"] = signature
        else:
            self.orphan_signatures += 1

    def part(self, part):
        signature = part.get("thoughtSignature")
        if "functionCall" in part:
            call = part["functionCall"]
            tool_id = "toolu_" + uuid.uuid4().hex[:24]
            TOOL_CALLS[tool_id] = {"name": call["name"], "id": call.get("id"), "signature": signature}
            self.start("tool_use", {"type": "tool_use", "id": tool_id, "name": call["name"], "input": {}})
            self.delta({"type": "input_json_delta", "partial_json": json.dumps(call.get("args") or {})})
            self.stop()
            self.last_tool_id = tool_id
            self.tool_calls += 1
        elif "text" in part and part.get("thought"):
            if part["text"]:
                if self.open != "thinking":
                    self.start("thinking", {"type": "thinking", "thinking": "", "signature": ""})
                self.delta({"type": "thinking_delta", "thinking": part["text"]})
            if signature:
                self.orphan_signatures += 1
        elif "text" in part:
            if part["text"]:
                if self.open != "text":
                    self.start("text", {"type": "text", "text": ""})
                    self.text = ""
                    self.text_signature = None
                self.text += part["text"]
                self.delta({"type": "text_delta", "text": part["text"]})
            if signature:
                self.attach_signature(signature)
        else:
            raise ValueError("unsupported Gemini part %s" % sorted(part))

    def chunk(self, chunk):
        if chunk.get("promptFeedback", {}).get("blockReason"):
            raise ValueError("prompt blocked: %s" % chunk["promptFeedback"]["blockReason"])
        for candidate in chunk.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                self.part(part)

    def stop_reason(self, finish_reason):
        if self.tool_calls:
            return "tool_use"
        return STOP_REASONS.get(finish_reason, "end_turn")


###############################################################################
class Collector:
    """Builds a non-streaming Anthropic message from the same events a stream would carry."""

    def __init__(self):
        self.content = []
        self.json = ""

    def __call__(self, event_type, data):
        if event_type == "content_block_start":
            self.content.append(dict(data["content_block"]))
            self.json = ""
        elif event_type == "content_block_delta":
            block, delta = self.content[-1], data["delta"]
            if delta["type"] == "text_delta":
                block["text"] += delta["text"]
            elif delta["type"] == "thinking_delta":
                block["thinking"] += delta["thinking"]
            else:
                self.json += delta["partial_json"]
        elif event_type == "content_block_stop" and self.content[-1]["type"] == "tool_use":
            self.content[-1]["input"] = json.loads(self.json)


###############################################################################
def last_finish_reason(chunk):
    return next((c["finishReason"] for c in chunk.get("candidates", []) if c.get("finishReason")), None)


###############################################################################
def log_usage(record):
    with LOG_LOCK, open(USAGE_LOG, "a") as log:
        log.write(json.dumps(record) + "\n")
    sys.stderr.write("%s %s %s %s\n" % (record["status"], record.get("finish_reason"), record.get("seconds"),
                                         json.dumps(record.get("usage_metadata"))))


###############################################################################
class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def api_key(self):
        bearer = self.headers.get("authorization", "")
        return bearer[len("Bearer "):] if bearer.startswith("Bearer ") else self.headers["x-api-key"]

    def send_json(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        self.wfile.write(data)

    def send_error_json(self, status, message):
        self.send_json(status, {"type": "error", "error": {"type": ERROR_TYPES.get(status, "api_error"), "message": message}})

    def upstream(self, model, method, body):
        connection = http.client.HTTPSConnection(UPSTREAM_HOST, timeout=UPSTREAM_TIMEOUT_SECONDS)
        connection.request("POST", UPSTREAM_PREFIX + model + ":" + method, body=json.dumps(body),
                           headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key()})
        return connection.getresponse()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        path = self.path.split("?")[0]
        try:
            request = gemini_request(body)
        except (KeyError, ValueError) as error:
            self.send_error_json(400, "gemini_proxy could not translate the request: %r" % error)
            return
        if path == "/v1/messages/count_tokens":
            self.count_tokens(body["model"], request)
        elif path == "/v1/messages" and body.get("stream"):
            self.stream(body, request)
        elif path == "/v1/messages":
            self.generate(body, request)
        else:
            self.send_error_json(404, "gemini_proxy does not serve %s" % path)

    def do_GET(self):
        self.send_error_json(404, "gemini_proxy does not serve %s" % self.path)

    def count_tokens(self, model, request):
        request["model"] = "models/" + model
        request.pop("generationConfig", None)
        response = self.upstream(model, "countTokens", {"generateContentRequest": request})
        data = response.read()
        if response.status != 200:
            self.send_error_json(response.status, data.decode(errors="replace"))
            return
        self.send_json(200, {"input_tokens": json.loads(data)["totalTokens"]})

    def generate(self, body, request):
        started = time.time()
        response = self.upstream(body["model"], "generateContent", request)
        data = response.read()
        record = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "model": body["model"], "stream": False,
                  "generation_config": request.get("generationConfig"), "status": response.status}
        if response.status != 200:
            record["error"] = data.decode(errors="replace")[:2000]
            log_usage(record)
            self.send_error_json(response.status, record["error"])
            return
        chunk = json.loads(data)
        collector = Collector()
        translator = Translator(collector)
        translator.chunk(chunk)
        translator.stop()
        finish_reason = last_finish_reason(chunk)
        metadata = chunk.get("usageMetadata", {})
        record.update({"response_id": chunk.get("responseId"), "model_version": chunk.get("modelVersion"),
                       "finish_reason": finish_reason, "usage_metadata": metadata, "tool_calls": translator.tool_calls,
                       "orphan_signatures": translator.orphan_signatures, "seconds": round(time.time() - started, 1)})
        log_usage(record)
        self.send_json(200, {"id": "msg_" + uuid.uuid4().hex, "type": "message", "role": "assistant",
                             "model": chunk.get("modelVersion", body["model"]), "content": collector.content,
                             "stop_reason": translator.stop_reason(finish_reason), "stop_sequence": None,
                             "usage": anthropic_usage(metadata)})

    def stream(self, body, request):
        started = time.time()
        record = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "model": body["model"], "stream": True,
                  "generation_config": request.get("generationConfig")}
        response = self.upstream(body["model"], "streamGenerateContent?alt=sse", request)
        record["status"] = response.status
        if response.status != 200:
            record["error"] = response.read().decode(errors="replace")[:2000]
            log_usage(record)
            self.send_error_json(response.status, record["error"])
            return
        events = queue.Queue()
        threading.Thread(target=pump, args=(response, events), daemon=True).start()

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

        def emit(event_type, data):
            self.wfile.write(("event: %s\ndata: %s\n\n" % (event_type, json.dumps(data))).encode())
            self.wfile.flush()

        message_id = "msg_" + uuid.uuid4().hex
        emit("message_start", {"type": "message_start", "message": {
            "id": message_id, "type": "message", "role": "assistant", "model": body["model"], "content": [],
            "stop_reason": None, "stop_sequence": None, "usage": anthropic_usage({})}})
        translator = Translator(emit)
        chunk = {}
        while True:
            try:
                kind, payload = events.get(timeout=PING_SECONDS)
            except queue.Empty:
                emit("ping", {"type": "ping"})
                continue
            if kind == "chunk":
                chunk = payload
                record["response_id"] = chunk.get("responseId", record.get("response_id"))
                record["model_version"] = chunk.get("modelVersion", record.get("model_version"))
                record["usage_metadata"] = chunk.get("usageMetadata", record.get("usage_metadata"))
                record["finish_reason"] = last_finish_reason(chunk) or record.get("finish_reason")
                try:
                    translator.chunk(chunk)
                    continue
                except ValueError as error:
                    kind, payload = "error", "gemini_proxy could not translate the response: %r" % error
            translator.stop()
            record.update({"message_id": message_id, "tool_calls": translator.tool_calls,
                           "orphan_signatures": translator.orphan_signatures,
                           "seconds": round(time.time() - started, 1)})
            if kind == "error":
                record["error"] = payload
                log_usage(record)
                emit("error", {"type": "error", "error": {"type": "api_error", "message": payload}})
                return
            log_usage(record)
            emit("message_delta", {"type": "message_delta",
                                   "delta": {"stop_reason": translator.stop_reason(record.get("finish_reason")),
                                             "stop_sequence": None},
                                   "usage": anthropic_usage(record.get("usage_metadata") or {})})
            emit("message_stop", {"type": "message_stop"})
            return

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s %s\n" % (time.strftime("%H:%M:%S"), self.command, self.path))


###############################################################################
def pump(response, events):
    """Reads Gemini's SSE stream on its own thread so the handler can ping Claude Code while Gemini is silent."""
    try:
        data = []
        for line in response:
            line = line.rstrip(b"\r\n")
            if line.startswith(b"data:"):
                data.append(line[5:].strip())
            elif not line and data:
                events.put(("chunk", json.loads(b"".join(data))))
                data = []
        if data:
            events.put(("chunk", json.loads(b"".join(data))))
        events.put(("end", None))
    except Exception as error:
        events.put(("error", "gemini_proxy upstream stream failed: %r" % error))


###############################################################################
def main():
    global USAGE_LOG
    port = int(sys.argv[1])
    USAGE_LOG = sys.argv[2]
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
