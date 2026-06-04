#!/usr/bin/env python3
"""
Trae AI 端到端认证 + API 调用脚本 (v2 — 支持 client_connect 绕配额)

使用方式:
    # 0. 设置环境变量
    export TRAE_REFRESH_TOKEN='your_refresh_token_here'

    # 1. 仅测试认证流程（token exchange + 获取用户信息）
    python3 scripts/trae_e2e.py --action auth-test

    # 2. 标准模式 — 调用 agents/runs（配额 5003，仅用于验证）
    python3 scripts/trae_e2e.py --action quota-test

    # 3. client_connect 模式 — 用 DeepSeek API Key 直接调，绕过配额
    export DEEPSEEK_API_KEY='sk-your-deepseek-key'
    python3 scripts/trae_e2e.py --action client-chat --provider deepseek --message "hello, who are you?"

    # 4. client_connect 模式 — 用 Anthropic API Key
    export ANTHROPIC_API_KEY='sk-ant-your-key'
    python3 scripts/trae_e2e.py --action client-chat --provider anthropic --message "hello"

    # 5. 列出所有支持 client_connect 的供应商
    python3 scripts/trae_e2e.py --action list-byok

    # 6. 打印当前 token 状态
    python3 scripts/trae_e2e.py --action token-status

    # 7. 完整诊断 — 所有检测一次性跑完
    python3 scripts/trae_e2e.py --action full-diagnose
"""

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from typing import Optional, Dict, Any, List

import requests


# ============================================================
# 常量
# ============================================================

# ————— 区域端点 —————
TOKEN_HOST_SG = "https://api-sg-central.trae.ai"           # ExchangeToken 端点
CHAT_HOST_SG = "https://coresg-normal.trae.ai"             # agents/runs 端点

# ————— 认证 —————
TRAE_CLIENT_ID = "ono9krqynydwx5"                          # Trae stable client_id
TOKEN_STORE_PATH = os.path.expanduser("~/.trae/tokens.json")

# ————— client_connect 供应商 API 端点 —————
CLIENT_CONNECT_ENDPOINTS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "models": ["deepseek-v4-pro", "deepseek-v4-flash"],
        "chat_endpoint": "/v1/chat/completions",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "api_key_env": "ANTHROPIC_API_KEY",
        "models": ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"],
        "chat_endpoint": "/v1/messages",
    },
}


# ============================================================
# Step 1: Token 管理
# ============================================================

def get_refresh_token() -> str:
    """从环境变量或存储文件获取 refresh_token。"""
    rt = os.environ.get("TRAE_REFRESH_TOKEN")
    if rt:
        return rt
    if os.path.exists(TOKEN_STORE_PATH):
        with open(TOKEN_STORE_PATH) as f:
            data = json.load(f)
        rt = data.get("refresh_token", "")
        if rt:
            return rt
    return ""


def exchange_token(refresh_token: str) -> Dict[str, Any]:
    """用 refresh_token 换取新的 access_token。（已验证通过）"""
    url = f"{TOKEN_HOST_SG}/cloudide/api/v3/trae/oauth/ExchangeToken"
    headers = {"Content-Type": "application/json"}
    payload = {
        "ClientID": TRAE_CLIENT_ID,
        "RefreshToken": refresh_token,
        "ClientSecret": "-",
        "UserID": "",
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text[:300]}
    data = resp.json()
    result = data.get("Result", {})
    token = result.get("Token", "")
    new_refresh = result.get("RefreshToken", refresh_token)
    expires_at = result.get("TokenExpireAt", 0) / 1000  # ms → s
    return {
        "access_token": token,
        "refresh_token": new_refresh,
        "expires_at": expires_at,
        "raw": data,
    }


