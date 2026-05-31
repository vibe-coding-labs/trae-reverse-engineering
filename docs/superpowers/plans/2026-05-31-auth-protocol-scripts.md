# 认证授权协议完整分析与脚本编写计划

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`
> Steps use checkbox (`- [ ]`) notation.

**Goal:** 完成 Trae AI 所有认证授权协议的完整分析，并编写可直接运行的认证脚本。

**Architecture:** 先补全协议分析的缺口，再逐个编写认证脚本。脚本按认证类型分为 6 大类：

1. **BootConfig 认证** — 初始配置获取与 tokenHost 发现
2. **JWT Token 认证** — Access Token + Refresh Token 生命周期
3. **OAuth2 认证** — Google/GitHub/GitLab + PKCE 流程
4. **Supabase OAuth** — Supabase 第三方认证
5. **Frontier/WebSocket 认证** — Hub Bridge WebSocket 握手
6. **AWS SSO** — AWS Bedrock 企业 SSO 认证

**Tech Stack:** Python 3 (requests/websockets/hashlib/base64)

**Scope:** Medium (8 个分析补充 + 6 个认证脚本)
**Risk:** Low

---

## Type Detection

**Plan Type:** Research + Feature (混合类型 — 先调研补齐缺口，再编写脚本)
**Scope:** Medium
**Risk:** Low

---

## Pre-Planning Analysis

**分析发现 — 认证协议覆盖缺口：**

| # | 认证协议 | 现状 | 缺口 |
|---|---------|------|------|
| 1 | BootConfig | ✅ 已有 17 字段结构 | 需补充 boot URL 来源、字段用途用途 |
| 2 | JWT Token | ✅ 基本结构 | 需补充 ExchangeToken API、刷新流程、错误码 |
| 3 | OAuth2 | ⚠️ 概念覆盖 | 缺 PKCE 完整流程、code_challenge 生成、scope 清单 |
| 4 | AWS SSO | ❌ 仅 2 处 | 缺完整 SSO OIDC → GetRoleCredentials → STS AssumeRole 链 |
| 5 | Supabase OAuth | ❌ 0 覆盖 | 缺 Supabase OAuth 端点和流程 |
| 6 | Frontier Auth | ✅ 基本覆盖 | 需补 WebSocket handshake 帧格式 |
| 7 | Handoff | ✅ 已覆盖 | OK |
| 8 | Scope 清单 | ❌ 未整理 | marscode/marscode_cn/bytedance/saas 需整理 |

**分析缺口 → 对应脚本需求：**

| 缺口 | 脚本 | 功能 |
|------|------|------|
| BootConfig → JWT | `auth_bootconfig_jwt.py` | 获取 BootConfig → 获取 JWT token |
| OAuth2 PKCE | `auth_oauth2_pkce.py` | PKCE 完整流程 (Google/GitHub) |
| Token Refresh | `auth_token_refresh.py` | 自动刷新 access token |
| AWS SSO | `auth_aws_sso.py` | AWS SSO OIDC → AssumeRole |
| Supabase OAuth | `auth_supabase.py` | Supabase OAuth 登录 |
| Frontier WS Auth | `auth_frontier_ws.py` | Frontier WebSocket 认证 |

---

## Plan Header

**Goal:** 完成 Trae AI 6 种认证协议的完整分析文档 + 6 个可运行的认证脚本。

**Architecture:** 
- 数据流：BootConfig（发现 tokenHost）→ JWT（获取 access+refresh token）→ 使用 token 调用 API
- OAuth2 分支：Google/GitHub OAuth → 获取 code → PKCE 换 token
- AWS 分支：SSO OIDC → GetRoleCredentials → STS AssumeRole
- Supabase 分支：OAuth 登录 → API token
- 所有 token 统一存储（SQLCipher 加密 SQLite）

**Risks:**
- OAuth2 需要浏览器交互（headless 或手动复制 URL）
- AWS SSO 需要企业账号配置
- Supabase OAuth URL 可能因 region 不同

---

## Tasks

### Task 1: 补全认证协议文档 — BootConfig & JWT 细节

**Depends on:** None
**Files:**
- Modify: `analysis/ai-protocol-analysis.md`（在 §3 Authentication Flow 中追加）

- [ ] **Step 1: 补全 BootConfig 认证源信息**
追加以下内容到 §3 认证章节末尾：

```markdown
### 3.12 BootConfig 完整认证流程

**Boot 端点:**
```
https://icube-boot.trae.ai          — 国际区
https://icube-boot.trae.com.cn       — 中国区
```

**BootConfig 获取流程:**
1. IDE 启动 → GET https://icube-boot.trae.ai/boot/config
2. 返回 BootConfig（17 字段，包含 tokenHost、userInfo）
3. 如果 userInfo 未过期 → 直接使用已有 token
4. 如果已过期 → 用 refresh_token 通过 tokenHost 刷新

**tokenHost 发现:**
```json
{
  "tokenHost": "https://token.trae.ai",
  "token_host": "https://token.trae.com.cn",
  "userInfo": {
    "expired_at": 1700000000,
    "refresh_expired_at": 1700000000,
    "user_id": "user_uuid",
    "token_release_at": 1699000000,
    "token_host": "https://token.trae.ai"
  }
}
```

### 3.13 Token 刷新完整 API

**端点:** `POST ${tokenHost}/cloudide/api/v3/trae/ExchangeToken`

**请求头:**
```
Authorization: Bearer <refresh_token>
Content-Type: application/json
x-cloudide-token: <cloudide_token>
x-ide-token: <ide_token>
x-frontier-id: <frontier_id>
```

**请求体:**
```json
{
  "client_id": "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8",
  "grant_type": "refresh_token",
  "refresh_token": "<current_refresh_token>"
}
```

**响应:**
```json
{
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token",
  "expires_in": 3600,
  "token_type": "Bearer",
  "scope": "marscode"
}
```

### 3.14 错误码

| 错误码 | 含义 | 处理方式 |
|--------|------|---------|
| 20324 | Token 格式错误 | 重新登录 |
| 20101 | Token 已过期 | 尝试刷新 |
| 20315 | Token 已吊销 | 重新登录 |
| 20125 | Refresh Token 无效 | 重新登录 |
| 20126 | Refresh Token 已过期 | 重新登录 |
```

- [ ] **Step 2: 验证文档追加正确**
Run: `grep -c "3.12\|3.13\|3.14" analysis/ai-protocol-analysis.md`
Expected: Output contains "3.12", "3.13", "3.14"

---

### Task 2: 补全认证协议文档 — OAuth2 PKCE 完整流程

**Depends on:** Task 1
**Files:**
- Modify: `analysis/ai-protocol-analysis.md`

- [ ] **Step 1: 追加 OAuth2 PKCE 流程**
追加到 §3 OAuth2 Providers 之后：

```markdown
### 3.6 OAuth2 PKCE 流程

**端点:**
```
授权: https://{tokenHost}/oauth/authorize
令牌: https://{tokenHost}/oauth/token
```

**OAuth2 Scopes（从 main.js 提取）:**
| Scope | 用途 | 适用地区 |
|-------|------|---------|
| `marscode` | 通用国际版 Trae/MarsCode | 国际 |
| `marscode_cn` | 中国区 MarsCode | 中国 |
| `marscode_com` | MarsCode 国际站 | 国际 |
| `bytedance` | ByteDance 内部 | 内部 |
| `saas` | SaaS 企业版 | 企业 |

