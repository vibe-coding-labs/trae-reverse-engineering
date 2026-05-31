#!/usr/bin/env python3
"""
Trae AI Chat Client & Reverse Proxy

用一个简单的 OpenAI 兼容接口调用 Trae 的 AI 能力。
支持直接调用和 HTTP 代理模式。

用法:
    # 先获取 token
    python scripts/trae_chat_client.py --action get-token --region us --refresh-token <rt>

    # 发送一条聊天消息
    python scripts/trae_chat_client.py --action chat --message "你好，用 Python 写一个快排"

    # 流式聊天
    python scripts/trae_chat_client.py --action chat-stream --message "解释一下 Rust 的所有权"

    # 列出可用模型
    python scripts/trae_chat_client.py --action list-models

    # 启动 HTTP 代理服务器 (OpenAI 兼容 API)
    python scripts/trae_chat_client.py --action serve --port 8080

环境变量:
    TRAE_REFRESH_TOKEN     - Refresh token (优先于 --refresh-token)
    TRAE_ACCESS_TOKEN      - 直接设置 access_token（跳过所有 token 获取流程）
    TRAE_TOKEN_HOST        - Token host (默认自动发现)
    TRAE_REGION            - 区域 us/cn (默认 us)
    TRAE_LISTEN            - 代理监听地址 (默认 0.0.0.0)
    TRAE_PORT              - 代理端口 (默认 8080)
    http_proxy/https_proxy - HTTP 代理（例如 http://127.0.0.1:7890）
"""

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from base64 import urlsafe_b64encode
from typing import Optional, Dict, Any, Generator

import requests

# === 常量 ====================================================================

CLIENT_ID = "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8"
AUTH_CLIENT_ID = "ono9krqynydwx5"  # Trae stable client_id from product.json
# 已知的 API 端点（BootConfig 可能不可达，用已知值硬编码）
TOKEN_HOSTS = {
    "us": "https://token.trae.ai",
    "cn": "https://token.trae.com.cn",
    "sg": "https://api-sg-central.trae.ai",
}
AUTH_CLIENT_IDS = {
    "trae": "ono9krqynydwx5",
    "solo": "en1oxy7wnw8j9n",
}
API_ENDPOINTS = {
    "us": {
        "chat": "https://icube-normal.trae.ai",
        "auth": "https://icube-normal.trae.ai",
        "model": "https://mcs-boot.trae.ai",
        "core": "https://core-normal.trae.ai",
    },
    "cn": {
        "chat": "https://icube-normal.trae.com.cn",
        "auth": "https://icube-normal.trae.com.cn",
        "model": "https://mcs-boot.trae.com.cn",
        "core": "https://core-normal.trae.com.cn",
    },
    "sg": {
        "chat": "https://coresg-normal.trae.ai",
        "auth": "https://api-sg-central.trae.ai",
        "model": "https://coresg-normal.trae.ai",
        "core": "https://coresg-normal.trae.ai",
    },
}
TOKEN_STORE_PATH = os.path.expanduser("~/.trae/tokens.json")

# === Token 管理 ==============================================================


def fetch_boot_config(region: str = "us") -> Dict[str, Any]:
    """尝试获取 BootConfig（可能不可达，失败时返回空字典）。"""
    url = f"https://icube-boot.{'trae.ai' if region == 'us' else 'trae.com.cn'}"
    print(f"[*] 尝试获取 BootConfig: {url}")
    try:
        resp = requests.get(url, headers={"User-Agent": "TraeAI/2.3.30128", "Accept": "application/json"}, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException as e:
        print(f"[!] BootConfig 不可达 ({e})，使用默认端点")
    return {}


def exchange_token(token_host: str, refresh_token: str) -> Dict[str, Any]:
    url = f"{token_host.rstrip('/')}/cloudide/api/v3/trae/ExchangeToken"
    headers = {"Authorization": f"Bearer {refresh_token}", "Content-Type": "application/json"}
    payload = {"client_id": CLIENT_ID, "grant_type": "refresh_token", "refresh_token": refresh_token}
    print(f"[*] 交换 Token: {url}")
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 60))
        print(f"[!] 限流，等待 {retry_after}s")
        time.sleep(retry_after)
        return exchange_token(token_host, refresh_token)
    resp.raise_for_status()
    return resp.json()