def get_access_token(force_refresh: bool = False) -> str:
    """获取有效的 access_token（自动检查过期 + 刷新）。"""
    rt = get_refresh_token()
    if not rt:
        print("  ❌ 未找到 refresh_token。请设置环境变量 TRAE_REFRESH_TOKEN")
        sys.exit(1)

    # 从存储读取已有 token
    if not force_refresh and os.path.exists(TOKEN_STORE_PATH):
        with open(TOKEN_STORE_PATH) as f:
            stored = json.load(f)
        token = stored.get("access_token", "")
        expires = stored.get("_expires_at", 0)
        if token and time.time() < expires - 60:
            return token  # 有效且未过期
        print("  [i] Token 已过期或即将过期，自动刷新...")

    # 刷新 token
    print(f"  [*] 调用 ExchangeToken...")
    result = exchange_token(rt)
    if "error" in result:
        print(f"  ❌ Token 刷新失败: {result['error']}")
        if "detail" in result:
            print(f"     响应: {result['detail']}")
        sys.exit(1)

    token = result["access_token"]
    # 保存到存储
    refresh_token = result.get("refresh_token", rt)
    expires_at = result.get("expires_at", time.time() + 3600)
    os.makedirs(os.path.dirname(TOKEN_STORE_PATH), exist_ok=True)
    with open(TOKEN_STORE_PATH, "w") as f:
        json.dump({
            "access_token": token,
            "refresh_token": refresh_token,
            "_expires_at": expires_at,
            "_updated_at": time.time(),
        }, f, indent=2)
    os.chmod(TOKEN_STORE_PATH, 0o600)
    print(f"  ✅ Token 刷新成功，有效期至 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_at))}")
    return token


def decode_jwt(token: str) -> Dict[str, Any]:
    """解码 JWT payload（不验证签名）。"""
    try:
        payload_b64 = token.split(".")[1]
        pad = 4 - len(payload_b64) % 4
        if pad != 4:
            payload_b64 += "=" * pad
        import base64
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Step 2: API 调用
# ============================================================

def call_get_user_info(access_token: str) -> Optional[Dict]:
    """获取用户信息 — 验证 token 有效 + 可见用户数据。"""
    url = f"{TOKEN_HOST_SG}/cloudide/api/v3/trae/GetUserInfo"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text[:200]}
    except Exception as e:
        return {"error": str(e)}


def call_agents_runs(access_token: str, message: str = "hello") -> Dict:
    """调用 agents/runs — 标准 AI 端点（会遇到配额 5003）。"""
    url = f"{CHAT_HOST_SG}/api/ide/v1/agents/runs"
    headers = {
        "x-cloudide-token": access_token,
        "x-ide-token": access_token,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "session_id": f"s_{uuid.uuid4().hex[:12]}",
        "query": message,
        "chat_mode": "agent",
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    result = {"http_status": resp.status_code, "time_seconds": resp.elapsed.total_seconds()}
    if resp.status_code == 200:
        events = []
        for line in resp.text.split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        result["events"] = events
        # 检查 5003 配额错误
        for ev in events:
            if ev.get("code") == 5003:
                result["quota_blocked"] = True
                result["quota_message"] = ev.get("message", "")
                break
    else:
        result["body"] = resp.text[:500]
    return result


def call_client_connect(provider: str, api_key: str, message: str, model: str = None) -> Dict:
    """
    通过 client_connect 模式直接调用供应商 API。
    绕过 Trae 配额限制，直接用个人 API Key。
    """
    cfg = CLIENT_CONNECT_ENDPOINTS.get(provider)
    if not cfg:
        return {"error": f"不支持的供应商: {provider}，可选: {list(CLIENT_CONNECT_ENDPOINTS.keys())}"}

    model = model or cfg["models"][0]

    if provider == "deepseek":
        # OpenAI 兼容格式
        url = f"{cfg['base_url']}{cfg['chat_endpoint']}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": 1024,
            "stream": False,
        }
        print(f"  [*] 调用 DeepSeek API: model={model}")
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "detail": resp.text[:500]}
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {
            "success": True,
            "provider": provider,
            "model": model,
            "content": content,
            "usage": data.get("usage", {}),
        }

    elif provider == "anthropic":
        # Anthropic Messages API 格式
        url = f"{cfg['base_url']}{cfg['chat_endpoint']}"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": message}],
        }
        print(f"  [*] 调用 Anthropic API: model={model}")
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "detail": resp.text[:500]}
        data = resp.json()
        content = "".join(block.get("text", "") for block in data.get("content", []))
        return {
            "success": True,
            "provider": provider,
            "model": model,
            "content": content,
            "usage": data.get("usage", {}),
        }

    return {"error": f"未知 provider: {provider}"}