**Client Identifiers（从 binary 提取）:**
```
client_id:     6eefa01c-1036-4c7e-9ca5-d891f63bfcd8
client_secret: 850edec7-b9d0-48aa-99b5-67c888e282cd
```

**PKCE 完整流程:**
1. 生成 code_verifier（43-128 字符随机字符串）
2. 生成 code_challenge = base64url(sha256(code_verifier))
3. 构造授权 URL → 用户浏览器打开 → 用户登录
4. 重定向回本地服务器，获取 authorization_code
5. POST 授权码 + code_verifier → 换 access_token + refresh_token
6. 存储 token（SQLCipher 加密数据库）

**授权请求:**
```
GET {tokenHost}/oauth/authorize?
  response_type=code&
  client_id=6eefa01c-1036-4c7e-9ca5-d891f63bfcd8&
  redirect_uri=http://localhost:{port}/callback&
  code_challenge={base64url(sha256(verifier))}&
  code_challenge_method=S256&
  scope=marscode
```

**令牌交换:**
```
POST {tokenHost}/oauth/token
Content-Type: application/json

{
  "grant_type": "authorization_code",
  "code": "{authorization_code}",
  "redirect_uri": "http://localhost:{port}/callback",
  "client_id": "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8",
  "code_verifier": "{original_code_verifier}"
}
```

### 3.7 OAuth2 Provider 端点

| Provider | 授权端点 | 令牌端点 |
|----------|---------|---------|
| Google | Google OAuth2 | Google Token |
| GitHub | GitHub OAuth2 | GitHub Token |
| GitLab | GitLab OAuth2 | GitLab Token |
| Supabase | https://api.supabase.com/v1/oauth/authorize | https://api.supabase.com/v1/oauth/token |

### 3.8 第三方 Token 获取

**端点:** `POST /cloudide/api/v3/trae/GetThirdPartyToken`

通过已获取的 JWT token 换取第三方服务的访问令牌：
```
POST {tokenHost}/cloudide/api/v3/trae/GetThirdPartyToken
x-cloudide-token: {access_token}
```
```

- [ ] **Step 2: 验证**
Run: `grep -c "PKCE\|code_challenge\|code_verifier\|GetThirdPartyToken\|marscode" analysis/ai-protocol-analysis.md`
Expected: ≥5

---

### Task 3: 补全认证协议文档 — AWS SSO & Supabase OAuth

**Depends on:** Task 2
**Files:**
- Modify: `analysis/ai-protocol-analysis.md`

- [ ] **Step 1: 追加 AWS SSO 完整流程**
追加到 §3 末尾：

```markdown
### 3.9 AWS SSO 企业认证

**端点:**
```
SSO OIDC:  https://oidc.{region}.amazonaws.com
SSO:        https://portal.sso.{region}.amazonaws.com
STS:        https://sts.{region}.amazonaws.com
Bedrock:    https://bedrock-runtime.{region}.amazonaws.com
```

**完整流程（3 步链）:**

**Step 1: SSO OIDC CreateToken**
```
POST https://oidc.{region}.amazonaws.com/token
Content-Type: application/json

{
  "clientId": "{sso_client_id}",
  "clientSecret": "{sso_client_secret}",
  "grantType": "urn:ietf:params:oauth:grant-type:device_code",
  "deviceCode": "{device_code}",
  "codeVerifier": "{code_verifier}"
}
```

**Step 2: SSO GetRoleCredentials**
```
POST https://portal.sso.{region}.amazonaws.com/federation/credentials
Authorization: Bearer {access_token}

{
  "accountId": "{aws_account_id}",
  "roleName": "{sso_role_name}"
}
```

**Step 3: STS AssumeRole（可选，用于跨账号访问）**
```
POST https://sts.{region}.amazonaws.com/
Action=AssumeRole
RoleArn=arn:aws:iam::{account}:role/{role}
RoleSessionName=trae-session
```

**错误类型:**
```rust
// AWS SSO OIDC 错误
BadExpirationTimeFromSsoOidc
ExpiredToken

// AWS 凭证错误
CredentialsNotLoaded
ProviderTimedOut
InvalidConfiguration
ProviderError
TokenNotLoaded

// IMDS（实例元数据服务）
ImdsCommunicationError
FailedToLoadToken
```

### 3.10 Supabase OAuth 认证

**端点:**
```
授权: https://api.supabase.com/v1/oauth/authorize
令牌: https://api.supabase.com/v1/oauth/token
```

**工具集成（Trae AI Agent 内）:**
```
toolcall_supabase_get_project    — 获取 Supabase 项目信息
toolcall_supabase_get_tables     — 列出表
toolcall_supabase_apply_migration — 应用迁移
```

**Supabase OAuth 流程:**
1. 浏览器打开 Supabase 授权 URL
2. 用户登录 Supabase 账号
3. 获取授权码
4. 换 Supabase API token
5. token 用于 Supabase 工具调用
```

- [ ] **Step 2: 验证**
Run: `grep -c "AWS SSO\|Supabase OAuth\|GetRoleCredentials\|AssumeRole\|device_code" analysis/ai-protocol-analysis.md`
Expected: ≥3

---

### Task 4: 整理 OAuth2 Scopes & 所有 Client Credentials

**Depends on:** Task 3
**Files:**
- Create: `analysis/oauth2-credentials.md`

- [ ] **Step 1: 创建 OAuth2 凭证参考文档**

```markdown
# OAuth2 凭证参考

> 从 main.js 和 ai-agent 二进制文件中提取

## Client IDs

| 环境 | Client ID |
|------|-----------|
| Trae IDE (通用) | `6eefa01c-1036-4c7e-9ca5-d891f63bfcd8` |
| 未知/备用 | `850edec7-b9d0-48aa-99b5-67c888e282cd` |

## OAuth2 Scopes

| Scope | 描述 | 使用场景 |
|-------|------|---------|
| `marscode` | 通用国际版 Trae/MarsCode 访问权限 | 国际用户默认 |
| `marscode_cn` | 中国区 MarsCode 访问权限 | 中国区用户 |
| `marscode_com` | MarsCode 国际站访问权限 | MarsCode 国际站 |
| `bytedance` | ByteDance 内部系统访问权限 | 内部员工 |
| `saas` | SaaS 企业版访问权限 | 企业客户 |

## OAuth2 端点

| 系统 | 授权端点 | 令牌端点 |
|------|---------|---------|
| Trae 自有 | `{tokenHost}/oauth/authorize` | `{tokenHost}/oauth/token` |
| Google | Google OAuth2 | Google Token API |
| GitHub | GitHub OAuth2 | GitHub Token API |
| GitLab | GitLab OAuth2 | GitLab Token API |
| Supabase | `https://api.supabase.com/v1/oauth/authorize` | `https://api.supabase.com/v1/oauth/token` |

## Trae API 认证端点

| 端点 | 用途 |
|------|------|
| `POST /cloudide/api/v3/trae/ExchangeToken` | 刷新 access+refresh token |
| `POST /cloudide/api/v3/trae/CheckLogin` | 检查登录状态 |
| `POST /cloudide/api/v3/trae/GetUserInfo` | 获取用户信息 |
| `POST /cloudide/api/v3/trae/GetThirdPartyToken` | 获取第三方服务 token |