def get_access_token(region: str, token_host: str = None, refresh_token: str = None) -> str:
    """获取有效的 access_token（自动刷新缓存）。"""
    # 1. 尝试从环境变量
    token = os.environ.get("TRAE_ACCESS_TOKEN")
    if token:
        return token

    # 2. 尝试从存储文件读取
    if os.path.exists(TOKEN_STORE_PATH):
        with open(TOKEN_STORE_PATH) as f:
            stored = json.load(f)
        access = stored.get("access_token")
        expires = stored.get("_expires_at", 0)
        rt = stored.get("refresh_token")
        if access and time.time() < expires - 60:
            return access
        # access 过期但有 refresh_token
        if rt and token_host:
            print("[*] Token 过期，自动刷新...")
            result = exchange_token(token_host, rt)
            if "access_token" in result:
                result["_expires_at"] = time.time() + result.get("expires_in", 3600)
                result["refresh_token"] = result.get("refresh_token", rt)
                os.makedirs(os.path.dirname(TOKEN_STORE_PATH), exist_ok=True)
                with open(TOKEN_STORE_PATH, "w") as f:
                    json.dump(result, f, indent=2)
                os.chmod(TOKEN_STORE_PATH, 0o600)
                return result["access_token"]

    # 3. 用 refresh_token 直接换
    if refresh_token and token_host:
        print("[*] 用 refresh_token 获取 access_token...")
        result = exchange_token(token_host, refresh_token)
        if "access_token" in result:
            result["_expires_at"] = time.time() + result.get("expires_in", 3600)
            result["refresh_token"] = result.get("refresh_token", refresh_token)
            os.makedirs(os.path.dirname(TOKEN_STORE_PATH), exist_ok=True)
            with open(TOKEN_STORE_PATH, "w") as f:
                json.dump(result, f, indent=2)
            os.chmod(TOKEN_STORE_PATH, 0o600)
            return result["access_token"]
            return result["access_token"]

    raise RuntimeError("无法获取 access_token。请设置 TRAE_REFRESH_TOKEN 环境变量或用 --refresh-token 参数。")


def resolve_config(region: str, token_host: str = None) -> tuple:
    """获取配置信息：返回 (token_host, api_endpoints)。"""
    if not token_host:
        boot = fetch_boot_config(region)
        token_host = boot.get("tokenHost") or boot.get("token_host", "")
    if not token_host:
        token_host = TOKEN_HOSTS.get(region, TOKEN_HOSTS["us"])
        print(f"[*] 使用默认 tokenHost: {token_host}")
    apis = API_ENDPOINTS.get(region, API_ENDPOINTS["us"])
    return token_host, apis


# === API 客户端 ==============================================================