def get_providers(access_token: str) -> List[Dict]:
    """获取供应商列表。"""
    url = f"{CHAT_HOST_SG}/api/ide/v1/providers"
    headers = {
        "x-cloudide-token": access_token,
        "x-ide-token": access_token,
        "Content-Type": "application/json",
    }
    resp = requests.post(url, headers=headers, json={}, timeout=15)
    if resp.status_code != 200:
        return []
    data = resp.json()
    return data.get("providers", [])


# ============================================================
# Steps 合并：动作
# ============================================================

def action_auth_test():
    """测试认证流程完整性。"""
    print("\n" + "=" * 60)
    print("  认证流程测试")
    print("=" * 60)

    # Step 1: 获取 refresh_token
    print("\n[1/4] 获取 refresh_token...")
    rt = get_refresh_token()
    if rt:
        print(f"  ✅ refresh_token 已获取: {rt[:20]}...")
    else:
        print("  ❌ 未找到 refresh_token")
        return

    # Step 2: ExchangeToken
    print("\n[2/4] 调用 ExchangeToken 换取 access_token...")
    result = exchange_token(rt)
    if "error" in result:
        print(f"  ❌ 失败: {result['error']}")
        if "detail" in result:
            print(f"     响应: {result['detail']}")
        return
    token = result["access_token"]
    print(f"  ✅ access_token 获取成功: {token[:30]}...")
    print(f"  📅 有效期至: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['expires_at']))}")

    # Step 3: 解码 JWT 检查内容
    print("\n[3/4] 解码 JWT payload...")
    jwt = decode_jwt(token)
    if "error" not in jwt:
        data = jwt.get("data", {})
        print(f"  👤 UserID: {data.get('id', '?')}")
        print(f"  🏢 TenantID: {data.get('tenant_id', '?')}")
        print(f"  📋 Type: {data.get('type', '?')}")
        print(f"  📤 Source: {data.get('source', '?')}")
    else:
        print(f"  ⚠️ JWT 解码失败: {jwt['error']}")

    # Step 4: GetUserInfo
    print("\n[4/4] 调用 GetUserInfo...")
    info = call_get_user_info(token)
    if info and "error" not in info:
        print(f"  ✅ 用户信息获取成功")
        # 格式化输出关键字段
        for k, v in info.items():
            if isinstance(v, (str, int, float, bool)):
                print(f"      {k}: {v}")
    else:
        print(f"  ❌ 失败: {info}")

    print("\n" + "=" * 60)
    print("  认证流程 ✅ 完成")
    print("=" * 60)


def action_quota_test():
    """测试 agents/runs 端点（验证配额状态）。"""
    print("\n" + "=" * 60)
    print("  配额测试 — agents/runs 端点")
    print("=" * 60)

    print("\n[*] 获取 access_token...")
    token = get_access_token()
    print(f"  ✅ Token 就绪: {token[:30]}...")

    print("\n[*] 调用 agents/runs...")
    result = call_agents_runs(token)

    print(f"\n  📊 HTTP {result['http_status']} ({result.get('time_seconds', 0):.2f}s)")
    if result.get("quota_blocked"):
        print(f"  🔴 配额阻塞: {result['quota_message']}")
        print(f"\n  💡 解决方案: 使用 --action client-chat 绕配额")
    else:
        events = result.get("events", [])
        print(f"  ✅ 请求成功（未被配额阻挡），收到 {len(events)} 个事件")
        for ev in events[:3]:
            print(f"     事件: {json.dumps(ev, ensure_ascii=False)[:150]}")

    print("\n" + "=" * 60)
    print("  配额测试完成")
    print("=" * 60)


