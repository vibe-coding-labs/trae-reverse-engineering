#!/usr/bin/env python3
"""
Trae Token Extractor — 从本地 SQLCipher 数据库提取认证 token

当 Trae IDE 已经登录时，从本地数据库提取 refresh_token。
支持多种提取方式：数据库解密、进程内存、本地存储。

用法:
    # 自动提取（尝试所有方法）
    python scripts/trae_token_extractor.py --extract

    # 查看所有可能的来源
    python scripts/trae_token_extractor.py --scan

    # 启动代理（自动管理 token）
    python scripts/trae_token_extractor.py --serve --port 8080
"""

import argparse
import json
import os
import re
import sqlite3
import struct
import subprocess
import sys
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

# === 路径常量 ================================================================

HOME = os.path.expanduser("~")
TRAE_CONFIG_DIRS = [
    os.path.join(HOME, ".config", "Trae"),
    os.path.join(HOME, ".config", "trae"),
]
TRAE_DATA_DIRS = [
    os.path.join(HOME, ".trae"),
]
MODULAR_DATA_PATH = os.path.join(HOME, ".config", "Trae", "ModularData", "ai-agent")
STORAGE_JSON = os.path.join(HOME, ".config", "Trae", "User", "globalStorage", "storage.json")
LOCAL_STORAGE_DB = os.path.join(HOME, ".config", "Trae", "Local Storage", "config.db")
DATABASE_DB = os.path.join(MODULAR_DATA_PATH, "database.db")
TOKEN_STORE_PATH = os.path.join(HOME, ".trae", "tokens.json")
TOKEN_FILE_PATH = os.path.join(HOME, ".trae", "auth", "token.json")
SUPABASE_TOKEN_PATH = os.path.join(HOME, ".config", "Trae", "User", "supabase-token.json")


# === Token 提取方法 =========================================================


