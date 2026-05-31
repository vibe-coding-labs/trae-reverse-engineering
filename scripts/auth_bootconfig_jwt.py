#!/usr/bin/env python3
"""
Trae AI BootConfig & JWT Token Authentication Script

从 BootConfig 发现 tokenHost，获取 JWT access/refresh token，
支持自动刷新和 token 状态检查。

用法:
    python scripts/auth_bootconfig_jwt.py --action get_boot_config
    python scripts/auth_bootconfig_jwt.py --action get_token --region us
    python scripts/auth_bootconfig_jwt.py --action refresh_token --refresh-token <token>
    python scripts/auth_bootconfig_jwt.py --action check_token --access-token <token>

API 端点:
    Boot: https://icube-boot.trae.ai
    Token Exchange: POST {tokenHost}/cloudide/api/v3/trae/ExchangeToken
"""

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from base64 import urlsafe_b64encode
from typing import Optional, Dict, Any

import requests

# === 常量 ====================================================================

BOOT_ENDPOINTS = {
    "us": "https://icube-boot.trae.ai",
    "cn": "https://icube-boot.trae.com.cn",
}

CLIENT_ID = "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8"

# === 工具函数 ================================================================


def gen_uuid() -> str:
    return str(uuid.uuid4())


def now_timestamp() -> int:
    return int(time.time())


def b64_encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def sha256_b64(data: str) -> str:
    return b64_encode(hashlib.sha256(data.encode()).digest())


# === BootConfig ==============================================================


def fetch_boot_config(region: str = "us") -> Dict[str, Any]:
    """从 Boot 端点获取初始配置。"""
    url = BOOT_ENDPOINTS.get(region, BOOT_ENDPOINTS["us"])
    headers = {"User-Agent": "TraeAI/2.3.30128", "Accept": "application/json"}

    print(f"[*] 获取 BootConfig: {url}")
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    config = resp.json()
    print(f"[+] BootConfig 获取成功")
    print(f"    tokenHost: {config.get('tokenHost', 'N/A')}")
    print(f"    token_host: {config.get('token_host', 'N/A')}")

    if "userInfo" in config:
        ui = config["userInfo"]
        print(f"    user_id: {ui.get('user_id', 'N/A')}")
        print(f"    expired_at: {ui.get('expired_at', 'N/A')}")
        print(f"    refresh_expired_at: {ui.get('refresh_expired_at', 'N/A')}")
        print(f"    token_release_at: {ui.get('token_release_at', 'N/A')}")

    return config


# === JWT Token 管理 =========================================================


def exchange_token(
    token_host: str,
    refresh_token: str,
    client_id: str = CLIENT_ID,
) -> Dict[str, Any]:
    """用 refresh_token 换取新的 access_token + refresh_token。"""
    url = f"{token_host.rstrip('/')}/cloudide/api/v3/trae/ExchangeToken"
    headers = {
        "Authorization": f"Bearer {refresh_token}",
        "Content-Type": "application/json",
        "x-cloudide-token": refresh_token,
    }
    payload = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    print(f"[*] 交换 Token: {url}")
    resp = requests.post(url, headers=headers, json=payload, timeout=10)

    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After", "60")
        print(f"[!] 限流，{retry_after} 秒后重试")
        return {"error": "rate_limited", "retry_after": int(retry_after)}

    resp.raise_for_status()
    result = resp.json()
    print(f"[+] Token 交换成功")
    print(f"    access_token: {result.get('access_token', 'N/A')[:20]}...")
    print(f"    refresh_token: {result.get('refresh_token', 'N/A')[:20]}...")
    print(f"    expires_in: {result.get('expires_in', 'N/A')}")
    print(f"    scope: {result.get('scope', 'N/A')}")

    return result


def check_token(access_token: str, token_host: str) -> bool:
    """检查 access_token 是否有效。"""
    url = f"{token_host.rstrip('/')}/cloudide/api/v3/trae/CheckLogin"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def get_user_info(access_token: str, token_host: str) -> Optional[Dict[str, Any]]:
    """获取当前用户信息。"""
    url = f"{token_host.rstrip('/')}/cloudide/api/v3/trae/GetUserInfo"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, timeout=5)
    if resp.status_code != 200:
        print(f"[!] 获取用户信息失败: {resp.status_code}")
        return None
    return resp.json()


def get_third_party_token(access_token: str, token_host: str) -> Optional[Dict[str, Any]]:
    """用 JWT token 换取第三方服务访问 token。"""
    url = f"{token_host.rstrip('/')}/cloudide/api/v3/trae/GetThirdPartyToken"
    headers = {"x-cloudide-token": access_token}
    resp = requests.post(url, headers=headers, timeout=5)
    if resp.status_code != 200:
        print(f"[!] 获取第三方 Token 失败: {resp.status_code}")
        return None
    return resp.json()


# === Token 生命周期管理 ======================================================