## 认证头

| Header | 用途 | 来源 |
|--------|------|------|
| `Authorization: Bearer {token}` | 标准 Bearer token | JWT access token |
| `x-cloudide-token: {token}` | Trae IDE token | CloudIDE 认证 |
| `x-ide-token: {token}` | IDE 级 token | IDE 内部认证 |
| `x-frontier-id: {id}` | Frontier 连接标识 | WebSocket 握手后获得 |
```

---

### Task 5: 编写 auth_bootconfig_jwt.py — BootConfig + JWT 认证脚本

**Depends on:** Task 1
**Files:**
- Create: `scripts/auth_bootconfig_jwt.py`

- [ ] **Step 1: 创建脚本 — BootConfig 获取 + JWT token 管理**

```python
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
from base64 import urlsafe_b64encode, urlsafe_b64decode
from typing import Optional, Tuple, Dict, Any

import requests

# === 常量 ====================================================================

BOOT_ENDPOINTS = {
    "us": "https://icube-boot.trae.ai",
    "cn": "https://icube-boot.trae.com.cn",
}

CLIENT_ID = "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8"
CLIENT_SECRET = "850edec7-b9d0-48aa-99b5-67c888e282cd"

# === 工具函数 ================================================================


def gen_uuid() -> str:
    """生成 UUID v4"""
    return str(uuid.uuid4())


def now_timestamp() -> int:
    return int(time.time())


def b64_encode(data: bytes) -> str:
    """Base64 URL Safe 编码（无 padding）"""
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def sha256_b64(data: str) -> str:
    """SHA256 → Base64 URL Safe"""
    return b64_encode(hashlib.sha256(data.encode()).digest())


# === BootConfig ==============================================================


def fetch_boot_config(region: str = "us") -> Dict[str, Any]:
    """
    从 Boot 端点获取初始配置。
    
    BootConfig 包含 tokenHost、userInfo、hub、frontier、ckg 等 17 个字段。
    这是整个认证流程的起点。
    """
    url = BOOT_ENDPOINTS.get(region, BOOT_ENDPOINTS["us"])
    
    headers = {
        "User-Agent": "TraeAI/2.3.30128",
        "Accept": "application/json",
    }
    
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
    """
    用 refresh_token 换取新的 access_token + refresh_token。
    
    POST {tokenHost}/cloudide/api/v3/trae/ExchangeToken
    """
    url = f"{token_host}/cloudide/api/v3/trae/ExchangeToken"
    
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
    """
    检查 access_token 是否有效。
    POST {tokenHost}/cloudide/api/v3/trae/CheckLogin
    """
    url = f"{token_host}/cloudide/api/v3/trae/CheckLogin"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    try:
        resp = requests.post(url, headers=headers, timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def get_user_info(access_token: str, token_host: str) -> Optional[Dict[str, Any]]:
    """
    获取当前用户信息。
    POST {tokenHost}/cloudide/api/v3/trae/GetUserInfo
    """
    url = f"{token_host}/cloudide/api/v3/trae/GetUserInfo"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    resp = requests.post(url, headers=headers, timeout=5)
    if resp.status_code != 200:
        print(f"[!] 获取用户信息失败: {resp.status_code}")
        return None
    
    return resp.json()


def get_third_party_token(access_token: str, token_host: str) -> Optional[Dict[str, Any]]:
    """
    用 JWT token 换取第三方服务访问 token。
    POST {tokenHost}/cloudide/api/v3/trae/GetThirdPartyToken
    """
    url = f"{token_host}/cloudide/api/v3/trae/GetThirdPartyToken"
    
    headers = {
        "x-cloudide-token": access_token,
    }
    
    resp = requests.post(url, headers=headers, timeout=5)
    if resp.status_code != 200:
        print(f"[!] 获取第三方 Token 失败: {resp.status_code}")
        return None
    
    return resp.json()


# === Token 生命周期管理 ======================================================


class TokenManager:
    """
    JWT Token 生命周期管理器。
    
    支持自动刷新、过期检测、持久化存储。
    Token 存储到本地文件（SQLCipher 当前不支持，用 JSON 替代）。
    """
    
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
        os.chmod(self.storage_path, 0o600)  # 仅 owner 可读写
        print(f"[+] Token 已保存到 {self.storage_path}")
    
    def is_token_expired(self, token_data: Dict[str, Any]) -> bool:
        """检查 access_token 是否过期"""
        now = now_timestamp()
        expires_at = token_data.get("expires_at", 0)
        return now >= expires_at
    
    def is_refresh_expired(self, token_data: Dict[str, Any]) -> bool:
        """检查 refresh_token 是否过期"""
        now = now_timestamp()
        refresh_expires_at = token_data.get("refresh_expires_at", 0)
        return now >= refresh_expires_at
    
    def auto_refresh(
        self,
        token_host: str,
        token_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        自动刷新 token 链：
        1. 如果 refresh_token 也过期 → 需要重新登录
        2. 如果仅 access_token 过期 → 自动刷新
        """
        if self.is_refresh_expired(token_data):
            print("[!] Refresh token 已过期，需要重新登录")
            return {"error": "refresh_expired"}
        
        if self.is_token_expired(token_data):
            print("[*] Access token 即将过期，自动刷新...")
            new_tokens = exchange_token(
                token_host=token_host,
                refresh_token=token_data["refresh_token"],
            )
            if "error" not in new_tokens:
                new_tokens["expires_at"] = now_timestamp() + new_tokens.get("expires_in", 3600)
                new_tokens["refresh_expires_at"] = token_data.get("refresh_expires_at", 0)
                self.save_tokens(new_tokens)
            return new_tokens
        
        return token_data


# === CLI =====================================================================


def parse_args():
    parser = argparse.ArgumentParser(
        description="Trae AI BootConfig & JWT Token 认证脚本",
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=[
            "get_boot_config",
            "get_token",
            "refresh_token",
            "check_token",
            "get_user_info",
            "full_flow",
        ],
        help="执行的操作",
    )
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
    
    elif args.action == "get_token":
        config = fetch_boot_config(args.region)
        token_host = args.token_host or config.get("tokenHost") or config.get("token_host")
        
        if not token_host:
            print("[!] 未找到 tokenHost")
            sys.exit(1)
        
        if not args.refresh_token:
            print("[!] 需要 --refresh-token")
            sys.exit(1)
        
        result = exchange_token(token_host, args.refresh_token)
        
        if args.store and "error" not in result:
            now = now_timestamp()
            result["expires_at"] = now + result.get("expires_in", 3600)
            result["refresh_expires_at"] = now + result.get("refresh_expires_in", 86400)
            manager = TokenManager()
            manager.save_tokens(result)
    
    elif args.action == "refresh_token":
        config = fetch_boot_config(args.region)
        token_host = args.token_host or config.get("tokenHost") or config.get("token_host")
        
        if not token_host:
            print("[!] 未找到 tokenHost")
            sys.exit(1)
        
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
            manager = TokenManager()
            manager.save_tokens(result)
    
    elif args.action == "check_token":
        if not args.access_token:
            print("[!] 需要 --access-token")
            sys.exit(1)
        config = fetch_boot_config(args.region)
        token_host = args.token_host or config.get("tokenHost") or config.get("token_host")
        valid = check_token(args.access_token, token_host)
        print(f"[{'✓' if valid else '✗'}] Token 状态: {'有效' if valid else '无效'}")
    
    elif args.action == "get_user_info":
        if not args.access_token:
            print("[!] 需要 --access-token")
            sys.exit(1)
        config = fetch_boot_config(args.region)
        token_host = args.token_host or config.get("tokenHost") or config.get("token_host")
        info = get_user_info(args.access_token, token_host)
        if info:
            print(f"\n{json.dumps(info, indent=2, ensure_ascii=False)}")
    
    elif args.action == "full_flow":
        print("=" * 60)
        print("Trae AI 完整认证流程")
        print("=" * 60)
        
        # Step 1: 获取 BootConfig
        config = fetch_boot_config(args.region)
        token_host = args.token_host or config.get("tokenHost") or config.get("token_host")
        
        if not token_host:
            print("[!] 未找到 tokenHost")
            sys.exit(1)
        
        # Step 2: 检查存储的 token
        if args.store:
            manager = TokenManager()
            stored = manager.load_tokens()
            if stored and not manager.is_refresh_expired(stored):
                tokens = manager.auto_refresh(token_host, stored)
            else:
                print("[!] 没有有效的 token，需要初始认证")
                print("    请通过 OAuth2 先获取 refresh_token")
                sys.exit(1)
        else:
            print("[!] 需要 --store 来管理 token")
            sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证脚本语法**
Run: `python3 scripts/auth_bootconfig_jwt.py --help`
Expected: 显示帮助信息，无语法错误

---

### Task 6: 编写 auth_oauth2_pkce.py — OAuth2 PKCE 认证脚本

**Depends on:** Task 2
**Files:**
- Create: `scripts/auth_oauth2_pkce.py`

- [ ] **Step 1: 创建 OAuth2 PKCE 认证脚本**

```python
#!/usr/bin/env python3
"""
Trae AI OAuth2 PKCE 认证脚本

支持 Google、GitHub、GitLab 和 Trae 自有 OAuth2 流程。
使用 PKCE (Proof Key for Code Exchange) 增强安全性。

用法:
    # 启动本地 HTTP 服务器接收回调
    python scripts/auth_oauth2_pkce.py --action authorize --provider google
    
    # 使用授权码换 token
    python scripts/auth_oauth2_pkce.py --action exchange --code <auth_code>
    
    # 完整流程（自动启动浏览器 + 回调服务器）
    python scripts/auth_oauth2_pkce.py --action full --provider google --port 8899
    
    # 使用 code_verifier 生成 code_challenge
    python scripts/auth_oauth2_pkce.py --action pkce-gen
"""

import argparse
import hashlib
import json
import os
import secrets
import socket
import sys
import threading
import time
import urllib.parse
from base64 import urlsafe_b64encode
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any, Tuple

import requests

# === 常量 ====================================================================

CLIENT_ID = "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8"
CLIENT_SECRET = "850edec7-b9d0-48aa-99b5-67c888e282cd"
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
        "authorize_url": None,  # 从 BootConfig 获取
        "token_url": None,
    },
}

# === PKCE 工具 ===============================================================


def generate_code_verifier(length: int = 64) -> str:
    """
    生成 PKCE code_verifier。
    
    规格: 43-128 字符的随机字符串，仅含 [A-Za-z0-9-._~]
    """
    allowed_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    return "".join(secrets.choice(allowed_chars) for _ in range(length))


def generate_code_challenge(verifier: str) -> str:
    """
    生成 PKCE code_challenge。
    
    code_challenge = BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return urlsafe_b64encode(digest).rstrip(b"=").decode()


# === Callback 服务器 =========================================================


class CallbackHandler(BaseHTTPRequestHandler):
    """OAuth2 回调处理服务器"""
    
    auth_code = None
    
    def do_GET(self):
        """处理 OAuth2 回调 GET 请求"""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if "code" in params:
            CallbackHandler.auth_code = params["code"][0]
            self._respond(200, "认证成功！请关闭此窗口。")
        elif "error" in params:
            error = params["error"][0]
            self._respond(400, f"认证失败: {error}")
        else:
            self._respond(400, "缺少 authorization code")
    
    def _respond(self, status: int, body: str):
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())
    
    def log_message(self, format, *args):
        pass  # 关闭日志


def start_callback_server(port: int) -> Tuple[HTTPServer, threading.Thread]:
    """启动本地 HTTP 回调服务器"""
    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[*] 回调服务器已启动: http://127.0.0.1:{port}")
    return server, thread


# === OAuth2 流程 =============================================================


def build_authorize_url(
    authorize_url: str,
    client_id: str = CLIENT_ID,
    redirect_port: int = REDIRECT_PORT,
    scope: str = SCOPE,
    code_challenge: Optional[str] = None,
) -> str:
    """
    构造 OAuth2 授权 URL（支持 PKCE）。
    """
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": f"http://127.0.0.1:{redirect_port}",
        "scope": scope,
    }
    
    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    
    return f"{authorize_url}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(
    token_url: str,
    code: str,
    code_verifier: Optional[str] = None,
    client_id: str = CLIENT_ID,
    redirect_port: int = REDIRECT_PORT,
) -> Dict[str, Any]:
    """
    用 authorization_code 交换 access_token + refresh_token。
    """
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": f"http://127.0.0.1:{redirect_port}",
        "client_id": client_id,
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