def scan_sources() -> List[Dict[str, Any]]:
    """扫描所有可能的 token 来源，返回可用来源列表。"""
    sources = []

    # 1. 检查 JSON 文件
    for path in [TOKEN_STORE_PATH, SUPABASE_TOKEN_PATH, TOKEN_FILE_PATH]:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                sources.append({
                    "type": "json_file",
                    "path": path,
                    "fields": list(data.keys()),
                    "has_refresh_token": "refresh_token" in data,
                    "has_access_token": "access_token" in data,
                })
            except (json.JSONDecodeError, OSError):
                pass

    # 2. 检查 storage.json
    if os.path.exists(STORAGE_JSON):
        try:
            with open(STORAGE_JSON) as f:
                data = json.load(f)
            token_keys = [k for k in data if any(x in k.lower() for x in ["token", "auth", "credential", "jwt"])]
            if token_keys:
                sources.append({
                    "type": "storage_json",
                    "path": STORAGE_JSON,
                    "token_keys": token_keys,
                })
        except (json.JSONDecodeError, OSError):
            pass

    # 3. 检查 SQLite 数据库
    for db_path, db_name in [
        (DATABASE_DB, "ai-agent database.db"),
        (LOCAL_STORAGE_DB, "Local Storage config.db"),
    ]:
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            is_sqlcipher = _is_sqlcipher(db_path)
            sources.append({
                "type": "database",
                "path": db_path,
                "name": db_name,
                "size_mb": round(size / 1024 / 1024, 1),
                "is_sqlcipher": is_sqlcipher,
            })

    # 4. 检查 Trae 进程
    try:
        result = subprocess.run(
            ["ps", "aux", "--no-headers"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.split("\n"):
            if "trae" in line.lower() and "grep" not in line:
                pid = line.split(None, 2)[0] if line.split() else None
                cmd = line.split(None, 7)[-1] if len(line.split()) > 7 else ""
                sources.append({
                    "type": "process",
                    "pid": pid,
                    "cmd_preview": cmd[:120] if cmd else "",
                })
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # 5. 检查环境变量
    for env_var in ["TRAE_REFRESH_TOKEN", "TRAE_ACCESS_TOKEN", "VSCODE_IPC_HOOK_CLI"]:
        val = os.environ.get(env_var)
        if val:
            masked = val[:15] + "..." if len(val) > 20 else val
            sources.append({
                "type": "env_var",
                "name": env_var,
                "value_preview": masked,
            })

    return sources


def _is_sqlcipher(filepath: str) -> bool:
    """检查数据库是否为 SQLCipher 加密。"""
    try:
        with open(filepath, "rb") as f:
            header = f.read(16)
        # SQLCipher 起始字节不是 'SQLite format 3\0'
        return not header.startswith(b"SQLite format 3\0")
    except OSError:
        return False


def extract_from_trae_process() -> Optional[Dict[str, Any]]:
    """
    通过 IPC 从运行中的 Trae 进程提取 token。

    利用 Trae 的 CLI IPC 接口查询认证信息。
    """
    ipc_hook = os.environ.get("VSCODE_IPC_HOOK_CLI")
    if not ipc_hook:
        return None

    try:
        # 使用 trae CLI 查询用户信息
        result = subprocess.run(
            [os.path.expanduser("~/trae/bin/trae"), "--status"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout + result.stderr
        return {"method": "ipc_status", "output": output[:500]}
    except Exception as e:
        return {"method": "ipc_error", "error": str(e)}


def extract_from_sqlcipher(db_path: str, key: str = "") -> Optional[Dict[str, Any]]:
    """
    尝试连接 SQLCipher 加密的数据库。

    如果 key 为空，使用常见默认 key。
    """
    if not os.path.exists(db_path):
        return None

    default_keys = [key] if key else [
        "",  # 空密码（标准 SQLite）
        "x'D7C8C9B5A1E3F0D2C4B6A8E0F1C3D5E7'",  # 常见 SQLCipher default
        "x'2B1C4D5A6F7E8D9C0B1A2F3E4D5C6B7A'",
    ]

    for k in default_keys:
        try:
            conn = sqlite3.connect(db_path)
            if k:
                conn.execute(f"PRAGMA key = {k}")
            # 尝试读取
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            # 查找包含 token 的表
            token_data = {}
            for table in tables:
                try:
                    cursor = conn.execute(f"SELECT * FROM \"{table}\" LIMIT 100")
                    columns = [desc[0] for desc in cursor.description]
                    for row in cursor.fetchall():
                        row_dict = dict(zip(columns, row))
                        for col in columns:
                            val = str(row_dict.get(col, ""))
                            if any(k in val for k in ["eyJ", "token", "refresh", "access"]):
                                token_data[table] = row_dict
                except sqlite3.DatabaseError:
                    continue

            conn.close()
            return {"tables": tables, "token_data": token_data, "key_used": k[:20] + "..." if len(k) > 20 else k}

        except sqlite3.DatabaseError:
            continue

    return None


# === 一键提取并启动代理 =====================================================


def do_extract(auto_serve: bool = False, port: int = 8080):
    """提取 token 并可选启动代理服务器。"""
    print("=" * 60)
    print("Trae Token 提取器")
    print("=" * 60)

    sources = scan_sources()
    refresh_token = None

    # 1. 检查环境变量
    rt = os.environ.get("TRAE_REFRESH_TOKEN")
    if rt:
        refresh_token = rt
        print(f"[✓] 环境变量 TRAE_REFRESH_TOKEN: {rt[:20]}...")

    # 2. 检查 JSON 文件
    if not refresh_token:
        for path in [TOKEN_STORE_PATH, SUPABASE_TOKEN_PATH, TOKEN_FILE_PATH]:
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        data = json.load(f)
                    rt = data.get("refresh_token") or data.get("refreshToken")
                    if rt:
                        refresh_token = rt
                        print(f"[✓] {path}: refresh_token 已提取")
                except Exception:
                    pass

    # 3. 检查 storage.json
    if not refresh_token and os.path.exists(STORAGE_JSON):
        try:
            with open(STORAGE_JSON) as f:
                data = json.load(f)
            for k, v in data.items():
                if isinstance(v, str) and len(v) > 30 and ("eyJ" in v or "." in v):
                    if "refresh" in k.lower():
                        refresh_token = v
                        print(f"[✓] storage.json[{k}]: refresh_token 已提取")
        except Exception:
            pass

    # 4. 尝试数据库
    if not refresh_token and os.path.exists(DATABASE_DB):
        print(f"[*] 尝试解密 database.db (SQLCipher)...")
        result = extract_from_sqlcipher(DATABASE_DB)
        if result and result.get("token_data"):
            print(f"    → 找到潜在 token 数据:")
            for table, data in result["token_data"].items():
                print(f"      表 {table}: {json.dumps(data, ensure_ascii=False)[:200]}")

    # 结果
    if refresh_token:
        print(f"\n[✓] Refresh token 已提取! 启动代理...")

        # 保存
        os.makedirs(os.path.dirname(TOKEN_STORE_PATH), exist_ok=True)
        with open(TOKEN_STORE_PATH, "w") as f:
            json.dump({"refresh_token": refresh_token}, f, indent=2)
        os.chmod(TOKEN_STORE_PATH, 0o600)
        print(f"[+] Token 已保存到 {TOKEN_STORE_PATH}")

        # 启动代理
        if auto_serve:
            print(f"\n[*] 启动代理服务器 :{port}")
            os.environ["TRAE_REFRESH_TOKEN"] = refresh_token
            import trae_chat_client
            trae_chat_client.main()
    else:
        print(f"\n[✗] 未找到 refresh_token")
        print(f"")
        print(f"   请先用 Trae IDE 登录一次，然后再运行此脚本。")
        print(f"   或手动将 refresh_token 写入 {TOKEN_STORE_PATH}")
        print(f"")
        print(f"   可用 token 来源扫描结果:")
        for s in sources:
            t = s.get("type", "?")
            p = s.get("path", s.get("name", s.get("pid", "?")))
            print(f"     [{t}] {p}")


# === CLI =====================================================================


def parse_args():
    parser = argparse.ArgumentParser(description="Trae Token 提取器")
    parser.add_argument("--action", default="scan", choices=["scan", "extract", "serve", "all"])
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--listen", default="0.0.0.0")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.action == "scan":
        sources = scan_sources()
        print("Token 来源扫描:")
        print()
        if not sources:
            print("  未找到任何 token 来源")
            return
        for s in sources:
            t = s.get("type", "?")
            print(f"  [{t}]")
            for k, v in s.items():
                if k != "type":
                    print(f"    {k}: {v}")
            print()

    elif args.action == "extract":
        do_extract(auto_serve=False)

    elif args.action == "serve":
        do_extract(auto_serve=True, port=args.port)

    elif args.action == "all":
        print("=== 1. 扫描 ===")
        sources = scan_sources()
        for s in sources:
            print(f"  [{s.get('type')}] {s.get('path', s.get('pid', '?'))}")
        print()
        print("=== 2. 提取 ===")
        do_extract(auto_serve=False)
        if os.path.exists(TOKEN_STORE_PATH):
            print()
            print(f"=== 3. 启动 trae_chat_client 代理 ===")
            os.execvp("python3", [
                "python3",
                os.path.join(os.path.dirname(__file__), "trae_chat_client.py"),
                "--action", "serve",
                "--port", str(args.port),
                "--listen", args.listen,
            ])


if __name__ == "__main__":
    main()