class TokenManager:
    """JWT Token 生命周期管理器。"""

    def __init__(self, storage_path: str = "~/.trae/tokens.json"):
        self.storage_path = os.path.expanduser(storage_path)
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def load_tokens(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.storage_path):
            return None
        with open(self.storage_path) as f:
            return json.load(f)

    def save_tokens(self, tokens: Dict[str, Any]):
        with open(self.storage_path, "w") as f:
            json.dump(tokens, f, indent=2)
        os.chmod(self.storage_path, 0o600)
        print(f"[+] Token 已保存到 {self.storage_path}")

    def is_token_expired(self, token_data: Dict[str, Any]) -> bool:
        now = now_timestamp()
        expires_at = token_data.get("expires_at", 0)
        return now >= expires_at

    def is_refresh_expired(self, token_data: Dict[str, Any]) -> bool:
        now = now_timestamp()
        refresh_expires_at = token_data.get("refresh_expires_at", 0)
        return now >= refresh_expires_at

    def auto_refresh(self, token_host: str, token_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.is_refresh_expired(token_data):
            print("[!] Refresh token 已过期，需要重新登录")
            return {"error": "refresh_expired"}
        if self.is_token_expired(token_data):
            print("[*] Access token 即将过期，自动刷新...")
            new_tokens = exchange_token(token_host=token_host, refresh_token=token_data["refresh_token"])
            if "error" not in new_tokens:
                new_tokens["expires_at"] = now_timestamp() + new_tokens.get("expires_in", 3600)
                new_tokens["refresh_expires_at"] = token_data.get("refresh_expires_at", 0)
                self.save_tokens(new_tokens)
            return new_tokens
        return token_data


# === CLI =====================================================================


def parse_args():
    parser = argparse.ArgumentParser(description="Trae AI BootConfig & JWT Token 认证脚本")
    parser.add_argument("--action", required=True, choices=[
        "get_boot_config", "get_token", "refresh_token", "check_token", "get_user_info", "full_flow",
    ], help="执行的操作")
    parser.add_argument("--region", default="us", choices=["us", "cn"])
    parser.add_argument("--refresh-token", help="Refresh token")
    parser.add_argument("--access-token", help="Access token")
    parser.add_argument("--token-host", help="Token host URL (覆盖 BootConfig)")
    parser.add_argument("--store", action="store_true", help="持久化存储 token")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.action == "get_boot_config":
        config = fetch_boot_config(args.region)
        print(f"\n{json.dumps(config, indent=2, ensure_ascii=False)}")
        return

    # All remaining actions need token_host
    config = fetch_boot_config(args.region)
    token_host = args.token_host or config.get("tokenHost") or config.get("token_host")
    if not token_host:
        print("[!] 未找到 tokenHost")
        sys.exit(1)

    if args.action == "get_token":
        if not args.refresh_token:
            print("[!] 需要 --refresh-token")
            sys.exit(1)
        result = exchange_token(token_host, args.refresh_token)
        if args.store and "error" not in result:
            now = now_timestamp()
            result["expires_at"] = now + result.get("expires_in", 3600)
            result["refresh_expires_at"] = now + result.get("refresh_expires_in", 86400)
            TokenManager().save_tokens(result)

    elif args.action == "refresh_token":
        if args.refresh_token:
            result = exchange_token(token_host, args.refresh_token)
        else:
            manager = TokenManager()
            stored = manager.load_tokens()
            if not stored:
                print("[!] 没有存储的 token")
                sys.exit(1)
            result = manager.auto_refresh(token_host, stored)
        if args.store and "error" not in result:
            now = now_timestamp()
            result["expires_at"] = now + result.get("expires_in", 3600)
            result["refresh_expires_at"] = now + result.get("refresh_expires_in", 86400)
            TokenManager().save_tokens(result)

    elif args.action == "check_token":
        if not args.access_token:
            print("[!] 需要 --access-token")
            sys.exit(1)
        valid = check_token(args.access_token, token_host)
        print(f"[{'✓' if valid else '✗'}] Token 状态: {'有效' if valid else '无效'}")

    elif args.action == "get_user_info":
        if not args.access_token:
            print("[!] 需要 --access-token")
            sys.exit(1)
        info = get_user_info(args.access_token, token_host)
        if info:
            print(f"\n{json.dumps(info, indent=2, ensure_ascii=False)}")

    elif args.action == "full_flow":
        print("=" * 60)
        print("Trae AI 完整认证流程")
        print("=" * 60)
        if args.store:
            manager = TokenManager()
            stored = manager.load_tokens()
            if stored and not manager.is_refresh_expired(stored):
                manager.auto_refresh(token_host, stored)
            else:
                print("[!] 没有有效的 token，需要初始认证")
                print("    请通过 OAuth2 先获取 refresh_token")
                sys.exit(1)
        else:
            print("[!] 需要 --store 来管理 token")
            sys.exit(1)


if __name__ == "__main__":
    main()