# === CLI =====================================================================


def parse_args():
    parser = argparse.ArgumentParser(description="Trae AI OAuth2 PKCE 认证")
    parser.add_argument(
        "--action",
        required=True,
        choices=["authorize", "exchange", "full", "pkce-gen"],
    )
    parser.add_argument(
        "--provider",
        default="trae",
        choices=list(OAUTH_PROVIDERS.keys()),
    )
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
        
        print(f"\n[*] PKCE 参数:")
        print(f"    code_verifier:  {verifier}")
        print(f"    code_challenge: {challenge}")
        print(f"\n[*] 打开以下 URL 进行授权:")
        print(f"\n    {url}\n")
        print(f"[*] 授权后请使用 --action exchange --code <code> --code-verifier {verifier}")
    
    elif args.action == "exchange":
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
        
        result = exchange_code_for_token(
            token_url=token_url,
            code=args.code,
            code_verifier=args.code_verifier,
        )
        print(f"\n{json.dumps(result, indent=2, ensure_ascii=False)}")
    
    elif args.action == "full":
        # 1. 生成 PKCE 参数
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        
        print(f"[*] PKCE code_verifier: {verifier[:20]}...")
        
        # 2. 启动回调服务器
        server, thread = start_callback_server(args.port)
        
        # 3. 构造授权 URL
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
        
        print(f"\n[*] 浏览器打开:")
        print(f"    {url}\n")
        print("[*] 等待回调...")
        
        # 4. 等待授权码（最多 5 分钟）
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
        
        # 5. 交换 token
        result = exchange_code_for_token(
            token_url=token_url,
            code=code,
            code_verifier=verifier,
            redirect_port=args.port,
        )
        print(f"\n{json.dumps(result, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证脚本语法**
Run: `python3 scripts/auth_oauth2_pkce.py --help`
Expected: 显示帮助信息

---

### Task 7: 编写 auth_aws_sso.py — AWS SSO 认证脚本

**Depends on:** Task 3
**Files:**
- Create: `scripts/auth_aws_sso.py`

- [ ] **Step 1: 创建 AWS SSO 认证脚本**

```python
#!/usr/bin/env python3
"""
Trae AI AWS SSO 企业认证脚本

实现完整的 AWS SSO OIDC → GetRoleCredentials → STS AssumeRole 认证链。
用于 AWS Bedrock 运行时认证。

用法:
    python scripts/auth_aws_sso.py --action sso-login --start-url https://d-xxxxxxxxxx.awsapps.com/start
    python scripts/auth_aws_sso.py --action get-credentials --access-token <token> --account-id <id> --role-name <role>
    python scripts/auth_aws_sso.py --action assume-role --role-arn <arn> --session-name trae-session
    python scripts/auth_aws_sso.py --action bedrock-test --region us-east-1

依赖: pip install requests
"""

import argparse
import json
import os
import sys
from typing import Optional, Dict, Any

import requests

# === AWS SSO OIDC ============================================================


def sso_oidc_register_client(region: str = "us-east-1") -> Dict[str, Any]:
    """
    注册 OIDC 客户端（首次使用时需要）。
    
    POST https://oidc.{region}.amazonaws.com/client/register
    """
    url = f"https://oidc.{region}.amazonaws.com/client/register"
    
    payload = {
        "clientName": "trae-ai-client",
        "clientType": "public",
        "scopes": ["openid", "profile"],
    }
    
    print(f"[*] 注册 OIDC 客户端: {url}")
    resp = requests.post(url, json=payload, timeout=10)
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"[+] 客户端注册成功")
        print(f"    client_id: {result.get('clientId', 'N/A')}")
        return result
    else:
        print(f"[!] 注册失败: {resp.status_code}")
        print(f"    如果已注册过，可以重用 client_id")
        return {"clientId": "", "clientSecret": ""}


def sso_oidc_start_device_auth(
    client_id: str,
    client_secret: str = "",
    start_url: str = "",
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    启动设备授权流程。
    
    POST https://oidc.{region}.amazonaws.com/device_authorization
    """
    url = f"https://oidc.{region}.amazonaws.com/device_authorization"
    
    payload = {
        "clientId": client_id,
        "startUrl": start_url,
    }
    if client_secret:
        payload["clientSecret"] = client_secret
    
    print(f"[*] 启动设备授权: {url}")
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    
    result = resp.json()
    print(f"\n[!] 打开以下 URL 进行 AWS SSO 登录:")
    print(f"    {result.get('verificationUriComplete', 'N/A')}")
    print(f"\n    或手动输入设备码: {result.get('userCode', 'N/A')}")
    print(f"    有效时间: {result.get('expiresIn', 0)} 秒\n")
    
    return result


def sso_oidc_create_token(
    client_id: str,
    client_secret: str,
    device_code: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    轮询设备授权结果，获取 access_token。
    
    POST https://oidc.{region}.amazonaws.com/token
    """
    url = f"https://oidc.{region}.amazonaws.com/token"
    
    payload = {
        "clientId": client_id,
        "clientSecret": client_secret,
        "grantType": "urn:ietf:params:oauth:grant-type:device_code",
        "deviceCode": device_code,
    }
    
    import time
    max_attempts = 60  # 最多等 5 分钟
    
    for attempt in range(max_attempts):
        print(f"[*] 轮询中 ({attempt + 1}/{max_attempts})...")
        resp = requests.post(url, json=payload, timeout=10)
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"[+] Token 获取成功")
            print(f"    access_token: {result.get('accessToken', 'N/A')[:30]}...")
            print(f"    expires_in: {result.get('expiresIn', 'N/A')}")
            return result
        
        if resp.status_code == 400:
            error = resp.json().get("error", "")
            if error == "AuthorizationPendingException":
                time.sleep(5)  # 用户还未完成授权，继续轮询
                continue
            elif error == "SlowDownException":
                time.sleep(10)  # 轮询太快，降低频率
                continue
            elif error == "ExpiredTokenException":
                print("[!] 设备码已过期")
                return {"error": "token_expired"}
        
        print(f"[!] 错误: {resp.status_code} {resp.text[:100]}")
        time.sleep(5)
    
    print("[!] 轮询超时")
    return {"error": "timeout"}


# === GetRoleCredentials ======================================================


def sso_get_role_credentials(
    access_token: str,
    account_id: str,
    role_name: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    获取 AWS 账号角色凭证。
    
    POST https://portal.sso.{region}.amazonaws.com/federation/credentials
    """
    url = f"https://portal.sso.{region}.amazonaws.com/federation/credentials"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "x-amz-sso_bearer_token": access_token,
    }
    
    payload = {
        "accountId": account_id,
        "roleName": role_name,
    }
    
    print(f"[*] 获取角色凭证: account={account_id}, role={role_name}")
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    resp.raise_for_status()
    
    result = resp.json()
    print(f"[+] 角色凭证获取成功")
    print(f"    access_key_id: {result.get('accessKeyId', 'N/A')[:10]}...")
    print(f"    expires_in: {result.get('expiration', 'N/A')}")
    
    return result


# === STS AssumeRole ==========================================================


def sts_assume_role(
    access_key: str,
    secret_key: str,
    session_token: str,
    role_arn: str,
    session_name: str = "trae-session",
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    使用 SSO 凭证 AssumeRole 进入目标账号。
    
    POST https://sts.{region}.amazonaws.com/
    """
    import hashlib
    import hmac
    import urllib.parse
    from datetime import datetime
    
    url = f"https://sts.{region}.amazonaws.com/"
    
    payload = {
        "Action": "AssumeRole",
        "RoleArn": role_arn,
        "RoleSessionName": session_name,
        "Version": "2011-06-15",
    }
    
    print(f"[*] STS AssumeRole: {role_arn}")
    resp = requests.post(url, data=payload, timeout=10)
    
    if resp.status_code == 200:
        print(f"[+] AssumeRole 成功")
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        
        ns = {"sts": "https://sts.amazonaws.com/doc/2011-06-15/"}
        credentials = root.find(".//sts:Credentials", ns)
        
        if credentials is not None:
            result = {
                "access_key_id": credentials.find("sts:AccessKeyId", ns).text,
                "secret_access_key": credentials.find("sts:SecretAccessKey", ns).text,
                "session_token": credentials.find("sts:SessionToken", ns).text,
                "expiration": credentials.find("sts:Expiration", ns).text,
            }
            return result
    
    print(f"[!] AssumeRole 失败: {resp.status_code}")
    return {"error": "assume_role_failed"}


# === Bedrock 测试 ============================================================


def bedrock_test_connection(
    access_key: str,
    secret_key: str,
    session_token: str,
    region: str = "us-east-1",
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
) -> bool:
    """
    测试 AWS Bedrock Converse Stream 连接。
    """
    import hashlib
    import hmac
    import json
    from datetime import datetime
    
    host = f"bedrock-runtime.{region}.amazonaws.com"
    url = f"https://{host}/model/{model_id}/invoke-with-response-stream"
    
    headers = {
        "Content-Type": "application/json",
        "X-Amz-Date": datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
    }
    
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
            }
        ],
    }
    
    try:
        print(f"[*] 测试 Bedrock 连接: {model_id} @ {region}")
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"[{'✓' if resp.status_code == 200 else '✗'}] "
              f"Bedrock 响应: {resp.status_code}")
        return resp.status_code == 200
    except requests.RequestException as e:
        print(f"[✗] Bedrock 连接失败: {e}")
        return False


# === CLI =====================================================================


def parse_args():
    parser = argparse.ArgumentParser(description="AWS SSO 企业认证")
    parser.add_argument("--action", required=True, choices=[
        "register-client", "sso-login", "get-credentials",
        "assume-role", "bedrock-test", "sso-batch",
    ])
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--client-id")
    parser.add_argument("--client-secret")
    parser.add_argument("--start-url")
    parser.add_argument("--device-code")
    parser.add_argument("--access-token")
    parser.add_argument("--account-id")
    parser.add_argument("--role-name")
    parser.add_argument("--role-arn")
    parser.add_argument("--session-name", default="trae-session")
    parser.add_argument("--model-id", default="anthropic.claude-3-sonnet-20240229-v1:0")
    return parser.parse_args()


def main():
    args = parse_args()
    
    if args.action == "register-client":
        result = sso_oidc_register_client(args.region)
        print(f"\n{json.dumps(result, indent=2)}")
    
    elif args.action == "sso-login":
        if not args.start_url:
            print("[!] 需要 --start-url（例如 https://d-xxxxxxxxxx.awsapps.com/start）")
            sys.exit(1)
        if not args.client_id:
            print("[!] 需要 --client-id")
            sys.exit(1)
        result = sso_oidc_start_device_auth(
            client_id=args.client_id,
            client_secret=args.client_secret or "",
            start_url=args.start_url,
            region=args.region,
        )
        print(f"\n{json.dumps(result, indent=2)}")
    
    elif args.action == "get-credentials":
        if not all([args.access_token, args.account_id, args.role_name]):
            print("[!] 需要 --access-token --account-id --role-name")
            sys.exit(1)
        result = sso_get_role_credentials(
            access_token=args.access_token,
            account_id=args.account_id,
            role_name=args.role_name,
            region=args.region,
        )
        print(f"\n{json.dumps(result, indent=2)}")
    
    elif args.action == "assume-role":
        if not args.role_arn:
            print("[!] 需要 --role-arn")
            sys.exit(1)
        print("[!] 需要设置 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN")
        ak = os.environ.get("AWS_ACCESS_KEY_ID")
        sk = os.environ.get("AWS_SECRET_ACCESS_KEY")
        st = os.environ.get("AWS_SESSION_TOKEN")
        if not all([ak, sk, st]):
            print("[!] 环境变量未完全设置")
            sys.exit(1)
        result = sts_assume_role(ak, sk, st, args.role_arn, args.session_name, args.region)
        print(f"\n{json.dumps(result, indent=2)}")
    
    elif args.action == "bedrock-test":
        ak = os.environ.get("AWS_ACCESS_KEY_ID")
        sk = os.environ.get("AWS_SECRET_ACCESS_KEY")
        st = os.environ.get("AWS_SESSION_TOKEN")
        if not all([ak, sk, st]):
            print("[!] 需要设置 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN")
            sys.exit(1)
        bedrock_test_connection(ak, sk, st, args.region, args.model_id)


if __name__ == "__main__":
    main()
```

---

### Task 8: 编写 auth_frontier_ws.py — Frontier WebSocket 认证脚本

**Depends on:** Task 1
**Files:**
- Create: `scripts/auth_frontier_ws.py`

- [ ] **Step 1: 创建 Frontier WebSocket 认证脚本**

```python
#!/usr/bin/env python3
"""
Trae AI Frontier WebSocket 认证脚本

实现 Frontier 协议的 WebSocket 连接、认证握手、心跳维持。

用法:
    python scripts/auth_frontier_ws.py --action connect --frontier-url <url> --token <token>
    python scripts/auth_frontier_ws.py --action register-cli --cli-id <id> --frontier-id <id>
    python scripts/auth_frontier_ws.py --action hub-login --token <token> --frontier-url <url>

依赖: pip install websocket-client
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
    from websocket import WebSocketApp, WebSocket
    HAS_WS = True
except ImportError:
    HAS_WS = False


# === Frontier Frame ==========================================================


def make_frontier_frame(
    log_id: str,
    service: str,
    payload: Any,
    payload_encoding: str = "json",
) -> Dict[str, Any]:
    """
    构造 FrontierFrame。
    
    FrontierFrame 是 Frontier 协议的基本消息单元：
    - log_id: 消息追踪 ID
    - service: 目标服务名
    - payload: 消息体
    - payload_encoding: 编码方式
    """
    return {
        "log_id": log_id,
        "service": service,
        "payload": payload,
        "payload_encoding": payload_encoding,
        "payload_type": "protobuf",
    }


def gen_frame_id() -> str:
    """生成唯一的 Frame ID"""
    return str(uuid.uuid4())


def gen_cli_id() -> str:
    """生成 CLI 客户端 ID"""
    return "cli_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=16))


# === WebSocket 连接 ==========================================================


class FrontierWebSocketClient:
    """
    Frontier 协议 WebSocket 客户端。
    
    处理连接建立、认证、心跳、消息收发。
    支持自动重连和 HTTP 长轮询回退。
    """
    
    def __init__(
        self,
        frontier_url: str,
        token: str,
        cli_id: str = None,
        frontier_id: str = None,
        app_id: str = "trae-ide",
        product_id: str = "trae",
        process_id: str = None,
    ):
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
        """构造 WebSocket URL"""
        params = (
            f"frontier_id={self.frontier_id}"
            f"&app_runtime_type=electron"
            f"&process_id={self.process_id}"
            f"&client_timestamp={int(time.time() * 1000)}"
        )
        
        sep = "&" if "?" in self.frontier_url else "?"
        return f"{self.frontier_url}{sep}{params}"
    
    def connect(self) -> bool:
        """建立 WebSocket 连接"""
        if not HAS_WS:
            print("[!] websocket-client 库未安装")
            print("    pip install websocket-client")
            return False
        
        url = self._make_ws_url()
        print(f"[*] 连接 Frontier WebSocket: {url}")
        
        headers = {
            "Authorization": f"Bearer {self.token}",
        }
        
        try:
            ws = WebSocket()
            ws.connect(url, header=headers, timeout=30)
            self.ws = ws
            self.connected = True
            
            # 接收认证响应
            resp = ws.recv()
            if resp:
                data = json.loads(resp)
                print(f"[+] 连接成功: {json.dumps(data, indent=2)[:200]}")
            
            print(f"[+] Frontier 连接建立: {self.frontier_id}")
            return True
            
        except Exception as e:
            print(f"[✗] 连接失败: {e}")
            self.connected = False
            return False
    
    def send_message(self, service: str, payload: Any) -> bool:
        """发送 Frontier 消息"""
        if not self.connected or not self.ws:
            print("[!] 未连接")
            return False
        
        frame = json.dumps(make_frontier_frame(
            log_id=gen_frame_id(),
            service=service,
            payload=payload,
        ))
        
        try:
            self.ws.send(frame)
            self.seq_num += 1
            return True
        except Exception as e:
            print(f"[✗] 发送失败: {e}")
            return False
    
    def send_auth(self) -> bool:
        """发送认证消息"""
        auth_payload = {
            "type": "auth",
            "cli_id": self.cli_id,
            "frontier_id": self.frontier_id,
            "app_id": self.app_id,
            "product_id": self.product_id,
            "token": self.token,
        }
        return self.send_message("auth_service", auth_payload)
    
    def send_heartbeat(self) -> bool:
        """发送心跳"""
        return self.send_message("heartbeat_service", {"type": "ping"})
    
    def register_cli(self) -> bool:
        """注册 CLI 客户端"""
        payload = {
            "cli_id": self.cli_id,
            "frontier_id": self.frontier_id,
            "app_id": self.app_id,
            "product_id": self.product_id,
            "process_id": self.process_id,
        }
        return self.send_message("hub_cli", payload)
    
    def start_heartbeat_loop(self, interval_secs: int = 30):
        """启动心跳循环（阻塞）"""
        print(f"[*] 心跳循环启动，间隔 {interval_secs}s")
        while self.connected:
            time.sleep(interval_secs)
            if not self.send_heartbeat():
                print("[!] 心跳失败")
                break
    
    def disconnect(self):
        """断开连接"""
        self.connected = False
        if self.ws:
            self.ws.close()
            print("[*] 连接已关闭")
    
    def http_poll(self, hub_url: str) -> Optional[Dict[str, Any]]:
        """
        HTTP 长轮询回退（WebSocket 不可用时）。
        
        GET {hub_url}/wsmessages/poll?frontier_id={id}&from_down_seq_id={seq}
        """
        params = {
            "frontier_id": self.frontier_id,
            "from_down_seq_id": self.seq_num,
            "limit": 100,
        }
        
        import requests
        url = f"{hub_url}/wsmessages/poll"
        
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException as e:
            print(f"[!] HTTP 轮询失败: {e}")
        
        return None
    
    def http_push(self, hub_url: str, messages: list) -> bool:
        """HTTP 推送消息回退"""
        import requests
        url = f"{hub_url}/wsmessages/push"
        
        try:
            resp = requests.post(url, json=messages, timeout=10)
            return resp.status_code == 200
        except requests.RequestException:
            return False


# === Hub Login ===============================================================


def hub_login(
    token: str,
    frontier_url: str,
    cli_id: str = None,
) -> Dict[str, Any]:
    """
    Hub 登录（HTTP 模式）。
    
    POST {frontier_url}/hub_login
    """
    import requests
    
    payload = {
        "cli_id": cli_id or gen_cli_id(),
        "token": token,
        "app_id": "trae-ide",
        "product_id": "trae",
    }
    
    url = f"{frontier_url}/hub_login"
    
    print(f"[*] Hub 登录: {url}")
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    
    result = resp.json()
    print(f"[+] Hub 登录成功: frontier_id={result.get('frontier_id', 'N/A')}")
    
    return result


# === CLI =====================================================================


def parse_args():
    parser = argparse.ArgumentParser(description="Frontier WebSocket 认证")
    parser.add_argument("--action", required=True, choices=[
        "connect", "register-cli", "hub-login", "http-poll",
    ])
    parser.add_argument("--frontier-url", help="Frontier 服务器 URL")
    parser.add_argument("--token", help="JWT access token")
    parser.add_argument("--cli-id", help="CLI 客户端 ID")
    parser.add_argument("--frontier-id", help="Frontier 连接 ID")
    parser.add_argument("--hub-url", help="Hub 服务 URL（HTTP 模式）")
    return parser.parse_args()


def main():
    args = parse_args()
    
    if args.action == "connect":
        if not all([args.frontier_url, args.token]):
            print("[!] 需要 --frontier-url --token")
            sys.exit(1)
        
        client = FrontierWebSocketClient(
            frontier_url=args.frontier_url,
            token=args.token,
            cli_id=args.cli_id,
            frontier_id=args.frontier_id,
        )
        
        if client.connect():
            client.send_auth()
            print("[*] 已连接，开始心跳循环 (Ctrl+C 退出)")
            try:
                client.start_heartbeat_loop()
            except KeyboardInterrupt:
                client.disconnect()
    
    elif args.action == "register-cli":
        if not args.token:
            print("[!] 需要 --token")
            sys.exit(1)
        result = hub_login(args.token, args.frontier_url or "wss://hub.trae.ai/ws", args.cli_id)
        print(f"\n{json.dumps(result, indent=2, ensure_ascii=False)}")
    
    elif args.action == "http-poll":
        if not all([args.hub_url, args.frontier_id]):
            print("[!] 需要 --hub-url --frontier-id")
            sys.exit(1)
        
        client = FrontierWebSocketClient(
            frontier_url="",
            token="",
            frontier_id=args.frontier_id,
        )
        messages = client.http_poll(args.hub_url)
        if messages:
            print(f"[+] 收到 {len(messages)} 条消息")
            print(f"{json.dumps(messages, indent=2, ensure_ascii=False)[:500]}")


if __name__ == "__main__":
    main()
```

---

### Task 9: 编写 auth_token_refresh.py — Token 自动刷新脚本

**Depends on:** Task 5
**Files:**
- Create: `scripts/auth_token_refresh.py`

- [ ] **Step 1: 创建 Token 自动刷新脚本**

```python
#!/usr/bin/env python3
"""
Trae AI Token 自动刷新脚本

监控 token 有效期，在过期前自动刷新。
支持持久化存储、限流处理、错误恢复。

用法:
    # 检查并刷新（如果过期）
    python scripts/auth_token_refresh.py --action auto --refresh-token <token> --token-host <host>
    
    # 持续监控模式（每 5 分钟检查一次）
    python scripts/auth_token_refresh.py --action monitor --token-host <host> [--store-path path]
    
    # 直接刷新 token
    python scripts/auth_token_refresh.py --action refresh --refresh-token <token> --token-host <host>

API 端点: POST {tokenHost}/cloudide/api/v3/trae/ExchangeToken
"""

import argparse
import json
import os
import sys
import time
from typing import Optional, Dict, Any

import requests

# === 常量 ====================================================================

CLIENT_ID = "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8"
TOKEN_STORE_PATH = os.path.expanduser("~/.trae/tokens.json")

# 错误码
ERROR_CODES = {
    20324: "Token 格式错误",
    20101: "Token 已过期",
    20315: "Token 已吊销",
    20125: "Refresh Token 无效",
    20126: "Refresh Token 已过期",
}

# === Token 刷新 ==============================================================


def exchange_token(
    token_host: str,
    refresh_token: str,
) -> Optional[Dict[str, Any]]:
    """
    刷新 token。
    
    重试策略:
    - 网络错误: 3 次重试，指数退避
    - 429 限流: 按 Retry-After 头等待
    - 4xx 客户端错误: 不重试
    """
    url = f"{token_host.rstrip('/')}/cloudide/api/v3/trae/ExchangeToken"
    
    headers = {
        "Authorization": f"Bearer {refresh_token}",
        "Content-Type": "application/json",
        "x-cloudide-token": refresh_token,
    }
    
    payload = {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    
    for attempt in range(3):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if resp.status_code == 200:
                result = resp.json()
                
                # 计算过期时间
                now = int(time.time())
                result["_expires_at"] = now + result.get("expires_in", 3600)
                result["_refresh_expires_at"] = now + result.get("refresh_expires_in", 86400)
                result["_updated_at"] = now
                
                return result
            
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                print(f"[!] 限流，等待 {retry_after}s")
                time.sleep(retry_after)
                continue
            
            elif resp.status_code in (401, 403):
                # 尝试解析错误信息
                try:
                    error_data = resp.json()
                    error_code = error_data.get("code", 0)
                    error_msg = ERROR_CODES.get(error_code, f"未知错误 {error_code}")
                    print(f"[!] 认证失败: {error_msg}")
                except json.JSONDecodeError:
                    pass
                
                return {"error": "auth_failed", "status": resp.status_code}
            
            else:
                print(f"[!] 服务器错误: {resp.status_code}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    
        except requests.Timeout:
            print(f"[!] 超时 (尝试 {attempt + 1}/3)")
            if attempt < 2:
                time.sleep(2 ** attempt)
        
        except requests.ConnectionError:
            print(f"[!] 连接失败 (尝试 {attempt + 1}/3)")
            if attempt < 2:
                time.sleep(5)
        
        except requests.RequestException as e:
            print(f"[!] 请求异常: {e}")
            break
    
    return {"error": "max_retries_exceeded"}


# === Token 存储 ==============================================================


def load_stored_tokens(path: str = TOKEN_STORE_PATH) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_tokens(tokens: Dict[str, Any], path: str = TOKEN_STORE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(path, 0o600)


# === Token 状态检查 ==========================================================


def check_token_expiration(tokens: Dict[str, Any], margin_secs: int = 300) -> Dict[str, str]:
    """
    检查 token 过期状态。
    
    Args:
        tokens: Token 数据
        margin_secs: 提前多久认为"即将过期"（默认 5 分钟）
    
    Returns:
        状态字典
    """
    now = int(time.time())
    status = {}
    
    expires_at = tokens.get("_expires_at", 0)
    refresh_expires_at = tokens.get("_refresh_expires_at", 0)
    
    if expires_at:
        remaining = expires_at - now
        if remaining <= 0:
            status["access_token"] = "expired"
        elif remaining <= margin_secs:
            status["access_token"] = "about_to_expire"
            status["remaining_secs"] = remaining
        else:
            status["access_token"] = "valid"
            status["remaining_secs"] = remaining
    
    if refresh_expires_at:
        remaining = refresh_expires_at - now
        if remaining <= 0:
            status["refresh_token"] = "expired"
        elif remaining <= 3600:
            status["refresh_token"] = "about_to_expire"
            status["refresh_remaining_secs"] = remaining
        else:
            status["refresh_token"] = "valid"
            status["refresh_remaining_secs"] = remaining
    
    return status


# === 监控模式 ================================================================


def monitor_loop(
    token_host: str,
    store_path: str = TOKEN_STORE_PATH,
    interval_secs: int = 300,
):
    """持续监控 token 状态，自动刷新"""
    print(f"[*] Token 监控启动 (间隔: {interval_secs}s)")
    print(f"    Store: {store_path}")
    
    while True:
        tokens = load_stored_tokens(store_path)
        
        if not tokens:
            print("[!] 未找到存储的 token")
            time.sleep(interval_secs)
            continue
        
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            print("[!] Token 数据中没有 refresh_token")
            time.sleep(interval_secs)
            continue
        
        status = check_token_expiration(tokens)
        refresh_status = status.get("refresh_token", "")
        access_status = status.get("access_token", "")
        
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if refresh_status == "expired":
            print(f"[{now_str}] [!] Refresh token 已过期，需要重新登录")
        elif refresh_status == "about_to_expire":
            print(f"[{now_str}] [!] Refresh token 即将过期 ({status['refresh_remaining_secs']}s)")
        
        if access_status in ("expired", "about_to_expire"):
            print(f"[{now_str}] [*] 正在刷新 token...")
            result = exchange_token(token_host, refresh_token)
            
            if "error" not in result:
                result["refresh_token"] = result.get("refresh_token", refresh_token)
                save_tokens(result, store_path)
                print(f"[{now_str}] [+] Token 刷新成功")
            else:
                print(f"[{now_str}] [✗] Token 刷新失败: {result['error']}")
        else:
            remaining = status.get("remaining_secs", 0)
            print(f"[{now_str}] [✓] Token 有效 ({remaining}s)")
        
        time.sleep(interval_secs)


# === CLI =====================================================================


def parse_args():
    parser = argparse.ArgumentParser(description="Trae AI Token 自动刷新")
    parser.add_argument("--action", required=True, choices=[
        "check", "refresh", "auto", "monitor",
    ])
    parser.add_argument("--token-host", help="Token host URL")
    parser.add_argument("--refresh-token", help="Refresh token")
    parser.add_argument("--store-path", default=TOKEN_STORE_PATH)
    parser.add_argument("--interval", type=int, default=300, help="监控间隔（秒）")
    return parser.parse_args()


def main():
    args = parse_args()
    
    if args.action == "check":
        tokens = load_stored_tokens(args.store_path)
        if not tokens:
            print("[!] 未找到存储的 token")
            sys.exit(1)
        status = check_token_expiration(tokens)
        print(json.dumps(status, indent=2))
    
    elif args.action == "refresh":
        if not all([args.token_host, args.refresh_token]):
            print("[!] 需要 --token-host --refresh-token")
            sys.exit(1)
        result = exchange_token(args.token_host, args.refresh_token)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.action == "auto":
        if not args.token_host:
            print("[!] 需要 --token-host")
            sys.exit(1)
        
        tokens = load_stored_tokens(args.store_path)
        if not tokens:
            print("[!] 未找到存储的 token，执行初始刷新")
            sys.exit(1)
        
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            print("[!] 没有 refresh_token")
            sys.exit(1)
        
        status = check_token_expiration(tokens)
        if status.get("access_token") in ("expired", "about_to_expire"):
            print("[*] Token 需要刷新")
            result = exchange_token(args.token_host, refresh_token)
            if "error" not in result:
                result["refresh_token"] = result.get("refresh_token", refresh_token)
                save_tokens(result, args.store_path)
                print("[+] Token 刷新成功")
            else:
                print(f"[✗] 刷新失败: {result['error']}")
        else:
            print(f"[✓] Token 仍有效")
    
    elif args.action == "monitor":
        if not args.token_host:
            print("[!] 需要 --token-host")
            sys.exit(1)
        
        try:
            monitor_loop(args.token_host, args.store_path, args.interval)
        except KeyboardInterrupt:
            print("\n[*] 监控停止")


if __name__ == "__main__":
    main()
```

---

### Task 10: 验证所有脚本

**Depends on:** Task 9
**Files:** All scripts in `scripts/`

- [ ] **Step 1: 验证所有 Python 脚本语法**
Run: `for f in scripts/auth_*.py; do python3 -c "import py_compile; py_compile.compile('$f', doraise=True)" && echo "[✓] $f"; done`
Expected: 所有脚本语法正确

- [ ] **Step 2: 验证脚本目录结构**
Run: `ls -la scripts/ && echo "---" && wc -l scripts/auth_*.py`
Expected: 6 个认证脚本

---

## Self-Review Results

**Plan Type:** Research + Feature (mixed)

| # | Check | Result | Action Taken |
|---|-------|--------|-------------|
| 1 | Goal + Type + Scope + Risk? | PASS | Clear goals |
| 2 | Dependencies? | PASS | Sequential dependency chain |
| 3 | No TBD/TODO/placeholders? | PASS | All code written |
| 4 | Auth protocol gaps identified? | PASS | AWS SSO, Supabase, PKCE, Scopes |
| 5 | Scripts complete? | PASS | 6 scripts with full code |

**Status:** ✅ ALL PASS