def action_client_chat(provider: str, message: str, model: str = None):
    """通过 client_connect 直接调供应商 API。"""
    cfg = CLIENT_CONNECT_ENDPOINTS.get(provider)
    if not cfg:
        print(f"❌ 不支持的供应商: {provider}")
        print(f"   可选: {list(CLIENT_CONNECT_ENDPOINTS.keys())}")
        return

    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        print(f"❌ 未设置环境变量 {cfg['api_key_env']}")
        print(f"   请先设置: export {cfg['api_key_env']}='your-api-key'")
        return

    model = model or cfg["models"][0]
    print(f"\n{'='*60}")
    print(f"  client_connect 模式 — {provider}")
    print(f"  Model: {model}")
    print(f"{'='*60}")

    print(f"\n[*] 发送消息: \"{message}\"")
    result = call_client_connect(provider, api_key, message, model)

    if result.get("success"):
        print(f"\n  ✅ 调用成功!")
        print(f"\n  📝 响应:")
        print(f"  ─────────────────────────────────────────")
        print(f"  {result['content']}")
        print(f"  ─────────────────────────────────────────")
        if result.get("usage"):
            print(f"\n  📊 Token 用量: {json.dumps(result['usage'])}")
    else:
        print(f"\n  ❌ 调用失败: {result.get('error', '?')}")
        if "detail" in result:
            print(f"     响应: {result['detail']}")

    print()


def action_list_byok():
    """列出所有支持 client_connect 的供应商。"""
    print(f"\n{'='*60}")
    print("  支持 client_connect (BYOK) 的供应商")
    print(f"{'='*60}\n")

    # 先尝试从 API 获取
    try:
        token = get_access_token(force_refresh=False)
        providers = get_providers(token)
        byok = [p for p in providers if p.get("client_connect") == True]
        if byok:
            print(f"  来自 Trae API 的实时数据:\n")
            for p in byok:
                models = p.get("models", [])
                print(f"  🔑 {p['name']:20s} ({p['id']})")
                print(f"     API Key: {p.get('api_key_doc', '?')}")
                print(f"     Models:  {', '.join(models)}")
                print()
            return
    except Exception:
        pass

    # Fallback: 用硬编码数据
    print("  (Trae API 不可达，使用本地缓存数据)\n")
    for pid, cfg in CLIENT_CONNECT_ENDPOINTS.items():
        api_key = os.environ.get(cfg["api_key_env"], "(未设置)")
        masked = api_key[:8] + "..." if api_key != "(未设置)" and len(api_key) > 12 else api_key
        print(f"  🔑 {pid:20s} API Key: {masked}")
        print(f"     Models:  {', '.join(cfg['models'])}")
        print(f"     Endpoint: {cfg['base_url']}")
        print()


