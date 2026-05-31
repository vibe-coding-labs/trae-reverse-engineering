#!/usr/bin/env python3
"""
Trae AI Frontier WebSocket 认证脚本

实现 Frontier 协议的 WebSocket 连接、认证握手、心跳维持。

用法:
    python scripts/auth_frontier_ws.py --action connect --frontier-url <url> --token <token>
    python scripts/auth_frontier_ws.py --action hub-login --token <token> --frontier-url <url>
    python scripts/auth_frontier_ws.py --action http-poll --hub-url <url> --frontier-id <id>

依赖: pip install websocket-client (可选)
"""

import argparse
import json
import random
import string
import sys
import time
import uuid
from typing import Optional, Dict, Any

try:
    from websocket import WebSocket
    HAS_WS = True
except ImportError:
    HAS_WS = False


def make_frontier_frame(log_id: str, service: str, payload: Any,
                        payload_encoding: str = "json") -> Dict[str, Any]:
    return {
        "log_id": log_id, "service": service, "payload": payload,
        "payload_encoding": payload_encoding, "payload_type": "protobuf",
    }


def gen_frame_id() -> str:
    return str(uuid.uuid4())


def gen_cli_id() -> str:
    return "cli_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=16))


class FrontierWebSocketClient:
    """Frontier 协议 WebSocket 客户端"""

    def __init__(self, frontier_url: str, token: str, cli_id: str = None,
                 frontier_id: str = None, app_id: str = "trae-ide",
                 product_id: str = "trae", process_id: str = None):
        self.frontier_url = frontier_url
        self.token = token
        self.cli_id = cli_id or gen_cli_id()
        self.frontier_id = frontier_id or str(uuid.uuid4())
        self.app_id = app_id
        self.product_id = product_id
        self.process_id = process_id or str(uuid.uuid4())[:8]
        self.seq_num = 0
        self.ws = None
        self.connected = False

    def _make_ws_url(self) -> str:
        params = (f"frontier_id={self.frontier_id}&app_runtime_type=electron"
                  f"&process_id={self.process_id}&client_timestamp={int(time.time() * 1000)}")
        sep = "&" if "?" in self.frontier_url else "?"
        return f"{self.frontier_url}{sep}{params}"

    def connect(self) -> bool:
        if not HAS_WS:
            print("[!] websocket-client 未安装: pip install websocket-client")
            return False
        url = self._make_ws_url()
        print(f"[*] 连接 Frontier: {url}")
        try:
            ws = WebSocket()
            ws.connect(url, header={"Authorization": f"Bearer {self.token}"}, timeout=30)
            self.ws = ws
            self.connected = True
            resp = ws.recv()
            if resp:
                print(f"[+] 连接成功: {json.dumps(json.loads(resp), indent=2)[:200]}")
            print(f"[+] Frontier 连接建立: {self.frontier_id}")
            return True
        except Exception as e:
            print(f"[✗] 连接失败: {e}")
            self.connected = False
            return False

    def send_message(self, service: str, payload: Any) -> bool:
        if not self.connected or not self.ws:
            print("[!] 未连接")
            return False
        frame = json.dumps(make_frontier_frame(gen_frame_id(), service, payload))
        try:
            self.ws.send(frame)
            self.seq_num += 1
            return True
        except Exception as e:
            print(f"[✗] 发送失败: {e}")
            return False

    def send_auth(self) -> bool:
        return self.send_message("auth_service", {
            "type": "auth", "cli_id": self.cli_id, "frontier_id": self.frontier_id,
            "app_id": self.app_id, "product_id": self.product_id, "token": self.token,
        })

    def send_heartbeat(self) -> bool:
        return self.send_message("heartbeat_service", {"type": "ping"})

    def register_cli(self) -> bool:
        return self.send_message("hub_cli", {
            "cli_id": self.cli_id, "frontier_id": self.frontier_id,
            "app_id": self.app_id, "product_id": self.product_id, "process_id": self.process_id,
        })

    def start_heartbeat_loop(self, interval_secs: int = 30):
        print(f"[*] 心跳循环启动 ({interval_secs}s)")
        while self.connected:
            time.sleep(interval_secs)
            if not self.send_heartbeat():
                print("[!] 心跳失败")
                break

    def disconnect(self):
        self.connected = False
        if self.ws:
            self.ws.close()
            print("[*] 连接已关闭")

    def http_poll(self, hub_url: str) -> Optional[Dict[str, Any]]:
        import requests as req
        url = f"{hub_url.rstrip('/')}/wsmessages/poll"
        params = {"frontier_id": self.frontier_id, "from_down_seq_id": self.seq_num, "limit": 100}
        try:
            resp = req.get(url, params=params, timeout=30)
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            print(f"[!] HTTP 轮询失败: {e}")
            return None

    def http_push(self, hub_url: str, messages: list) -> bool:
        import requests as req
        try:
            resp = req.post(f"{hub_url.rstrip('/')}/wsmessages/push", json=messages, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False


def hub_login(token: str, frontier_url: str, cli_id: str = None) -> Dict[str, Any]:
    import requests as req
    payload = {"cli_id": cli_id or gen_cli_id(), "token": token, "app_id": "trae-ide", "product_id": "trae"}
    url = f"{frontier_url}/hub_login"
    print(f"[*] Hub 登录: {url}")
    resp = req.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    print(f"[+] Hub 登录成功: frontier_id={result.get('frontier_id', 'N/A')}")
    return result


def parse_args():
    parser = argparse.ArgumentParser(description="Frontier WebSocket 认证")
    parser.add_argument("--action", required=True, choices=["connect", "register-cli", "hub-login", "http-poll"])
    parser.add_argument("--frontier-url")
    parser.add_argument("--token")
    parser.add_argument("--cli-id")
    parser.add_argument("--frontier-id")
    parser.add_argument("--hub-url")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.action == "connect":
        if not all([args.frontier_url, args.token]):
            print("[!] 需要 --frontier-url --token"); sys.exit(1)
        client = FrontierWebSocketClient(args.frontier_url, args.token, args.cli_id, args.frontier_id)
        if client.connect():
            client.send_auth()
            print("[*] 心跳循环 (Ctrl+C 退出)")
            try:
                client.start_heartbeat_loop()
            except KeyboardInterrupt:
                client.disconnect()

    elif args.action == "register-cli":
        if not args.token:
            print("[!] 需要 --token"); sys.exit(1)
        result = hub_login(args.token, args.frontier_url or "wss://hub.trae.ai/ws", args.cli_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "hub-login":
        if not all([args.token, args.frontier_url]):
            print("[!] 需要 --token --frontier-url"); sys.exit(1)
        result = hub_login(args.token, args.frontier_url, args.cli_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "http-poll":
        if not all([args.hub_url, args.frontier_id]):
            print("[!] 需要 --hub-url --frontier-id"); sys.exit(1)
        client = FrontierWebSocketClient("", "", frontier_id=args.frontier_id)
        messages = client.http_poll(args.hub_url)
        if messages:
            print(f"[+] 收到 {len(messages)} 条消息")
            print(json.dumps(messages, indent=2, ensure_ascii=False)[:500])


if __name__ == "__main__":
    main()
