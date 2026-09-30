import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import time
import uuid

REAL_HOME = pathlib.Path.home()
PACBAKE = REAL_HOME / ".pacbake"
SHARED = pathlib.Path("/Users/Shared/pacbake")
CELLS_ROOT = SHARED / "cells"
GROK_CELLS_ROOT = SHARED / "grok-cells"
TMP_ROOT = SHARED / "tmp"
GROK_HOME = SHARED / "homes" / "grok"
GROK_BIN = SHARED / "bin" / "grok"
GROK_SEATBELT = SHARED / "homes" / "grok-seatbelt.sb"
DEAD_PROXY = "http://127.0.0.1:9"
GROK_API_HOSTS = ".grok.com,grok.com,.x.ai,x.ai"
RUNS_ROOT = PACBAKE / "runs"
HARNESS_CONFIG = PACBAKE / "harness-config"
PATH = f"/opt/homebrew/bin:{REAL_HOME}/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
TIMEOUT_SECONDS = 3600
GROK_COMPAT_VENDORS = ["CLAUDE", "CODEX", "CURSOR"]
GROK_COMPAT_SURFACES = ["SKILLS", "RULES", "AGENTS", "MCPS", "HOOKS", "SESSIONS"]


###############################################################################
def cell_tmp(cell):
    tmp = (cell.parent / f"{cell.name}.tmp") if cell.parent == GROK_CELLS_ROOT else (TMP_ROOT / cell.name)
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp


###############################################################################
def base_env(home, cell):
    return {
        "HOME": str(home),
        "PATH": PATH,
        "USER": os.environ["USER"],
        "LOGNAME": os.environ["USER"],
        "TMPDIR": str(cell_tmp(cell)),
        "LANG": "en_US.UTF-8",
        "SHELL": "/bin/zsh",
    }


###############################################################################
def make_cell(prompt_file, root):
    cell = root / str(uuid.uuid4())
    cell.mkdir(parents=True)
    shutil.copy(prompt_file, cell / "PROMPT.md")
    git = ["git", "-c", "user.name=pacbake", "-c", "user.email=pacbake@local"]
    subprocess.run(["git", "init", "-q"], cwd=cell, check=True)
    subprocess.run(git + ["add", "PROMPT.md"], cwd=cell, check=True)
    subprocess.run(git + ["commit", "-qm", "init"], cwd=cell, check=True)
    return cell


###############################################################################
def claude_settings(cell, run_dir, deny_home):
    cell_glob = f"/{cell}/**"
    settings = {
        "permissions": {
            "allow": [f"Read({cell_glob})", f"Edit({cell_glob})", f"Write({cell_glob})",
                      "Glob", "Grep", "Bash", "TodoWrite", "Task"],
            "deny": ["WebFetch", "WebSearch"],
        },
        "sandbox": {
            "enabled": True,
            "autoAllowBashIfSandboxed": True,
            "allowUnsandboxedCommands": False,
            "filesystem": {
                "denyRead": [f"{deny_home}/", "/Users/Shared/pacbake/"],
                "allowRead": [str(cell), str(cell_tmp(cell))],
            },
            "network": {"allowedDomains": []},
        },
    }
    path = run_dir / "claude-settings.json"
    path.write_text(json.dumps(settings, indent=2))
    return path


###############################################################################
def claude_flags(model, settings_path):
    return ["claude", "-p", "--model", model, "--effort", "high",
            "--settings", str(settings_path), "--permission-mode", "dontAsk",
            "--disallowedTools", "WebFetch", "WebSearch", "--strict-mcp-config",
            "--no-session-persistence", "--output-format", "stream-json", "--verbose"]


###############################################################################
def unlock_keychain():
    script = ('source ~/dev/buildtail/lib/keychain.sh; pw="$(buildtail_keychain_password_from_ssm)"; '
              'security unlock-keychain -p "$pw" "$BUILDTAIL_KEYCHAIN_PATH"')
    subprocess.run(["bash", "-c", script], check=True, env={**os.environ, "PATH": PATH})


###############################################################################
def build_claude(model, cell, run_dir):
    unlock_keychain()
    env = base_env(REAL_HOME, cell)
    env["DISABLE_AUTOUPDATER"] = "1"
    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    env["CLAUDE_CODE_TMPDIR"] = str(cell_tmp(cell))
    settings = claude_settings(cell, run_dir, REAL_HOME)
    cmd = claude_flags(model, settings) + ["--safe-mode", "--setting-sources", "project,local"]
    return cmd, env, True


###############################################################################
def build_claude_openrouter(model, cell, run_dir):
    fake_home = pathlib.Path("/Users/Shared/pacbake/fakehome-claude-or")
    fake_home.mkdir(parents=True, exist_ok=True)
    env = base_env(fake_home, cell)
    key = (PACBAKE / "secrets" / "openrouter_api_key").read_text().strip()
    env["CLAUDE_CONFIG_DIR"] = str(fake_home / ".claude")
    env["ANTHROPIC_BASE_URL"] = os.environ.get("PACBAKE_OR_BASE_URL", "https://openrouter.ai/api")
    env["ANTHROPIC_AUTH_TOKEN"] = key
    env["ANTHROPIC_API_KEY"] = ""
    env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
    for slot in ["ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
                 "ANTHROPIC_DEFAULT_HAIKU_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL"]:
        env[slot] = model
    env["DISABLE_AUTOUPDATER"] = "1"
    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    env["CLAUDE_CODE_TMPDIR"] = str(cell_tmp(cell))
    settings = claude_settings(cell, run_dir, REAL_HOME)
    return claude_flags(model, settings), env, True


