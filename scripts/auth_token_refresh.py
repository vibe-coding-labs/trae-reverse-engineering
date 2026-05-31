#!/usr/bin/env python3
"""
Trae AI Token 自动刷新脚本

监控 token 有效期，在过期前自动刷新。
支持持久化存储、限流处理、错误恢复。

用法:
    python scripts/auth_token_refresh.py --action check
    python scripts/auth_token_refresh.py --action refresh --refresh-token <token> --token-host <host>
    python scripts/auth_token_refresh.py --action auto --token-host <host>
    python scripts/auth_token_refresh.py --action monitor --token-host <host>
"""

import argparse
import json
import os
import sys
import time
from typing import Optional, Dict, Any

import requests

CLIENT_ID = "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8"
TOKEN_STORE_PATH = os.path.expanduser("~/.trae/tokens.json")
TOKEN_STORE_DIR = os.path.dirname(TOKEN_STORE_PATH)

ERROR_CODES = {
    20324: "Token 格式错误",
    20101: "Token 已过期",
    20315: "Token 已吊销",
    20125: "Refresh Token 无效",
    20126: "Refresh Token 已过期",
}


def exchange_token(token_host: str, refresh_token: str) -> Optional[Dict[str, Any]]:
    """刷新 token，支持重试和限流。"""
    url = f"{token_host.rstrip('/')}/cloudide/api/v3/trae/ExchangeToken"
    headers = {
        "Authorization": f"Bearer {refresh_token}",
        "Content-Type": "application/json",
        "x-cloudide-token": refresh_token,
    }
    payload = {"client_id": CLIENT_ID, "grant_type": "refresh_token", "refresh_token": refresh_token}

    for attempt in range(3):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                now = int(time.time())
                result["_expires_at"] = now + result.get("expires_in", 3600)
                result["_refresh_expires_at"] = now + result.get("refresh_expires_in", 86400)
                result["_updated_at"] = now
                return result
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                print(f"[!] 限流，等待 {retry_after}s"); time.sleep(retry_after)
                continue
            if resp.status_code in (401, 403):
                try:
                    err = resp.json()
                    msg = ERROR_CODES.get(err.get("code"), f"未知错误 {err.get('code')}")
                    print(f"[!] 认证失败: {msg}")
                except json.JSONDecodeError:
                    pass
                return {"error": "auth_failed", "status": resp.status_code}
            print(f"[!] 服务器错误: {resp.status_code}")
            if attempt < 2:
                time.sleep(2 ** attempt)
        except requests.Timeout:
            print(f"[!] 超时 ({attempt + 1}/3)")
            if attempt < 2:
                time.sleep(2 ** attempt)
        except requests.ConnectionError:
            print(f"[!] 连接失败 ({attempt + 1}/3)")
            if attempt < 2:
                time.sleep(5)
        except requests.RequestException as e:
            print(f"[!] 请求异常: {e}")
            break
    return {"error": "max_retries_exceeded"}


def load_stored_tokens(path: str = TOKEN_STORE_PATH) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_tokens(tokens: Dict[str, Any], path: str = TOKEN_STORE_PATH):
    os.makedirs(TOKEN_STORE_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(path, 0o600)


def check_token_expiration(tokens: Dict[str, Any], margin_secs: int = 300) -> Dict[str, str]:
    """检查 token 过期状态。"""
    now = int(time.time())
    status = {}
    ea = tokens.get("_expires_at", 0)
    ra = tokens.get("_refresh_expires_at", 0)

    if ea:
        r = ea - now
        status["access_token"] = "expired" if r <= 0 else ("about_to_expire" if r <= margin_secs else "valid")
        status["remaining_secs"] = r
    if ra:
        r = ra - now
        status["refresh_token"] = "expired" if r <= 0 else ("about_to_expire" if r <= 3600 else "valid")
        status["refresh_remaining_secs"] = r
    return status


def monitor_loop(token_host: str, store_path: str = TOKEN_STORE_PATH, interval_secs: int = 300):
    """持续监控 token 状态，自动刷新。"""
    print(f"[*] Token 监控启动 (间隔: {interval_secs}s, 存储: {store_path})")
    while True:
        tokens = load_stored_tokens(store_path)
        if not tokens:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [!] 未找到存储的 token")
            time.sleep(interval_secs)
            continue
        rt = tokens.get("refresh_token")
        if not rt:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [!] 没有 refresh_token")
            time.sleep(interval_secs)
            continue

        status = check_token_expiration(tokens)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        if status.get("refresh_token") == "expired":
            print(f"[{now_str}] [!] Refresh token 已过期，需要重新登录")
        elif status.get("refresh_token") == "about_to_expire":
            print(f"[{now_str}] [!] Refresh token 即将过期 ({status.get('refresh_remaining_secs')}s)")

        if status.get("access_token") in ("expired", "about_to_expire"):
            print(f"[{now_str}] [*] 刷新 token...")
            result = exchange_token(token_host, rt)
            if "error" not in result:
                result["refresh_token"] = result.get("refresh_token", rt)
                save_tokens(result, store_path)
                print(f"[{now_str}] [+] 刷新成功")
            else:
                print(f"[{now_str}] [✗] 刷新失败: {result['error']}")
        else:
            print(f"[{now_str}] [✓] 有效 ({status.get('remaining_secs')}s)")

        time.sleep(interval_secs)


def parse_args():
    parser = argparse.ArgumentParser(description="Trae AI Token 自动刷新")
    parser.add_argument("--action", required=True, choices=["check", "refresh", "auto", "monitor"])
    parser.add_argument("--token-host")
    parser.add_argument("--refresh-token")
    parser.add_argument("--store-path", default=TOKEN_STORE_PATH)
    parser.add_argument("--interval", type=int, default=300)
    return parser.parse_args()


def main():
    args = parse_args()

    if args.action == "check":
        tokens = load_stored_tokens(args.store_path)
        if not tokens:
            print("[!] 未找到存储的 token"); sys.exit(1)
        print(json.dumps(check_token_expiration(tokens), indent=2))

    elif args.action == "refresh":
        if not all([args.token_host, args.refresh_token]):
            print("[!] 需要 --token-host --refresh-token"); sys.exit(1)
        result = exchange_token(args.token_host, args.refresh_token)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "auto":
        if not args.token_host:
            print("[!] 需要 --token-host"); sys.exit(1)
        tokens = load_stored_tokens(args.store_path)
        if not tokens:
            print("[!] 没有存储的 token"); sys.exit(1)
        rt = tokens.get("refresh_token")
        if not rt:
            print("[!] 没有 refresh_token"); sys.exit(1)
        status = check_token_expiration(tokens)
        if status.get("access_token") in ("expired", "about_to_expire"):
            print("[*] 刷新 token...")
            result = exchange_token(args.token_host, rt)
            if "error" not in result:
                result["refresh_token"] = result.get("refresh_token", rt)
                save_tokens(result, args.store_path)
                print("[+] 刷新成功")
            else:
                print(f"[✗] 刷新失败: {result['error']}")
        else:
            print(f"[✓] Token 仍有效")

    elif args.action == "monitor":
        if not args.token_host:
            print("[!] 需要 --token-host"); sys.exit(1)
        try:
            monitor_loop(args.token_host, args.store_path, args.interval)
        except KeyboardInterrupt:
            print("\n[*] 停止")


if __name__ == "__main__":
    main()
