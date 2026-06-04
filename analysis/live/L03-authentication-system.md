# L03: 认证系统完整解析

> 生成时间: 2026-06-01 ~11:53 GMT+8  
> 分析版本: Trae IDE v2.3.30128

---

## 目录

1. [认证系统总览](#1-认证系统总览)
2. [BootConfig 启动配置](#2-bootconfig-启动配置)
3. [OAuth2 PKCE 流程](#3-oauth2-pkce-流程)
4. [Token 交换与刷新](#4-token-交换与刷新)
5. [多 Scope 认证系统](#5-多-scope-认证系统)
6. [Supabase OAuth 集成](#6-supabase-oauth-集成)
7. [AWS SSO/OIDC 企业认证](#7-aws-ssooidc-企业认证)
8. [Token 数据结构与生命周期](#8-token-数据结构与生命周期)
9. [认证头与 API 端点](#9-认证头与-api-端点)
10. [错误码参考](#10-错误码参考)
11. [完整认证流程图](#11-完整认证流程图)
12. [Token 存储与安全](#12-token-存储与安全)

---

## 1. 认证系统总览

Trae 的认证系统支持多种认证方式，按认证层级分为三层：

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Provider 认证                                       │
│  OAuth2 PKCE │ Supabase │ AWS SSO │ Enterprise SSO          │
│  Google │ GitHub │ GitLab │ ByteDance Internal              │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Trae Token 认证                                     │
│  BootConfig (icube-boot) → ExchangeToken → JWT               │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: API 认证                                            │
│  x-cloudide-token │ x-ide-token │ Authorization: Bearer     │
│  x-frontier-id (WebSocket 握手后获得)                        │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 支持的认证方式

| 认证方式 | 类型 | 适用场景 |
|---------|------|---------|
| Google OAuth2 | 授权码 + PKCE | 国际用户登录 |
| GitHub OAuth2 | 授权码 + PKCE | 开发者登录 |
| GitLab OAuth2 | 授权码 + PKCE | 开发者登录 |
| Supabase OAuth | 授权码 | 云端服务认证 |
| AWS SSO OIDC | 设备授权码 | 企业 AWS Bedrock 用户 |
| Enterprise SSO | SAML/OIDC | 企业客户 |
| ByteDance Internal | 自定义 | 字节内部员工 |
| CLI Token | Bearer | trae-cli 命令行 |
| Device Registration | 设备码 | 设备注册 |

---

## 2. BootConfig 启动配置

### 2.1 获取端点

```
GET https://icube-boot.trae.ai
GET https://icube-boot.trae.com.cn (中国区)
```

返回 JSON 配置，包含 17 个字段（从 main.js 和协议分析提取）：

```json
{
    "agent": { ... },           // Agent 配置
    "ckg": { ... },             // 代码知识图谱配置
    "hub": { ... },             // Hub Bridge 配置
    "imageHost": "string",      // 图片托管地址
    "tokenHost": "string",      // Token 服务器地址 (Bearer)
    "token_host": "string",     // Token 服务器地址 (旧格式)
    "userInfo": {               // 用户信息
        "expiredAt": 0,         // 过期时间 (Unix ms)
        "refreshExpiredAt": 0,  // Refresh 过期时间
        "userId": "string",     // 用户 ID
        "tokenReleaseAt": 0     // Token 释放时间
    },
    "imageX": { ... },          // 图片处理配置
    "cdnPrefix": "string",      // CDN 前缀
    "hostTmpDir": "string",     // 临时目录
    "storeRegion": "string",    // 存储区域
    "frontier": { ... },        // Frontier 协议配置
    "ugApi": "string",          // 用户图谱 API
    "ppeEnv": "string"          // PPE 环境标识
}
```

### 2.2 Token Host 列表

| 区域 | Token Host | Boot Endpoint |
|------|-----------|---------------|
| 国际 (US) | `https://token.trae.ai` | `https://icube-boot.trae.ai` |
| 中国 (CN) | `https://token.trae.com.cn` | `https://icube-boot.trae.com.cn` |
| 新加坡 (SG) | `https://api-sg-central.trae.ai` | 同上 |

### 2.3 BootConfig 用户信息 (`BootUserInfo`)

```javascript
// main.js 中检测到
{
    "user_id": "string",           // 用户标识
    "expired_at": 1735689600000,   // Token 过期时间戳 (ms)
    "refresh_expired_at": 0,       // Refresh 过期时间戳
    "token_release_at": 0          // Token 释放时间戳
}
```

---

## 3. OAuth2 PKCE 流程

### 3.1 Client ID

```javascript
CLIENT_ID = "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8"
AUTH_CLIENT_ID = "ono9krqynydwx5"   // Trae stable product.json client_id
```

### 3.2 PKCE 参数生成

```javascript
// code_verifier: 43-128 字符 [A-Za-z0-9-._~]
function generateCodeVerifier(length = 64) {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
    return Array.from({ length }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
}

// code_challenge: BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))
function generateCodeChallenge(verifier) {
    const digest = crypto.createHash('sha256').update(verifier).digest();
    return digest.toString('base64url').replace(/=+$/, '');
}
```

### 3.3 完整 OAuth2 PKCE 流程

```
┌─────────────────────┐         ┌──────────────────┐         ┌──────────────┐
│  Electron Main      │         │  Auth Server     │         │  OAuth       │
│  Process            │         │  (tokenHost)     │         │  Provider    │
└──────┬──────────────┘         └────────┬─────────┘         └──────┬───────┘
       │                                 │                         │
       │ 1. 生成 PKCE 参数                │                         │
       │    code_verifier (64 chars)      │                         │
       │    code_challenge = SHA256(...)  │                         │
       │                                 │                         │
       │ 2. 打开浏览器授权 URL            │                         │
       │    GET /oauth/authorize          │                         │
       │    ?response_type=code           │                         │
       │    &client_id=6eefa01c...        │                         │
       │    &redirect_uri=http://127.0.0.1│                         │
       │    &scope=marscode               │                         │
       │    &code_challenge=...           │                         │
       │    &code_challenge_method=S256   │                         │
       ├─────────────────────────────────►│                         │
       │                                 │  3. 重定向到 Provider   │
       │                                 ├────────────────────────►│
       │                                 │                         │
       │                                 │  4. 用户登录授权        │
       │                                 │   ←  授权码 (code) ────┤
       │                                 │                         │
       │ 5. 回调 HTTP 服务器接收 code     │                        │
       │    http://127.0.0.1:8899/?code= │                        │
       │                                 │                         │
       │ 6. POST /oauth/token            │                         │
       │    grant_type=authorization_code │                         │
       │    code={授权码}                 │                         │
       │    code_verifier={PKCE验证器}    │                         │
       │    redirect_uri=http://127.0.0.1 │                         │
       │    client_id=6eefa01c...        │                         │
       ├─────────────────────────────────►│                         │
       │                                 │                         │
       │ 7. 返回 Token                   │                         │
       │    access_token (JWT)           │                         │
       │    refresh_token                │                         │
       │    expires_in                   │                         │
       ◄─────────────────────────────────┤                         │
       │                                 │                         │
```

### 3.4 OAuth2 Provider 端点

| Provider | 授权端点 | Token 端点 |
|----------|---------|-----------|
| Google | `https://accounts.google.com/o/oauth2/v2/auth` | `https://oauth2.googleapis.com/token` |
| GitHub | `https://github.com/login/oauth/authorize` | `https://github.com/login/oauth/access_token` |
| GitLab | `https://gitlab.com/oauth/authorize` | `https://gitlab.com/oauth/token` |
| Supabase | `https://api.supabase.com/v1/oauth/authorize` | `https://api.supabase.com/v1/oauth/token` |
| Trae 自有 | `{tokenHost}/oauth/authorize` | `{tokenHost}/oauth/token` |

---

## 4. Token 交换与刷新

### 4.1 ExchangeToken API

**端点：** `POST {tokenHost}/cloudide/api/v3/trae/ExchangeToken`

**请求格式（已验证的格式）：**
```json
{
    "ClientID": "ono9krqynydwx5",
    "RefreshToken": "base64_encoded_refresh_token...",
    "ClientSecret": "-",
    "UserID": ""
}
```

或使用标准 OAuth2 格式：
```json
{
    "client_id": "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8",
    "grant_type": "refresh_token",
    "refresh_token": "base64_refresh_token..."
}
```

**认证头（两种都常用）：**
```
Authorization: Bearer {refresh_token}
x-cloudide-token: {refresh_token}
Content-Type: application/json
```

**成功响应：**
```json
{
    "Result": {
        "Token": "eyJhbGciOiJ...",
        "RefreshToken": "base64_new_refresh_token...",
        "TokenExpireDuration": 3600,
        "TokenExpireAt": 0,
        "Scope": "marscode"
    }
}
```

**限流响应：**
```json
HTTP 429
Headers:
    X-RateLimit-Remaining: 0
    X-RateLimit-Reset: 60
    X-RateLimit-Limit: 100
    Retry-After: 60
```

### 4.2 自动刷新机制

```javascript
// main.js 中的自动刷新逻辑
refreshConfig = {
    expires_in: 3600,           // Access token 有效期 (1小时)
    refresh_expires_in: 86400,   // Refresh token 有效期 (24小时)
    auto_refresh_before: 300,    // 过期前 5 分钟自动刷新
}

// Token 管理器行为
1. 初始化: 从 ~/.trae/tokens.json 加载
2. 检查 access_token 是否过期 (< 300s)
3. 如果过期 → 调用 ExchangeToken
4. 如果 refresh_token 也过期 → 要求重新登录
5. 限流时等待 Retry-After 后重试 (最多 3 次)
```

### 4.3 其他 Token API

**CheckLogin：**
```
POST {tokenHost}/cloudide/api/v3/trae/CheckLogin
Authorization: Bearer {access_token}
→ 200 OK = 有效
→ 其他 = 无效/过期
```

**GetUserInfo：**
```
POST {tokenHost}/cloudide/api/v3/trae/GetUserInfo
Authorization: Bearer {access_token}
→ 返回用户资料 JSON
```

**GetThirdPartyToken：**
```
POST {tokenHost}/cloudide/api/v3/trae/GetThirdPartyToken
x-cloudide-token: {access_token}
→ 返回第三方服务 token（Supabase 等）
```

---

## 5. 多 Scope 认证系统

### 5.1 Scope 定义

| Scope | 值 | 适用地区 | 说明 |
|-------|-----|---------|------|
| `marscode` | `marscode` | 国际 | 默认国际版，主 scope |
| `marscode_cn` | `marscode_cn` | 中国 | 中国区 MarsCode 服务 |
| `marscode_com` | `marscode_com` | 国际 | MarsCode 国际站 |
| `bytedance` | `bytedance` | 内部 | ByteDance 内部系统 |
| `saas` | `saas` | 企业 | SaaS 企业版 |

### 5.2 Auth Client IDs

| 客户端 | Client ID | 用途 |
|--------|-----------|------|
| Trae IDE Stable | `ono9krqynydwx5` | 正式版 Trae IDE |
| SOLO | `en1oxy7wnw8j9n` | Trae SOLO 模式 |
| UUID 格式 | `6eefa01c-1036-4c7e-9ca5-d891f63bfcd8` | 备用/通用 |

### 5.3 作用域选择逻辑

- **国际用户**: `marscode`
- **中国区用户**: `marscode_cn`
- **字节跳动内部**: `bytedance`（额外 + `marscode`）
- **企业 SSO**: `saas`（额外 + `marscode`）
- **MarsCode 国际站**: `marscode_com`

---

## 6. Supabase OAuth 集成

### 6.1 Supabase 端点

```
Authorization:
    https://api.supabase.com/v1/oauth/authorize
Token:
    https://api.supabase.com/v1/oauth/token
```

### 6.2 Supabase Token

```javascript
// Supabase token 存储路径
~/.config/Trae/User/supabase-token.json
// 或
~/.trae/auth/token.json
```

### 6.3 集成方式

Supabase OAuth 通过 `GetThirdPartyToken` API 关联到 Trae 主认证：

```
1. 用户通过 Trae OAuth2 登录 → 获取主 JWT
2. 调用 GetThirdPartyToken → 获取 Supabase 服务 token
3. Supabase token 用于：
   - 数据库访问
   - 实时订阅
   - 存储服务
```

---

## 7. AWS SSO/OIDC 企业认证

### 7.1 认证流程（设备授权码模式）

```
┌─────────────┐        ┌──────────────────┐        ┌──────────────┐
│  Trae IDE   │        │  AWS SSO OIDC    │        │  AWS SSO     │
│             │        │  oidc.{region}   │        │  portal.sso  │
└──────┬──────┘        └────────┬─────────┘        └──────┬───────┘
       │                        │                         │
       │ 1. RegisterClient      │                         │
       │ POST /client/register  │                         │
       ├───────────────────────►│                         │
       │ ◄── clientId ─────────┤                         │
       │                        │                         │
       │ 2. StartDeviceAuth     │                         │
       │ POST /device_authorize │                         │
       │ clientId + startUrl    │                         │
       ├───────────────────────►│                         │
       │ ◄── deviceCode ───────┤                         │
       │     userCode           │                         │
       │     verificationUri    │                         │
       │     expiresIn          │                         │
       │                        │                         │
       │ 3. [用户浏览器打开]     │                         │
       │    verificationUri     │                         │
       │    → 登录 AWS SSO     ├────────────────────────►│
       │                        │                         │
       │ 4. CreateToken (轮询)  │                         │
       │ POST /token            │                         │
       │ grant_type=device_code │                         │
       ├───────────────────────►│                         │
       │ (轮询直到用户授权完成)  │                         │
       │ ◄── accessToken ──────┤                         │
       │                        │                         │
       │ 5. GetRoleCredentials  │                         │
       │ POST /federation/      │                         │
       │   credentials          │                         │
       │ accessToken +          ├────────────────────────►│
       │ accountId + roleName   │                         │
       │                        │                         │
       │ ◄── accessKeyId ──────┤                         │
       │     secretAccessKey    │                         │
       │     sessionToken       │                         │
       │                        │                         │
       │ 6. (可选) STS AssumeRole│                        │
       │    (如需要跨账户访问)   │                         │
       │                        │                         │
       │ 7. 使用 AWS 凭证       │                         │
       │ → Bedrock Converse     │                         │
       │   Stream API           │                         │
```

### 7.2 AWS 端点

| 服务 | 端点 | 用途 |
|------|------|------|
| SSO OIDC | `https://oidc.{region}.amazonaws.com` | OIDC 客户端注册、设备授权、Token |
| SSO Portal | `https://portal.sso.{region}.amazonaws.com` | 角色凭证获取 |
| STS | `https://sts.{region}.amazonaws.com/` | 临时安全凭证 |
| Bedrock Runtime | `https://bedrock-runtime.{region}.amazonaws.com` | LLM 推理 |

### 7.3 错误处理

```
AuthorizationPendingException → 等待 5s 重试
SlowDownException             → 等待 10s 重试
ExpiredTokenException         → 需要重新发起设备授权
```

---

## 8. Token 数据结构与生命周期

### 8.1 Token 存储结构

```javascript
// ~/.trae/tokens.json
{
    "access_token": "eyJhbGciOiJSUzI1NiIs...",       // JWT
    "refresh_token": "base64_encoded_long_token...",   // Refresh token
    "expires_in": 3600,                                 // 有效期（秒）
    "expires_at": 1735712345,                           // 过期时间戳
    "refresh_expires_in": 86400,                        // Refresh 有效期
    "_expires_at": 1735712345,                           // 本地缓存过期时间
    "_refresh_expires_at": 1735802345,                   // 本地缓存 Refresh 过期
    "_updated_at": 1735708745,                           // 更新时间戳
    "scope": "marscode",                                 // 作用域
    "token_type": "Bearer"                               // Token 类型
}
```

### 8.2 Token 生命周期

```
access_token:   签发 → 有效(3600s) → 即将过期(300s) → 过期
                    ↓ 自动刷新              ↓
refresh_token:  签发 → 有效(86400s) → 过期
                    ↓                      ↓
                自动刷新                 重新登录
```

### 8.3 Token 存储位置

| 存储方式 | 路径 | 加密 |
|---------|------|------|
| JSON 文件 | `~/.trae/tokens.json` | 文件权限 600 |
| SQLCipher 数据库 | `~/.trae/ai-agent/database.db` | AES-256 加密 |
| 全局存储 | `~/.config/Trae/User/globalStorage/storage.json` | 无 |
| Supabase Token | `~/.config/Trae/User/supabase-token.json` | 可加密 |

---

## 9. 认证头与 API 端点

### 9.1 认证头完整列表

| Header | 格式 | 用途 | 场景 |
|--------|------|------|------|
| `Authorization` | `Bearer {access_token}` | 标准 Bearer | ExchangeToken, API 调用 |
| `x-cloudide-token` | `{access_token}` | Trae IDE 专用 | Chat API, Agent API |
| `x-ide-token` | `{access_token}` | IDE 内部认证 | 模型列表, Provider |
| `x-frontier-id` | `{id}` | Frontier 连接标识 | WebSocket 握手后 |
| `Content-Type` | `application/json` | JSON 请求体 | 所有 POST API |

### 9.2 API 端点矩阵

| 端点 | 需要的 Auth Header | Base URL |
|------|-------------------|----------|
| `GET /` | 无 | `icube-boot.trae.ai` |
| `POST /cloudide/api/v3/trae/ExchangeToken` | `Authorization: Bearer {refresh_token}` | `token.trae.ai` |
| `POST /cloudide/api/v3/trae/CheckLogin` | `Authorization: Bearer {access_token}` | `token.trae.ai` |
| `POST /cloudide/api/v3/trae/GetUserInfo` | `Authorization: Bearer {access_token}` | `token.trae.ai` |
| `POST /api/ide/v1/agents/runs` | `x-cloudide-token` + `x-ide-token` + `Authorization` | `coresg-normal.trae.ai` |
| `POST /api/ide/v2/llm_raw_chat` | `x-cloudide-token` + `x-ide-token` | `coresg-normal.trae.ai` |
| `POST /api/ide/v1/model_list` | `x-ide-token` + `x-cloudide-token` | `coresg-normal.trae.ai` |

### 9.3 CLI 认证方式

CLI (trae-cli v0.120.35) 使用不同的认证方式：

```javascript
// CLI Auth Struct
{
    DeviceID: string,
    Host: string,
    LoginBaseURL: string,
    Scope: string,
    OauthToken: OAuthTokenStore
}

// 存储方式（优先级）
1. KeyringStore (go-keyring)   // 系统密钥链
2. OAuthTokenStore             // 文件存储
3. MemoryStore                 // 内存（临时）

// 认证头: Authorization: Bearer {token}
// (不使用 x-cloudide-token)
```

---

## 10. 错误码参考

### 10.1 Token 错误码

| 错误码 | 含义 | 处理方式 |
|--------|------|---------|
| 20324 | Token 格式错误 | 重新获取 token |
| 20101 | Token 已过期 | 使用 refresh_token 刷新 |
| 20315 | Token 已吊销 | 重新登录 |
| 20125 | Refresh Token 无效 | 重新登录 |
| 20126 | Refresh Token 已过期 | 重新登录 |

### 10.2 HTTP 状态码处理

| 状态码 | 含义 | 处理 |
|--------|------|------|
| 200 | 成功 | 正常处理 |
| 401 | 未授权 | Token 无效或过期，尝试刷新 |
| 403 | 禁止访问 | Token 无权限 |
| 429 | 限流 | 等待 Retry-After 头指定的时间 |
| 502/503/504 | 服务不可用 | 重试（最多 3 次，指数退避） |

### 10.3 限流参数

```javascript
rateLimitConfig = {
    algorithm: "Token Bucket",          // 令牌桶算法
    keyed_by: "tenant_id",              // 按租户 ID 限流
    headers: {
        remaining: "X-RateLimit-Remaining",
        reset: "X-RateLimit-Reset",
        limit: "X-RateLimit-Limit",
    },
    response: {
        status: 429,
        header: "Retry-After",
    }
}
```

---

## 11. 完整认证流程图

### 11.1 IDE 启动认证

```
IDE 启动
  │
  ├─ GET icube-boot.trae.ai
  │  └─ 返回 BootConfig
  │     ├─ tokenHost: "https://token.trae.ai"
  │     └─ userInfo: { expiredAt, userId, ... }
  │
  ├─ userInfo 是否有效?
  │  ├─ 有效:
  │  │   └─ 已有 access_token → 直接使用
  │  └─ 无效/过期:
  │      └─ 自动刷新流程
  │
  ├─ 刷新判断:
  │  ├─ refresh_token 有效?
  │  │  ├─ 是: POST ExchangeToken → 新 tokens 保存
  │  │  └─ 否: 跳转到登录页
  │  │
  │  └─ 登录页:
  │      ├─ Google OAuth2
  │      ├─ GitHub OAuth2
  │      ├─ GitLab OAuth2
  │      ├─ Enterprise SSO
  │      └─ (中国区) 手机号/邮箱
  │
  └─ 登录完成
     ├─ 获取 access_token / refresh_token
     ├─ 保存到 ~/.trae/tokens.json
     └─ 建立 WebSocket 连接 (x-frontier-id 从 hub 获取)
```

### 11.2 API 调用认证

```
调用 API
  │
  ├─ 获取 access_token
  │  ├─ 从 ~/.trae/tokens.json 读取
  │  └─ 检查 _expires_at > now + 60
  │
  ├─ Token 过期?
  │  ├─ 否 → 直接使用
  │  └─ 是 → 自动刷新
  │      ├─ ExchangeToken(refresh_token)
  │      ├─ 保存新 tokens
  │      └─ 使用新 access_token
  │
  └─ 设置认证头
     ├─ x-cloudide-token: {access_token}
     ├─ x-ide-token: {access_token}
     ├─ Authorization: Bearer {access_token}
     └─ Content-Type: application/json
```

---

## 12. Token 存储与安全

### 12.1 存储层次

```
内存 (进程生命周期)
  │
  ├─ ~/.trae/tokens.json
  │   └─ 文件权限: 0600
  │
  ├─ ~/.trae/ai-agent/database.db (SQLCipher)
  │   ├─ AES-256 加密
  │   └─ 存储 refresh_token / api_keys
  │
  └─ macOS Keychain / Windows Credential Vault / Linux Secret Service
      └─ CLI Token 存储 (go-keyring)
```

### 12.2 安全措施

```javascript
// 1. 文件权限
fs.chmod(tokensPath, 0o600);  // 仅所有者可读写

// 2. 数据库加密
// SQLCipher: AES-256-CBC + HMAC-SHA512

// 3. 模型参数加密
// alkali (libsodium): AES-256-GCM
// 保护: API Keys, 自定义模型凭证

// 4. 传输安全
// TLS 1.3 (OpenSSL 静态链接)
// WebSocket: WSS (TLS)

// 5. PKCE 安全
// Code Verifier: 64 字符随机 [A-Za-z0-9-._~]
// Code Challenge: SHA-256 → Base64URL
```

---

> 本报告基于 main.js 反编译 + 认证脚本分析 + 协议分析文档。
> 实际端点可能因区域和版本有所不同。