def list_models(access_token: str, api_host: str) -> list:
    """获取可用模型列表。"""
    url = f"{api_host}/api/ide/v1/model_list"
    headers = {"x-ide-token": access_token, "x-cloudide-token": access_token, "Content-Type": "application/json"}
    print(f"[*] 获取模型列表: {url}")
    resp = requests.post(url, headers=headers, json={}, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        models = data.get("model_list", data.get("data", []))
        print(f"[+] 找到 {len(models)} 个模型")
        return models
    print(f"[!] 获取失败: {resp.status_code} {resp.text[:200]}")
    return []


def send_chat_message(access_token: str, api_host: str, message: str,
                      model: str = None, stream: bool = False) -> Dict[str, Any]:
    """发送聊天消息到 Trae AI。"""
    url = f"{api_host}/api/ide/v1/chat"
    headers = {
        "x-ide-token": access_token,
        "x-cloudide-token": access_token,
        "Content-Type": "application/json",
    }

    payload = {
        "session_id": str(uuid.uuid4()),
        "message": {
            "content": message,
            "role": "user",
        },
        "stream": stream,
        "model_config": {
            "model_name": model or "claude-3.5-sonnet",
        },
    }

    print(f"[*] 发送消息 (model={model or 'default'}): {url}")
    if stream:
        resp = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                decoded = line.decode("utf-8", errors="replace")
                if decoded.startswith("data: "):
                    yield json.loads(decoded[6:])
    else:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            print(f"[!] API 错误: {resp.status_code} {resp.text[:500]}")
            return {"error": resp.status_code, "detail": resp.text[:500]}
        return resp.json()


def send_llm_raw_chat(access_token: str, api_host: str, messages: list,
                      model: str = "claude-3.5-sonnet", stream: bool = False) -> Dict[str, Any]:
    """
    直接调用 LLM API（绕过 session 管理）。

    这是最干净的方式 — 直接发消息给 LLM，不需要创建 session。
    """
    url = f"{api_host}/api/ide/v2/llm_raw_chat"
    headers = {
        "x-ide-token": access_token,
        "x-cloudide-token": access_token,
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 4096,
        "stream": stream,
        "temperature": 0.7,
    }

    print(f"[*] LLM Raw Chat: model={model}, messages={len(messages)}")
    if stream:
        resp = requests.post(url, headers=headers, json=payload, timeout=300, stream=True)
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                decoded = line.decode("utf-8", errors="replace")
                if decoded.startswith("data: "):
                    yield json.loads(decoded[6:])
    else:
        resp = requests.post(url, headers=headers, json=payload, timeout=300)
        if resp.status_code != 200:
            print(f"[!] LLM API 错误: {resp.status_code}")
            print(f"    {resp.text[:500]}")
            return {"error": resp.status_code, "detail": resp.text[:500]}
        return resp.json()


# === OpenAI 兼容代理服务器 ===================================================


def start_proxy_server(token_host: str, api_host: str, listen: str = "0.0.0.0",
                        port: int = 8080, refresh_token: str = None):
    """
    启动 OpenAI 兼容的 HTTP API 服务器。

    POST /v1/chat/completions
    GET  /v1/models

    这样任何 OpenAI 客户端（比如 ChatGPT-Next-Web, LobeChat 等）
    都可以通过配置自定义 API 地址来使用 Trae 的 AI 能力。
    """
    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
    except ImportError:
        print("[!] 标准库 http.server 不可用")
        raise

    _token_host = token_host
    _refresh_token = refresh_token or os.environ.get("TRAE_REFRESH_TOKEN", "")

    class TraeProxyHandler(BaseHTTPRequestHandler):
        host = api_host
        refresh_token = _refresh_token
        token_host = _token_host

        def _resolve_token(self) -> str:
            """按需解析 access_token。"""
            # 1. 环境变量
            t = os.environ.get("TRAE_ACCESS_TOKEN")
            if t:
                return t
            # 2. 存储文件
            if os.path.exists(TOKEN_STORE_PATH):
                with open(TOKEN_STORE_PATH) as f:
                    stored = json.load(f)
                access = stored.get("access_token")
                expires = stored.get("_expires_at", 0)
                if access and time.time() < expires - 60:
                    return access
                # 尝试刷新
                rt = stored.get("refresh_token") or self.refresh_token
                if rt:
                    print("[*] Token 过期，自动刷新...")
                    result = exchange_token(self.token_host, rt)
                    if "access_token" in result:
                        result["_expires_at"] = time.time() + result.get("expires_in", 3600)
                        result["refresh_token"] = result.get("refresh_token", rt)
                        os.makedirs(os.path.dirname(TOKEN_STORE_PATH), exist_ok=True)
                        with open(TOKEN_STORE_PATH, "w") as f:
                            json.dump(result, f, indent=2)
                        os.chmod(TOKEN_STORE_PATH, 0o600)
                        return result["access_token"]
            # 3. 用 refresh_token 直接换
            if self.refresh_token and self.token_host:
                result = exchange_token(self.token_host, self.refresh_token)
                if "access_token" in result:
                    result["_expires_at"] = time.time() + result.get("expires_in", 3600)
                    result["refresh_token"] = self.refresh_token
                    os.makedirs(os.path.dirname(TOKEN_STORE_PATH), exist_ok=True)
                    with open(TOKEN_STORE_PATH, "w") as f:
                        json.dump(result, f, indent=2)
                    os.chmod(TOKEN_STORE_PATH, 0o600)
                    return result["access_token"]
            raise RuntimeError("无法获取 access_token。设置 TRAE_REFRESH_TOKEN 或 TRAE_ACCESS_TOKEN")

        def _send_json(self, status: int, data: dict):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

        def _send_stream(self, status: int, generator):
            self.send_response(status)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()
            for chunk in generator:
                self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()

        def do_GET(self):
            # Health endpoint - no auth needed
            if self.path in ("/health", "/"):
                self._send_json(200, {"status": "ok", "service": "trae-ai-proxy"})
                return

            try:
                token = self._resolve_token()
            except RuntimeError as e:
                self._send_json(401, {"error": str(e)})
                return
            if self.path == "/v1/models":
                models = list_models(token, self.host)
                data = {
                    "object": "list",
                    "data": [{"id": m.get("model_name", m), "object": "model"} for m in models]
                } if models else {
                    "object": "list",
                    "data": [
                        {"id": "claude-3.5-sonnet", "object": "model"},
                        {"id": "claude-3.5-haiku", "object": "model"},
                        {"id": "gpt-5", "object": "model"},
                        {"id": "deepseek-v3", "object": "model"},
                        {"id": "gemini-3-flash", "object": "model"},
                    ],
                }
                self._send_json(200, data)
            else:
                self._send_json(404, {"error": "not_found"})

        def do_POST(self):
            if self.path == "/v1/chat/completions":
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body = json.loads(self.rfile.read(length))
                except Exception as e:
                    self._send_json(400, {"error": f"invalid_json: {e}"})
                    return

                try:
                    token = self._resolve_token()
                except RuntimeError as e:
                    self._send_json(401, {"error": str(e)})
                    return

                messages = body.get("messages", [])
                model = body.get("model", "claude-3.5-sonnet")
                stream = body.get("stream", False)

                # 调用 llm_raw_chat
                url = f"{self.host}/api/ide/v2/llm_raw_chat"
                headers = {
                    "x-ide-token": token,
                    "x-cloudide-token": token,
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": body.get("max_tokens", 4096),
                    "temperature": body.get("temperature", 0.7),
                    "stream": stream,
                }

                try:
                    resp = requests.post(url, headers=headers, json=payload,
                                         timeout=300, stream=stream)
                    if resp.status_code != 200:
                        self._send_json(502, {"error": f"trae_api_error: {resp.status_code}",
                                              "detail": resp.text[:500]})
                        return

                    if stream:
                        def gen():
                            for line in resp.iter_lines():
                                if line:
                                    d = line.decode("utf-8", errors="replace")
                                    if d.startswith("data: "):
                                        yield json.loads(d[6:])
                        self._send_stream(200, gen())
                    else:
                        result = resp.json()
                        # 转成 OpenAI 格式
                        reply = {
                            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                            "object": "chat.completion",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": result.get("content", result.get("text", "")),
                                },
                                "finish_reason": "stop",
                            }],
                            "usage": result.get("usage", {}),
                        }
                        self._send_json(200, reply)
                except Exception as e:
                    self._send_json(502, {"error": f"upstream_error: {str(e)}"})
            else:
                self._send_json(404, {"error": "not_found. use POST /v1/chat/completions"})

        def log_message(self, fmt, *args):
            print(f"[{self.command} {self.path}] {args[0]}" if args else f"[{self.command} {self.path}]")

    server = HTTPServer((listen, port), TraeProxyHandler)
    print(f"\n{'='*60}")
    print(f"Trae AI 代理已启动")
    print(f"OpenAI 兼容 API: http://{listen}:{port}/v1")
    print(f"模型列表:        http://{listen}:{port}/v1/models")
    print(f"聊天补全:        POST http://{listen}:{port}/v1/chat/completions")
    print(f"{'='*60}")
    print(f"\n任何 OpenAI 客户端配置:")
    print(f"  API URL:  http://{listen}:{port}/v1")
    print(f"  API Key:  trae-ai (任意值)")
    print(f"\n按 Ctrl+C 停止\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] 服务器已停止")
        server.server_close()


