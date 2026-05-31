#!/usr/bin/env python3
"""
Trae AI OAuth2 PKCE 认证脚本

支持 Google、GitHub、GitLab 和 Trae 自有 OAuth2 流程。
使用 PKCE (Proof Key for Code Exchange) 增强安全性。

用法:
    python scripts/auth_oauth2_pkce.py --action pkce-gen
    python scripts/auth_oauth2_pkce.py --action authorize --provider google
    python scripts/auth_oauth2_pkce.py --action exchange --code <auth_code> --code-verifier <verifier>
    python scripts/auth_oauth2_pkce.py --action full --provider google --port 8899
"""

import argparse
import hashlib
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
from base64 import urlsafe_b64encode
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any, Tuple

import requests

CLIENT_ID = "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8"
REDIRECT_PORT = 8899
SCOPE = "marscode"

OAUTH_PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
    },
    "gitlab": {
        "authorize_url": "https://gitlab.com/oauth/authorize",
        "token_url": "https://gitlab.com/oauth/token",
    },
    "supabase": {
        "authorize_url": "https://api.supabase.com/v1/oauth/authorize",
        "token_url": "https://api.supabase.com/v1/oauth/token",
    },
    "trae": {
        "authorize_url": None,
        "token_url": None,
    },
}


def generate_code_verifier(length: int = 64) -> str:
    """生成 PKCE code_verifier (43-128 字符，仅含 [A-Za-z0-9-._~])"""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_code_challenge(verifier: str) -> str:
    """生成 PKCE code_challenge = BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))"""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return urlsafe_b64encode(digest).rstrip(b"=").decode()


class CallbackHandler(BaseHTTPRequestHandler):
    """OAuth2 回调处理服务器"""
    auth_code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            CallbackHandler.auth_code = params["code"][0]
            self._respond(200, "认证成功！请关闭此窗口。")
        elif "error" in params:
            self._respond(400, f"认证失败: {params['error'][0]}")
        else:
            self._respond(400, "缺少 authorization code")

    def _respond(self, status: int, body: str):
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        pass


def start_callback_server(port: int) -> Tuple[HTTPServer, threading.Thread]:
    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[*] 回调服务器已启动: http://127.0.0.1:{port}")
    return server, thread


def build_authorize_url(authorize_url: str, client_id: str = CLIENT_ID,
                        redirect_port: int = REDIRECT_PORT, scope: str = SCOPE,
                        code_challenge: Optional[str] = None) -> str:
    params = {
        "response_type": "code", "client_id": client_id,
        "redirect_uri": f"http://127.0.0.1:{redirect_port}", "scope": scope,
    }
    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    return f"{authorize_url}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(token_url: str, code: str, code_verifier: Optional[str] = None,
                            client_id: str = CLIENT_ID, redirect_port: int = REDIRECT_PORT) -> Dict[str, Any]:
    payload = {
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": f"http://127.0.0.1:{redirect_port}", "client_id": client_id,
    }
    if code_verifier:
        payload["code_verifier"] = code_verifier

    print(f"[*] 交换授权码 -> Token: {token_url}")
    resp = requests.post(token_url, data=payload, timeout=10)
    resp.raise_for_status()

    result = resp.json()
    print(f"[+] Token 获取成功")
    print(f"    access_token: {result.get('access_token', 'N/A')[:30]}...")
    print(f"    refresh_token: {result.get('refresh_token', 'N/A')[:30]}...")
    print(f"    expires_in: {result.get('expires_in', 'N/A')}")
    return result


def parse_args():
    parser = argparse.ArgumentParser(description="Trae AI OAuth2 PKCE 认证")
    parser.add_argument("--action", required=True, choices=["authorize", "exchange", "full", "pkce-gen"])
    parser.add_argument("--provider", default="trae", choices=list(OAUTH_PROVIDERS.keys()))
    parser.add_argument("--port", type=int, default=REDIRECT_PORT)
    parser.add_argument("--code", help="Authorization code")
    parser.add_argument("--code-verifier", help="PKCE code_verifier")
    parser.add_argument("--token-host", help="Token host（Trae 自有 OAuth 需要）")
    return parser.parse_args()


def main():
    args = parse_args()
    provider = OAUTH_PROVIDERS[args.provider]

    if args.action == "pkce-gen":
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        print(f"code_verifier:  {verifier}")
        print(f"code_challenge: {challenge}")
        return

    if args.action == "authorize":
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        if args.provider == "trae":
            if not args.token_host:
                print("[!] Trae OAuth 需要 --token-host")
                sys.exit(1)
            auth_url = f"{args.token_host}/oauth/authorize"
        else:
            auth_url = provider["authorize_url"]
        url = build_authorize_url(auth_url, code_challenge=challenge)
        print(f"\n[*] PKCE code_verifier: {verifier}")
        print(f"[*] 打开以下 URL 进行授权:\n\n    {url}\n")
        print(f"[*] 授权后: --action exchange --code <code> --code-verifier {verifier}")
        return

    if args.action == "exchange":
        if not args.code:
            print("[!] 需要 --code")
            sys.exit(1)
        if args.provider == "trae":
            if not args.token_host:
                print("[!] Trae OAuth 需要 --token-host")
                sys.exit(1)
            token_url = f"{args.token_host}/oauth/token"
        else:
            token_url = provider["token_url"]
        result = exchange_code_for_token(token_url=token_url, code=args.code, code_verifier=args.code_verifier)
        print(f"\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        return

    if args.action == "full":
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        server, thread = start_callback_server(args.port)

        if args.provider == "trae":
            if not args.token_host:
                print("[!] Trae OAuth 需要 --token-host")
                sys.exit(1)
            auth_url = f"{args.token_host}/oauth/authorize"
            token_url = f"{args.token_host}/oauth/token"
        else:
            auth_url = provider["authorize_url"]
            token_url = provider["token_url"]

        url = build_authorize_url(auth_url, code_challenge=challenge, redirect_port=args.port)
        print(f"\n[*] 浏览器打开:\n    {url}\n")
        print("[*] 等待回调 (5分钟超时)...")

        timeout = 300
        start = time.time()
        while CallbackHandler.auth_code is None:
            if time.time() - start > timeout:
                print("[!] 等待超时")
                server.shutdown()
                sys.exit(1)
            time.sleep(0.1)

        code = CallbackHandler.auth_code
        server.shutdown()
        print(f"[+] 获取到授权码: {code[:20]}...")

        result = exchange_code_for_token(token_url=token_url, code=code, code_verifier=verifier, redirect_port=args.port)
        print(f"\n{json.dumps(result, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
