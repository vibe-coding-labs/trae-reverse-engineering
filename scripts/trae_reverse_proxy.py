#!/usr/bin/env python3
"""
Trae AI 反向代理服务器（直接可用版）

不需要 refresh_token，不需要 Trae 账号。
直接通过 client_connect 模式调供应商 API。

用法:
    export DEEPSEEK_API_KEY='sk-your-key'
    python3 scripts/trae_reverse_proxy.py --port 8080

    # 然后在任何 OpenAI 客户端配置:
    # API地址: http://服务器IP:8080/v1
    # API Key: 任意值
"""

import argparse
import json
import os
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

# 供应商配置
PROVIDERS = {
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "chat_endpoint": "/v1/chat/completions",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "anthropic": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com",
        "chat_endpoint": "/v1/messages",
        "models": [],
    },
}


class ProxyHandler(BaseHTTPRequestHandler):
    def _get_provider_for_model(self, model: str) -> tuple:
        """根据模型名选择供应商。"""
        if model.startswith("deepseek") or model in PROVIDERS["deepseek"]["models"]:
            return "deepseek", PROVIDERS["deepseek"]
        if model.startswith("claude") or model.startswith("anthropic"):
            return "anthropic", PROVIDERS["anthropic"]
        # 默认用 deepseek
        return "deepseek", PROVIDERS["deepseek"]

    def _call_deepseek(self, body: dict) -> dict:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            return {"error": "DEEPSEEK_API_KEY not set"}

        url = f"{PROVIDERS['deepseek']['base_url']}{PROVIDERS['deepseek']['chat_endpoint']}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": body.get("model", "deepseek-chat"),
            "messages": body.get("messages", []),
            "max_tokens": body.get("max_tokens", 4096),
            "temperature": body.get("temperature", 0.7),
            "stream": body.get("stream", False),
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=300, stream=payload["stream"])
        return resp

    def _openai_to_deepseek_response(self, resp: requests.Response) -> dict:
        data = resp.json()
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": data.get("model", "deepseek-chat"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": data.get("usage", {}),
        }

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health" or self.path == "/":
            self.send_json(200, {"status": "ok", "service": "trae-reverse-proxy"})
            return
        if self.path == "/v1/models":
            models = []
            for pid, cfg in PROVIDERS.items():
                key = os.environ.get(cfg["api_key_env"], "")
                if key:
                    for m in cfg.get("models", []):
                        models.append({"id": m, "object": "model"})
                    models.append({"id": f"{pid}-*", "object": "model"})
            self.send_json(200, {"object": "list", "data": models})
            return
        self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_json(404, {"error": "use POST /v1/chat/completions"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception as e:
            self.send_json(400, {"error": f"invalid json: {e}"})
            return

        model = body.get("model", "deepseek-chat")
        stream = body.get("stream", False)
        provider_name, _ = self._get_provider_for_model(model)

        if provider_name == "deepseek":
            resp = self._call_deepseek(body)
            if resp.status_code != 200:
                self.send_json(502, {"error": f"upstream: {resp.status_code}", "detail": resp.text[:500]})
                return
            if stream:
                self.send_stream(200, resp.iter_lines())
            else:
                result = self._openai_to_deepseek_response(resp)
                self.send_json(200, result)
        else:
            self.send_json(501, {"error": f"provider {provider_name} not yet implemented"})

    def send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def send_stream(self, status: int, lines):
        self.send_response(status)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        for line in lines:
            if line:
                d = json.loads(line.decode())
                chunk = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": d.get("model", "deepseek-chat"),
                    "choices": [{"index": 0, "delta": {"content": d.get("choices", [{}])[0].get("delta", {}).get("content", "")}, "finish_reason": None}],
                }
                self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")

    def log_message(self, fmt, *args):
        print(f"[{self.command} {self.path}] {args[0]}" if args else f"[{self.command} {self.path}]")


def main():
    parser = argparse.ArgumentParser(description="Trae AI 反向代理")
    parser.add_argument("--port", type=int, default=8080, help="监听端口")
    parser.add_argument("--listen", default="0.0.0.0", help="监听地址")
    args = parser.parse_args()

    # 检查 API Key
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("⚠️ DEEPSEEK_API_KEY 未设置，代理将无法正常工作")
        print("   export DEEPSEEK_API_KEY='sk-your-key'")
        print()

    server = HTTPServer((args.listen, args.port), ProxyHandler)
    print(f"Trae AI 反向代理已启动")
    print(f"OpenAI 兼容 API: http://{args.listen}:{args.port}/v1")
    print(f"健康检查:        http://{args.listen}:{args.port}/health")
    print(f"模型列表:        http://{args.listen}:{args.port}/v1/models")
    print()
    print("任何 OpenAI 客户端配置:")
    print(f"  API URL: http://{args.listen}:{args.port}/v1")
    print(f"  API Key: 任意值")
    print()
    print("支持的模型: deepseek-chat, deepseek-reasoner")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止")
        server.server_close()


if __name__ == "__main__":
    main()