# === CLI =====================================================================


def parse_args():
    parser = argparse.ArgumentParser(description="Trae AI Chat Client & Reverse Proxy")
    parser.add_argument("--action", required=True, choices=[
        "get-token", "chat", "chat-stream", "list-models", "serve",
    ])
    parser.add_argument("--region", default=os.environ.get("TRAE_REGION", "us"), choices=["us", "cn"])
    parser.add_argument("--token-host", default=os.environ.get("TRAE_TOKEN_HOST"))
    parser.add_argument("--refresh-token", default=os.environ.get("TRAE_REFRESH_TOKEN"))
    parser.add_argument("--message", "-m", help="聊天消息")
    parser.add_argument("--model", default="claude-3.5-sonnet", help="模型名称")
    parser.add_argument("--port", type=int, default=int(os.environ.get("TRAE_PORT", "8080")))
    parser.add_argument("--listen", default=os.environ.get("TRAE_LISTEN", "0.0.0.0"))
    return parser.parse_args()


def main():
    args = parse_args()

    # 解析配置
    token_host, apis = resolve_config(args.region, args.token_host)
    refresh_token = args.refresh_token or os.environ.get("TRAE_REFRESH_TOKEN")

    if args.action == "get-token":
        if not refresh_token:
            print("[!] 需要 --refresh-token 或设置 TRAE_REFRESH_TOKEN")
            sys.exit(1)
        result = exchange_token(token_host, refresh_token)
        print(f"\naccess_token: {result.get('access_token', '')}")
        print(f"refresh_token: {result.get('refresh_token', '')}")
        print(f"expires_in: {result.get('expires_in', '')}s")
        print(f"scope: {result.get('scope', '')}")
        # 保存
        result["_expires_at"] = time.time() + result.get("expires_in", 3600)
        os.makedirs(os.path.dirname(TOKEN_STORE_PATH), exist_ok=True)
        with open(TOKEN_STORE_PATH, "w") as f:
            json.dump(result, f, indent=2)
        os.chmod(TOKEN_STORE_PATH, 0o600)
        print(f"\nToken 已保存到 {TOKEN_STORE_PATH}")
        return

    if args.action == "serve":
        # Serve 模式：服务器先启动，不要求先有 token
        print(f"[*] 启动代理服务器...")
        start_proxy_server(token_host, apis["chat"], args.listen, args.port, refresh_token)
        return

    # 以下操作需要 access_token
    try:
        access_token = get_access_token(args.region, token_host, refresh_token)
    except RuntimeError as e:
        print(f"[!] {e}")
        sys.exit(1)

    if args.action == "list-models":
        models = list_models(access_token, apis["chat"])
        for m in models[:30]:
            name = m.get("model_name", m.get("id", str(m)[:60]))
            print(f"  - {name}")

    elif args.action == "chat":
        if not args.message:
            print("[!] 需要 --message")
            sys.exit(1)
        result = send_llm_raw_chat(access_token, apis["chat"], [
            {"role": "user", "content": args.message},
        ], model=args.model)
        print(f"\n响应:")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])

    elif args.action == "chat-stream":
        if not args.message:
            print("[!] 需要 --message")
            sys.exit(1)
        print(f"\n[流式响应]\n")
        for chunk in send_llm_raw_chat(access_token, apis["chat"], [
            {"role": "user", "content": args.message},
        ], model=args.model, stream=True):
            print(chunk, end="", flush=True)
        print()

    elif args.action == "serve":
        print(f"[*] 启动代理服务器...")
        # 验证 token 有效
        try:
            models = list_models(access_token, apis["chat"])
            print(f"[+] 验证通过，{len(models)} 个模型可用")
        except Exception as e:
            print(f"[!] 验证失败: {e}")
            print("[!] 代理仍会启动，但可能无法正常工作")
        start_proxy_server(access_token, apis["chat"], args.listen, args.port)


if __name__ == "__main__":
    main()
