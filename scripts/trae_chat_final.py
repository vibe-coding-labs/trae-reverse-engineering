#!/usr/bin/env python3
"""
Trae AI Chat Client — 最终版

直接通过 agents/runs 调用 chat API（已验证 SSE 流格式正确）。
需要设置 TRAE_REFRESH_TOKEN 环境变量。

用法:
    export TRAE_REFRESH_TOKEN='your_refresh_token'
    export https_proxy=http://127.0.0.1:7890   # 如果在中国需要代理

    # 聊天（自动选模型）
    python3 scripts/trae_chat_client.py --action chat --message "你好"

    # 启动 OpenAI 兼容代理
    python3 scripts/trae_chat_client.py --action serve --port 8080
"""

import argparse, hashlib, json, os, sys, time, uuid
from typing import Optional, Dict, Any
import requests

AUTH_CLIENT_ID = "ono9krqynydwx5"
TOKEN_STORE = os.path.expanduser("~/.trae/tokens.json")

# SG region endpoints (your account's region)
TOKEN_HOST = "https://api-sg-central.trae.ai"
CHAT_HOST = "https://coresg-normal.trae.ai"

def exchange_token(refresh_token: str) -> Dict[str, Any]:
    r = requests.post(f"{TOKEN_HOST}/cloudide/api/v3/trae/oauth/ExchangeToken",
        json={"ClientID": AUTH_CLIENT_ID, "RefreshToken": refresh_token, "ClientSecret": "-", "UserID": ""},
        headers={"Content-Type": "application/json"},
        timeout=10)
    r.raise_for_status()
    data = r.json()["Result"]
    return {"access_token": data["Token"], "refresh_token": data.get("RefreshToken", refresh_token),
            "expires_at": time.time() + 3600 * 24}

def get_token() -> str:
    rt = os.environ.get("TRAE_REFRESH_TOKEN")
    token = os.environ.get("TRAE_ACCESS_TOKEN")
    if token: return token
    if os.path.exists(TOKEN_STORE):
        with open(TOKEN_STORE) as f:
            stored = json.load(f)
        if stored.get("access_token") and time.time() < stored.get("_expires_at", 0) - 60:
            return stored["access_token"]
        rt = rt or stored.get("refresh_token")
    if rt:
        result = exchange_token(rt)
        result["_expires_at"] = time.time() + 3600 * 24
        os.makedirs(os.path.dirname(TOKEN_STORE), exist_ok=True)
        with open(TOKEN_STORE, "w") as f:
            json.dump(result, f, indent=2)
        os.chmod(TOKEN_STORE, 0o600)
        return result["access_token"]
    raise RuntimeError("Need TRAE_REFRESH_TOKEN")

def chat(message: str, model: str = "auto", stream: bool = False):
    token = get_token()
    headers = {"x-cloudide-token": token, "x-ide-token": token,
               "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    sid = "s_" + uuid.uuid4().hex[:12]

    r = requests.post(f"{CHAT_HOST}/api/ide/v1/agents/runs",
        json={"session_id": sid, "query": message, "chat_mode": "agent"},
        headers=headers, stream=stream, timeout=120)

    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}"}

    if stream:
        for line in r.iter_lines():
            if line:
                d = line.decode()
                if d.startswith("data: "):
                    yield json.loads(d[6:])
        return

    result = {"events": []}
    for line in r.text.split("\n"):
        if line.startswith("data: "):
            result["events"].append(json.loads(line[6:]))
    return result

def start_proxy(port: int = 8080, listen: str = "0.0.0.0"):
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def _token(self):
            t = os.environ.get("TRAE_ACCESS_TOKEN")
            if t: return t
            if os.path.exists(TOKEN_STORE):
                with open(TOKEN_STORE) as f:
                    s = json.load(f)
                if s.get("access_token") and time.time() < s.get("_expires_at", 0) - 60:
                    return s["access_token"]
            return get_token()

        def _send(self, status, data, ctype="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if ctype == "application/json":
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.end_headers()

        def do_GET(self):
            if self.path in ("/health", "/"):
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "not_found"})

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                self._send(404, {"error": f"use POST /v1/chat/completions"})
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            except:
                self._send(400, {"error": "invalid json"})
                return

            messages = body.get("messages", [])
            query = messages[-1]["content"] if messages else "hello"
            stream = body.get("stream", False)
            token = self._token()
            headers = {"x-cloudide-token": token, "x-ide-token": token,
                       "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            sid = "s_" + uuid.uuid4().hex[:12]

            r = requests.post(f"{CHAT_HOST}/api/ide/v1/agents/runs",
                json={"session_id": sid, "query": query, "chat_mode": "agent"},
                headers=headers, stream=stream, timeout=120)

            if r.status_code != 200 or stream:
                self._send(502, {"error": f"upstream: {r.status_code}"})
                return

            result = {"text": ""}
            for line in r.text.split("\n"):
                if line.startswith("data: "):
                    ev = json.loads(line[6:])
                    if "content" in str(ev):
                        result["text"] += str(ev)

            reply = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion", "created": int(time.time()),
                "model": "trae-ai",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": result["text"]}, "finish_reason": "stop"}],
            }
            self._send(200, reply)

        def log_message(self, *a): pass

    server = HTTPServer((listen, port), Handler)
    print(f"Trae AI Proxy: http://{listen}:{port}/v1/chat/completions")
    server.serve_forever()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True, choices=["chat", "chat-stream", "serve"])
    parser.add_argument("--message", "-m")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--listen", default="0.0.0.0")
    args = parser.parse_args()

    if args.action == "serve":
        start_proxy(args.port, args.listen)
    elif args.action == "chat":
        if not args.message:
            print("[!] need --message"); sys.exit(1)
        result = chat(args.message)
        for ev in result.get("events", []):
            print(json.dumps(ev, ensure_ascii=False))
    elif args.action == "chat-stream":
        if not args.message:
            print("[!] need --message"); sys.exit(1)
        for ev in chat(args.message, stream=True):
            print(json.dumps(ev, ensure_ascii=False))

if __name__ == "__main__":
    main()
