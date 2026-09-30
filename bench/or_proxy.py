import http.client
import http.server
import json
import sys

UPSTREAM_HOST = "openrouter.ai"
UPSTREAM_PREFIX = "/api"
PROVIDERS_BY_VENDOR = {
    "z-ai": ["z-ai"],
    "deepseek": ["fireworks", "together"],
    "moonshotai": ["moonshotai"],
    "minimax": ["minimax"],
    "qwen": ["alibaba"],
}
HOP_HEADERS = {"host", "content-length", "connection", "transfer-encoding", "accept-encoding"}


###############################################################################
def pin_provider(body):
    payload = json.loads(body)
    vendor = payload["model"].split("/")[0]
    payload["provider"] = {"order": PROVIDERS_BY_VENDOR[vendor], "allow_fallbacks": False}
    return json.dumps(payload).encode()


###############################################################################
class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def forward(self):
        length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(length) if length else None
        if body and self.path.startswith("/v1/messages") and not self.path.startswith("/v1/messages/count_tokens"):
            body = pin_provider(body)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_HEADERS}
        if body is not None:
            headers["Content-Length"] = str(len(body))
        upstream = http.client.HTTPSConnection(UPSTREAM_HOST, timeout=600)
        upstream.request(self.command, UPSTREAM_PREFIX + self.path, body=body, headers=headers)
        resp = upstream.getresponse()
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() not in HOP_HEADERS:
                self.send_header(k, v)
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        while True:
            chunk = resp.read1(65536)
            if not chunk:
                break
            self.wfile.write(chunk)
            self.wfile.flush()
        upstream.close()

    def do_POST(self):
        self.forward()

    def do_GET(self):
        self.forward()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path))


###############################################################################
def main():
    port = int(sys.argv[1])
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