###############################################################################
def build_codex(model, cell, run_dir):
    env = base_env(REAL_HOME, cell)
    env["CODEX_HOME"] = str(PACBAKE / "homes" / "codex-chatgpt")
    cmd = ["codex", "exec", "--cd", str(cell), "-m", model,
           "-c", 'model_reasoning_effort="high"', "--ephemeral", "--json",
           "-o", str(run_dir / "final_message.md"), "-"]
    return cmd, env, True


###############################################################################
def openai_api_key():
    import boto3
    ssm = boto3.Session(profile_name="jclegg", region_name="us-east-1").client("ssm")
    return ssm.get_parameter(Name="/somewhere/openai-api-key", WithDecryption=True)["Parameter"]["Value"].strip()


###############################################################################
def build_codex_apikey(model, cell, run_dir):
    """API-key auth, so the published rate card prices every response the run made."""
    env = base_env(REAL_HOME, cell)
    env["CODEX_HOME"] = str(PACBAKE / "homes" / "codex-apikey")
    env["OPENAI_API_KEY"] = openai_api_key()
    cmd = ["codex", "exec", "--cd", str(cell), "-m", model,
           "-c", 'model_reasoning_effort="high"', "--ephemeral", "--json",
           "-o", str(run_dir / "final_message.md"), "-"]
    return cmd, env, True


###############################################################################
def build_grok(model, cell, run_dir):
    fake_home = SHARED / "fakehome-grok"
    fake_home.mkdir(parents=True, exist_ok=True)
    env = base_env(fake_home, cell)
    env["PATH"] = f"{GROK_BIN.parent}:{PATH}"
    env["GROK_HOME"] = str(GROK_HOME)
    env["GROK_DISABLE_AUTOUPDATER"] = "1"
    env["GROK_MEMORY"] = "0"
    for vendor in GROK_COMPAT_VENDORS:
        for surface in GROK_COMPAT_SURFACES:
            env[f"GROK_{vendor}_{surface}_ENABLED"] = "0"
    for var in ["HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy", "all_proxy"]:
        env[var] = DEAD_PROXY
    env["NO_PROXY"] = GROK_API_HOSTS
    env["no_proxy"] = GROK_API_HOSTS
    cmd = ["sandbox-exec", "-f", str(GROK_SEATBELT), str(GROK_BIN),
           "--prompt-file", str(cell / "PROMPT.md"), "--cwd", str(cell),
           "-m", model, "--effort", "high", "--always-approve",
           "--disable-web-search", "--disallowed-tools", "web_search,web_fetch",
           "--max-turns", "400", "-s", str(uuid.uuid4()), "--output-format", "streaming-json"]
    return cmd, env, False


BUILDERS = {
    "claude-code": build_claude,
    "claude-code-openrouter": build_claude_openrouter,
    "codex-chatgpt": build_codex,
    "codex-apikey": build_codex_apikey,
    "grok-build": build_grok,
}


###############################################################################
def run_harness(cmd, env, stdin_prompt, cell, run_dir):
    transcript = open(run_dir / "transcript.jsonl", "wb")
    stderr = open(run_dir / "stderr.log", "wb")
    stdin = open(cell / "PROMPT.md", "rb") if stdin_prompt else subprocess.DEVNULL
    proc = subprocess.Popen(cmd, cwd=cell, env=env, stdin=stdin, stdout=transcript, stderr=stderr,
                            start_new_session=True)
    status = "done"
    try:
        proc.wait(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, 9)
        proc.wait()
        status = "timeout"
    return proc.returncode, status


###############################################################################
def harvest(cell, run_dir):
    shutil.copytree(cell, run_dir / "workspace", ignore=shutil.ignore_patterns(".git"))
    diff = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=cell,
                          capture_output=True, text=True).stdout
    (run_dir / "git_status.txt").write_text(diff)
    html = cell / "pacman.html"
    if not html.exists():
        return {"exists": False}
    shutil.copy(html, run_dir / "pacman.html")
    data = html.read_bytes()
    return {"exists": True, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


###############################################################################
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("harness", choices=sorted(BUILDERS))
    parser.add_argument("model")
    parser.add_argument("run_name")
    parser.add_argument("--prompt", default=str(pathlib.Path(__file__).parent / "prompts" / "pacman.md"))
    args = parser.parse_args()

    run_dir = RUNS_ROOT / args.run_name
    run_dir.mkdir(parents=True, exist_ok=False)
    cell = make_cell(args.prompt, GROK_CELLS_ROOT if args.harness == "grok-build" else CELLS_ROOT)
    cmd, env, stdin_prompt = BUILDERS[args.harness](args.model, cell, run_dir)
    (run_dir / "command.json").write_text(json.dumps(cmd, indent=2))

    started = time.time()
    exit_code, status = run_harness(cmd, env, stdin_prompt, cell, run_dir)
    ended = time.time()
    html = harvest(cell, run_dir)
    if status == "done" and not html["exists"]:
        status = "no_file"

    meta = {
        "run_name": args.run_name,
        "cell_uuid": cell.name,
        "harness": args.harness,
        "model_requested": args.model,
        "effort": "high",
        "prompt_sha256": hashlib.sha256(pathlib.Path(args.prompt).read_bytes()).hexdigest(),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(started)),
        "wall_seconds": round(ended - started, 1),
        "exit_code": exit_code,
        "status": status,
        "pacman_html": html,
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    shutil.rmtree(cell)
    shutil.rmtree(cell_tmp(cell))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