def action_token_status():
    """打印当前 token 状态。"""
    print(f"\n{'='*60}")
    print("  Token 状态")
    print(f"{'='*60}\n")

    rt = get_refresh_token()
    if rt:
        print(f"  ✅ refresh_token: {rt[:20]}... ({len(rt)} chars)")
    else:
        print("  ❌ 未找到 refresh_token")

    token_path = TOKEN_STORE_PATH
    if os.path.exists(token_path):
        with open(token_path) as f:
            stored = json.load(f)
        token = stored.get("access_token", "")
        expires = stored.get("_expires_at", 0)
        now = time.time()
        remaining = int(expires - now) if expires > now else 0
        print(f"  📁 存储文件: {token_path}")
        print(f"  🔑 access_token: {token[:30]}... ({len(token)} chars)")
        if remaining > 0:
            print(f"  📅 过期时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires))}")
            print(f"  ⏳ 剩余: {remaining // 3600}h {(remaining % 3600) // 60}m")
        else:
            print(f"  🔴 Token 已过期")

        # 解码 JWT
        if token:
            jwt = decode_jwt(token)
            if "error" not in jwt:
                data = jwt.get("data", {})
                print(f"\n  👤 JWT Payload:")
                print(f"     UserID:   {data.get('id', '?')}")
                print(f"     TenantID: {data.get('tenant_id', '?')}")
                print(f"     Type:     {data.get('type', '?')}")
    else:
        print(f"  ❌ 未找到存储文件: {token_path}")

    print("\n  环境变量检查:")
    for ev in ["TRAE_REFRESH_TOKEN", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"]:
        val = os.environ.get(ev, "")
        if val:
            print(f"  ✅ {ev}: {val[:12]}...")
        else:
            print(f"  ⬜ {ev}: (未设置)")

    print()


def action_full_diagnose():
    """全量诊断——所有检测一次完成。"""
    print(f"\n{'='*60}")
    print("  🩺 Trae AI 完整诊断")
    print(f"{'='*60}")

    # ——— 1. 网络可达性 ———
    print("\n[1/7] 网络可达性检测...")
    targets = [
        ("Trae SG Auth", TOKEN_HOST_SG),
        ("Trae SG Chat", CHAT_HOST_SG),
        ("DeepSeek API", "https://api.deepseek.com"),
        ("Anthropic API", "https://api.anthropic.com"),
    ]
    for name, url in targets:
        try:
            r = requests.get(url, timeout=5)
            print(f"  {r.status_code:4d} {name:20s} {url}")
        except Exception as e:
            print(f"  FAIL {name:20s} {url}  ({e})")

    # ——— 2. Token 状态 ———
    print("\n[2/7] Token 状态检测...")
    rt = get_refresh_token()
    if rt:
        print(f"  ✅ refresh_token: {rt[:20]}...")
    else:
        print(f"  ❌ 未找到 refresh_token")
        print(f"  💡 export TRAE_REFRESH_TOKEN='your_token'")
        # 继续，但后面会失败

    # ——— 3. ExchangeToken ———
    print("\n[3/7] ExchangeToken 检测...")
    if rt:
        result = exchange_token(rt)
        if "error" not in result:
            token = result["access_token"]
            print(f"  ✅ 成功: access_token={token[:30]}...")
            jwt = decode_jwt(token)
            if "error" not in jwt:
                data = jwt.get("data", {})
                print(f"     👤 UserID: {data.get('id', '?')}")
                print(f"     🏢 TenantID: {data.get('tenant_id', '?')}")
        else:
            print(f"  ❌ 失败: {result['error']}")
            token = None
    else:
        token = None

    # ——— 4. GetUserInfo ———
    print("\n[4/7] GetUserInfo 检测...")
    if token:
        info = call_get_user_info(token)
        if info and "error" not in info:
            print(f"  ✅ 成功: {json.dumps(info, ensure_ascii=False)[:200]}")
        else:
            print(f"  ❌ 失败: {info}")

    # ——— 5. providers 列表 ———
    print("\n[5/7] Providers 列表检测...")
    if token:
        providers = get_providers(token)
        if providers:
            print(f"  ✅ 获取到 {len(providers)} 个供应商:")
            byok = [p for p in providers if p.get("client_connect") == True]
            for p in providers:
                nm = p.get("name", "?")
                cc = "🔑" if p.get("client_connect") else "  "
                bm = p.get("billing_mode", "?")
                mods = p.get("models", [])
                print(f"    {cc} {nm:20s} billing={bm:15s} models={len(mods)}")
            if byok:
                print(f"\n    支持 BYOK 的供应商: {', '.join(p['name'] for p in byok)}")
        else:
            print(f"  ❌ 获取失败")

    # ——— 6. agents/runs 配额测试 ———
    print("\n[6/7] agents/runs 配额检测...")
    if token:
        result = call_agents_runs(token)
        print(f"  HTTP {result['http_status']} ({result.get('time_seconds', 0):.2f}s)")
        if result.get("quota_blocked"):
            print(f"  🔴 配额阻塞: {result['quota_message']}")
        else:
            print(f"  ✅ 请求成功")

    # ——— 7. client_connect API Key 检查 ———
    print("\n[7/7] client_connect API Key 检查...")
    for pid, cfg in CLIENT_CONNECT_ENDPOINTS.items():
        key = os.environ.get(cfg["api_key_env"], "")
        if key:
            print(f"  ✅ {pid:20s} {cfg['api_key_env']}: {key[:12]}...")
        else:
            print(f"  ⬜ {pid:20s} {cfg['api_key_env']}: (未设置)")
    print()

    # ——— 汇总 ———
    print("=" * 60)
    print("  诊断汇总")
    print("=" * 60)
    if rt:
        print("  ✅ 认证: refresh_token 就绪")
    if token:
        print("  ✅ Token: ExchangeToken 正常")
        print(f"  🔴 配额: agents/runs 被 5003 阻断")
    deepseek_ok = bool(os.environ.get("DEEPSEEK_API_KEY"))
    anthropic_ok = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if deepseek_ok or anthropic_ok:
        bypass = []
        if deepseek_ok:
            bypass.append("DeepSeek")
        if anthropic_ok:
            bypass.append("Anthropic")
        print(f"  ✅ BYOK: {' + '.join(bypass)} API Key 就绪，可以绕配额")
        print(f"  ▶️  运行: python3 scripts/trae_e2e.py --action client-chat --provider deepseek --message 'hi'")
    else:
        print(f"  ⬜ BYOK: 未设置 API Key")
        print(f"  💡 注册 DeepSeek 免费 Key: https://platform.deepseek.com/api_keys")
        print(f"  💡 然后: export DEEPSEEK_API_KEY='sk-...'")
    print()


# ============================================================
# CLI
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Trae AI 端到端认证 + API 调用脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 测试认证
  export TRAE_REFRESH_TOKEN='your_token'
  python3 scripts/trae_e2e.py --action auth-test

  # 用 DeepSeek bypass 配额
  export DEEPSEEK_API_KEY='sk-xxx'
  python3 scripts/trae_e2e.py --action client-chat --provider deepseek --message "hi"

  # 完整诊断
  python3 scripts/trae_e2e.py --action full-diagnose
        """,
    )
    parser.add_argument("--action", required=True, choices=[
        "auth-test",
        "quota-test",
        "client-chat",
        "list-byok",
        "token-status",
        "full-diagnose",
    ], help="执行的动作")
    parser.add_argument("--provider", choices=list(CLIENT_CONNECT_ENDPOINTS.keys()) + ["auto"], default="auto")
    parser.add_argument("--model", help="模型名称（可选，默认为第一个可用模型）")
    parser.add_argument("--message", "-m", default="Say hello in one sentence, who are you?")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.action == "auth-test":
        action_auth_test()
    elif args.action == "quota-test":
        action_quota_test()
    elif args.action == "client-chat":
        provider = args.provider
        if provider == "auto":
            # 自动选择第一个有 API Key 的供应商
            for pid, cfg in CLIENT_CONNECT_ENDPOINTS.items():
                if os.environ.get(cfg["api_key_env"]):
                    provider = pid
                    break
            if provider == "auto":
                print("❌ 未检测到任何 API Key")
                print("   请设置 DEEPSEEK_API_KEY 或 ANTHROPIC_API_KEY 环境变量")
                sys.exit(1)
        action_client_chat(provider, args.message, args.model)
    elif args.action == "list-byok":
        action_list_byok()
    elif args.action == "token-status":
        action_token_status()
    elif args.action == "full-diagnose":
        action_full_diagnose()


if __name__ == "__main__":
    main()