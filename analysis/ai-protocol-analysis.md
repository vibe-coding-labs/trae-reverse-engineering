# Trae AI Communication Protocol Analysis

## Executive Summary

This document analyzes the AI communication protocol used by Trae IDE v2.3.30128, focusing on the IPC/RPC mechanisms, API endpoints, authentication flow, and data structures. The goal is to understand how to proxy Trae's AI capabilities for use with Codex.

---

## 1. IPC/RPC Protocol Stack

### 1.1 Transport Layer: AHA IPC (ZeroMQ)

Trae uses a custom IPC system called **AHA IPC** built on top of ZeroMQ (ZMQ).

**Key Components:**
- **@aha-kit/ipc** - Node.js IPC client/server library
- **@aha-kit/rpc** - JSON-RPC 2.0 implementation over IPC
- **ZeroMQ** - High-performance messaging library

**Connection Model:**
```
Electron Main Process ←→ ZeroMQ Dealer ←→ ZeroMQ Router ←→ ai-agent
```

**IPC Address Generation:**
```javascript
// From @aha-kit/ipc/dist/utils.js
function generateIpcAddress(serverName, runtimeDir) {
    // Generates Unix domain socket path
    return `ipc:///tmp/aha-${serverName}-${process.pid}`;
}
```

**Connection Parameters:**
- Heartbeat interval: Configurable (default from constants)
- Heartbeat timeout: Configurable
- Routing ID: UUID v4 generated per connection
- Message format: JSON-RPC 2.0

### 1.2 Protocol Layer: JSON-RPC 2.0

Trae uses standard JSON-RPC 2.0 with extensions for streaming.

**Message Format:**
```json
{
    "jsonrpc": "2.0",
    "method": "method_name",
    "params": { ... },
    "meta": { ... },
    "id": 123
}
```

**Standard Error Codes:**
```javascript
const JSONRPC_ERRORS = {
    PARSE_ERROR: { code: -32700 },
    INVALID_REQUEST: { code: -32600 },
    METHOD_NOT_FOUND: { code: -32601 },
    INVALID_PARAMS: { code: -32602 },
    INTERNAL_ERROR: { code: -32603 }
};
```

**Custom Error Codes:**
- `-32000`: Stream timeout
- `-32001`: Stream cancelled

### 1.3 RPC Control Messages

The RPC layer includes control messages for connection management:

#### rpc.ping

```json
{
    "jsonrpc": "2.0",
    "method": "rpc.ping",
    "params": { ... },
    "id": "request-id"
}
```

**Parameters:** `RpcPingParams` (2 elements)

#### rpc.close

```json
{
    "jsonrpc": "2.0",
    "method": "rpc.close",
    "params": { ... },
    "id": "request-id"
}
```

**Parameters:** `RpcCloseParams` (3 elements)

**Behavior:** Closes the connection when received.

#### RPC Method Registration

```
rpc.service — Register service
rpc.method — Register method
set in `read_before_execution` — Pre-execution hook
```

### 1.4 Streaming Protocol

Trae implements streaming over JSON-RPC using notifications.

**Stream Notification Format:**
```json
{
    "jsonrpc": "2.0",
    "method": "rpc.stream.{streamId}",
    "params": { "data": "..." },
    "meta": {
        "stream": true,
        "streamId": "uuid",
        "chunkIndex": 0,
        "done": false
    }
}
```

**Stream Lifecycle:**
1. **Open**: Client creates stream with UUID
2. **Write**: Server sends chunks via notifications
3. **End**: Server sends final chunk with `done: true`
4. **Cancel**: Client sends cancel notification
5. **Error**: Server sends error in stream

**Stream Timeout:**
- Configurable timeout per stream
- Timeout check every 1 second
- Auto-dispose on timeout

### 1.5 SSE Parameter Structures

#### SseOpenParams (2 elements)

```rust
struct SseOpenParams {
    stream_id: String,  // Unique stream identifier
    // ... 1 more field
}
```

#### SseOpenPayload (1 element)

```rust
struct SseOpenPayload {
    // Stream open payload
}
```

#### SseDeltaParams

```rust
struct SseDeltaParams {
    seq: i32,           // Sequence number
    // ... additional fields
}
```

#### SseEndParams

```rust
struct SseEndParams {
    last_seq: i32,      // Last sequence number
    // ... additional fields
}
```

#### SseErrorParams

```rust
struct SseErrorParams {
    error: SseErrorData,
    // ... additional fields
}
```

#### SseCancelParams (3 elements)

```rust
struct SseCancelParams {
    target_id: String,  // Target stream to cancel
    // ... 2 more fields
}
```

---

## 2. AI API Endpoints

### 2.1 Boot Configuration API

**Endpoint:** `https://icube-boot.trae.ai`

**Purpose:** Initial configuration and authentication

**Response Structure:**
```typescript
interface BootConfig {
    agent: AgentConfig;
    ckg: CKGConfig;
    hub: HubConfig;
    imageHost: string;
    tokenHost: string;
    token_host: string;
    userInfo: BootUserInfo;
    imageX: ImageXConfig;
    cdnPrefix: string;
    hostTmpDir: string;
    storeRegion: string;
    frontier: FrontierConfig;
    ugApi: string;
    ppeEnv: string;
}
```

**User Info Structure:**
```typescript
interface BootUserInfo {
    expiredAt: number;
    refreshExpiredAt: number;
    userId: string;
    tokenReleaseAt: number;
}
```

### 2.2 Chat Session API

**Methods:**
- `create_chat_session` - Create new chat session
- `send_message` - Send message to AI
- `stop_chat_session` - Stop running session
- `commit_chat_session` - Commit session changes
- `delete_chat_session` - Delete session
- `get_chat_session` - Get session details
- `list_chat_sessions` - List all sessions

**Request Structure (send_message):**
```typescript
interface SendMessageRequest {
    session_id: string;
    message: {
        content: string;
        type: 'text' | 'image' | 'file';
        attachments?: Attachment[];
    };
    model_config?: ModelConfig;
    tools?: ToolConfig[];
}
```

**Response Structure (SSE Stream):**
```
event: message_start
data: {"type":"message_start","message":{"id":"msg_xxx","role":"assistant"}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_stop
data: {"type":"message_stop"}
```

### 2.3 Model Management API

**Methods:**
- `model_list_by_function` - Get models by function
- `update_custom_model` - Update custom model
- `add_custom_model` - Add custom model
- `get_model_selection_mode` - Get selection mode
- `prefetch_for_auto` - Prefetch for auto mode

**Model Configuration Structure:**
```typescript
interface ModelDetailConfig {
    temperature: number;
    promptMaxTokens: number;
    ckgPromptMaxTokens: number;
    topP: number;
    topK: number;
    minNewTokens: number;
    repetitionPenalty: number;
    enabledModels: string[];
}
```

### 2.4 Tool Call API

**Methods:**
- `toolcall_run_command` - Execute shell command
- `toolcall_view_file` - View file content
- `toolcall_edit_file` - Edit file
- `toolcall_agent_finish` - Finish agent execution
- `toolcall_response_to_user` - Respond to user
- `toolcall_ask_user_question` - Ask user question
- `toolcall_notify_user` - Notify user

**Tool Call Event Structure:**
```typescript
interface ToolCallEvent {
    toolcall_id: string;
    tool_name: string;
    arguments: Record<string, any>;
    result?: any;
    error?: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
}
```

---

## 3. Authentication Flow - Complete Details

### 3.1 Authentication Methods

Trae supports multiple authentication methods:

| Method | Description | Source |
|--------|-------------|--------|
| **JWT** | JSON Web Token with access + refresh tokens | Primary authentication |
| **OAuth2** | OAuth2 authorization code flow | Google, GitHub, GitLab |
| **Enterprise SSO** | Enterprise single sign-on | SAML, OIDC |
| **IDE Token** | IDE-specific token (`x-ide-token` header) | API authentication |

### 3.2 JWT Token Structure

```rust
// JWT Strategy variants
enum ReturnToLocalJwtStrategy {
    Reuse,      // Reuse existing token
    External,   // External JWT strategy
}

struct variant ReturnToLocalJwtStrategy::External {
    jwt_token: String,  // JWT token for external strategy
    // ... 1 more field
}
```

### 3.3 JWT Token Fields

```
jwt_strategy.jwt_token is required for external strategy
```

### 3.4 OAuth2 Flow

```
POST /api/oauth/authorize
- OAuth2 authorization code flow
- Supports Google, GitHub, GitLab providers
- Returns JWT access & refresh tokens
```

### 3.5 OAuth2 Providers

| Provider | Flow | Token Type |
|----------|------|------------|
| Google | OAuth2 authorization code | JWT |
| GitHub | OAuth2 authorization code | JWT |
| GitLab | OAuth2 authorization code | JWT |

### 3.6 Enterprise SSO Integration

```
Enterprise SSO Integration
- SAML-based SSO
- OIDC-based SSO
- Custom SSO providers
```

### 3.7 Domain Authentication for Handoff

```rust
struct DomainAuthMeta {
    sso_type: String,      // SSO provider type
    sso_host: String,      // SSO host URL
    auth_from: String,     // Authentication source
    api_base: String,      // API base URL
    tenant_id: String,     // Tenant identifier
    domain: String,        // Domain identifier
}
```

### 3.8 Handoff Domain Configurations

```
handoff_domain_auth_solo_cn — SOLO China domain auth
handoff_domain_auth_bytedance_internal — ByteDance internal domain auth
```

### 3.9 Boot Configuration Authentication

```rust
struct BootUserInfo {
    expired_at: i64,           // Token expiration timestamp
    refresh_expired_at: i64,   // Refresh token expiration
    user_id: String,           // User identifier
    token_release_at: i64,     // Token release timestamp
    token_host: String,        // Token host URL
    // ... 1 more field
}
```

### 3.10 Authentication Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/handler/user_configuration.rs:81
apps/icube_server_rs/modules/ai-agent/src/handler/base.rs
apps/icube_server_rs/crates/ai-config/src/source/async_builder.rs:296
```

### 3.11 Authentication Error Messages

```
remote git session repo_url is empty
current session is not a supported git session
remote session source type is empty
remote session source is empty
```

### 3.1 Authentication Providers

**Supported Providers:**
- `icube.cloudide` - Trae IDE native auth
- Google OAuth2
- GitHub OAuth2
- GitLab OAuth2
- Enterprise SSO

### 3.2 JWT Token Structure

**Access Token:**
```typescript
interface AccessToken {
    sub: string;        // User ID
    iss: string;        // Issuer (trae.ai)
    aud: string;        // Audience
    exp: number;        // Expiration time
    iat: number;        // Issued at
    jti: string;        // JWT ID
    scope: string;      // Permissions
}
```

**Refresh Token:**
```typescript
interface RefreshToken {
    sub: string;
    iss: string;
    exp: number;
    jti: string;
    type: 'refresh';
}
```

### 3.3 Token Lifecycle

1. **Initial Auth:** User logs in via OAuth2 or native auth
2. **Token Issuance:** Server issues access + refresh tokens
3. **Token Storage:** Tokens stored in encrypted SQLite (SQLCipher)
4. **Token Refresh:** Automatic refresh before expiration
5. **Token Revocation:** On logout or security event

### 3.4 BootConfig Authentication

**Flow:**
```
1. IDE starts → Fetch BootConfig from icube-boot.trae.ai
2. BootConfig contains tokenHost and userInfo
3. IDE uses tokenHost to refresh tokens
4. Tokens used for all subsequent API calls
```

**Token Refresh:**
```typescript
// Pseudocode
async function refreshToken() {
    const response = await fetch(`${tokenHost}/refresh`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${refreshToken}`
        }
    });
    const { accessToken, refreshToken: newRefreshToken } = await response.json();
    // Store new tokens
}
```

### 3.5 BootConfig 完整认证流程

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

### 3.6 Token 刷新完整 API

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

### 3.7 错误码

| 错误码 | 含义 | 处理方式 |
|--------|------|---------|
| 20324 | Token 格式错误 | 重新登录 |
| 20101 | Token 已过期 | 尝试刷新 |
| 20315 | Token 已吊销 | 重新登录 |
| 20125 | Refresh Token 无效 | 重新登录 |
| 20126 | Refresh Token 已过期 | 重新登录 |

### 3.8 OAuth2 PKCE 流程

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

### 3.9 OAuth2 Provider 端点

| Provider | 授权端点 | 令牌端点 |
|----------|---------|---------|
| Google | Google OAuth2 | Google Token |
| GitHub | GitHub OAuth2 | GitHub Token |
| GitLab | GitLab OAuth2 | GitLab Token |
| Supabase | https://api.supabase.com/v1/oauth/authorize | https://api.supabase.com/v1/oauth/token |

### 3.10 第三方 Token 获取

**端点:** `POST /cloudide/api/v3/trae/GetThirdPartyToken`

通过已获取的 JWT token 换取第三方服务的访问令牌：
```
POST {tokenHost}/cloudide/api/v3/trae/GetThirdPartyToken
x-cloudide-token: {access_token}
```

### 3.11 AWS SSO 企业认证

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

### 3.12 Supabase OAuth 认证

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

---

## 4. Hub Bridge Service

### 4.1 Overview

Hub Bridge is the primary remote communication service for Trae AI.

**Features:**
- HTTP polling fallback
- WebSocket push notifications
- Message sequencing and confirmation
- Automatic reconnection
- Message replay on reconnect

### 4.2 Communication Modes

**HTTP Mode:**
- Polling for new messages
- Batch message sending
- Fallback when WebSocket fails

**WebSocket Mode:**
- Real-time push notifications
- Bidirectional communication
- Heartbeat keep-alive

### 4.3 Message Format

**Upstream (IDE → Server):**
```typescript
interface UpstreamMessage {
    seq_id: number;
    type: string;
    payload: any;
    timestamp: number;
}
```

**Downstream (Server → IDE):**
```typescript
interface DownstreamMessage {
    down_seq: number;
    type: string;
    payload: any;
    timestamp: number;
}
```

### 4.4 Reconnection Logic

```typescript
// Pseudocode
async function reconnect() {
    let attempt = 0;
    while (attempt < maxReconnectAttempts) {
        try {
            await connectWebSocket();
            // Replay missed messages
            await replayMessages(lastSeqId);
            return;
        } catch (error) {
            attempt++;
            await delay(wsReconnectDelaySecs * 1000);
        }
    }
    // Fallback to HTTP mode
    switchToHttpMode();
}
```

---

## 5. Custom Model Proxy

### 5.1 Overview

Custom Model Proxy allows connecting to external AI providers via WebSocket or HTTP.

**Transport Modes:**
- WebSocket (preferred)
- HTTP (fallback)

### 5.2 WebSocket Protocol

**Connection:**
```typescript
interface WebSocketConnectionConfig {
    baseUrl?: string;
    fullUrl?: string;
    headers?: Record<string, string>;
    subprotocol?: string;
}
```

**Message Types:**
- `sse.open` - Open SSE stream
- `sse.delta` - Stream data chunk
- `sse.end` - End stream
- `sse.error` - Stream error
- `sse.cancel` - Cancel stream
- `rpc.close` - Close connection
- `rpc.ping` - Keep-alive ping

### 5.3 SSE Stream Protocol

**Open Request:**
```json
{
    "method": "sse.open",
    "params": {
        "target_id": "stream_uuid"
    }
}
```

**Delta Response:**
```json
{
    "method": "sse.delta",
    "params": {
        "target_id": "stream_uuid",
        "seq": 0,
        "data": "Hello"
    }
}
```

**End Response:**
```json
{
    "method": "sse.end",
    "params": {
        "target_id": "stream_uuid",
        "last_seq": 10
    }
}
```

---

## 6. Unified Transport Server

### 6.1 Overview

The Unified Transport Server provides both HTTP and WebSocket interfaces for the ai-agent.

**Features:**
- HTTP REST API
- WebSocket real-time communication
- Binary and text message support
- Connection management

### 6.2 HTTP API

**Endpoints:**
- `POST /chat` - Send chat message
- `GET /sessions` - List sessions
- `POST /sessions` - Create session
- `GET /sessions/:id` - Get session
- `DELETE /sessions/:id` - Delete session

### 6.3 WebSocket API

**Connection:** `ws://localhost:{port}`

**Message Format:**
```typescript
interface WSMessage {
    service: string;
    user: string;
    payload: any;
}
```

---

## 7. Proxy Implementation Guide

### 7.1 Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Codex CLI  │ ──→ │  Trae Proxy │ ──→ │ Trae Backend│
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │                   │                   │
    AI Request      Protocol Translation    Original AI
       │                   │                   │
       ↓                   ↓                   ↓
    AI Response      Response Translation   Stream Response
```

### 7.2 Key Components

1. **Protocol Translator** - Convert Codex requests to Trae protocol
2. **Authentication Manager** - Handle token lifecycle
3. **Stream Processor** - Handle SSE streaming
4. **Error Handler** - Map error codes

### 7.3 Implementation Steps

1. **Setup Authentication:**
   - Implement OAuth2 flow
   - Handle token refresh
   - Secure token storage

2. **Implement Protocol Translation:**
   - Map Codex API to Trae methods
   - Convert request/response formats
   - Handle streaming

3. **Implement Error Handling:**
   - Map error codes
   - Implement retry logic
   - Handle rate limiting

4. **Testing:**
   - Unit tests for protocol translation
   - Integration tests with Trae backend
   - Load testing for performance

---

## 8. Security and Encryption

### 8.1 Database Encryption

Trae uses **SQLCipher** for encrypted SQLite database storage.

**Encryption Details:**
- Algorithm: AES-256
- Key derivation: PBKDF2
- Database path: `~/.trae/ai-agent/database.db`

**Encryption Flow:**
```sql
-- Check if database is encrypted
SELECT sql FROM sqlite_master WHERE type='table';

-- Encrypt existing database
ATTACH DATABASE '' AS encrypted KEY 'encryption_key';
SELECT sqlcipher_export('encrypted');
DETACH DATABASE encrypted;
```

**Key Management:**
```typescript
// Pseudocode
async function initializeDatabase() {
    // Check if database exists
    if (!databaseExists()) {
        // Create new encrypted database
        const encryptionKey = generateEncryptionKey();
        await createEncryptedDatabase(encryptionKey);
    } else {
        // Verify encryption
        if (!isDatabaseEncrypted()) {
            // Encrypt existing database
            await encryptDatabase();
        }
    }
}
```

### 8.2 Model Parameter Encryption

Trae uses **AES-256-GCM** via the `alkali` crate (libsodium wrapper) for encrypting model parameters.

**Encryption Location:**
```
apps/icube_server_rs/crates/llm-client/src/crypto/crypto.rs
```

**Key Features:**
- Algorithm: AES-256-GCM
- Library: alkali (libsodium wrapper)
- Purpose: Encrypt sensitive model parameters
- Key storage: Secure key management

### 8.3 Token Security

**Token Storage:**
- Tokens stored in encrypted database
- Refresh tokens have longer expiration
- Automatic token refresh before expiry

**Token Validation:**
```typescript
// Pseudocode
async function validateToken(token: string): Promise<boolean> {
    // Decode JWT
    const decoded = decodeJWT(token);

    // Check expiration
    if (decoded.exp < Date.now() / 1000) {
        return false;
    }

    // Verify signature
    const signatureValid = await verifySignature(token, publicKey);
    return signatureValid;
}
```

### 8.4 TLS/SSL

Trae uses **OpenSSL** statically linked for TLS connections.

**Features:**
- TLS 1.2/1.3 support
- Certificate validation
- Secure cipher suites

---

## 9. Model Configuration System - Complete Details

### 9.1 Model Configuration Structures

#### ModelConfigInfo (12 elements)

```rust
struct ModelConfigInfo {
    is_new: bool,
    memory_display_config: MemoryDisplayConfig,
    model_capability: String,
    is_beta: bool,
    fee_model_level: String,
    max_mode: String,
    is_dollar_max: bool,
    is_max_default: bool,
    can_use_super_model: bool,
    commercial_info: CommercialInfo,
    memory_display_config: MemoryDisplayConfig,
    feedback_group_link: String,
    is_internal_usage_limit: bool,
    is_l4_repo_restricted: bool,
    hot_info: HotInfo,
}
```

#### ModelConfigMeta (9 elements)

```rust
struct ModelConfigMeta {
    encrypted_prompt_set: String,
    // ... 8 more fields
}
```

#### ModelSelectionModeConfig (8 elements)

```rust
struct ModelSelectionModeConfig {
    // 8-element configuration for model selection mode
    // Controls how models are selected for different tasks
}
```

#### ModelDetailConfig (12 elements)

```rust
struct ModelDetailConfig {
    temperature: f32,
    prompt_max_tokens: i32,
    ckg_prompt_max_tokens: i32,
    top_p: f32,
    top_k: i32,
    min_new_tokens: i32,
    repetition_penalty: f32,
    enabled_models: Vec<String>,
    threshold: f32,
    // ... 3 more fields
}
```

### 9.2 Model Selection Flow

```
1. User sends chat request
2. ModelSelectionModeConfig determines selection strategy
3. ModelConfigInfo provides model capabilities
4. ModelDetailConfig provides fine-tuning parameters
5. Model selected based on:
   - Task type (chat, code, search)
   - User preferences
   - Model availability
   - Cost optimization
```

### 9.3 Model Configuration Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/handler/model.rs:84
apps/icube_server_rs/crates/ai-config/src/source/async_builder.rs
```

### 9.1 Model Config Cache

Trae caches model configurations in a database table.

**Database Schema:**
```sql
CREATE TABLE model_config_cache (
    user_id TEXT,
    env TEXT,
    function TEXT,
    config_data TEXT,
    updated_at TIMESTAMP,
    PRIMARY KEY (user_id, env, function)
);
```

**Cache Operations:**
```typescript
// Save model config
async function saveModelConfig(userId: string, env: string, function_: string, config: any) {
    await db.query(`
        INSERT INTO model_config_cache (user_id, env, function, config_data, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (user_id, env, function)
        DO UPDATE SET config_data = ?, updated_at = ?
    `, [userId, env, function_, JSON.stringify(config), new Date(), JSON.stringify(config), new Date()]);
}

// Retrieve model config
async function getModelConfig(userId: string, env: string, function_: string) {
    const result = await db.query(`
        SELECT config_data FROM model_config_cache
        WHERE user_id = ? AND env = ? AND function = ?
    `, [userId, env, function_]);
    return result ? JSON.parse(result.config_data) : null;
}
```

### 9.2 Auto Model Selection

Trae supports automatic model selection based on task type.

**Configuration:**
```typescript
interface DynamicAgenticAutoModelConfig {
    matches: DynamicAgenticAutoModelConfigMatch[];
}

interface DynamicAgenticAutoModelConfigMatch {
    configName: string;
    fallbackList: DynamicAgenticAutoModelConfigFallbackItem[];
}

interface DynamicAgenticAutoModelConfigFallbackItem {
    minScore: number;
    maxScore: number;
    modelName: string;
}
```

**Selection Logic:**
```typescript
// Pseudocode
async function selectAutoModel(taskType: string, context: any) {
    // Get auto model config
    const config = await getAutoModelConfig();

    // Find matching config
    const match = config.matches.find(m => m.configName === taskType);
    if (!match) {
        return getDefaultModel();
    }

    // Select model based on score
    for (const fallback of match.fallbackList) {
        const score = calculateScore(context);
        if (score >= fallback.minScore && score <= fallback.maxScore) {
            return fallback.modelName;
        }
    }

    return getDefaultModel();
}
```

### 9.3 Model Extra Configuration

Trae has extensive model configuration options (142 elements).

**Key Configuration Parameters:**
```typescript
interface ModelExtraConfig {
    // History management
    v2_kept_history_token_limit: number;
    v2_kept_history_message_count_limit: number;

    // Token quotas
    v2_current_turn_min_token_quota: number;
    v2_multimodal_summary_look_back_count: number;
    v2_multimodal_per_message_token_limit: number;
    v2_summary_message_token_limit: number;

    // Rendering options
    v2_render_by_dsl: boolean;
    v2_render_by_dsl_with_one_function: boolean;

    // File handling
    v2_view_file_auto_expand: boolean;
    v2_view_file_truncated_and_hint: boolean;
    v2_view_file_max_file_size_kb: number;
    v2_view_file_enable_outline: boolean;
    v2_view_file_max_char_size: number;

    // Search configuration
    v2_search_codebase_result_max_token: number;

    // Error detection
    v2_detect_hash_mention_file_linter_error: boolean;
    v2_detect_edit_file_linter_error: boolean;
    v2_read_old_linter_error_enabled: boolean;
    v2_edit_file_linter_error_sleep_time: number;

    // Command execution
    run_command_output_char_count: number;
    run_command_max_blocking_ms: number;
    run_command_remove_blocking: boolean;
    run_command_default_timeout_ms: number;

    // Interaction flow
    v2_interaction_flow_enable_file_diff: boolean;
    v2_user_message_simplify: boolean;
    v2_use_session_context: boolean;

    // Code search
    v2_enable_file_level_search_by_regex: boolean;
    v2_disable_lint_error_after_finish: boolean;
    v2_add_file_search_tool: boolean;

    // Tool call management
    max_duplicated_tool_calls: number;
    stop_duplicated_tool_calls: number;
    enable_duplicated_tool_calls_reminder: boolean;

    // Apply operations
    enable_search_replace_apply_in_chat: boolean;

    // Security
    encrypted_content_token_limit: number;
    enable_ai_sandbox_awareness: boolean;

    // Multi-agent support
    v2_multi_agent_read_enable: boolean;
    v2_multi_agent_read_model_config_name: string;
    v2_multi_agent_read_support_tools: string[];
    v2_multi_agent_read_agent_blacklist: string[];
    v2_multi_agent_read_handoff_tools_blacklist: string[];
    v2_multi_agent_read_history_skip_tools: string[];

    // Function calling
    native_function_call: boolean;
    nfc_force_use_edit_file_update: boolean;
    parallel_tool_calling: boolean;
    nfc_use_original_tool_call_id: boolean;

    // Max mode
    v2_max_mode_enabled: boolean;

    // Compression
    v2_post_compress_enabled: boolean;
    v2_post_compress_compare_percent: number;

    // Truncation
    v2_max_mention_file_context_truncation_type: string;
    v2_max_mention_file_context_truncation_size: number;
    v2_max_code_selection_truncation_type: string;
    v2_max_code_selection_truncation_size: number;
    v2_max_current_line_truncation_type: string;
    v2_max_current_line_truncation_size: number;

    // Tool call limits
    v2_max_toolcall_chars: number;
    v2_search_codebase_max_tokens: number;

    // Prompt collection
    collect_raw_prompt_input: boolean;

    // Agent configuration
    v3_solo_coder_disable_sub_agents: boolean;
    v3_solo_coder_disable_plan_mode: boolean;

    // Compaction
    v3_solo_coder_cumulative_compaction_strategy: string;
    v3_passive_compaction_user_perceptible: boolean;
    v3_solo_coder_compaction_restore_reading_nums: number;

    // Tool limits
    v3_ls_max_result_chars: number;
    v3_read_max_content_byte_size: number;
    v3_read_enable_truncation: boolean;
    v3_read_enable_start_end_line: boolean;
    v3_solo_coder_only_single_chat: boolean;
    v3_grep_max_result_chars: number;
    v3_grep_default_output_mode: string;
    v3_grep_enable_hidden: boolean;
    v3_grep_max_columns: number;
    v3_grep_post_sort: boolean;
    v3_ripgrep_partial_on_timeout: boolean;
    v3_snippet_content_max_char_count: number;

    // Sub-agent routing
    v3_sub_agent_route_enable: boolean;
    v3_sub_agent_summary_return_after_error: boolean;

    // Token limits
    v3_compaction_token_limit_ratio: number;
    v3_async_compaction_token_limit_ratio: number;
    v3_micro_compact_trigger_token_ratio: number;
    v3_micro_compact_kept_token: number;
    v3_micro_compact_min_token: number;

    // Parallel agents
    v3_parallel_agents_disabled: boolean;
    v3_max_concurrent_tasks: number;
    v3_concurrent_task_timeout: number;

    // Memory
    shallow_memento_disabled: boolean;
    core_memory_block_rough_max_token: number;

    // Apply patches
    replace_edit_tools_by_apply_patch: boolean;
    apply_patch_return_fuzzy_match_result: boolean;

    // History
    history_adapter_strategy: string;
    is_gpt5: boolean;
    disable_history_adapter: boolean;

    // Tool choice
    v3_optimize_tool_choice_strategy: string;

    // Glob
    v3_glob_enable_ripgrep: boolean;
    v3_glob_enable_no_ignore: boolean;
    v3_disable_nfc_dummy_tool: boolean;

    // Cloud agent
    cloud_agent_snippet_content_max_char_count: number;
    cloud_agent_category_content_max_char_count: number;

    // NFC
    enable_nfc_prefill_agent_name: boolean;

    // MCP
    run_mcp_result_max_char_count: number;
    run_custom_tool_output_max_char_count: number;

    // Enhanced checks
    enhanced_command_ast_check_2605: boolean;

    // User input
    v3_user_input_prompt_min_tokens: number;
    v3_user_input_prompt_max_tokens_ratio: number;
    v3_custom_rules_max_chars: number;

    // Streaming
    v3_stream_throttle_enabled: boolean;

    // Line numbers
    v3_padding_line_num_before_line_content: boolean;

    // Multi-edit
    v3_enable_multi_edit_tool: boolean;
    v3_replace_edit_tools_by_edit_file_update: boolean;
    v3_use_edit_file_update_replace_blocks: boolean;

    // Rename
    v3_rename_custom_tool_apply_patch_name: string;

    // Diagnostics
    v3_require_get_diagnostics_after_edit: boolean;

    // Tool call format
    v3_llm_message_use_separate_toolcall: boolean;

    // Sub-agent models
    v3_sub_agent_model_config_names: string[];

    // Image/video to text
    read_tool_image_to_text_config_name: string;
    enable_read_tool_image_to_text: boolean;
    read_tool_video_to_text_config_name: string;
    enable_read_tool_video_to_text: boolean;

    // View files
    v3_use_view_files_tool: boolean;

    // Custom tools
    v3_custom_tool_list: string[];

    // Skills and knowledge
    v3_enable_skill_tool: boolean;
    v3_enable_knowledge_tool: boolean;
    v3_enable_web_fetch_tool: boolean;

    // File diff
    v3_enable_file_diff_resolver: boolean;
    v3_enable_file_diff_resolver_v2: boolean;

    // User interaction
    v3_enable_ask_user_question_tool: boolean;

    // Dynamic tool loading
    dynamic_tool_loading_search: boolean;
    dynamic_tool_loading_filesystem: boolean;

    // Browser
    enable_browser_screenshot_auto_read: boolean;

    // Todo
    todo_write_allow_partial_input: boolean;

    // Web search
    web_search_skip_crawler_when_snippet_exists: boolean;

    // Toolcall result
    save_toolcall_result_config: any;

    // File read cache
    v3_file_read_state_cache_enabled: boolean;
    v3_read_dedup_enabled: boolean;

    // Command semantics
    enable_command_exit_code_semantics: boolean;

    // Path suggestions
    enable_read_enoent_path_suggestion: boolean;

    // Tool result trimming
    enable_tool_result_trimming: boolean;

    // Core memory
    core_memory_disabled: boolean;
}
```

---

## 10. Rate Limiting and Quotas

### 10.1 Token Bucket Algorithm

Trae uses a **token bucket algorithm** for rate limiting, keyed by tenant ID.

**Implementation Location:**
```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/common/rate_limiter.rs
```

**Rate Limit Headers:**
```http
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1717000000
X-RateLimit-Limit: 100
```

**Rate Limit Response (HTTP 429):**
```json
{
    "error": {
        "code": "rate_limit_exceeded",
        "message": "Rate limit exceeded. Please try again later.",
        "details": {
            "retry_after": 60,
            "limit": 100,
            "remaining": 0,
            "reset": 1717000000
        }
    }
}
```

### 10.2 Usage Tracking

**Session Usage Structure:**
```typescript
interface SessionUsage {
    session_id: string;
    user_id: string;
    model: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    cost: number;
    duration_ms: number;
}
```

**Token Usage Event:**
```typescript
interface TokenUsageEvent {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    cache_hit: boolean;
    cache_creation_input_tokens: number;
    cache_read_input_tokens: number;
}
```

**Timing Cost Event:**
```typescript
interface TimingCostEvent {
    duration_ms: number;
    first_token_ms: number;
    tokens_per_second: number;
    cost_usd: number;
}
```

---

## 11. Frontier Protocol (Hub Bridge) - Complete Message Types

### 11.1 Hub Bridge Message Types

The Hub Bridge uses a rich set of message types for real-time communication:

#### Client Messages (IDE → Server)

| Message Type | Description |
|--------------|-------------|
| `CliRequest` | Client request to server |
| `CliResponse` | Client response to server |
| `CreateTask` | Create new task |
| `DeleteTask` | Delete existing task |
| `BatchInsertEvents` | Batch insert events |
| `ConfirmWsMessage` | Confirm WebSocket message receipt |
| `PushConversationsDelete` | Delete conversations |
| `PushDeleteMessages` | Delete messages |
| `PushMessageDelete` | Delete single message |
| `PushMessageRevert` | Revert message changes |

#### Server Messages (Server → IDE)

| Message Type | Description |
|--------------|-------------|
| `SessionCreated` | New session created |
| `SessionUpdated` | Session updated |
| `SessionDeleted` | Session deleted |
| `PushSync` | Synchronize data |
| `PushConversationSize` | Conversation size update |
| `PushMessageSize` | Message size update |

### 11.2 HubRemoteConfig (17 elements)

```rust
struct HubRemoteConfig {
    fp_id: String,                    // Frontier protocol ID
    frontier_url: String,             // Frontier server URL
    max_ws_reconnect_attempts: i32,   // Max WebSocket reconnect attempts
    ws_reconnect_delay_secs: i32,     // WebSocket reconnect delay
    default_empty_flush_count: i32,   // Default empty flush count
    poll_interval_ms: i32,            // HTTP polling interval
    flush_interval_ms: i32,           // Flush interval
    flush_count_threshold: i32,       // Flush count threshold
    ws_msg_size_threshold: i32,       // WebSocket message size threshold
    push_sync: bool,                  // Enable push sync
    push_conversation_size: i32,      // Push conversation size limit
    push_message_size: i32,           // Push message size limit
    sync_session_chunk_size: i32,     // Session sync chunk size
    max_sent_message_cache: i32,      // Max sent message cache
    // ... 3 more fields
}
```

### 11.3 HubNetService Communication Flow

```
1. Register with Hub:
   [HubNetService] register_hub request: {product_id, app_runtime_type, process_id, client_timestamp}

2. Fetch Frontier URL:
   [HubNetService] frontier_url is None, re-fetching boot config
   [HubNetService] frontier_url: {url}, base_host: {host}

3. Record Frontier ID:
   [HubNetService] record_frontier_id: {id}

4. HTTP Polling Phase:
   [HubNetService] HTTP flush, messages from={seq}
   [HubNetService] HTTP polled {count} messages, no more

5. WebSocket Connection:
   [HubNetService] WS connect failed (attempt {n})
   [HubNetService] WS connected, replaying {count} remaining messages

6. WebSocket Communication:
   [HubNetService] WS recv, down_seq={seq}, proto={proto}
   [HubNetService] WS send {count} messages, from={seq}

7. Error Handling:
   [HubNetService] down_seq gap detected: expected {seq}, switching to HttpFallback
   [HubNetService] WS closed by remote
   [HubNetService] WS reconnect exhausted ({attempts} attempts), falling back to HTTP
```

### 11.4 WsMessage Structure (4 elements)

```rust
struct WsMessage {
    // 4-element structure for Hub Bridge WebSocket communication
    // Used for confirm/push/sync message types
}
```

### 11.5 FrontierFrame Structure

```
FrontierHeader
  ├── log_id
  ├── service
  ├── payload_encoding
  ├── payload_type
  ├── log_id_new
  ├── server_timing
  ├── msg_id
  └── frame_type
```

### 11.6 FrontierFrame Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/transport/hub_bridge/sender.rs:100
apps/icube_server_rs/modules/ai-agent/src/infrastructure/aha_net/stream.rs
```

### 11.1 FrontierFrame Format

The Hub Bridge uses a custom binary/text protocol called **Frontier** for remote communication.

**FrontierFrame Structure:**
```typescript
interface FrontierFrame {
    log_id: string;           // Unique request ID for tracing
    service: string;          // Target service name
    payload_encoding: string; // "json" | "protobuf" | "raw"
    payload_type: string;     // Message type identifier
    payload: Buffer;          // Encoded payload data
}
```

**Frontier Configuration:**
```typescript
interface FrontierConfig {
    frontier_id: string;      // Connection identifier
    frontier_url: string;     // WebSocket endpoint URL
    heartbeat_interval: number;
    reconnect_delay: number;
    max_reconnect_attempts: number;
}
```

### 11.2 WebSocket Bridge

**Connection Flow:**
```
1. IDE connects to frontier_url via WebSocket
2. Sends FrontierFrame with service="hub" and payload_type="auth"
3. Server authenticates and returns frontier_id
4. Subsequent messages use frontier_id for routing
```

**Message Types:**
- `auth` - Authentication handshake
- `chat` - Chat message forwarding
- `sync` - State synchronization
- `notification` - Push notifications
- `heartbeat` - Keep-alive

### 11.3 HTTP Polling Fallback

When WebSocket is unavailable, Hub Bridge falls back to HTTP polling:

```typescript
// Polling endpoint
GET /api/hub/messages?frontier_id={id}&last_seq={seq}

// Response
interface PollingResponse {
    messages: DownstreamMessage[];
    next_seq: number;
    has_more: boolean;
}
```

---

## 12. Domain Authentication (Handoff)

### 12.1 DomainAuthMeta Structure

For cloud-to-local and local-to-cloud session handoff:

```typescript
interface DomainAuthMeta {
    sso_type: string;         // "okta" | "azure_ad" | "google" | "custom"
    sso_host: string;         // SSO provider URL
    auth_from: string;        // "trae" | "icube" | "cloud"
    api_base: string;         // API base URL for the domain
    tenant_id: string;        // Organization tenant ID
    domain: string;           // Enterprise domain
}
```

### 12.2 Handoff Flow

**Local to Cloud:**
```
1. IDE requests handoff with session_id
2. Server generates handoff_token with short TTL
3. IDE forwards handoff_token to cloud agent
4. Cloud agent validates token and resumes session
```

**Cloud to Local:**
```
1. Cloud agent requests handoff with session_id
2. Server generates handoff_token
3. Cloud agent forwards to local IDE
4. Local IDE validates and resumes session
```

---

## 13. LLM Client Request/Response Types - Complete Details

### 13.1 LLMClientRequestRaw

```rust
struct LLMClientRequestRaw {
    model: String,
    messages: Vec<LLMClientRequestMessageRaw>,
    max_tokens: Option<i32>,
    max_completion_tokens: Option<i32>,
    tools: Option<Vec<LLMClientTool>>,
    usage: Option<LLMClientUsageRaw>,
    thinking: Option<LLMClientThinkingRaw>,
    reasoning: Option<LLMClientReasoningRaw>,
    inference_config: Option<InferenceConfig>,
    anthropic_version: Option<String>,
    // ... additional fields
}
```

### 13.2 LLMClientRequestMessageRaw

```rust
struct LLMClientRequestMessageRaw {
    role: String,
    content: Option<String>,
    reasoning_content: Option<String>,
    tool_call_id: Option<String>,
    tool_calls: Option<Vec<LLMClientToolCallItemRaw>>,
    reasoning_details: Option<Vec<LLMClientReasoningDetailsRaw>>,
    // ... additional fields
}
```

### 13.3 LLMClientToolCall (5 elements)

```rust
struct LLMClientToolCall {
    id: String,
    r#type: String,
    function: LLMClientToolCallFunction,
    extra_content: Option<LLMClientToolCallExtraContent>,
    // ... 1 more field
}
```

### 13.4 LLMClientToolCallFunction (2 elements)

```rust
struct LLMClientToolCallFunction {
    name: String,
    arguments: String,
}
```

### 13.5 LLMClientToolCallExtraContent

```rust
struct LLMClientToolCallExtraContent {
    google: Option<LLMClientToolCallExtraContentGoogle>,
}
```

### 13.6 LLMClientToolCallExtraContentGoogle

```rust
struct LLMClientToolCallExtraContentGoogle {
    thought_signature: String,
}
```

### 13.7 LLMClientReasoningDetailsRaw (8 elements)

```rust
struct LLMClientReasoningDetailsRaw {
    // 8-element structure for reasoning details
    // Used for models with reasoning capabilities
}
```

### 13.8 LLMClientMessage (6 elements)

```rust
struct LLMClientMessage {
    // 6-element structure for LLM messages
    // Contains: role, content, tool_calls, etc.
}
```

### 13.9 LLMClientMessageExtraInfo (3 elements)

```rust
struct LLMClientMessageExtraInfo {
    image_url: Option<String>,
    // ... 2 more fields
}
```

### 13.10 LLMClientMessageBlockContent (3 elements)

```rust
struct LLMClientMessageBlockContent {
    // 3-element structure for message block content
    // Used for Anthropic-style content blocks
}
```

### 13.11 Provider-Specific Content Blocks

#### OpenAI Content Blocks

```rust
struct OpenAIClientMessageContentBlock {
    // OpenAI content block
}

struct OpenAIClientMessageContentBlockImage {
    // OpenAI image content block
}
```

#### AWS Content Blocks

```rust
struct AWSClientMessageContentBlockText {
    // AWS text content block
}

struct AWSClientMessageContentBlockImage {
    // AWS image content block
}

struct AWSClientMessageImageBlock {
    // AWS image block
}

struct AWSClientMessageImageSource {
    // AWS image source
}

struct AWSClientMessageImageS3Location {
    bucket_owner: String,
    // ... additional fields
}
```

#### AWS Inference Configuration

```rust
struct AWSClientInferenceConfiguration {
    max_tokens: i32,
    temperature: f32,
    top_p: f32,
}
```

### 13.12 Cache Control

```rust
struct CacheControl {
    // Cache control for Anthropic API
    // Used for prompt caching
}

struct LLMClientCacheControl {
    // LLM client cache control
}
```

### 13.13 Tool Definitions

#### OpenAI Tool

```rust
struct OpenAITool {
    r#type: String,
    function: OpenAIToolFunction,
}

struct OpenAIToolFunction {
    name: String,
    description: String,
    parameters: serde_json::Value,
}
```

#### Anthropic Tool

```rust
struct AnthropicTool {
    name: String,
    description: String,
    input_schema: serde_json::Value,
}
```

### 13.14 LLM Client Source Paths

```
apps/icube_server_rs/crates/llm-client/src/provider/anthropic.rs:185
apps/icube_server_rs/crates/llm-client/src/provider/openai.rs:267
apps/icube_server_rs/crates/llm-client/src/provider/deepseek.rs:186
apps/icube_server_rs/crates/llm-client/src/provider/gemini.rs:126
apps/icube_server_rs/crates/llm-client/src/provider/aws.rs:125
apps/icube_server_rs/crates/llm-client/src/provider/volcengine.rs:63
apps/icube_server_rs/crates/llm-client/src/provider/openrouter.rs:135
```

### 13.1 LLMClientRequestRaw

**Structure:**
```typescript
interface LLMClientRequestRaw {
    model: string;                    // Model identifier
    messages: LLMMessage[];           // Conversation messages
    max_tokens?: number;              // Max response tokens
    temperature?: number;             // Sampling temperature
    top_p?: number;                   // Nucleus sampling
    top_k?: number;                   // Top-k sampling
    tools?: LLMTool[];                // Available tools
    tool_choice?: string;             // "auto" | "none" | "required"
    thinking?: boolean;               // Enable thinking/reasoning
    reasoning?: boolean;              // Enable reasoning mode
    stream?: boolean;                 // Enable streaming
    stop?: string[];                  // Stop sequences
    response_format?: ResponseFormat; // JSON mode, etc.
}
```

### 13.2 Native Provider Responses

**Anthropic Response:**
```typescript
interface NativeAnthropicLLMResponse {
    id: string;
    type: "message";
    role: "assistant";
    content: ContentBlock[];
    model: string;
    stop_reason: string;
    stop_sequence: string;
    usage: NativeAnthropicUsage;
}

interface NativeAnthropicUsage {
    input_tokens: number;
    output_tokens: number;
    cache_creation_input_tokens: number;
    cache_read_input_tokens: number;
}
```

**OpenRouter Response:**
```typescript
interface NativeOpenrouterLLMResponse {
    id: string;
    model: string;
    choices: OpenrouterChoice[];
    usage: OpenrouterUsage;
}

interface OpenrouterChoice {
    index: number;
    message: LLMMessage;
    finish_reason: string;
}

interface OpenrouterUsage {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
}
```

---

## 14. AI Features Configuration Limits - Complete Details

### 14.1 DynamicConfigAiFeatures (19 elements)

```rust
struct DynamicConfigAiFeatures {
    mcp_tool_limit: i32,
    mcp_token_limit: i32,
    mcp_token_limit_m8: i32,
    mcp_tool_hard_cap: i32,
    custom_prompt_token_limit: i32,
    custom_prompt_token_limit_m8: i32,
    fix_edit_file_size_limit: i32,
    chat_message_query_limit: i32,
    history_query_limit: i32,
    server_history_cache_limit: i32,
    server_history_sync_timeout_secs: i32,
    raw_rules_max_chars: i32,
    snippet_content_max_char_count: i32,
    category_content_max_char_count: i32,
    tool_confirm_timeout_secs: i32,
    schedule_task_max_count: i32,
    schedule_min_interval_minutes: i32,
    // ... 2 more fields
}
```

### 14.2 DynamicConfigICubeAppData (37 elements)

```rust
struct DynamicConfigICubeAppData {
    feature_gates: DynamicConfigFeatureGatesData,
    snapshot_v2: SnapshotV2,
    snapshot_clean_up: SnapshotCleanUp,
    snapshot_ignore: SnapshotIgnore,
    auto_accept: AutoAccept,
    agentic_flow_config: DynamicAgenticFlowConfigMatch,
    agentic_auto_model_config: AgenticAutoModelConfig,
    agentic_summary_config: DymanicAgenticSummaryConfig,
    lint_error: DynamicConfigLintError,
    todo_list_tool_call: TodoListToolCall,
    ai_features: DynamicConfigAiFeatures,
    context_usage_chunk: DynamicConfigContextUsageChunk,
    http_timeout_config: HTTPTimeoutConfig,
    solo_builder_config_name: String,
    error_log_report: ErrorLogReport,
    agent_v3: DynamicConfigAgentV3,
    evaluation_config: EvaluationConfig,
    auto_run_config: AutoRunConfig,
    sqlite_optimization: SqliteOptimizationPlatformConfig,
    finish_collect_strategy: FinishCollectStrategy,
    custom_model_fallback_config: CustomModelFallbackConfig,
    mb_config: MbConfig,
    builtin_skill_mapping: BuiltinSkillMapping,
    chat_memory_with_history: ChatMemoryWithHistoryConfig,
    virtual_path: VirtualPathConfig,
    hub_config: HubConfig,
    solo_vm_config: SoloVMConfig,
    aigc_tag_config: AigcTagConfig,
    prompt_meta_filter_config: PromptMetaFilterConfig,
    dynamic_ui: DynamicConfigDynamicUI,
    skill_as_agent: SkillAsAgentConfig,
    toolcall_output_persistence_visible: bool,
    toolcall_output_persistence_default_enabled: bool,
    generate_image: DynamicConfigGenerateImage,
    // ... 3 more fields
}
```

### 14.3 DynamicConfigFeatureGatesData

```rust
struct DynamicConfigFeatureGatesData {
    enable_remote_dcdn_domain: bool,
    enable_cmd_blocking: bool,
    // ... additional fields
}
```

### 14.4 DynamicAgenticFlowConfigMatch

```rust
struct DynamicAgenticFlowConfigMatch {
    max_plan_turns: i32,
    max_left_turns: i32,
    enable_user_prompt_cache: bool,
    toolcall_cache_limit: i32,
}
```

### 14.5 DymanicAgenticSummaryConfig

```rust
struct DymanicAgenticSummaryConfig {
    summary_message_token_limit: i32,
    kept_history_token_limit: i32,
    kept_history_message_limit: i32,
    minimum_current_turn_token_usage: i32,
    multimodal_summary_look_back_count: i32,
}
```

### 14.6 Configuration Source Path

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/ide_command/dynamic_config.rs:917
```

### 14.1 MCP Limits

```typescript
interface MCPLimits {
    mcpToolLimit: number;         // Max MCP tools per session (default: 40)
    mcpTokenLimit: number;        // Max tokens for MCP context (default: 8000)
    mcpToolHardCap: number;       // Hard limit on total MCP tools
    mcpServerTimeout: number;     // MCP server connection timeout
}
```

### 14.2 Tool Execution Limits

```typescript
interface ToolLimits {
    toolConfirmTimeoutSecs: number;    // Timeout for tool confirmation (default: 30)
    maxConcurrentTools: number;        // Max parallel tool executions
    toolExecutionTimeoutMs: number;    // Single tool execution timeout
    maxToolResultSize: number;         // Max tool result size in bytes
}
```

### 14.3 Session Limits

```typescript
interface SessionLimits {
    maxSessionDurationMs: number;      // Max session duration
    maxMessagesPerSession: number;     // Max messages in a session
    maxContextWindowTokens: number;    // Max context window size
    compactionThresholdRatio: number;  // When to trigger compaction
}
```

---

## 15. HTTP Timeout and SSE Retry Logic

### 15.1 HTTPTimeoutConfig (8 elements)

```rust
struct HTTPTimeoutConfig {
    http_response_header_timeout: i32,  // Response header timeout (ms)
    http_sse_stream_timeout: i32,       // SSE stream timeout (ms)
    http_upstream_call_timeout: i32,    // Upstream call timeout (ms)
    http_sse_no_event_timeout: i32,     // SSE no-event timeout (ms)
    max_retry_count: i32,               // Maximum retry count
    retry_timeout: i32,                 // Retry timeout (ms)
    retry_http_code: i32,               // HTTP code to retry on
    internal_network_timeout: i32,      // Internal network timeout (ms)
}
```

### 15.2 SSE Retry Logic

```
retryCount: 3 (default)
retryTimeout: 1000ms (default)
retryCode: [502, 503, 504] (HTTP codes to retry on)
noEventTimeout: 30000ms (30 seconds)
backoffMultiplier: 2 (exponential backoff)
```

### 15.3 SSE Retry Flow

```
1. SSE stream opens (sse.open event)
2. Server sends sse.delta events
3. If no event received for 30s:
   - Send sse.heartbeat
   - If still no response, retry connection
4. If HTTP 502/503/504 received:
   - Wait retryTimeout (1s)
   - Retry connection
   - Exponential backoff (2x)
5. After maxRetryCount (3) failures:
   - Send sse.error event
   - Close stream
6. Normal close:
   - Send sse.end event
   - Close stream
```

### 15.4 SSE Event Types

```
sse.open — Stream opened
sse.delta — Stream data chunk
sse.end — Stream ended
sse.error — Stream error
sse.cancel — Stream cancelled
sse.heartbeat — Keep-alive heartbeat
sse.retry — Retry signal
```

### 15.5 SSE Parameter Structures

```rust
struct SseOpenParams {
    stream_id: String,
    // ... 1 more field
}

struct SseOpenPayload {
    // Stream open payload
}

struct SseDeltaParams {
    seq: i32,
    // ... additional fields
}

struct SseEndParams {
    last_seq: i32,
    // ... additional fields
}

struct SseErrorParams {
    error: SseErrorData,
    // ... additional fields
}

struct SseCancelParams {
    target_id: String,
    // ... 2 more fields
}
```

### 15.1 Retry Parameters

```typescript
interface SSERetryConfig {
    retryCount: number;           // Max retry attempts (default: 3)
    retryTimeout: number;         // Base retry timeout in ms (default: 1000)
    retryCode: number[];          // HTTP codes to retry (default: [502, 503, 504])
    noEventTimeout: number;       // Timeout if no events received (default: 30000)
    backoffMultiplier: number;    // Exponential backoff multiplier (default: 2)
    maxRetryTimeout: number;      // Max retry timeout (default: 30000)
}
```

### 15.2 Retry Flow

```
1. Client sends request with stream=true
2. If connection fails with retryCode → wait retryTimeout * (backoffMultiplier ^ attempt)
3. If no events for noEventTimeout → send heartbeat ping
4. If heartbeat fails → reconnect with retry logic
5. After retryCount exhausted → return error to user
```

### 15.3 SSE Event Types

```typescript
// Stream lifecycle events
type SSEEventType =
    | "sse.open"      // Stream opened
    | "sse.delta"     // Data chunk
    | "sse.end"       // Stream ended
    | "sse.error"     // Stream error
    | "sse.cancel"    // Stream cancelled
    | "sse.heartbeat" // Keep-alive
    | "sse.retry"     // Retry instruction
```

---

## 16. Tool Call System (Complete Taxonomy)

Trae's AI agent supports a rich set of tool calls for code editing, search, and system interaction.

### 16.1 Tool Call Types

| Tool Name | Category | Description |
|-----------|----------|-------------|
| `toolcall_run_command` | System | Execute shell commands |
| `toolcall_grep` | Search | Search file contents by regex |
| `toolcall_glob` | Search | Find files by glob pattern |
| `toolcall_read` | File | Read file contents |
| `toolcall_view_file` | File | View file with syntax highlighting |
| `toolcall_edit_file` | File | Edit file contents (search-replace) |
| `toolcall_create_file` | File | Create new files |
| `toolcall_delete_file` | File | Delete files |
| `toolcall_apply_patch` | File | Apply code patches |
| `toolcall_web_search` | Web | Search the web |
| `toolcall_web_fetch` | Web | Fetch web page content |
| `toolcall_ask_user_question` | Interactive | Ask user a question |
| `toolcall_notify_user` | Interactive | Send notification to user |
| `toolcall_response_to_user` | Interactive | Send response to user |
| `toolcall_agent_finish` | Control | Complete agent execution |
| `toolcall_supabase_get_tables` | Database | List Supabase tables |
| `toolcall_supabase_apply_migration` | Database | Apply Supabase migration |

### 16.2 Tool Call Event Structure

```rust
// From ai-agent binary strings
struct ToolCallEvent with 11 elements
struct LLMClientToolcallItem with 4 elements
struct RawLLMResponseToolCall with 3 elements
struct OutputEventToolCall with 4 elements
```

### 16.3 Source Path

```
apps/icube_server_rs/modules/ai-agent/src/domain/toolcall/
```

---

## 17. Content Security System

Trae implements rule-based content filtering for AI outputs.

### 17.1 Security Events

```
content_security_blocked — Content blocked by security rules
```

### 17.2 Implementation

```
apps/icube_server_rs/modules/ai-agent/src/domain/content_security/service.rs
```

### 17.3 Features

- Rule-based content filtering for AI outputs
- Block/allow list for sensitive content
- Integration with tool call system for dangerous operations
- `need_manual_confirm` flag for dangerous operations
- `in_enterprise_command_blacklist` for enterprise environments
- `file_outside_workspace` boundary checks

---

## 18. MCP (Model Context Protocol) Integration

Trae implements the Model Context Protocol for extensible tool systems.

### 18.1 MCP Limits

| Parameter | Value | Description |
|-----------|-------|-------------|
| `mcpToolLimit` | 40 | Maximum MCP tools per session |
| `mcpTokenLimit` | 8000 | Maximum tokens for MCP context |
| `mcpToolHardCap` | Hard limit | Absolute maximum tools |

### 18.2 MCP Data Structures

```
struct MCPWhitelist with 11 elements
struct MCPWhitelistConfigInfo with 2 elements
```

### 18.3 MCP Components

- `mcp_server` — Server management
- `mcp_tool` — Tool registration and invocation
- `mcp_safety` — Safety checks for MCP tools
- `mcp_name_resolver` — Resolve MCP tool names

### 18.4 Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/toolcall/mcp_name_resolver.rs
```

### 18.5 MCP Integration Details

- Forked Anthropic SDK: `@byted/modelcontextprotocol-client` v2.0.0-alpha.2.byted.5
- Per-agent MCP server configuration with `mcp_server_agent_relation` database table
- SOLO-mode builtin MCP extension

---

## 19. Sub-Agent System

Trae supports multi-agent orchestration through file-based agent definitions.

### 19.1 Sub-Agent Frontmatter

```rust
struct SubAgentFrontmatter {
    // File-based agent definition with frontmatter
    mcpServers: Vec<String>,      // MCP servers to use
    disallowedTools: Vec<String>, // Tools not available to this agent
}
```

### 19.2 Sub-Agent Features

- File-based agent definitions (YAML frontmatter)
- Per-agent MCP server configuration
- Tool restrictions per agent
- Agent invocation and orchestration

### 19.3 Source Path

```
apps/icube_server_rs/modules/ai-agent/src/domain/context_asset/subagents/
```

---

## 20. Core Memory System

Trae implements persistent memory blocks for agent context across sessions.

### 20.1 Memory Eviction Strategies

| Strategy | Description |
|----------|-------------|
| `w_tinylfu` | Weighted TinyLFU cache eviction |
| `hybrid_half_life` | Hybrid half-life decay strategy |

### 20.2 Implementation

```
apps/icube_server_rs/modules/ai-agent/src/domain/memory/core_memory/service.rs
```

### 20.3 Features

- Persistent memory blocks across sessions
- Configurable eviction strategies
- Memory block management (add, update, delete, query)
- Integration with agent context

---

## 21. Scheduled Tasks System

Trae supports cron-based autonomous task scheduling.

### 21.1 Scheduled Task Configuration

```rust
struct ScheduledTaskAutoRunConfig with 4 elements {
    // Configuration for automatic task execution
}
```

### 21.2 Limits

- Maximum number of scheduled tasks (configurable)
- Persistent execution across sessions

### 21.3 Features

- Cron-like scheduling
- Autonomous task execution
- Task persistence
- Integration with agent system

---

## 22. Handoff Protocol

Trae supports session migration between local and cloud environments.

### 22.1 Handoff Types

| Type | Direction | Description |
|------|-----------|-------------|
| `handoff_down_session` | Cloud → Local | Migrate session from cloud to local |
| `handoff_up_session` | Local → Cloud | Migrate session from local to cloud |

### 22.2 Domain Authentication for Handoff

```rust
struct DomainAuthMeta {
    sso_type: String,      // SSO provider type
    sso_host: String,      // SSO host URL
    auth_from: String,     // Authentication source
    api_base: String,      // API base URL
    tenant_id: String,     // Tenant identifier
    domain: String,        // Domain identifier
}
```

### 22.3 Handoff Domain Configurations

```
handoff_domain_auth_solo_cn — SOLO China domain auth
handoff_domain_auth_bytedance_internal — ByteDance internal domain auth
```

### 22.4 Source Path

```
apps/icube_server_rs/modules/ai-agent/src/domain/handoff/
```

---

## 23. Sandbox System

Trae provides code execution sandboxing for safety.

### 23.1 Sandbox Errors

```
TRAE Sandbox Error: init failed
create_sandbox failed
sdk crash
process launch failed
process crashed
hit restricted
```

### 23.2 Sandbox Features

- Linux namespace sandbox + Lite VM for code execution
- Windows sandbox with Job Objects
- File/network access controls
- Command red list
- `sandbox_rw_list` / `sandbox_ro_list` for file access

### 23.3 Sandbox Binary

- `trae-sandbox` — 18MB binary
- `sbox_sdk.dll` — 1.9MB (Windows)

---

## 24. Browser Automation System

Trae includes a full Playwright-like browser automation suite for AI agents.

### 24.1 Browser Tools

| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to URL |
| `browser_navigate_back` | Go back |
| `browser_navigate_forward` | Go forward |
| `browser_click` | Click element |
| `browser_type` | Type text |
| `browser_press_key` | Press keyboard key |
| `browser_screenshot` | Take screenshot |
| `browser_take_screenshot` | Take screenshot (alias) |
| `browser_snapshot` | Page state snapshot |
| `browser_evaluate` | Execute JavaScript |
| `browser_select_option` | Select dropdown option |
| `browser_fill` | Fill form field |
| `browser_fill_form` | Fill entire form |
| `browser_hover` | Hover over element |
| `browser_drag` | Drag element |
| `browser_scroll` | Scroll page |
| `browser_upload_file` | Upload file |
| `browser_download` | Download file |
| `browser_wait_for` | Wait for condition |
| `browser_handle_dialog` | Handle dialog/popup |
| `browser_get_attribute` | Get element attribute |
| `browser_get_bounding_box` | Get element bounds |
| `browser_get_input_value` | Get input value |
| `browser_is_visible` | Check visibility |
| `browser_is_enabled` | Check if enabled |
| `browser_is_checked` | Check if checked |
| `browser_lock` | Lock browser session |
| `browser_unlock` | Unlock browser session |
| `browser_hand_over` | Transfer control to user |

---

## 25. Cloud Agent System

Trae supports remote agent execution with event streaming.

### 25.1 Implementation

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/cloud_agent/mod.rs
```

### 25.2 Features

- Remote agent execution
- Event streaming from cloud agents
- Session management for cloud agents
- Integration with handoff protocol

---

## 26. Custom Model Proxy Internals

### 26.1 Transport Modes

| Mode | Description |
|------|-------------|
| WebSocket | Real-time bidirectional communication |
| HTTP | Fallback mode with SSE streaming |

### 26.2 Proxy Features

- WebSocket/HTTP dual-transport
- SSE message types for streaming
- Retry logic for connection failures
- Model configuration management

### 26.3 Source Path

```
apps/icube_server_rs/crates/custom-model-proxy-client/src/
```

### 26.4 Log Messages

```
[CustomModelProxy] WebSocket connect failed: , falling back to HTTP mode
WebSocketConnectionConfig is required
```

---

## 27. Unified Transport Server

### 27.1 Architecture

The unified transport server handles both HTTP and WebSocket on a single port.

### 27.2 Message Types

```
[UnifiedTransport] binary message
[UnifiedTransport] text message
[UnifiedTransport] WebSocket connection established
[UnifiedTransport] WebSocket connection closed
```

### 27.3 Source Path

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/transport/unified.rs
```

### 27.4 Features

- HTTP + WebSocket on single port
- Binary and text message support
- Connection management
- Message routing

---

## 28. Context and Render System

### 28.1 Context Structure (23 elements)

```rust
struct Context {
    current_file: Option<String>,
    hash_files: Vec<String>,
    hash_codes: Vec<String>,
    hash_folder_paths: Vec<String>,
    hash_code_browser_selections: Vec<String>,
    hash_log_messages: Vec<String>,
    workspace_contexts: Vec<String>,
    selected_code_snippets: Vec<String>,
    terminal_selections: Vec<String>,
    user_interaction_contexts: Vec<String>,
    file_changes_summary: Option<FilesChangesSummary>,
    file_changes_context: Option<FilesChangesContext>,
    lint_error_flag: bool,
    lint_errors: Vec<String>,
    hash_rule_file_paths: Vec<String>,
    updated_rule_files: Vec<String>,
    resolved_slash_commands: Vec<ResolvedSlashCommandDTO>,
    user_uploaded_files: Vec<UserUploadedFile>,
    user_comment_text_data: Option<UserCommentTextData>,
    user_comment_sheet_data: Option<UserCommentSheetData>,
    // ... 3 more fields
}
```

### 28.2 UserInput (15 elements)

```rust
struct UserInput {
    // 15-element structure for user input
    // Contains: message, context, selections, etc.
}
```

### 28.3 RenderVariables (112 elements)

```rust
struct RenderVariables {
    enable_parallel_tool_calling: bool,
    is_in_chat_mode: bool,
    is_in_plan_v2: bool,
    response_can_be_text: bool,
    left_turns: i32,
    text_to_image_url: String,
    enable_multi_agent_reader: bool,
    sub_agents: Vec<String>,
    user_auto_run_prompt: String,
    is_use_npm_mirror: bool,
    language_settings: String,
    actived_environments: Vec<String>,
    supported_environments: Vec<String>,
    init_env_enabled: bool,
    has_terminal_info: bool,
    max_terminals_count: i32,
    available_terminals_count: i32,
    available_terminals: Vec<String>,
    terminal_shell_type: String,
    refresh_project_memento_mode: String,
    memory_info: MemoryInfo,
    is_not_updated_todo_list_recently: bool,
    current_filename: String,
    brand: String,
    hash_workspace: String,
    hash_code: String,
    hash_file: String,
    is_command: bool,
    is_inline_chat: bool,
    badge_clickable: bool,
    home_dir: String,
    unique_user_id: String,
    user_data_dir: String,
    skills_dir: String,
    vm_session_base_dir: String,
    work_dir: String,
    upload_dir: String,
    user_message_simplify: bool,
    use_session_context: bool,
    disable_prompt_selected_code: bool,
    selected_code: String,
    channel: String,
    is_line_comment: bool,
    merging_process: bool,
    merge_source_branch: String,
    merge_target_branch: String,
    merge_changed_files: Vec<String>,
    merge_conflict_files: Vec<String>,
    sandbox_mode_enabled: bool,
    sandbox_filesystem_config: SandboxConfig,
    sandbox_network_config: SandboxConfig,
    // ... 61 more fields
}
```

### 28.4 RalphLoopContext (13 elements)

```rust
struct RalphLoopContext {
    ralph_loop_round: i32,
    ralph_loop_max_round: i32,
    ralph_loop_document_paths: Vec<String>,
    ralph_loop_user_input_history: Vec<String>,
    ralph_loop_task_last_turn_mark_done: bool,
    is_auto_continuation: bool,
    accumulated_input_tokens: i32,
    accumulated_output_tokens: i32,
    spec_dir_name: String,
    is_loop_done: bool,
    round_start_time: i64,
    round_end_time: i64,
    current_turn_all_mark_done: bool,
}
```

### 28.5 ChatTurn (10 elements)

```rust
struct ChatTurn {
    conversations: Vec<History>,
    // ... 9 more fields
}
```

### 28.6 History (1 element)

```rust
struct History {
    messages: Vec<Message>,
}
```

### 28.7 Message (3 elements)

```rust
struct Message {
    role: String,
    content: String,
    use_cache: bool,
}
```

### 28.8 Multimedia (6 elements)

```rust
struct Multimedia {
    // 6-element structure for multimedia content
    // Supports: images, videos, files, etc.
}
```

### 28.9 Context Meta Structures

```rust
struct ContextMeta with 16 elements
struct ContextInfo with 6 elements
struct ContextResolverResultMetadata with 2 elements
struct ContextResolverReference with 7 elements
```

### 28.10 Context Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/handler/git/mod.rs:357
```

---

## 29. Document RAG System

### 29.1 Document Set Structures

```rust
struct DocumentSetListItem with 7 elements
struct DocumentSetListResponse with 3 elements
struct DocumentsList with 2 elements
struct DocumentListItem with 6 elements
struct DocumentSetInfoData with 7 elements
struct DocumentSetInfoResponse with 4 elements
struct DocumentInfoResponse with 1 element
struct DocumentSetDiffItem with 3 elements
struct DocumentSetDiffResponse with 3 elements
```

### 29.2 Document Request/Response Types

```rust
struct DocumentSetListRequest with 4 elements
struct DocumentSetInfoRequest with 3 elements
struct DocumentInfoRequest with 2 elements
struct DocumentSetDiffRequest with 1 element
```

### 29.3 Document RAG API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/documentrag/official/check_should_update` | GET | Check for updates |
| `api/ide/v1/documentrag/official/latest_document_sets` | GET | Get latest doc sets |
| `api/ide/v1/documentrag/custom/index_document_set` | POST | Index custom doc set |
| `api/ide/v1/documentrag/custom/delete_document_set` | DELETE | Delete custom doc set |
| `api/ide/v1/documentrag/custom/document_sets_status` | GET | Get doc sets status |
| `api/ide/v1/documentrag/retrieve` | POST | Retrieve from docs |

### 29.4 Document Build Status

```rust
struct DocumentBuildStatus with 3 elements
struct DocumentIndexStatus with 3 elements
```

### 29.5 External Documents

```rust
struct ExternalDocument {
    related_doc: Vec<RelatedDoc>,
    // ... additional fields
}
```

---

## 30. Team Agent System

### 30.1 Team Agent Structures

```rust
struct TeamAgentListItem {
    agent_env: String,
    last_updated_at: i64,
    avatar_url: String,
    // ... additional fields
}

struct TeamAgentDetailsItem {
    // Team agent details
}

struct TeamAgentDetailsResponse {
    // Response with agent details
}

struct BackendTeamAgentSubAgent {
    // Backend sub-agent structure
}

struct BackendTeamAgentCreateRequest {
    // Request to create team agent
}
```

### 30.2 Team Agent Request/Response Types

```rust
struct TeamAgentSubTeamAgentRemoveRequest { ... }
struct TeamAgentListRequest {
    search_key_word: String,
    sort_by: String,
    sort_order: String,
}
struct TeamAgentListResponse { ... }
struct TeamAgentDetailsRequest { ... }
```

### 30.3 Team Agent API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/agent/team_agent/create` | POST | Create team agent |
| `api/ide/v1/agent/team_agent/update` | POST | Update team agent |
| `api/ide/v1/agent/team_agent/remove` | DELETE | Remove team agent |
| `api/ide/v1/agent/team_agent/list` | GET | List team agents |
| `api/ide/v1/agent/team_agent/details` | GET | Get agent details |
| `api/ide/v1/agent/team_agent/change_status` | POST | Change agent status |

---

## 31. MCP Whitelist System

### 31.1 MCP Whitelist Structures

```rust
struct MCPWhitelistConfigInfo {
    global_enable: bool,
    whitelists: Vec<MCPWhitelist>,
}

struct MCPWhitelist {
    arg: String,
    args_hash: String,
    config_json: String,
    // ... additional fields
}
```

### 31.2 MCP Whitelist Features

- Global enable/disable for MCP tools
- Per-tool whitelist configuration
- Argument hash for tool validation
- JSON configuration for tool settings

---

## 32. Event and Telemetry System

### 32.1 Chat Event Types

| Event Type | Elements | Description |
|------------|----------|-------------|
| `ToolCallEvent` | 11 | Tool call execution event |
| `TaskCreatedEvent` | 2 | Task created event |
| `ThoughtEvent` | 8 | Agent thought event |
| `TurnCompletionEvent` | 6 | Turn completion event |
| `MissingHistoryEvent` | 1 | Missing history event |
| `RequiredContextEvent` | 1 | Required context event |
| `HistoryEvent` | 6 | History event |
| `SubAgentCreateEvent` | 6 | Sub-agent creation event |
| `AgentIdleEvent` | 6 | Agent idle event |
| `ErrorEvent` | 4 | Error event |
| `DoneEvent` | 1 | Done event |
| `QueueBeginEvent` | 4 | Queue begin event |
| `QueueEndEvent` | 3 | Queue end event |
| `QueueContinueEvent` | 1 | Queue continue event |

### 32.2 Hook System

```rust
struct RawEventHookGroup with 3 elements
struct RawHookItem with 3 elements
struct RawHookOutput with 5 elements
struct RawHookSpecificOutput with 5 elements
```

### 32.3 Telemetry Events

```rust
struct LogEvent with 5 elements
struct SandboxTraceEvent with 3 elements
```

### 32.4 Slardar Telemetry

```rust
struct SlardarParams {
    // Slardar telemetry parameters
    // Used for performance monitoring and error tracking
}
```

### 32.5 Event Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/cloud_agent/event.rs:31
apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/slardar_tracing/transport.rs:114
```

### 32.6 Telemetry Events

```
icube_ai_completion_execute — Completion execution
process_startup_event — Process startup
icube_ai_chat_first_token — First token in chat
icube_ai_front_response — Front response
icube_ai_completion_extension_active — Extension active
icube_device_register_init — Device register
icube_ai_chat_view_init — Chat view init
icube_rust_start_manager — Rust manager start
icube_rust_error — Rust error
icube_ai_start_mcp — MCP start
icube_ai_mcp_call_tool — MCP tool call
icube_ai_mcp_call_success — MCP call success
icube_ai_start_mcp_failed — MCP start failed
icube_ai_catch_mcp_error — MCP error catch
extensionHostCrash — Extension host crash
utilityprocessCrash — Utility process crash
icube_ai_apply_finished — Apply finished
icube_ai_completion_extension_crash — Extension crash
icube_ai_mcp_call_failed — MCP call failed
icube_ai_asr_error — ASR error
icube_ai_agent_react_error — Agent react error
icube_ai_agent_project_create — Agent project create
code_comp_request — Code completion request
code_comp_success — Code completion success
tool_call_request — Tool call request
tool_call_run — Tool call run
tool_call_success — Tool call success
tool_call_failed — Tool call failed
tool_call_skip — Tool call skip
icube_generate_title_request — Generate title request
icube_generate_title_success — Generate title success
skill_recommend_trigger — Skill recommend trigger
hooks_execute — Hooks execute
icube_hooks_report — Hooks report
```

---

## 33. Todo List and Task Management

### 33.1 Todo List Structures

```rust
struct TodoList {
    items: Vec<TodoItem>,
}

struct TodoItem {
    // Todo item structure
}

struct TodoLine with 3 elements {
    // Todo line structure
    cleared: bool,
    // ... 2 more fields
}
```

### 33.2 Todo List Request/Response Types

```rust
struct GetCurrentTodoListBySessionRequest { ... }
struct GetCurrentTodoListBySessionResponse { ... }
struct ClearSessionLastMessageTodoItemsRequest { ... }
struct ClearSessionLastMessageTodoItemsResponse { ... }
struct GetTodoListFeatureStatusResponse { ... }
```

### 33.3 Todo Write Tool

```rust
struct TodoWriteParams {
    // Parameters for todo_write tool
}

struct TodoWriteResult {
    // Result of todo_write tool
}
```

### 33.4 Todo List Configuration

```rust
struct DynamicConfigTodoList {
    // Dynamic configuration for todo list
}

struct TodoListConfiguration {
    // Todo list configuration
}
```

---

## 34. Skill System

### 34.1 Skill Structures

```rust
struct RecommendedSkill with 11 elements
struct TrialSkillInfo with 12 elements
struct SkillAsAgentConfig with 2 elements
struct SkillConfig {
    builtin_skill_status: String,
    // ... additional fields
}
```

### 34.2 Skill Request/Response Types

```rust
struct ListSkillsRequest with 1 element
struct ListSkillsResponse {
    skills: Vec<SkillItem>,
}

struct SkillItem {
    // Skill item structure
}

struct SkillRecommendParams { ... }
struct SkillRecommendConfig { ... }
struct GetSkillRecommendationResponse { ... }
struct SkillLanguage { ... }
struct SkillRecommendResult { ... }
struct SkillRecommendResultItem { ... }
```

### 34.3 Skill Frontmatter

```rust
struct SkillFrontmatter {
    // Skill frontmatter structure
    // Used for skill definition files
}

struct ToolYamlDefinition {
    // Tool YAML definition
}

struct ShadowKnowledgeFrontmatter {
    // Shadow knowledge frontmatter
}
```

### 34.4 Skill Parameters

```rust
struct SkillParams with 1 element
struct SkillResult with 3 elements
```

### 34.5 Skill Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/skill/util.rs:168
apps/icube_server_rs/modules/ai-agent/src/domain/snapshot/snapshot_service.rs:82
```

---

## 35. Plan System

### 35.1 Plan Structures

```rust
struct MessagePlanItem with 16 elements
struct ExitPlanModeParams with 2 elements
struct PlanRetrySlardarEventParams with 2 elements
```

### 35.2 Plan Context

```rust
struct CurrentPlanContext {
    current_plan: String,
    // ... additional fields
}
```

### 35.3 Plan Features

- Plan mode with exit capability
- Plan retry with telemetry
- Plan item management
- Integration with todo list

---

## 36. Configuration System

### 36.1 Configuration Structures

```rust
struct ShallowMementoConfiguration { ... }
struct LintErrorAutoFixConfiguration { ... }
struct CoreMemoryConfiguration { ... }
struct ResourceDiagnosisConfiguration { ... }
struct GitAiConfiguration { ... }
struct StuckChatDiagnosisConfiguration { ... }
struct RefactorAgentConfiguration { ... }
struct AgentReviewConfiguration { ... }
struct AskUserQuestionConfiguration { ... }
struct InitCommandConfiguration { ... }
struct SlashCommandsConfiguration { ... }
struct ChatMemoryConfiguration { ... }
struct ChatInputCompletionConfiguration { ... }
struct ChatSuggestConfiguration { ... }
struct ChatSkillRecommendConfiguration { ... }
struct ChatSkillRecommendOpenConfiguration { ... }
struct PastChatsConfiguration { ... }
struct KnowledgesConfiguration { ... }
struct VisualEditorConfiguration { ... }
struct JetBrainsGoEnhanceConfiguration { ... }
struct ForkChatConfiguration { ... }
struct AssistantConfiguration { ... }
struct SoloTeamConfiguration { ... }
struct FileSubAgentsConfiguration { ... }
struct DeepWikiConfiguration { ... }
struct DynamicUIConfiguration { ... }
struct BytedanceInternalCodingSkillConfiguration { ... }
struct FileOpOutsideWorkspaceConfiguration { ... }
```

### 36.2 CKG Configuration

```rust
struct CKGProject { ... }
struct CKGInitRequest { ... }
struct CKGCancelIndexRequest { ... }
struct CKGDeleteIndexRequest { ... }
struct CKGRefreshTokenRequest { ... }
struct CKGGetBuildStatusRequest { ... }
struct CKGDocumentActionFile { ... }
struct CKGDocumentActionRequest { ... }
struct CKGSetupRequest { ... }
struct CKGCursorMoveRequest { ... }
struct CKGIsCKGEnabledForNonWorkspaceScenarioRequest { ... }
struct CKGGetBuildStatusResponse {
    storage_size: i64,
    // ... additional fields
}
struct CKGUpdatePortRequest { ... }
```

---

## 37. Finish and Merge System

### 37.1 Finish Structures

```rust
struct FinishParams with 1 element
struct FinishData with 2 elements
struct FinishDataProducts with 10 elements
struct FinishDataPreview with 1 element
```

### 37.2 Merge Structures

```rust
struct MergePrInfo with 2 elements
struct MergeProducts with 8 elements
struct MergeTotalDiffInfo { ... }
struct MergeFileDiffInfo { ... }
```

### 37.3 Changed Skills and Files

```rust
struct ChangedSkills {
    skills: Vec<SkillInfo>,
}

struct SkillInfo {
    // Skill information
}

struct ChangedFiles {
    // Changed files information
}
```

### 37.4 Finish Data Products

```rust
struct FinishDataProducts {
    scheduled_task_product: Option<ScheduledTaskProduct>,
    merge_pr_info: Option<MergePrInfo>,
    merge_products: Option<MergeProducts>,
    feishu_doc_info: Option<FeishuDocInfo>,
    changed_files: Option<ChangedFiles>,
    // ... 5 more fields
}
```

### 37.5 Scheduled Task Product

```rust
struct ScheduledTaskProduct {
    // Scheduled task product structure
}
```

### 37.6 Feishu Doc Info

```rust
struct FeishuDocInfo {
    // Feishu document information
}
```

### 37.7 Finish Source Path

```
apps/icube_server_rs/modules/ai-agent/src/domain/toolcall/tools/finish.rs:385
```

---

## 38. File Diff System

### 38.1 File Diff Structures

```rust
struct AIFileDiffResult with 3 elements
struct FileDiffResult with 2 elements
struct FileToolcallDataChangeDiffInfo { ... }
```

### 38.2 File Tool Call Data

```rust
struct FileToolcallData {
    change: FileToolcallDataChange,
    // ... additional fields
}

struct FileToolcallDataChange {
    diff_info: FileToolcallDataChangeDiffInfo,
    // ... additional fields
}
```

### 38.3 Tool Call Result

```rust
struct ToolcallResult {
    // Tool call result structure
}

struct ToolcallResultImage {
    // Tool call result with image
}
```

---

## 39. Search System

### 39.1 Ripgrep Integration

```rust
struct RipgrepOutput with 2 elements
struct RipgrepData with 5 elements
struct RipgrepPath with 1 element
struct RipgrepLines with 1 element
struct RipgrepSubmatch with 2 elements
```

### 39.2 Search Structures

```rust
struct SearchReplaceFixResponse with 1 element
struct SearchReplaceFixResponseItem with 2 elements
struct WebSearchReference with 7 elements
struct WebSearchResponse with 3 elements
struct FileSearchItem with 4 elements
struct SearchGlobalResultMatches with 2 elements
struct SearchGlobalResultMatchesLine with 2 elements
```

### 39.3 Search Parameters

```rust
struct GrepParams {
    // Grep tool parameters
}

struct GrepResult {
    // Grep tool result
}

struct SearchByRegexParams {
    search_directory: String,
    search_level: i32,
    // ... additional fields
}

struct SearchByRegexEventParams {
    // Search by regex event parameters
}

struct SearchByRegexEventMetrics {
    matched_result_num: i32,
    matched_result_chars: i32,
}
```

### 39.4 Search Codebase

```rust
struct SearchCodebaseParams { ... }
struct SearchCodebaseFile { ... }
struct SearchCodebaseResult { ... }
```

### 39.5 Search Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/workspace/ripgrep.rs:131
apps/icube_server_rs/modules/ai-agent/src/domain/toolcall/tools/search_codebase.rs:375
```

### 39.6 Web Search

```rust
struct WebSearchParams {
    // Web search parameters
}
```

---

## 40. Snapshot and Worktree System

### 40.1 Snapshot Structures

```rust
struct UpdateSnapshotArgs with 5 elements
struct CleanUpSnapshotArgs with 2 elements
struct SnapshotRevertArgs with 3 elements
struct SnapshotFileReviewArgs with 3 elements
struct GetSnapshotIdByMessageIdsArgs with 3 elements
struct DeleteSnapshotArgs with 3 elements
struct SnapshotDiffData with 1 element
struct SnapshotRevertResult with 6 elements
```

### 40.2 Snapshot Configuration

```rust
struct SnapshotV2 {
    enable_v2: bool,
    force_double_write: bool,
}

struct SnapshotCleanUp {
    // Snapshot cleanup configuration
}

struct SnapshotIgnore {
    ignore_rule_list: Vec<String>,
}
```

### 40.3 Snapshot Events

```
SnapshotCreateSlardarEventParams
SnapshotUpdateSlardarEventParams
SnapshotRevertSlardarEventParams
SnapshotListSlardarEventParams
SnapshotDoubleWriteSlardarEventParams
SnapshotStorageSlardarEventParams
```

### 40.4 Worktree Structures

```rust
struct WorktreeMetaData with 3 elements
struct WorktreeData with 11 elements
struct BatchMarkWorktreesDeletedArgs with 1 element
struct RemoveWorkTreeResponse {
    paths: Vec<String>,
}
```

### 40.5 Git AI Checkpoint

```rust
struct GitAiCheckpointAcceptedBlockReport {
    old_content_sha256: String,
    new_content_sha256: String,
    runtime: String,
    diff: String,
    accepted_blocks: Vec<String>,
}

struct GitAiCheckpointChangeReport {
    operation_id: String,
    repo_working_dir: String,
    // ... additional fields
}

struct GitAiCheckpointReport {
    // Git AI checkpoint report
}
```

### 40.6 Snapshot Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/agent_v3/service/git_ai_checkpoint.rs:115
```

---

## 41. Billing and Payment System

### 41.1 Stripe Integration

```rust
struct StripePriceInfo with 7 elements {
    anon_key: String,
    project_url: String,
    service_role_key: String,
    interval_count: i32,
    currency: String,
    unit_amount_decimal: String,
    nickname: String,
}

struct StripeProduct with 5 elements {
    // Stripe product structure
}

struct StripePaymentStore with 3 elements {
    prices: Vec<StripePriceInfo>,
    // ... 2 more fields
}
```

### 41.2 Session Usage

```rust
struct GetSessionUsageResponse with 1 element
struct SessionUsage with 9 elements
struct SessionUsageExtraInfo with 4 elements
struct CloudContextUsageItem with 4 elements
```

### 41.3 Usage Tracking

```
TokenUsageEvent with 9 elements
TimingCostEvent with 20 elements
```

### 41.4 Billing API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `api/v1/commercial/get_session_usage` | GET | Get session usage |
| `api/v1/commercial/get_user_activity` | GET | Get user activity |
| `api/v1/commercial/get_mode_info` | GET | Get mode info |
| `api/v1/commercial/chat_mode` | GET | Get chat mode |
| `api/v1/commercial/save_status` | POST | Save status |

---

## 42. Browser Automation Parameters

### 42.1 Browser Navigate Parameters

```rust
struct BrowserNavigateParams with 6 elements {
    url: String,
    new_tab: bool,
    take_screenshot_afterwards: bool,
    original_url: String,
    // ... 2 more fields
}
```

### 42.2 Browser Snapshot Parameters

```rust
struct BrowserSnapshotParams with 11 elements {
    max_nodes: i32,
    include_ignored: bool,
    interactive: bool,
    include_diff: bool,
    return_image_uri: bool,
    // ... 6 more fields
}
```

### 42.3 Browser Click Parameters

```rust
struct BrowserClickParams with 6 elements {
    double_click: bool,
    modifiers: Vec<String>,
    // ... 4 more fields
}
```

### 42.4 Browser Type Parameters

```rust
struct BrowserTypeParams with 6 elements {
    submit: bool,
    slowly: bool,
    // ... 4 more fields
}
```

### 42.5 Browser Hover Parameters

```rust
struct BrowserHoverParams with 3 elements {
    // 3-element hover parameters
}
```

### 42.6 Browser Scroll Parameters

```rust
struct BrowserScrollParams with 8 elements {
    direction: String,
    delta_x: f64,
    delta_y: f64,
    scroll_into_view: bool,
    // ... 4 more fields
}
```

### 42.7 Browser Select Option Parameters

```rust
struct BrowserSelectOptionParams with 4 elements {
    // 4-element select option parameters
}
```

### 42.8 Browser Press Key Parameters

```rust
struct BrowserPressKeyParams with 3 elements {
    // 3-element press key parameters
}
```

### 42.9 Browser Wait For Parameters

```rust
struct BrowserWaitForParams with 6 elements {
    text: Option<String>,
    gone: Option<bool>,
    // ... 4 more fields
}
```

### 42.10 Browser Get Attribute Parameters

```rust
struct BrowserGetAttributeParams with 3 elements {
    // 3-element get attribute parameters
}
```

### 42.11 Browser Console Messages Parameters

```rust
struct BrowserConsoleMessagesParams with 1 element {
    // 1-element console messages parameters
}
```

### 42.12 Browser Network Requests Parameters

```rust
struct BrowserNetworkRequestsParams with 1 element {
    // 1-element network requests parameters
}
```

### 42.13 Browser Evaluate Script Parameters

```rust
struct BrowserEvaluateScriptParams with 2 elements {
    // 2-element evaluate script parameters
}
```

### 42.14 Browser Take Screenshot Parameters

```rust
struct BrowserTakeScreenshotParams with 5 elements {
    full_page: bool,
    // ... 4 more fields
}
```

### 42.15 Browser Go Back Parameters

```rust
struct BrowserGoBackParams with 2 elements {
    // 2-element go back parameters
}
```

### 42.16 Browser Tabs Parameters

```rust
struct BrowserTabsParams with 3 elements {
    // 3-element tabs parameters
}
```

### 42.17 Browser Lock Parameters

```rust
struct BrowserLockParams with 4 elements {
    // 4-element lock parameters
}
```

### 42.18 Browser Unlock Parameters

```rust
struct BrowserUnlockParams with 3 elements {
    plan_item_id: String,
    // ... 2 more fields
}
```

### 42.19 Browser Drag Parameters

```rust
struct BrowserDragParams with 6 elements {
    hand_over_to_user: bool,
    // ... 5 more fields
}
```

### 42.20 Browser Upload File Parameters

```rust
struct BrowserUploadFileParams with 5 elements {
    source_ref: String,
    target_ref: String,
    target_x: f64,
    target_y: f64,
    // ... 1 more field
}
```

### 42.21 Browser Handle Dialog Parameters

```rust
struct BrowserHandleDialogParams with 3 elements {
    editor_id: String,
    // ... 2 more fields
}
```

### 42.22 Browser Waiting For User Interaction

```rust
struct BrowserWaitingForUserInteractionParams with 2 elements {
    // 2-element waiting for user interaction parameters
}
```

### 42.23 Browser Code Variable

```rust
struct BrowserCodeVariable with 5 elements {
    source_code: String,
    // ... 4 more fields
}
```

---

## 43. MCP Server Management

### 43.1 MCP Server Structure

```rust
struct MCPServer with 4 elements {
    // MCP server configuration
}
```

### 43.2 MCP Request/Response Types

```rust
struct RemoveMcpServerReq with 1 element {
    mcp_server_ids: Vec<String>,
}

struct UpdateMcpAgentRelationsReq with 3 elements {
    // Update MCP agent relations
}

struct UpdateAgentMcpServersReq with 2 elements {
    mcp_servers: Vec<String>,
    // ... 1 more field
}
```

### 43.3 MCP Tool Like Result

```rust
struct McpToolLikeResultContentItem with 5 elements {
    prompt_text: String,
    // ... 4 more fields
}

struct McpToolLikeResult with 3 elements {
    // MCP tool like result
}
```

### 43.4 MCP Service Parameters

```rust
struct RunMcpParams {
    // Run MCP parameters
}

struct RunMcpServiceParams with 3 elements {
    target_terminal: String,
    blocking: bool,
    wait_ms_before_async: i32,
}
```

### 43.5 MCP Tool Name Parsing

```
[parse_mcp_tool_name] wildcard not supported
[parse_mcp_tool_name] tool_name is empty
[parse_mcp_tool_name] server_label is empty
[parse_mcp_tool_name] server-level wildcard not supported, please specify a concrete tool name
```

### 43.6 MCP Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/dal/model/mcp_server_agent_relation.rs
apps/icube_server_rs/modules/ai-agent/src/handler/agent.rs:235
```

---

## 44. Agent DSL System

### 44.1 Agent DSL Structures

```rust
struct AgentDsl {
    // Agent DSL structure
}

struct AgentRunInfoDto {
    // Agent run info
}

struct McpFolderInfo {
    servers: Vec<String>,
    // ... additional fields
}
```

### 44.2 Create Agent Task Request

```rust
struct CreateAgentTaskRequest {
    tunnel_id: String,
    is_custom_model: bool,
    ide_version: String,
    extra_context: serde_json::Value,
    history_id_list: Vec<String>,
    missing_history: bool,
    available_tool_list: Vec<String>,
    mcp_tool_name: String,
    mcp_tool_list: Vec<String>,
    request_seq: i32,
    custom_agent_list: Vec<String>,
    agent_version: String,
    ab_info: serde_json::Value,
    mode_type: String,
    custom_subagent_info: serde_json::Value,
    skill_list: Vec<String>,
    agent_dsl: AgentDsl,
    agent_static_dsl_name: String,
    mcp_folder_info: McpFolderInfo,
    access_type: String,
    mcp_folder_base_path: String,
    cached_tool_groups: Vec<String>,
    enable_decouple_model_extra_config: bool,
    history_message_limit: i32,
    raw_rules: Vec<String>,
    enterprise_custom_hyper_params: EnterpriseCustomHyperParams,
    message_origin: String,
    additional_instruction: String,
}
```

### 44.3 Enterprise Custom Hyper Params

```rust
struct EnterpriseCustomHyperParams with 4 elements {
    // Enterprise custom hyper parameters
}
```

---

## 45. Chat Turn Cost Detail

### 45.1 Chat Turn Cost Detail Args

```rust
struct GetChatTurnCostDetailArgs with 1 element {
    // Chat turn cost detail arguments
}
```

### 45.2 Chat Turn Cost Steps

```
rs_01_chat_begin — Chat begin
rs_02_get_session — Get session
rs_03_get_history_message — Get history message
rs_04_create_message — Create message
rs_05_create_snapshot — Create snapshot
rs_06_get_custom_model — Get custom model
rs_06_get_fast_apply_model — Get fast apply model
rs_06_fast_apply_fallback — Fast apply fallback
rs_06_resolver_diagnostic — Resolver diagnostic
rs_06_resolver_project_labels — Resolver project labels
rs_06_resolver_metadata — Resolver metadata
rs_06_resolver_current_editor — Resolver current editor
rs_06_resolver_user_message — Resolver user message
rs_06_resolver_selection — Resolver selection
rs_06_resolver_terminal — Resolver terminal
rs_06_resolver_custom_rules — Resolver custom rules
rs_06_resolver_doc — Resolver doc
rs_06_resolver_lint_error — Resolver lint error
rs_06_resolver_problem — Resolver problem
rs_06_resolver_log_message — Resolver log message
rs_06_resolver_user_interaction — Resolver user interaction
rs_06_resolver_websearch — Resolver websearch
rs_06_resolver_browser_selection — Resolver browser selection
rs_06_resolver_file_diff — Resolver file diff
rs_06_resolver_slash_command — Resolver slash command
rs_06_resolvers_begin — Resolvers begin
rs_06_resolve_contexts — Resolve contexts
rs_07_create_task — Create task
rs_08_create_turn — Create turn
rs_09_process_task — Process task
rs_10_prepare_guideline_context — Prepare guideline context
rs_11_ckg_retrieve_02_call_ckg — CKG retrieve call
rs_11_ckg_retrieve_03_add_folder — CKG retrieve add folder
rs_11_ckg_retrieve_04_finish_verify — CKG retrieve finish verify
rs_12_list_01_agent_tools — List agent tools
rs_12_list_02_mcp_tools — List MCP tools
rs_13_render_user_prompt — Render user prompt
rs_14_get_history_plan — Get history plan
rs_15_before_generate_plan — Before generate plan
rs_16_llm_generate_plain_item — LLM generate plain item
rs_17_before_request_llm — Before request LLM
rs_18_llm_response_first_token — LLM response first token
rs_19_llm_response_done — LLM response done
net_01_process — Network process
svr_01_queue_timing — Server queue timing
svr_02_preprocess_timing — Server preprocess timing
svr__02_preprocess_check_risk — Server preprocess check risk
svr__02_preprocess_build_llm_prompt — Server preprocess build LLM prompt
svr__02_preprocess_other — Server preprocess other
svr_04_postprocess_timing — Server postprocess timing
svr__04_postprocess_security_check — Server postprocess security check
svr__04_postprocess_other — Server postprocess other
svr_02_gateway_preprocess_timing — Server gateway preprocess timing
svr_06_platform_first_token_timing — Server platform first token timing
svr__06_platform_preprocess — Server platform preprocess
svr__06_platform_inner_first_token_timing — Server platform inner first token timing
svr__06_platform_network_latency — Server platform network latency
svr__06_platform_provider_first_token_timing — Server platform provider first token timing
svr__06_platform_provider_network_latency — Server platform provider network latency
svr__06_platform_other — Server platform other
svr_09_middleware_processing_timing — Server middleware processing timing
svr_10_first_sse_event_timing — Server first SSE event timing
svr_11_server_processing_time — Server processing time
svr_11_gateway_server_processing_time — Server gateway server processing time
svr_11_cloud_agent_preprocessing — Server cloud agent preprocessing
svr_11_cloud_agent_postprocessing — Server cloud agent postprocessing
svr_11_cloud_agent_middleware — Server cloud agent middleware
rs_start_chat_01_begin — Start chat begin
```

---

## 46. Custom Tool System

### 46.1 Custom Tool Structures

```rust
struct RunCustomToolParams with 2 elements {
    rewrite: bool,
    // ... 1 more field
}

struct CustomToolDefForCloud {
    // Custom tool definition for cloud
}

struct ToolYamlDefinition {
    // Tool YAML definition
}

struct SkillFrontmatter {
    // Skill frontmatter
}

struct ShadowKnowledgeFrontmatter {
    // Shadow knowledge frontmatter
}
```

### 46.2 Custom Tool Features

- YAML-based tool definitions
- Skill frontmatter for tool configuration
- Shadow knowledge for tool context
- Cloud-specific tool definitions

### 46.3 Custom Tool Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/skill/util.rs:168
```

---

## 47. Additional Subsystems

### 28.1 CKG (Code Knowledge Graph)

- 44MB shared library for code understanding
- `ckg retrieve is None` — No results
- `ckg retrieve finished` — Retrieval complete
- Integration with prompt system

### 28.2 DeepWiki

```
generate_deepwiki — Generate wiki content
update_deepwiki — Update wiki content
clear_wiki — Clear wiki content
```

- Repository documentation/knowledge system
- Wiki content management

### 28.3 Voice System

```
voice_transcription — Speech to text
voice_summary — Voice summary generation
voice_chat — Voice-based chat
```

### 28.4 Lark/Feishu Integration

```
lark token prefetch — Prefetch Lark tokens
lark-cli — Lark CLI integration
```

- IM bridge for enterprise messaging
- Token management for Lark API

### 28.5 Skills System

```rust
struct RecommendedSkill with 11 elements
struct TrialSkillInfo with 12 elements
struct SkillAsAgentConfig with 2 elements
```

- Skill recommendation system
- Trial skill management
- Skill-as-agent configuration

### 28.6 Knowledge System

```
TRAE-knowledges — Hierarchical knowledge base system
```

- Hierarchical knowledge base
- Knowledge retrieval for context

### 28.7 gRPC/Protobuf

- Internal service communication via `volo-grpc`
- Structured message serialization via `volo-gen`
- Used for high-performance internal RPC

### 28.8 Telemetry (Slardar)

- ByteDance's APM/telemetry system
- Performance monitoring
- Error tracking
- Usage analytics

### 28.9 Render Variables

```rust
struct RenderVariables with 112 elements {
    enable_parallel_tool_calling: bool,
    is_in_chat_mode: bool,
    is_in_plan_v2: bool,
    response_can_be_text: bool,
    left_turns: i32,
    text_to_image_url: String,
    enable_multi_agent_reader: bool,
    sub_agents: Vec<String>,
    user_auto_run_prompt: String,
    is_use_npm_mirror: bool,
    language_settings: String,
    actived_environments: Vec<String>,
    supported_environments: Vec<String>,
    // ... 99 more fields
}
```

### 28.10 Image Generation

- Text-to-image URL support
- Image generation integration

---

## 16. Next Steps

1. **Network Traffic Analysis** - Capture actual API calls
2. **Token Format Analysis** - Decode JWT structure
3. **Error Code Mapping** - Complete error code reference
4. **Performance Optimization** - Connection pooling, caching
5. **Security Audit** - Token security, input validation
6. **Proxy Implementation** - Build actual proxy server
7. **Testing** - Validate proxy with Codex integration

---

## Appendix A: Key File Locations

| File | Purpose |
|------|---------|
| `@aha-kit/rpc/dist/index.js` | JSON-RPC implementation |
| `@aha-kit/ipc-linux-arm64/dist/client.js` | IPC client |
| `product.json` | API endpoint configuration |
| `ai-agent-win32-strings.txt` | Binary string analysis |

## Appendix B: Error Codes

| Code | Name | Description |
|------|------|-------------|
| -32700 | Parse Error | Invalid JSON |
| -32600 | Invalid Request | Invalid JSON-RPC request |
| -32601 | Method Not Found | Unknown method |
| -32602 | Invalid Params | Invalid parameters |
| -32603 | Internal Error | Server error |
| -32000 | Stream Timeout | Stream timed out |
| -32001 | Stream Cancelled | Stream cancelled by client |

## Appendix C: Boot Configuration Structure

The BootConfig is the initial configuration fetched from `icube-boot.trae.ai`.

### BootConfig (17 elements)

```rust
struct BootConfig {
    agent: AgentConfig,          // AI agent configuration
    ckg: CKGConfig,             // Code Knowledge Graph config
    hub: HubConfig,             // Hub Bridge config
    tea_lite: TeaConfig,        // Tea telemetry (lite)
    tea_web: TeaConfig,         // Tea telemetry (web)
    slardar: Slardar,           // Slardar APM config
    ttnet: TTNetConfig,         // Network config
    userInfo: BootUserInfo,     // User authentication info
    image_x: ImageXConfig,      // Image service config
    cdn_prefix: String,         // CDN URL prefix
    host_tmp_dir: String,       // Temporary directory
    store_region: String,       // Storage region
    frontier: FrontierConfig,   // Frontier protocol config
    ug_api: String,             // User generated API
    ppe_env: String,            // PPE environment
    // ... 2 more fields
}
```

### BootUserInfo (6 elements)

```rust
struct BootUserInfo {
    expired_at: i64,           // Token expiration timestamp
    refresh_expired_at: i64,   // Refresh token expiration
    user_id: String,           // User identifier
    token_release_at: i64,     // Token release timestamp
    token_host: String,        // Token host URL
    // ... 1 more field
}
```

### BootConfig Source Path

```
apps/icube_server_rs/crates/ai-config/src/source/async_builder.rs:296
```

### BootConfig Fields

```
agent, ckg, hub, teaLite, teaWeb, slardar, ttnet, userInfo, imageX, cdnPrefix, hostTmpDir, storeRegion, frontier, ugApi, ppeEnv
```

---

## Appendix D: OpenAI-Compatible Request/Response Structures

### OpenAIRequest (7 elements)

```rust
struct OpenAIRequest {
    model: String,
    messages: Vec<OpenAIMessage>,
    tools: Option<Vec<OpenAITool>>,
    tool_choice: Option<String>,
    stream: Option<bool>,
    max_tokens: Option<i32>,
    temperature: Option<f32>,
}
```

### OpenAIMessage (4 elements)

```rust
struct OpenAIMessage {
    role: String,
    content: Option<OpenAIMessageContent>,
    tool_calls: Option<Vec<OpenAIToolCall>>,
    tool_call_id: Option<String>,
}
```

### OpenAITool (2 elements)

```rust
struct OpenAITool {
    r#type: String,
    function: OpenAIFunction,
}
```

### OpenAIFunction (3 elements)

```rust
struct OpenAIFunction {
    name: String,
    description: String,
    parameters: serde_json::Value,
}
```

### OpenAIToolCall (3 elements)

```rust
struct OpenAIToolCall {
    id: String,
    r#type: String,
    function: OpenAIFunctionCall,
}
```

### OpenAIFunctionCall (2 elements)

```rust
struct OpenAIFunctionCall {
    name: String,
    arguments: String,
}
```

### OpenAIContentPart (3 elements)

```rust
struct OpenAIContentPart {
    r#type: String,
    text: Option<String>,
    image_url: Option<OpenAIImageUrl>,
}
```

### OpenAIImageUrl (1 element)

```rust
struct OpenAIImageUrl {
    url: String,
}
```

---

## Appendix E: Native LLM Response Structures

### NativeLLMMessage (8 elements)

```rust
struct NativeLLMMessage {
    role: String,
    content: Option<String>,
    tool_calls: Option<Vec<LLMClientToolCall>>,
    tool_call_id: Option<String>,
    reasoning_details: Option<Vec<LLMClientReasoningDetailsRaw>>,
    // ... 3 more fields
}
```

### NativeLLMUsage (3 elements)

```rust
struct NativeLLMUsage {
    prompt_tokens: i32,
    completion_tokens: i32,
    total_tokens: i32,
}
```

### NativeAnthropicLLMResponse (3 elements)

```rust
struct NativeAnthropicLLMResponse {
    content: Vec<NativeAnthropicContent>,
    model: String,
    usage: NativeAnthropicUsage,
}
```

### NativeAnthropicMessageDelta (2 elements)

```rust
struct NativeAnthropicMessageDelta {
    // 2-element structure for Anthropic message deltas
    // Used for streaming responses
}
```

### NativeAnthropicUsage (4 elements)

```rust
struct NativeAnthropicUsage {
    input_tokens: i32,
    output_tokens: i32,
    cache_creation_input_tokens: Option<i32>,
    cache_read_input_tokens: Option<i32>,
}
```

### AnthropicDeltaContent (6 elements)

```rust
struct AnthropicDeltaContent {
    r#type: String,
    text: Option<String>,
    partial_json: Option<String>,
    // ... 3 more fields
}
```

### NativeOpenrouterLLMResponse (7 elements)

```rust
struct NativeOpenrouterLLMResponse {
    id: String,
    model: String,
    choices: Vec<NativeOpenrouterLLMChoice>,
    usage: NativeOpenRouterLLMUsage,
    // ... 3 more fields
}
```

### NativeOpenrouterLLMChoice (5 elements)

```rust
struct NativeOpenrouterLLMChoice {
    index: i32,
    message: NativeLLMMessage,
    delta: Option<Delta>,
    finish_reason: Option<String>,
    native_finish_reason: Option<String>,
}
```

### NativeOpenrouterLLMError (2 elements)

```rust
struct NativeOpenrouterLLMError {
    message: String,
    r#type: String,
}
```

### NativeOpenrouterLLMErrorResponse (1 element)

```rust
struct NativeOpenrouterLLMErrorResponse {
    error: NativeOpenrouterLLMError,
}
```

### NativeOpenRouterLLMUsage (3 elements)

```rust
struct NativeOpenRouterLLMUsage {
    prompt_tokens: i32,
    completion_tokens: i32,
    total_tokens: i32,
}
```

### Delta (6 elements)

```rust
struct Delta {
    role: Option<String>,
    content: Option<String>,
    tool_calls: Option<Vec<LLMClientToolCall>>,
    // ... 3 more fields
}
```

### Choice (4 elements)

```rust
struct Choice {
    index: i32,
    message: NativeLLMMessage,
    finish_reason: Option<String>,
    // ... 1 more field
}
```

---

## Appendix F: Anthropic-Compatible Response Structures

### NativeAnthropicLLMResponse (3 elements)

```rust
struct NativeAnthropicLLMResponse {
    content: Vec<NativeAnthropicContent>,
    model: String,
    usage: NativeAnthropicUsage,
}
```

### NativeAnthropicUsage (4 elements)

```rust
struct NativeAnthropicUsage {
    input_tokens: i32,
    output_tokens: i32,
    cache_creation_input_tokens: Option<i32>,
    cache_read_input_tokens: Option<i32>,
}
```

### AnthropicDeltaContent (6 elements)

```rust
struct AnthropicDeltaContent {
    r#type: String,
    text: Option<String>,
    // ... 4 more fields
}
```

### AnthropicModel (4 elements)

```rust
struct AnthropicModel {
    id: String,
    display_name: String,
    // ... 2 more fields
}
```

### AnthropicModelListResponse (4 elements)

```rust
struct AnthropicModelListResponse {
    data: Vec<AnthropicModel>,
    has_more: bool,
    first_id: String,
    last_id: String,
}
```

---

## Appendix F: Native LLM Message Structure

### NativeLLMMessage (8 elements)

```rust
struct NativeLLMMessage {
    role: String,
    content: Option<String>,
    tool_calls: Option<Vec<LLMClientToolCall>>,
    tool_call_id: Option<String>,
    // ... 4 more fields
}
```

### LLMClientToolCall (5 elements)

```rust
struct LLMClientToolCall {
    id: String,
    r#type: String,
    function: LLMClientToolCallFunction,
    // ... 2 more fields
}
```

### LLMClientToolCallFunction (2 elements)

```rust
struct LLMClientToolCallFunction {
    name: String,
    arguments: String,
}
```

---

## Appendix G: Complete API Endpoint Reference

### IDE API v1 Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/chat` | POST | Main chat endpoint |
| `api/ide/v1/llm_raw_chat` | POST | Raw LLM chat (direct model access) |
| `api/ide/v2/llm_raw_chat` | POST | Raw LLM chat v2 |
| `api/ide/v1/model_list` | GET | List available models |
| `api/ide/v1/get_model_list` | GET | Get model list (alternative) |
| `api/ide/v1/get_detail_param` | GET | Get detailed parameters |
| `api/ide/v1/agents/runs` | POST | Start agent run |
| `api/ide/v1/agents/runs/:id/tool_call_outputs` | POST | Submit tool call outputs |
| `api/ide/v1/chat_prompt` | GET | Get chat prompt |
| `api/ide/v1/llm_raw_chat_prompt` | GET | Get raw chat prompt |
| `api/ide/v1/fast_apply` | POST | Fast code application |
| `api/ide/v1/connect` | POST | Connection management |
| `api/ide/v1/ping` | GET | Health check |
| `api/ide/v1/feedback` | POST | Submit feedback |
| `api/ide/v1/context_select` | POST | Context selection |
| `api/ide/v1/intent_detect` | POST | Intent detection |
| `api/ide/v1/query_rewrite` | POST | Query rewriting |
| `api/ide/v1/check_content` | POST | Content security check |
| `api/ide/v1/providers` | GET | List providers |
| `api/ide/v1/web_search` | POST | Web search |
| `api/ide/v1/web_fetch` | POST | Web page fetch |
| `api/ide/v1/skill_recommend` | GET | Skill recommendations |
| `api/ide/unstable/tools/diff` | POST | Diff tool (unstable) |

### Custom Model Management

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/add_custom_model` | POST | Add custom model |
| `api/ide/v1/update_custom_model` | POST | Update custom model |
| `api/ide/v1/get_custom_model_type_config` | GET | Get custom model config |

### Task Queue Management

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/cancel_queue_task` | POST | Cancel queued task |
| `api/ide/v1/jump_queue_task` | POST | Jump queue (priority) |

### Image Generation

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/text_to_image` | POST | Text to image |
| `api/ide/v1/tool_text_to_image` | POST | Tool text to image |
| `api/ide/v1/tool_text_to_image_stream` | POST | Streaming text to image |

### Document RAG (Retrieval Augmented Generation)

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/documentrag/official/check_should_update` | GET | Check for updates |
| `api/ide/v1/documentrag/official/latest_document_sets` | GET | Get latest doc sets |
| `api/ide/v1/documentrag/custom/index_document_set` | POST | Index custom doc set |
| `api/ide/v1/documentrag/custom/delete_document_set` | DELETE | Delete custom doc set |
| `api/ide/v1/documentrag/custom/document_sets_status` | GET | Get doc sets status |
| `api/ide/v1/documentrag/retrieve` | POST | Retrieve from docs |

### Resource Management

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/get_resource_upload_token` | GET | Get upload token |
| `api/ide/v1/get_resource_upload_url` | GET | Get upload URL |
| `api/ide/v1/get_resource_url` | GET | Get resource URL |
| `api/ide/v1/commit_resource_upload_result` | POST | Commit upload result |

### Privacy and Content

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/privacy/operation` | POST | Privacy operation |
| `api/ide/v1/privacy/query` | GET | Query privacy status |
| `api/ide/v1/report/multimodal` | POST | Report multimodal usage |
| `api/ide/v1/get/multimodal` | GET | Get multimodal data |

### Team Agent Management

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/agent/team_agent/create` | POST | Create team agent |
| `api/ide/v1/agent/team_agent/update` | POST | Update team agent |
| `api/ide/v1/agent/team_agent/remove` | DELETE | Remove team agent |
| `api/ide/v1/agent/team_agent/list` | GET | List team agents |
| `api/ide/v1/agent/team_agent/details` | GET | Get agent details |
| `api/ide/v1/agent/team_agent/change_status` | POST | Change agent status |

### Practice and Conversation

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/practice/generate_conversation_title` | POST | Generate title |

### Tenant Management

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/tenant/get_tenant_user_config` | GET | Get tenant config |
| `api/ide/v1/tenant/report_audit_log` | POST | Report audit log |

### Commercial API

| Path | Method | Purpose |
|------|--------|---------|
| `api/v1/commercial/get_mode_info` | GET | Get mode info |
| `api/v1/commercial/chat_mode` | GET | Get chat mode |
| `api/v1/commercial/save_status` | POST | Save status |
| `api/v1/commercial/get_session_usage` | GET | Get session usage |
| `api/v1/commercial/get_user_activity` | GET | Get user activity |

### Knowledge Base API

| Path | Method | Purpose |
|------|--------|---------|
| `api/v1/knowledgebase/teamDoc/getDocumentSetLists` | GET | Get doc set lists |
| `api/v1/knowledgebase/teamDoc/getDocumentSetInfo` | GET | Get doc set info |
| `api/v1/knowledgebase/teamDoc/getDocumentUrl` | GET | Get doc URL |
| `api/v1/knowledgebase/teamDoc/getDocumentSetDiff` | GET | Get doc set diff |

### Model Provider Endpoints

| Provider | Endpoint | Method | Purpose |
|----------|----------|--------|---------|
| **OpenAI** | `/models/chat/completions` | POST | OpenAI-compatible chat |
| **OpenAI** | `/v1/models` | GET | List models (OpenAI format) |
| **OpenAI** | `/openai/v1/chat/completions` | POST | OpenAI proxy endpoint |
| **Anthropic** | `/v1/messages` | POST | Anthropic messages API |
| **DeepSeek** | `deepseek/v1/models` | GET | DeepSeek models |
| **AWS Bedrock** | `/foundation-models/` | - | AWS Bedrock foundation models |
| **OpenRouter** | `/api/v1/chat/completions` | POST | OpenRouter chat completions |
| **Volcengine** | `/api/v1/chat/completions` | POST | Volcengine chat completions |
| **Gemini** | `/v1/models` | GET | Gemini models |
| **xAI** | `/v1/chat/completions` | POST | xAI chat completions |

### Provider-Specific Features

| Provider | Streaming | Tool Use | Vision | Reasoning |
|----------|-----------|----------|--------|-----------|
| OpenAI | Yes | Yes | Yes | Yes |
| Anthropic | Yes | Yes | Yes | Yes |
| DeepSeek | Yes | Yes | No | Yes |
| Gemini | Yes | Yes | Yes | Yes |
| AWS Bedrock | Yes | Yes | Yes | Yes |
| OpenRouter | Yes | Yes | Yes | Yes |
| Volcengine | Yes | Yes | No | No |
| xAI | Yes | Yes | No | No |

### Header: `x-ide-token`

The `x-ide-token` header is used for authentication on IDE API endpoints.

### Backend Service Endpoints

| Endpoint | Purpose |
|----------|---------|
| `icube-boot.trae.ai` | Boot configuration |
| `icube-normal.trae.ai` | Main AI backend |
| `core-normal.trae.ai` | Core API |
| `mcs-boot.trae.ai` | Model config service |
| `starling-normal.trae.ai` | Starling service |
| `libra-normal.trae.ai` | Libra service |

### IDE API Paths

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/chat` | POST | Main chat endpoint |
| `api/ide/v1/llm_raw_chat` | POST | Raw LLM chat (direct model access) |
| `api/ide/v1/model_list` | GET | List available models |
| `api/ide/v1/model_list_by_function` | GET | List models by function |
| `api/ide/v1/agents/runs` | POST | Start agent run |
| `api/ide/v1/agents/runs/:id` | GET | Get agent run status |
| `api/ide/v1/agents/runs/:id/stop` | POST | Stop agent run |

### Model Provider Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/models/chat/completions` | POST | OpenAI-compatible chat |
| `/v1/models` | GET | List models (OpenAI format) |
| `/v1/messages` | POST | Anthropic messages API |
| `/openai/v1/chat/completions` | POST | OpenAI proxy endpoint |

### Session Management

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/chat/sessions` | GET | List chat sessions |
| `api/ide/v1/chat/sessions` | POST | Create chat session |
| `api/ide/v1/chat/sessions/:id` | GET | Get session details |
| `api/ide/v1/chat/sessions/:id` | DELETE | Delete session |
| `api/ide/v1/chat/sessions/:id/messages` | GET | Get session messages |
| `api/ide/v1/chat/sessions/:id/messages` | POST | Send message |

### Tool and Agent APIs

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/tools` | GET | List available tools |
| `api/ide/v1/tools/:name/execute` | POST | Execute tool |
| `api/ide/v1/agents` | GET | List agents |
| `api/ide/v1/agents/:id` | GET | Get agent details |
| `api/ide/v1/agents/:id/start` | POST | Start agent |

### User and Config APIs

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/user/info` | GET | Get user info |
| `api/ide/v1/user/config` | GET | Get user config |
| `api/ide/v1/user/config` | PUT | Update user config |
| `api/ide/v1/models/config` | GET | Get model config |
| `api/ide/v1/models/config` | PUT | Update model config |

---

## Appendix H: Chat Session Data Structures

### RemoteChatSessionData (23 elements)

```rust
struct RemoteChatSessionData {
    // 23-element structure for remote chat session
    // Contains session metadata, user info, model config, etc.
}
```

### CreateChatSessionData (5 elements)

```rust
struct CreateChatSessionData {
    // 5-element structure for creating new chat sessions
}
```

### CreateChatSessionResponse (4 elements)

```rust
struct CreateChatSessionResponse {
    // 4-element response for session creation
}
```

### RemoteGetChatSessionResponse (3 elements)

```rust
struct RemoteGetChatSessionResponse {
    // 3-element response for getting session details
}
```

### FreezeChatSessionResponse (2 elements)

```rust
struct FreezeChatSessionResponse {
    // 2-element response for freezing sessions
}
```

### ThawChatSessionData (1 element)

```rust
struct ThawChatSessionData {
    // 1-element structure for thawing frozen sessions
}
```

### ThawChatSessionResponse (3 elements)

```rust
struct ThawChatSessionResponse {
    // 3-element response for thawing sessions
}
```

### RemoteGetMessagesResponse (3 elements)

```rust
struct RemoteGetMessagesResponse {
    // 3-element response for getting messages
}
```

### SubmitMessageResponse (2 elements)

```rust
struct SubmitMessageResponse {
    // 2-element response for submitting messages
}
```

### SimplifiedChatRequest (11 elements)

```rust
struct SimplifiedChatRequest {
    // 11-element request for simplified chat
    // Contains: model, messages, tools, etc.
}
```

### ChatSessionListItem

```rust
struct ChatSessionListItem {
    // Chat session list item with metadata
    fs_server_url: String,
    vm_host_dir_mapping_list: Vec<String>,
    // ... additional fields
}
```

### Chat Session Handler Source

```
apps/icube_server_rs/modules/ai-agent/src/handler/todo_list.rs:99
apps/icube_server_rs/modules/ai-agent/src/infrastructure/transport/hub_bridge/sender.rs:100
```

### Chat Session Events

```
session_created — New session created
session_updated — Session updated
session_deleted — Session deleted
message_deleted — Message deleted
message_reverted — Message reverted
```

---

## Appendix I: Task Management Structures

### Task Request/Response Types

```rust
struct CancelTaskRequest { ... }
struct CancelTaskResponse { ... }
struct ConfirmTaskRequest { ... }
struct ConfirmTaskResponse { ... }
struct AppendTaskRequest { ... }
struct AppendTaskResponse { ... }
struct DeleteTaskRequest { ... }
struct DeleteTaskResponse { ... }
struct RevertTaskRequest { ... }
struct RevertTaskResponse { ... }
struct RevertTaskCheckRequest { ... }
struct RevertTaskCheckResponse { ... }
```

### Task Events

```
scheduled_task_created — Scheduled task created
scheduled_task_updated — Scheduled task updated
scheduled_task_deleted — Scheduled task deleted
scheduled_task_triggered — Scheduled task triggered
scheduled_task_execution_completed — Task execution completed
scheduled_task_disabled — Task disabled
```

---

## Appendix J: Conversation Management

### Conversation Request/Response Types

```rust
struct ChangeConversationRequest { ... }
struct ChangeConversationResponse { ... }
struct DeleteConversationRequest { ... }
struct DeleteConversationResponse { ... }
struct HubGetConversationRequest { ... }
struct HubGetConversationResponse { ... }
struct RemoteConversationListMessagesRequest { ... }
struct ListMessagesResponse { ... }
struct BatchInsertMessagesRequest { ... }
struct BatchInsertMessagesItem { ... }
```

### Conversation Data

```rust
struct HubChatMessageData { ... }
struct ChatResponseBody { ... }
```

---

## Appendix K: Project Management

### Project Request/Response Types

```rust
struct CreateProjectRequest { ... }
struct ListProjectsRequest { ... }
struct GetProjectRequest { ... }
struct GetProjectByFolderRequest { ... }
struct UpdateProjectRequest { ... }
struct DeleteProjectRequest { ... }
```

### Project Events

```
project_created — Project created
project_updated — Project updated
project_deleted — Project deleted
```

---

## Appendix L: Diff View

### DiffView Structures

```rust
struct GetDiffViewRequest {
    // Diff view request
}

struct DiffViewFileDiffInfo {
    // File diff information
}

struct DiffViewChangedFiles {
    // Changed files in diff
    total_insert_line_count: i32,
    total_delete_line_count: i32,
}

struct GetDiffViewData {
    // Diff view data
}
```

---

## Appendix M: Model List and Configuration Structures

### GetModelListRequest (1 element)

```rust
struct GetModelListRequest {
    jwt_token: String,
    jwt_token_type: String,
}
```

### GetModelListByFunctionRequest (2 elements)

```rust
struct GetModelListByFunctionRequest {
    // 2-element request for model list by function
}
```

### GetModelListByFunctionResponse

```rust
struct GetModelListByFunctionResponse {
    // Response containing model list by function
    function_model_list: Vec<FunctionModelList>,
    model_context_window_size: ModelContextWindowSize,
    saas_usage: SaasUsage,
}
```

### ModelCommonResponse (3 elements)

```rust
struct ModelCommonResponse {
    // 3-element common model response
    editing_plan: Option<String>,
    editing_logic: Option<String>,
}
```

### GetModelSelectionModesResponse (1 element)

```rust
struct GetModelSelectionModesResponse {
    mode_list: Vec<String>,
}
```

### GetModelSelectionModesResponseData (1 element)

```rust
struct GetModelSelectionModesResponseData {
    mode_list: Vec<String>,
}
```

### LLMCustomModelRawMessageResponse (1 element)

```rust
struct LLMCustomModelRawMessageResponse {
    // 1-element response for custom model raw messages
}
```

### GetCustomModelTypeConfigResponse (1 element)

```rust
struct GetCustomModelTypeConfigResponse {
    custom_model_type_list: Vec<CustomModelTypeInfo>,
}
```

### CustomModelTypeInfo

```rust
struct CustomModelTypeInfo {
    type_display_name: String,
    // ... additional fields
}
```

### ModelUpdateRequest (13 elements)

```rust
struct ModelUpdateRequest {
    // 13-element request for model updates
}
```

### ChatFastApplyRequest (8 elements)

```rust
struct ChatFastApplyRequest {
    // 8-element request for fast apply
}
```

### ProvidersListRequest / ProvidersListResponse

```rust
struct ProvidersListRequest {
    // Request to list providers
}

struct ProvidersListResponse {
    // Response with provider list
}
```

### GetSessionUsageResponse

```rust
struct GetSessionUsageResponse {
    usage_time: i64,
    use_max_mode: bool,
    amount_float: f64,
    cost_money_float: f64,
    remain_discount_times: i32,
    session_usage: SessionUsage,
}
```

### SessionUsage

```rust
struct SessionUsage {
    output_token: i32,
    cache_read_token: i32,
    cache_write_token: i32,
    // ... additional fields
}
```

### SessionUsageExtraInfo

```rust
struct SessionUsageExtraInfo {
    // Extra info for session usage
    open: bool,
    // ... additional fields
}
```

### Model Custom Config

```rust
struct ModelCustomConfig {
    // Custom model configuration
}

struct ModelEcryptedPrompt {
    // Encrypted prompt for model
}
```

### Model Provider Response Structures

### DeepseekModel (3 elements)

```rust
struct DeepseekModel {
    id: String,
    owned_by: String,
    // ... 1 more field
}
```

### OpenrouterModel (2 elements)

```rust
struct OpenrouterModel {
    id: String,
    // ... 1 more field
}
```

### OpenrouterModelListResponse (1 element)

```rust
struct OpenrouterModelListResponse {
    data: Vec<OpenrouterModel>,
}
```

### AnthropicModel (4 elements)

```rust
struct AnthropicModel {
    id: String,
    display_name: String,
    // ... 2 more fields
}
```

### AnthropicModelListResponse (4 elements)

```rust
struct AnthropicModelListResponse {
    data: Vec<AnthropicModel>,
    has_more: bool,
    first_id: String,
    last_id: String,
}
```

### GeminiModel (1 element)

```rust
struct GeminiModel {
    id: String,
}
```

### GeminiModelListResponse (1 element)

```rust
struct GeminiModelListResponse {
    data: Vec<GeminiModel>,
}
```

### OpenAIModelListResponse (2 elements)

```rust
struct OpenAIModelListResponse {
    data: Vec<OpenAIModel>,
    // ... 1 more field
}
```

### AWSModelLifecycle (1 element)

```rust
struct AWSModelLifecycle {
    // Model lifecycle status
}
```

### AWSModelSummary (10 elements)

```rust
struct AWSModelSummary {
    customizations_supported: Vec<String>,
    inference_types_supported: Vec<String>,
    input_modalities: Vec<String>,
    model_arn: String,
    model_id: String,
    model_lifecycle: AWSModelLifecycle,
    model_name: String,
    output_modalities: Vec<String>,
    provider_name: String,
    response_streaming_supported: bool,
}
```

### AWSModelListResponse (1 element)

```rust
struct AWSModelListResponse {
    model_summaries: Vec<AWSModelSummary>,
}
```

### VolcengineContextCreateResponse (1 element)

```rust
struct VolcengineContextCreateResponse {
    // Volcengine context creation response
}
```

### VolcengineError (4 elements)

```rust
struct VolcengineError {
    param: String,
    r#type: String,
    // ... 2 more fields
}
```

### Model Provider Source Paths

```
apps/icube_server_rs/crates/llm-client/src/provider/anthropic.rs:185
apps/icube_server_rs/crates/llm-client/src/provider/openai.rs:267
apps/icube_server_rs/crates/llm-client/src/provider/deepseek.rs:186
apps/icube_server_rs/crates/llm-client/src/provider/gemini.rs:126
apps/icube_server_rs/crates/llm-client/src/provider/aws.rs
apps/icube_server_rs/crates/llm-client/src/provider/volcengine.rs:63
apps/icube_server_rs/crates/llm-client/src/provider/openrouter.rs:135
```

---

## Appendix N: Token Usage and Timing Events

### TokenUsageEvent (9 elements)

```rust
struct TokenUsageEvent {
    // 9-element structure for token usage tracking
    // Tracks: input tokens, output tokens, cache tokens, etc.
}
```

### TimingCostEvent (20 elements)

```rust
struct TimingCostEvent {
    // 20-element structure for timing metrics
    // Tracks: preprocessing, first token, provider latency, etc.
}
```

### TimingCostEvent Fields

```
check_risk — Risk check timing
build_llm_prompt — LLM prompt building timing
preprocess_timing — Preprocessing timing
first_token_timing — First token timing
provider_first_token — Provider first token timing
network_latency — Network latency
provider_network_latency — Provider network latency
middleware_processing_time — Middleware processing time
queue_timing — Queue timing
postprocess_timing — Postprocessing timing
preprocessing_detail — Preprocessing detail
agent_preprocess_timing — Agent preprocessing timing
agent_postprocess_timing — Agent postprocessing timing
agent_middleware_timing — Agent middleware timing
gateway_preprocess_timing — Gateway preprocessing timing
gateway_server_processing_time — Gateway server processing time
platform_detail — Platform detail
post_processing_detail — Post-processing detail
platform_first_token_timing — Platform first token timing
server_processing_time — Server processing time
first_sse_event_time — First SSE event time
is_retry — Is retry flag
account_type — Account type
account_name — Account name
provider_model_name — Provider model name
```

### MetadataEvent (5 elements)

```rust
struct MetadataEvent {
    // 5-element structure for metadata events
}
```

### OutputEvent (3 elements)

```rust
struct OutputEvent {
    // 3-element structure for output events
}
```

### OutputEventToolCall (4 elements)

```rust
struct OutputEventToolCall {
    // 4-element structure for tool call output events
}
```

### OutputEventFunctionCall (2 elements)

```rust
struct OutputEventFunctionCall {
    // 2-element structure for function call output events
}
```

### ExtraInfoEvent

```rust
struct ExtraInfoEvent {
    // Extra information event
}
```

### SuggestedQuestion / SuggestedQuestionsEvent

```rust
struct SuggestedQuestion {
    // Suggested question structure
}

struct SuggestedQuestionsEvent {
    // Suggested questions event
}
```

### Token Usage Tracking Flow

```
1. Chat request received
2. TokenUsageEvent created with initial counts
3. As LLM streams response:
   - Input tokens counted
   - Output tokens counted
   - Cache tokens tracked (creation + read)
4. TimingCostEvent populated with all timing metrics
5. Events sent to telemetry (Slardar)
```

---

## Appendix O: Wiki/DeepWiki Structures

### Wiki Content Structures

```rust
struct WikiContentItem with 5 elements
struct GetWikiContentResponse with 3 elements
struct WikiMeta with 4 elements
struct WikiRepoInfo with 12 elements
struct GetWikiRepoInfoResponse with 3 elements
struct WikiCatalog with 9 elements
struct WikiStatus with 7 elements
struct GetWikiStatusResponse with 9 elements
```

### Wiki API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/wiki/clear_wiki` | POST | Clear wiki content |
| `api/ide/v1/wiki/update_wiki_progress_status` | POST | Update wiki progress |
| `api/ide/v1/wiki/get_wiki_content` | GET | Get wiki content |
| `api/ide/v1/wiki/get_wiki_status` | GET | Get wiki status |
| `api/ide/v1/wiki/get_wiki_repo_info` | GET | Get wiki repo info |

---

## 47. Remote Session Management

### 47.1 Remote Session Data Structures

```rust
struct RemoteChatSessionData with 23 elements {
    // 23-element structure for remote chat session
    // Contains: session metadata, user info, model config, etc.
}

struct RemoteChatMessageData with 38 elements {
    // 38-element structure for remote chat message
    unrevertible_reason: Option<String>,
    // ... 37 more fields
}
```

### 47.2 Create Chat Session Request

```rust
struct CreateChatSessionRequest with 10 elements {
    project_extra_info: Option<serde_json::Value>,
    auto_create_project: bool,
    create_reason: String,
    timestamp_ms: i64,
    // ... 6 more fields
}
```

### 47.3 History Sync Structures

```rust
struct GetHistoryDownloadURLData with 1 element
struct GetHistoryDownloadURLResponse with 3 elements
struct GetHistoryUploadURLData with 1 element
struct GetHistoryUploadURLResponse with 3 elements
struct CheckHistoryExistsData with 2 elements
struct CheckHistoryExistsResponse with 3 elements
struct BatchSyncHistoryResponse with 2 elements
```

### 47.4 History Sync Flow

```
1. Check if history exists:
   CheckHistoryExistsRequest → CheckHistoryExistsResponse

2. Download history:
   GetHistoryDownloadURLRequest → GetHistoryDownloadURLResponse

3. Upload history:
   GetHistoryUploadURLRequest → GetHistoryUploadURLResponse

4. Batch sync:
   BatchSyncHistoryRequest → BatchSyncHistoryResponse
```

### 47.5 Commit Session

```rust
struct CommitSessionRequest {
    history_file_uri: String,
    version_snapshot: Option<VersionSnapshotInfo>,
    pre_termination: bool,
    handoff: Option<HandoffInfo>,
    // ... additional fields
}

struct CommitSessionResponse {
    // Commit session response
}
```

### 47.6 Version Snapshot Info

```rust
struct VersionSnapshotInfo {
    version_type: String,
    version_ref: String,
    repo_uri: String,
    parent_ref: String,
    has_new_commit: bool,
}

struct RemoteSource with 6 elements {
    repo_name: String,
    // ... 5 more fields
}

struct RemoteTarget {
    allocation_status: String,
    // ... additional fields
}
```

### 47.7 Remote Sandbox Info

```rust
struct RemoteSandboxInfo {
    explorer_url: String,
    vnc_url: String,
    vnc_template_url: String,
    environment_name: String,
    browser_use_sandbox: bool,
    uploads_path: String,
}
```

### 47.8 Handoff Session Request/Response

```rust
struct HandoffDownSessionRequest with 4 elements {
    // Handoff down (cloud → local) request
}

struct HandoffDownSessionData {
    messages_restored: i32,
    messages_archived: i32,
    warnings: Vec<String>,
}

struct HandoffUpSessionRequest with 4 elements {
    revert_changes: bool,
    // ... 3 more fields
}

struct HandoffUpSessionData {
    // Handoff up (local → cloud) response data
}
```

### 47.9 Handoff Target and Info

```rust
struct HandoffTarget {
    // Handoff target structure
}

struct HandoffInfo {
    // Handoff information
}
```

### 47.10 Remote Session Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/handoff/down/service.rs
```

### 47.11 Handoff Error Messages

```
handoff_down_session failed
handoff_up_session failed
handoff_down_pre_check completed
handoff_up: hide local session failed
handoff_up: remote not found, creating via HANDOFF_UP
handoff_up: remote exists with has_local_counterpart, idempotent path
```

---

## 48. Auto-Run Configuration

### 48.1 Auto-Run Config Structures

```rust
struct AutoRunConfig with 6 elements {
    confirm_mode: String,
    run_mode: String,
    version: String,
    file_op: String,
    mcp_auto_run: bool,
    command_mode: String,
}

struct AutoRunConfigFlagV2 with 2 elements {
    allow_list: Vec<String>,
    deny_list: Vec<String>,
}

struct AutoRunCommandsConfigV2 with 2 elements {
    always_ask: Vec<String>,
    always_run: Vec<String>,
}

struct DynamicAutoRunConfig with 6 elements {
    command_red_list: Vec<String>,
    v2_always_run_disable_red_list: Vec<String>,
    sandbox_rw_list: Vec<String>,
    sandbox_ro_list: Vec<String>,
    disable_sandbox_win_net: bool,
    sandbox_win_net_default_use_config: bool,
}

struct ScheduledTaskAutoRunConfig with 4 elements {
    // Scheduled task auto-run configuration
}
```

### 48.2 Auto-Run Features

- Command red list (dangerous commands)
- Sandbox file access lists (read-write and read-only)
- Windows network sandbox control
- MCP auto-run configuration
- Scheduled task auto-run with limits

---

## 49. Agent Status and Events

### 49.1 Agent Status Structures

```rust
struct AgentStatus with 2 elements {
    hooks_tool_call_name: String,
    hooks_event_name: String,
    deny_message: String,
}

struct AgentStatusItem with 3 elements {
    // Agent status item
}

struct AgentStatusEvent with 1 element {
    // Agent status event
}
```

### 49.2 Agent Resume Event

```rust
struct AgentResumeEvent with 6 elements {
    resume_agent_run_id: String,
    // ... 5 more fields
}
```

### 49.3 Agent Wakeup Event

```rust
struct AgentWakeupEvent {
    // Agent wakeup event
}
```

### 49.4 Agent Idle Event

```rust
struct AgentIdleEvent with 6 elements {
    check_interval_ms: i32,
    // ... 5 more fields
}
```

### 49.5 Agent Run Info

```rust
struct AgentRunInfo {
    // Agent run information
}

struct GetResumeAgentTaskStatusResponse with 2 elements {
    last_history_id: String,
    // ... 1 more field
}
```

### 49.6 Agent Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/llm/event.rs:809
apps/icube_server_rs/modules/ai-agent/src/domain/plan/simple_service_v2/tool_cache.rs:66
```

---

## 50. Tool Cache System

### 50.1 Tool Cache Structures

```rust
struct ToolCacheDataEvent with 2 elements {
    group_name: String,
    // ... 1 more field
}

struct ToolCacheGroup with 3 elements {
    // Tool cache group
}

struct ToolCacheItem with 3 elements {
    // Tool cache item
}
```

### 50.2 Tool Call with 4 elements

```rust
struct ToolCall with 4 elements {
    // Tool call structure
}
```

### 50.3 Force Tool Call Input

```rust
struct ForceToolCallInput with 6 elements {
    node_type: String,
    start_index: i32,
    end_index: i32,
    // ... 3 more fields
}
```

### 50.4 Tool Result Line

```rust
struct ToolResultLine with 3 elements {
    // Tool result line structure
}
```

### 50.5 Run Terminal Parameters

```rust
struct RunTerminalParams {
    tool_call_id: String,
    is_shell: bool,
    target_terminal: String,
    exec_env: String,
    sandbox_storage_path: String,
    sandbox_config_name: String,
    sandbox_log_dir: String,
    agent_blocking: bool,
    enable_tool_call_result_file: bool,
    tool_call_result_file_threshold: i32,
}
```

### 50.6 Tool Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/llm/event.rs:809
apps/icube_server_rs/modules/ai-agent/src/domain/history_v2/service.rs:2294
```

---

## 51. Compact and Summary System

### 51.1 Compact Event Structures

```rust
struct GenerateSummaryEvent with 2 elements {
    // Generate summary event
}

struct CompactEvent with 8 elements {
    compact_id: String,
    // ... 7 more fields
}

struct CompactFinishEvent with 6 elements {
    // Compact finish event
}
```

### 51.2 Summary Configuration

```rust
struct DymanicAgenticSummaryConfig with 5 elements {
    summary_message_token_limit: i32,
    kept_history_token_limit: i32,
    kept_history_message_limit: i32,
    minimum_current_turn_token_usage: i32,
    multimodal_summary_look_back_count: i32,
}
```

### 51.3 Summary Message Render Variables

```rust
struct SummaryMessageRenderVariables {
    lastest_message_summaries: Vec<String>,
    // ... additional fields
}

struct SummaryMessageExtraContext {
    user_profile_changed: bool,
    project_memory_changed: bool,
    conversation_topics: Vec<String>,
}
```

### 51.4 Topics Memory Payload

```rust
struct TopicsMemoryPayload with 5 elements {
    // Topics memory payload
}

struct TopicRenderVariables {
    current_user_memory: String,
    current_project_memory: String,
    // ... additional fields
}

struct TopicMessageExtraContext {
    // Topic message extra context
}
```

### 51.5 Chat Memory

```rust
struct ChatMemoryConfig with 1 element {
    // Chat memory configuration
}

struct ChatMemoryWithHistoryConfig with 1 element {
    // Chat memory with history configuration
}

struct ChatMemoryTriggerEvent with 2 elements {
    chat_memory_scene: String,
    force_update: bool,
}
```

### 51.6 Chat Memory Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/hub/hook/trigger.rs:26
```

---

## 52. Context Usage System

### 52.1 Context Usage Structures

```rust
struct DynamicConfigContextUsageChunk with 2 elements {
    max_items: i32,
    max_bytes: i32,
}

struct CloudContextUsageItem with 4 elements {
    // Cloud context usage item
}

struct CloudContextUsageEvent {
    // Cloud context usage event
}
```

### 52.2 Context Resolver Structures

```rust
struct ContextInfo with 6 elements {
    char_limit: i32,
    unique_str: String,
    lines: i32,
    first_line_index: i32,
    last_line_index: i32,
    is_complete: bool,
}

struct ContextResolverResultMetadata with 2 elements {
    above: i32,
    below: i32,
}

struct ContextResolverReference with 7 elements {
    context_info: ContextInfo,
    // ... 6 more fields
}
```

### 52.3 Context Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/contextfs/resolver.rs:49
```

---

## 53. Diagnosis System

### 53.1 Diagnosis Structures

```rust
struct SystemDiagnosisReq {
    // System diagnosis request
}

struct SystemResourceUsage {
    // System resource usage
}

struct RecentDiagnosisSnapshot {
    // Recent diagnosis snapshot
}

struct RecentDiagnosisRecord {
    // Recent diagnosis record
}

struct ExtensionOwner {
    // Extension owner
}

struct ProcessInfo {
    // Process information
}

struct CommandSchema {
    // Command schema
}

struct DiskInfo {
    // Disk information
}

struct UnresponsiveExtensionInfo {
    // Unresponsive extension info
}
```

### 53.2 Diagnosis Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/contextfs/resolver.rs:49
```

---

## 54. Document Set Management

### 54.1 Document Set Structures

```rust
struct DocumentSetListItem with 7 elements
struct DocumentSetListResponse with 3 elements
struct DocumentsList with 2 elements
struct DocumentListItem with 6 elements
struct DocumentSetInfoData with 7 elements
struct DocumentSetInfoResponse with 4 elements
struct DocumentInfoResponse with 1 element
struct DocumentSetDiffItem with 3 elements
struct DocumentSetDiffResponse with 3 elements
struct ExternalDocument with 4 elements
```

### 54.2 Docset Structures

```rust
struct DocsetItemDTO { ... }
struct PageListItem { ... }
struct DocsetVersionInfo {
    should_update: bool,
}

struct FetchOnlineDocsetDetailParams { ... }
struct RetrieveDocsetRagParam { ... }
struct CheckShouldUpdateOfficialDocSetResponse { ... }
struct PullLatestOfficialDocSetResponse { ... }
struct GetDocSetStatusResponse {
    detailed_status_list: Vec<DocSetStatusListItem>,
}

struct DocSetStatusListItem {
    document_set: String,
    document_page_list: Vec<String>,
}

struct RetrieveDocsetRagResponse {
    query_context: String,
}
```

### 54.3 Docset External Document

```rust
struct DocsetExternalDocumentVariablesDTO with 4 elements
struct DocsetExternalDocumentRelatedDocDTO with 8 elements
```

### 54.4 Docset Project Management

```rust
struct DocsetVirtualProjectInitRequestParams { ... }
struct DocsetLocalFilesCreateRequestParams { ... }
struct DocsetLocalFilesCreateResponse {
    blocked_files: Vec<BlockedFileInfo>,
}

struct BlockedFileInfo {
    // Blocked file info
}

struct DocsetProjectIdentifier { ... }
struct DocsetGetIndexStatusRequestParams { ... }
struct DocsetCancelIndexRequestParams { ... }
struct DocsetDeleteRequestParams { ... }
struct DocsetDocument { ... }
struct DocsetUrlCreateRequestParams { ... }
struct DocsetReferenceData { ... }
struct NormalizedDocumentIndexStatus { ... }
struct NormalizedProjectDocumentsIndexStatus { ... }
struct ExternalDocumentReferenceItem { ... }
struct EnterpriseDocReference { ... }
```

### 54.5 Document Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/docset/model.rs:583
```

---

## 55. Scheduled Task System

### 55.1 Scheduled Task Events

```
ScheduledTaskCreated — Scheduled task created
ScheduledTaskUpdated — Scheduled task updated
ScheduledTaskDeleted — Scheduled task deleted
ScheduledTaskTriggered — Scheduled task triggered
ScheduledTaskExecutionCompleted — Task execution completed
ScheduledTaskDisabled — Task disabled
```

### 55.2 Scheduled Task Payload

```rust
struct ScheduledTaskDisabledPayload {
    // Scheduled task disabled payload
}
```

### 55.3 Trigger Configuration

```rust
struct TriggerConfig {
    // Trigger configuration
}
```

### 55.4 Schedule Tool

```rust
struct ScheduleParams {
    // Schedule tool parameters
}

struct ScheduleToolResult {
    // Schedule tool result
}
```

### 55.5 Scheduled Task Features

- Cron-based scheduling
- Autonomous task execution
- Task persistence
- Maximum task limits
- Minimum interval between tasks
- Integration with agent system

---

## 56. Supabase Integration

### 56.1 Supabase Structures

```rust
struct SupabaseProject with 3 elements {
    api_key: String,
    // ... 2 more fields
}

struct SupabaseGetTablesParams with 2 elements {
    schemas: Vec<String>,
    // ... 1 more field
}

struct SupabaseApplyMigrationParams with 1 element {
    // Supabase apply migration parameters
}

struct SupabaseResponse with 3 elements {
    // Supabase response
}
```

### 56.2 Supabase Tools

```
toolcall_supabase_get_tables — List Supabase tables
toolcall_supabase_apply_migration — Apply Supabase migration
toolcall_supabase_get_project — Get Supabase project
```

### 56.3 Supabase Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/toolcall/tools/supabase_get_tables.rs
apps/icube_server_rs/modules/ai-agent/src/domain/toolcall/tools/supabase_apply_migration.rs
```

---

## 57. Voice System

### 57.1 Voice Tools

```
voice_transcription — Speech to text
voice_summary — Voice summary generation
```

### 57.2 Voice Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/agent_process_v3/solo/voice_transcription/roles/voice_transcription_agent.rs
apps/icube_server_rs/modules/ai-agent/src/domain/agent_process_v3/solo/voice_summary/roles/voice_summary_agent.rs
```

---

## 58. Image Generation

### 58.1 Image Generation Structures

```rust
struct TextToImageResponse with 3 elements {
    // Text to image response
}

struct UploadMultimodalImageResponse with 1 element {
    // Upload multimodal image response
}

struct DownloadMultimodalImageResponse with 2 elements {
    // Download multimodal image response
}

struct DynamicConfigGenerateImage {
    enable_stream: bool,
}
```

### 58.2 Image Generation API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/text_to_image` | POST | Text to image |
| `api/ide/v1/tool_text_to_image` | POST | Tool text to image |
| `api/ide/v1/tool_text_to_image_stream` | POST | Streaming text to image |
| `api/ide/v1/report/multimodal` | POST | Report multimodal usage |
| `api/ide/v1/get/multimodal` | GET | Get multimodal data |

---

## 59. Complete Tool List

### 59.1 All Available Tools

```
ViewFile, ViewFiles, WriteToFile, EditFileRename, EditFileUpdate, EditFileUpdateFc,
EditFileFastApply, EditFileSearchReplace, ShowDiff, ShowDiffFc, ViewFolder,
SearchByKeyword, SearchByRegex, FileSearch, OpenPreview, CheckCommandStatus,
InitEnv, SendToCommand, AgentFinish, ResponseToUser, RunMcp, RunCustomTool,
RunAgent, Condense, ShallowMemento, ManageCoreMemory, OpenProject,
WriteToProductDocument, EditProductDocumentUpdate, EditProductDocumentUpdateFc,
EditProductDocumentFastApply, DeployToRemote, SupabaseGetProject,
SupabaseApplyMigration, SupabaseGetTables, GetLLMConfig, GetPreviewConsoleLogs,
StripeGetConfig, CheckCommandStatusV3, WebSearchV3, RunCommandV3, OpenPreviewV3,
SearchCodebaseV3, StopCommandV3, TodoWriteV3, Schedule, DeleteFileV3,
ApplyPatchV3, SearchReplace, SkillRecommend, Knowledge,
BrowserNavigate, BrowserNavigateBack, BrowserTabs, BrowserSnapshot,
BrowserTakeScreenshot, BrowserClick, BrowserHover, BrowserType,
BrowserSelectOption, BrowserPressKey, BrowserGetAttribute, BrowserScroll,
BrowserConsoleMessages, BrowserNetworkRequests, BrowserLock, BrowserUnlock,
BrowserWaitFor, BrowserEvaluate, BrowserDrag, BrowserUploadFile,
BrowserHandleDialog, NotifyUser, PureShowWidget
```

### 59.2 Tool Name Mapping

```
view_file → ViewFile
view_files → ViewFiles
delete_file → DeleteFile
write_to_file → WriteToFile
edit_file_rename → EditFileRename
edit_file_update → EditFileUpdate
edit_file_update_fc → EditFileUpdateFc
edit_file_fast_apply → EditFileFastApply
edit_file_search_replace → EditFileSearchReplace
show_diff_fc → ShowDiffFc
view_folder → ViewFolder
search_by_keyword → SearchByKeyword
search_by_regex → SearchByRegex
search_codebase → SearchCodebase
run_command → RunCommand
check_command_status → CheckCommandStatus
stop_command → StopCommand
init_env → InitEnv
send_to_command → SendToCommand
no_need_execute → NoNeedExecute
run_agent → RunAgent
write_refactor_output → WriteRefactorOutput
open_project → OpenProject
write_to_product_document → WriteToProductDocument
edit_product_document_update → EditProductDocumentUpdate
edit_product_document_update_fc → EditProductDocumentUpdateFc
edit_product_document_fast_apply → EditProductDocumentFastApply
deploy_to_remote → DeployToRemote
supabase_get_project → SupabaseGetProject
supabase_apply_migration → SupabaseApplyMigration
supabase_get_tables → SupabaseGetTables
get_llm_config → GetLLMConfig
get_preview_console_logs → GetPreviewConsoleLogs
stripe_get_config → StripeGetConfig
browser_lock → BrowserLock
browser_unlock → BrowserUnlock
```

---

## 60. Sandbox Safety System

### 60.1 Sandbox Safety Checks

```
SandboxSupportCheckParams — Check sandbox support
UserNotEnableAutoRun — User not enabled auto-run
ModelJudgeUnsafe — Model judged unsafe
InDenyList — In deny list
InRedList — In red list
NotInAllowList — Not in allow list
SandboxNotBlockCommand — Sandbox not blocking command
SandboxUnavailable — Sandbox unavailable
SandboxExecuteFailure — Sandbox execution failure
SandboxToRecovery — Sandbox recovery needed
```

### 60.2 Sandbox Recovery Types

```
sandbox_to_recovery_user_manual_recovery — User manual recovery
sandbox_to_recovery_auto_recovery_needs_privilege — Auto recovery needs privilege
sandbox_to_recovery_auto_recovery_none_privilege — Auto recovery no privilege
```

### 60.3 Sandbox Safety Features

```
in_deny_list_and_not_in_allow_list — In deny list and not in allow list
user_enable_protect_delete_file — User enabled file deletion protection
user_enable_protect_mcp_tool — User enabled MCP tool protection
unsafe_only_support_internal_user — Unsafe, only support internal user
call_exit_plan_mode — Call exit plan mode
call_notify_user — Call notify user
call_supabase_apply_migration — Call Supabase apply migration
browser_waiting_for_user_interaction — Browser waiting for user interaction
file_outside_workspace — File outside workspace
schedule_write_operation — Schedule write operation
un_handle_toolcall — Unhandled tool call
in_enterprise_command_blacklist — In enterprise command blacklist
sandbox_model_escape — Sandbox model escape
```

### 60.4 Sandbox Status

```
need_manual_confirm — Need manual confirm
manual_confirm_reason — Manual confirm reason
run_mode — Run mode
running_command_list — Running command list
block_level — Block level
block_command_list — Block command list
run_mode_version — Run mode version
sandbox_status — Sandbox status
sandbox_recovery_type — Sandbox recovery type
sandbox_config_command — Sandbox config command
hit_red_list — Hit red list
hit_black_list — Hit black list
now_run_mode — Now run mode
auto_cancel — Auto cancel
```

---

## 61. Stripe Payment Integration

### 61.1 Stripe Structures

```rust
struct StripePriceInfo with 7 elements {
    anon_key: String,
    project_url: String,
    service_role_key: String,
    interval_count: i32,
    currency: String,
    unit_amount_decimal: String,
    nickname: String,
}

struct StripeProduct with 5 elements {
    // Stripe product structure
}

struct StripePaymentStore with 3 elements {
    prices: Vec<StripePriceInfo>,
    // ... 2 more fields
}

struct StripeResponse with 3 elements {
    // Stripe response
}
```

### 61.2 Stripe API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/stripe/get_config` | GET | Get Stripe config |

---

## 62. Deploy System

### 62.1 Deploy Structures

```rust
struct VercelDeployCreator {
    // Vercel deploy creator
}

struct DeployInfo {
    // Deploy information
}

struct DeployResponse {
    // Deploy response
}

struct OpenPreviewParams {
    wait_for_load: bool,
    error_limit: i32,
}
```

### 62.2 Deploy API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/deploy_to_remote` | POST | Deploy to remote |

---

## 63. LLM Config System

### 63.1 LLM Config Structures

```rust
struct LLMConfig with 2 elements {
    // LLM configuration
}

struct GetLLMConfigParams with 1 element {
    required_providers: Vec<String>,
}

struct GetLLMConfigResponse with 1 element {
    unconfigured_providers: Vec<String>,
}
```

### 63.2 LLM Config Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/toolcall/tools/get_llm_config.rs
```

### 63.3 Custom Model Config

```rust
struct CustomModelConfigDetail with 3 elements {
    // Custom model configuration detail
}
```

---

## 64. Resource Upload System

### 64.1 Resource Upload Structures

```rust
struct StoreInfoItem {
    biz_type: String,
    store_uri: String,
    upload_hosts: Vec<String>,
    store_infos: Vec<String>,
    session_key: String,
}

struct GetResourceUploadUrlResponse {
    // Resource upload URL response
}

struct CommitResourceUploadResultResponse {
    success_oids: Vec<String>,
}

struct GetResourceUrlRequest {
    // Get resource URL request
}

struct GetResourceUrlResponse {
    // Resource URL response
}
```

### 64.2 Resource Upload API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `api/ide/v1/get_resource_upload_token` | GET | Get upload token |
| `api/ide/v1/get_resource_upload_url` | GET | Get upload URL |
| `api/ide/v1/get_resource_url` | GET | Get resource URL |
| `api/ide/v1/commit_resource_upload_result` | POST | Commit upload result |

### 64.3 Resource Upload Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/common/imagex.rs:262
```

---

## 65. Git Integration

### 65.1 Git Structures

```rust
struct GitGenerateCommitMessageReq {
    // Git generate commit message request
}

struct GetReturnToLocalSessionGitContextReq {
    // Get return to local session git context request
}

struct ReportGitAiCodeContributionResponse with 3 elements {
    // Report git AI code contribution response
}
```

### 65.2 Git AI Configuration

```rust
struct GitAiConfiguration {
    // Git AI configuration
}
```

### 65.3 Git Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/handler/git/mod.rs:357
```

---

## 66. Code Review System

### 66.1 Code Review Skills

```rust
struct ABTestTraeCodeReviewSkill {
    // A/B test Trae code review skill
}

struct ABTestTraeSecurityReviewSkill {
    // A/B test Trae security review skill
}

struct ABTestTraeUiCodeDesignSkill {
    // A/B test Trae UI code design skill
}

struct ABTestTraeKnowledgesSkill {
    // A/B test Trae knowledges skill
}
```

### 66.2 Agent Review Configuration

```rust
struct AgentReviewConfiguration {
    // Agent review configuration
}
```

---

## 67. Chat Session Management

### 67.1 Chat Session Request/Response Types

```rust
struct ListChatSessionsRequest { ... }
struct ListChatSessionsData { ... }
struct GetChatSessionRequest { ... }
struct CommitChatSessionRequest { ... }
struct FreezeChatSessionRequest { ... }
struct StopChatSessionRequest { ... }
struct DeleteChatSessionRequest { ... }
struct GetMessagesRequest { ... }
struct GetMessagesData { ... }
struct GetMessageByIdRequest { ... }
struct GetMessageByIdData { ... }
struct SendMessageRequest { ... }
struct SendMessageData { ... }
struct SubscribeEventsRequest { ... }
struct SubscribeEventsResponse { ... }
```

### 67.2 VM Init Progress

```rust
struct VmInitProgressPayload {
    stage: String,
    stage_message: String,
    stage_percentage: f64,
}
```

### 67.3 Status Changed Payload

```rust
struct StatusChangedPayload {
    old_status: String,
    new_status: String,
}
```

### 67.4 VM Operate

```rust
struct VmOperateRequest { ... }
struct VmOperateResponseData { ... }
struct VmOperateResponse { ... }
```

### 67.5 Chat Session Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/lite/typing.rs:954
```

---

## 68. Prompt Template System

### 68.1 Prompt Template Structures

```rust
struct PromptTemplateMetadata with 1 element {
    // Prompt template metadata
}

struct PromptTemplateInfo with 5 elements {
    prompt_key: String,
    prompt_version: String,
    prompt_label: String,
    prompt_list: Vec<PromptTemplateItem>,
    // ... 1 more field
}

struct PromptTemplateItem with 2 elements {
    // Prompt template item
}

struct PromptTemplateQueryItem with 2 elements {
    // Prompt template query item
}
```

### 68.2 Prompt Key Types

```
plan_v2 — Plan v2 prompt
agents — Agents prompt
master_agent — Master agent prompt
search_agent — Search agent prompt
compact_prompt — Compact prompt
custom_sub_agent — Custom sub-agent prompt
multimodal_video — Multimodal video prompt
document_agent — Document agent prompt
project_preparation_agent — Project preparation agent prompt
web_development_agent — Web development agent prompt
resource_diagnosis — Resource diagnosis prompt
```

### 68.3 Model Prompt Config

```rust
struct ModelPromptConfig with 3 elements {
    client_connect: bool,
    custom_model_id: String,
    is_custom_base_url: bool,
}

struct ModelEcryptedPrompt with 4 elements {
    // Encrypted prompt for model
}
```

### 68.4 Prompt Renderer

```rust
struct PromptRenderer {
    history_user_input: Vec<String>,
    history: Vec<String>,
    relevant_contexts_current_file: Vec<String>,
    relevant_contexts_workspace: Vec<String>,
    relevant_contexts: Vec<String>,
    side_chat_rules: Vec<String>,
    user_input_str: String,
    assistant_response: String,
    assistant_response_extra_code_change: String,
    web_reference: String,
    relevant_web_search_contents: Vec<String>,
    available_instructions: Vec<String>,
    relevant_context_documents: Vec<String>,
    document_snippet: String,
    toolcall_result: String,
    final_input: String,
    user_files_changes: Vec<String>,
    modified_file_changes: Vec<String>,
    browser_selection_snippet: String,
    log_message_snippet: String,
    environment_contexts: Vec<String>,
    custom_user_rules: Vec<String>,
    lint_error_mention_snippet: String,
}
```

### 68.5 Prompt Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/model/model_mgr.rs:1222
apps/icube_server_rs/modules/ai-agent/src/domain/toolcall/tools/base.rs:168
```

---

## 69. Rule System

### 69.1 Rule Structures

```rust
struct RuleDetail with 9 elements {
    target_file_path: String,
    target_file_paths: Vec<String>,
    created_time: i64,
    modified_time: i64,
    workspace_folder: String,
    rule_scope_root: String,
    rule_source: String,
    is_complete: bool,
    // ... 1 more field
}

struct GetRulesDetailsResponse with 2 elements {
    // Rules details response
}

struct FileRule with 5 elements {
    processed_content: String,
    file_rules: Vec<String>,
    // ... 3 more fields
}
```

### 69.2 Rule Query Structures

```rust
struct QueryRuleData with 7 elements {
    hash_type: String,
    // ... 6 more fields
}

struct QueryRuleAutoAttachItem with 8 elements {
    parameter_values: Vec<String>,
    invalid: bool,
    rule_brand: String,
    // ... 5 more fields
}

struct QueryRuleAutoAttachData with 1 element {
    // Rule auto attach data
}
```

### 69.3 Rule Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/rule/repository.rs:40
apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/ide_command/tool.rs:668
```

---

## 70. Knowledge Base System

### 70.1 Knowledge Structures

```rust
struct KnowledgesConfiguration {
    // Knowledges configuration
}

struct ShadowKnowledgeFrontmatter {
    // Shadow knowledge frontmatter
}
```

### 70.2 Knowledge API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `api/v1/knowledgebase/teamDoc/getDocumentSetLists` | GET | Get doc set lists |
| `api/v1/knowledgebase/teamDoc/getDocumentSetInfo` | GET | Get doc set info |
| `api/v1/knowledgebase/teamDoc/getDocumentUrl` | GET | Get doc URL |
| `api/v1/knowledgebase/teamDoc/getDocumentSetDiff` | GET | Get doc set diff |

---

## 71. Diagnostic System

### 71.1 Diagnostic Structures

```rust
struct Diagnostic with 6 elements {
    related_information: Vec<DiagnosticRelatedInformation>,
    // ... 5 more fields
}

struct DiagnosticRelatedInformation with 3 elements {
    // Diagnostic related information
}

struct DiagnosticInfo {
    // Diagnostic info
}

struct DiagnosticRange {
    // Diagnostic range
}

struct DiagnosticPosition {
    // Diagnostic position
}
```

### 71.2 Get Diagnostics

```rust
struct GetDiagnosticsParams with 1 element {
    tos_uri: String,
    local_path: String,
}

struct GetDiagnosticsResult with 1 element {
    // Diagnostics result
}

struct GetDiagnosticsRightResult with 5 elements {
    // Diagnostics right result
}

struct FileDiagnostics {
    // File diagnostics
}
```

### 71.3 Diagnostic Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/ide_command/tool.rs:2397
```

---

## 72. Refactor System

### 72.1 Refactor Structures

```rust
struct WriteRefactorOutputParams with 2 elements {
    // Write refactor output parameters
}

struct WriteRefactorOutputData with 2 elements {
    filename: String,
    // ... 1 more field
}

struct RefactorAgentConfiguration with 3 elements {
    // Refactor agent configuration
}
```

### 72.2 Refactor Source Paths

```
apps/icube_server_rs/modules/ai-agent/src/domain/agent_v3/tools/write_refactor_output.rs:82
```

---

## 73. Ask User Question System

### 73.1 Ask User Question Structures

```rust
struct AskUserQuestionParams {
    // Ask user question parameters
}

struct QuestionItem {
    // Question item
}

struct OptionItem {
    // Option item
}

struct QuestionAnswer {
    // Question answer
}

struct AskUserQuestionResult {
    // Ask user question result
}

struct AskUserQuestionConfiguration {
    // Ask user question configuration
}
```

---

## 74. Assistant Message System

### 74.1 Assistant Message Structures

```rust
struct AssistantMessage with 3 elements {
    calls: Vec<String>,
    // ... 2 more fields
}

struct AssistantBizExtra {
    is_dummy_exception: bool,
}

struct AssistantLine with 6 elements {
    // Assistant line structure
}

struct AssistantResponseExtra with 1 element {
    // Assistant response extra
}

struct ChatAssistantTaskContent with 3 elements {
    // Chat assistant task content
}
```

---

## 75. Slash Command System

### 75.1 Slash Command Structures

```rust
struct ResolvedSlashCommandDTO with 5 elements {
    // Resolved slash command DTO
}

struct SlashCommandInfo with 5 elements {
    parameter_values: Vec<String>,
    // ... 4 more fields
}

struct QuerySlashCommandData with 4 elements {
    // Query slash command data
}

struct QuerySlashCommandParameters {
    // Query slash command parameters
    invalid: bool,
    rule_brand: String,
}
```

### 75.2 Slash Command Configuration

```rust
struct SlashCommandsConfiguration {
    // Slash commands configuration
}
```

---

## 76. Configuration Summary

### 76.1 All Configuration Types

```rust
struct ShallowMementoConfiguration { ... }
struct TodoListConfiguration { ... }
struct LintErrorAutoFixConfiguration { ... }
struct CoreMemoryConfiguration { ... }
struct ResourceDiagnosisConfiguration { ... }
struct GitAiConfiguration { ... }
struct StuckChatDiagnosisConfiguration { ... }
struct RefactorAgentConfiguration { ... }
struct AgentReviewConfiguration { ... }
struct AskUserQuestionConfiguration { ... }
struct InitCommandConfiguration { ... }
struct SlashCommandsConfiguration { ... }
struct ChatMemoryConfiguration { ... }
struct ChatInputCompletionConfiguration { ... }
struct ChatSuggestConfiguration { ... }
struct ChatSkillRecommendConfiguration { ... }
struct ChatSkillRecommendOpenConfiguration { ... }
struct PastChatsConfiguration { ... }
struct KnowledgesConfiguration { ... }
struct VisualEditorConfiguration { ... }
struct JetBrainsGoEnhanceConfiguration { ... }
struct ForkChatConfiguration { ... }
struct AssistantConfiguration { ... }
struct SoloTeamConfiguration { ... }
struct FileSubAgentsConfiguration { ... }
struct DeepWikiConfiguration { ... }
struct DynamicUIConfiguration { ... }
struct BytedanceInternalCodingSkillConfiguration { ... }
struct FileOpOutsideWorkspaceConfiguration { ... }
```

### 76.2 Configuration Categories

| Category | Configurations |
|----------|---------------|
| **Memory** | CoreMemoryConfiguration, ChatMemoryConfiguration, PastChatsConfiguration |
| **Agent** | RefactorAgentConfiguration, AgentReviewConfiguration, FileSubAgentsConfiguration |
| **UI** | VisualEditorConfiguration, DynamicUIConfiguration, ForkChatConfiguration |
| **Tools** | LintErrorAutoFixConfiguration, TodoListConfiguration, SlashCommandsConfiguration |
| **Skills** | ChatSkillRecommendConfiguration, ChatSkillRecommendOpenConfiguration |
| **Editor** | JetBrainsGoEnhanceConfiguration, BytedanceInternalCodingSkillConfiguration |
| **Safety** | AskUserQuestionConfiguration, FileOpOutsideWorkspaceConfiguration |
| **Other** | ShallowMementoConfiguration, ResourceDiagnosisConfiguration, GitAiConfiguration |

---

## 77. Runtime Environment & Agent Extensions

### 77.1 Runtime Environment System

The Runtime Environment system manages execution environments for AI agents, including binary management and environment detection.

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/ide_command/tool.rs:2397`

#### Core Structures

```rust
// Runtime binary definition
struct RuntimeEnvironmentBinary {
    // 3 elements - binary path, version, platform
}

// Runtime environment with install path and binaries
struct RuntimeEnvironment {
    install_path: String,
    binaries: Vec<RuntimeEnvironmentBinary>,
    // 4 elements total
}

// Supported environments list
struct RuntimeSupportedEnvironment {
    // 1 element - list of supported environments
}

// Response for listing environments
struct RuntimeEnvironmentListResponse {
    supported_environments: Vec<RuntimeSupportedEnvironment>,
    actived_environments: Vec<RuntimeEnvironment>,
    // 2 elements total
}
```

#### Related Commands

| Command | Description |
|---------|-------------|
| `icube.common.commands.tooling.initializeRuntimeEnvironment` | Initialize runtime environment |
| `GetEnvCheckResultArgs` | Check environment status |
| `InstallDepsArgs` | Install dependencies |
| `WriteCfgArgs` | Write configuration |
| `RunInJailArgs` | Run in sandboxed jail |

### 77.2 Agent Extension System

The Agent Extension system allows extending AI agent capabilities through manifest-based tool registration.

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/ide_command/tool.rs`

```rust
// Extension manifest with tools
struct AgentExtensionManifest {
    // 2 elements - manifest metadata
}

// Individual tool in extension
struct AgentExtensionTool {
    // 3 elements - tool name, parameters, description
}

// Full agent extension
struct AgentExtension {
    // 7 elements - id, name, version, manifest, tools, etc.
}

// Run extension request
struct RunAgentExtensionParams {
    extension_id: String,
    // additional params
}

// Run extension response
struct RunAgentExtensionResponse {
    // 3 elements
}

struct RunAgentExtensionResponseData {
    is_error: bool,
    history: String,
    run_mode: String,
    // 3 elements total
}
```

### 77.3 Document Text Range

```rust
struct DocumentTextRangeParams {
    // Parameters for selecting text range in documents
}

struct GetDocumentByUriParams {
    language_id: String,
    // URI-based document retrieval
}

struct GetDocumentByUriResponse {
    // 2 elements - document content and metadata
}
```

---

## 78. Web Search & Crawler System

### 78.1 Web Search

The web search system provides AI agents with internet search capabilities.

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/agent_v3/tools/web_fetch.rs`

```rust
// Web search parameters
struct WebSearchParams {
    // 3 elements - query, max_results, etc.
}

// Search result reference
struct WebSearchReference {
    // 7 elements - url, title, snippet, score, etc.
}

// Web search response
struct WebSearchResponse {
    // 3 elements - references, total_count, etc.
}
```

### 78.2 Web Fetch

```rust
// Web fetch parameters
struct WebFetchParams {
    // 1 element - URL to fetch
}

// Fetch response
struct GetWebFetchResponse {
    // Response with content items
}

// Content item from fetch
struct WebFetchContentItem {
    target_url: String,
    // content, title, etc.
}

// Link item
struct WebFetchLinkItem {
    image_doc_id: String,
    caption: String,
    display_url: String,
    internal_url: String,
    thumbnail_display_url: String,
    thumbnail_internal_url: String,
}

// Image item
struct WebFetchImageItem {
    no_display: bool,
    no_display_reason: String,
}

// Display info
struct WebFetchDisplayInfo {
    // Display metadata for fetched content
}
```

### 78.3 Crawler Content

```rust
// Batch fetch crawler content
struct BatchFetchCrawlerContentParams {
    links: Vec<String>,
    sandbox_id: String,
    // Crawler configuration
}

// Slardar telemetry for crawler
struct SlardarEventCrawlerContentPayload {
    // Crawler content metrics
}

struct SlardarEventCrawlerContentMetrics {
    content_item_count: u32,
    total_content_length: u64,
    avg_content_length: f64,
    truncated_count: u32,
    truncated_content_length: u64,
    avg_truncated_content_length: f64,
}
```

### 78.4 Search Reference System

```rust
// Search reference link
struct SearchReferenceLink {
    link_type: String,
    // URL, title, etc.
}

// Full search reference
struct SearchReference {
    // 8 elements - comprehensive search result
}

// Search reference data
struct SearchReferenceData {
    // 4 elements - snippets, metadata
}
```

### 78.5 Telemetry Events

| Event | Description |
|-------|-------------|
| `icube_ai_agent_web_search` | Web search execution |
| `icube_ai_agent_crawler_content` | Crawler content fetch |
| `icube_ai_agent_remote_web_fetch` | Remote web fetch |
| `icube_ai_agent_web_search_request` | Search request details |

---

## 79. Pending VM Task System

The Pending VM Task system manages asynchronous task execution in Lite VM environments.

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/lite/work_vm_aha.rs:281`

```rust
// Task payload variants (adjacently tagged enum)
enum PendingTaskPayload {
    CreateSession { /* session params */ },
    SendMessage { /* message params */ },
}

// Failure info
struct PendingTaskFailureInfo {
    failed_stage: String,
    failed_at: String,
    // 4 elements total
}

// VM task with full lifecycle
struct PendingVmTask {
    force_stop: bool,
    execution_status: String,  // Initializing | Processing
    failure_info: Option<PendingTaskFailureInfo>,
    retry_count: u32,
    last_processed_at: String,
    // 14 elements total
}
```

### VM Configuration

```rust
struct SoloVMConfig {
    fetch_max_connections: u32,
    // 1 element
}
```

---

## 80. Hook System

The Hook System provides event-driven extensibility for AI agent operations.

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/hub/hook/trigger.rs:26`

### Hook Structures

```rust
// Raw hook configuration
struct RawHooksConfig {
    // Hook definitions
}

// Event hook group
struct RawEventHookGroup {
    // 3 elements - group metadata
}

// Individual hook item
struct RawHookItem {
    // 3 elements - hook_type, conditions, etc.
}

// Hook output
struct RawHookOutput {
    // 5 elements - permission_decision, etc.
}

struct RawHookSpecificOutput {
    hook_specific_output: String,
    permission_decision: String,
    permission_decision_reason: String,
    updated_input: String,
    additional_context: String,
    // 5 elements total
}
```

### Hook Types

| Hook | Description |
|------|-------------|
| `hub_on_title_generated` | Triggered when chat title is generated |
| `hub_on_turn_end` | Triggered at end of conversation turn |
| `hub_on_toolcall_end` | Triggered after tool call completes |

### Hook Configuration

```rust
struct HooksConfiguration {
    // Global hooks config
}

struct HooksPermissionResult {
    // Permission check result from hooks
}

struct MessageConfirmInfo {
    // Confirmation info for message hooks
}
```

---

## 81. Memory Eviction Strategies

### 81.1 Hybrid Retention Config

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/memory/core_memory/strategy/hybrid_half_life.rs:119`

```rust
struct HybridRetentionConfig {
    h_f: f64,      // half-life factor
    h_n: f64,      // half-life normalization
    h_r: f64,      // half-life recency
    h_ref: f64,    // half-life reference
    h_uw: f64,     // user weight
    h_cw: f64,     // context weight
    h_fw: f64,     // frequency weight
    h_nw: f64,     // novelty weight
    h_rw: f64,     // recency weight
    h_uw_v: f64,   // user weight variant
    // 11 elements total
}
```

### 81.2 Eviction Strategy Types

| Strategy | Source File | Description |
|----------|------------|-------------|
| `LRU` | `linear_decay.rs` | Least Recently Used |
| `LFU` | `linear_decay.rs` | Least Frequently Used |
| `LinearDecay` | `linear_decay.rs` | Linear time decay |
| `ExponentialDecay` | `exponential_decay.rs` | Exponential time decay |
| `HybridHalfLife` | `hybrid_half_life.rs` | Hybrid half-life algorithm |
| `WTinyLFU` | - | Weighted Tiny LFU |

---

## 82. Deploy & Billing System

### 82.1 Vercel Deploy

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/ide_command/tool.rs`

```rust
struct VercelDeployCreator {
    email: String,
    uid: String,
    // 3 elements total
}

struct DeployInfo {
    project_id: String,
    alias: String,
    ready_state: String,
    created_at: String,
    creator: VercelDeployCreator,
    inspector_url: String,
    // 11 elements total
}

struct DeployResponse {
    // 2 elements - deploy info and status
}

struct DeployToRemoteParams {
    deploy_target: String,
    // 1 element
}
```

### 82.2 Stripe Billing

```rust
struct StripePriceInfo {
    interval_count: u32,
    currency: String,
    unit_amount_decimal: String,
    nickname: String,
    // 7 elements total
}

struct StripeProduct {
    prices: Vec<StripePriceInfo>,
    // 5 elements total
}

struct StripePaymentStore {
    stripe_pk: String,
    stripe_sk: String,
    selected_products: Vec<StripeProduct>,
    // 3 elements total
}

struct StripeResponse {
    // 3 elements
}
```

### 82.3 Supabase Integration

```rust
struct SupabaseProject {
    anon_key: String,
    project_url: String,
    service_role_key: String,
    // 3 elements total
}

struct SupabaseGetTablesParams {
    schemas: Vec<String>,
    // 2 elements
}

struct SupabaseApplyMigrationParams {
    // 1 element - migration SQL
}

struct SupabaseResponse {
    // 3 elements
}
```

---

## 83. Custom Model System

### 83.1 Custom Model Configuration

**Source:** `apps/icube_server_rs/crates/custom-model-proxy-client/src/`

```rust
struct CustomModelTypeInfo {
    type_display_name: String,
    // 5 elements total
}

struct GetCustomModelTypeConfigRequest {
    // 1 element
}

struct GetCustomModelTypeConfigResponse {
    custom_model_type_list: Vec<CustomModelTypeInfo>,
    // 1 element
}

struct CustomModelConfigDetail {
    // 3 elements
}

struct PersistCustomModelMeta {
    // Custom model persistence metadata
}

struct CustomModel {
    // Full custom model definition
}
```

### 83.2 Custom Model Fallback

```rust
struct CustomModelFallbackConfig {
    poll_interval: u32,
    flush_interval: u32,
    max_send_retries: u32,
    // Fallback behavior config
}

struct LLMCustomModelRawMessageResponse {
    // 1 element - raw response
}
```

### 83.3 LLM Config

```rust
struct LLMConfig {
    // 2 elements
}

struct GetLLMConfigParams {
    required_providers: Vec<String>,
    // 1 element
}

struct GetLLMConfigResponse {
    unconfigured_providers: Vec<String>,
    // 1 element
}

struct ModelUpdateRequest {
    // 13 elements - model configuration update
}
```

---

## 84. Fork Chat System

The Fork Chat system allows branching conversations from any point.

**Source:** Dynamic config `ForkChatConfiguration`

```rust
struct ForkChatConfiguration {
    // Fork chat feature configuration
}
```

---

## 85. Agentic Flow Configuration

### 85.1 Dynamic Agentic Flow

```rust
struct DynamicAgenticFlowConfig {
    // Global agentic flow configuration
}

struct DynamicAgenticFlowConfigMatch {
    max_plan_turns: u32,
    max_left_turns: u32,
    steps: Vec<String>,
    enable_user_prompt_cache: bool,
    toolcall_cache_limit: u32,
    // 5 elements total
}
```

### 85.2 Auto Model Selection

```rust
struct DynamicAgenticAutoModelConfig {
    matches: Vec<DynamicAgenticAutoModelConfigMatch>,
    // 1 element
}

struct DynamicAgenticAutoModelConfigMatch {
    config_name: String,
    fallback_list: Vec<DynamicAgenticAutoModelConfigFallbackItem>,
    // 2 elements
}

struct DynamicAgenticAutoModelConfigFallbackItem {
    min_score: f64,
    max_score: f64,
    // 4 elements total
}
```

### 85.3 Summary Configuration

```rust
struct DymanicAgenticSummaryConfig {
    summary_message_token_limit: u32,
    kept_history_token_limit: u32,
    kept_history_message_limit: u32,
    minimum_current_turn_token_usage: u32,
    multimodal_summary_look_back_count: u32,
    // 5 elements total
}
```

---

## 86. SQLite Optimization

```rust
struct SqliteOptimizationPlatformConfig {
    cache_size: u32,
    mmap_size: u32,
    wal_autocheckpoint: u32,
    enable_temp_store: bool,
    memory_threshold_gb: f64,
    // SQLite performance tuning
}
```

---

## 87. Snapshot V2 System

```rust
struct SnapshotV2 {
    enable_v2: bool,
    force_double_write: bool,
    // 2 elements
}

struct SnapshotCleanUp {
    // Snapshot cleanup configuration
}

struct SnapshotIgnore {
    ignore_rule_list: Vec<String>,
    // Ignore rules for snapshots
}

struct AigcTagConfig {
    watermark: String,
    // AIGC watermarking
}
```

---

## 88. Additional Telemetry Events

Beyond the events documented in Section 38, additional Slardar events discovered:

| Event | Description |
|-------|-------------|
| `icube_ai_agent_v3_execute_multi_agent_task` | Multi-agent task execution |
| `icube_ai_agent_v3_execute_workflow` | Workflow execution |
| `icube_ai_agent_v3_create_agent` | Agent creation |
| `icube_ai_agent_v3_create_initial_task_handle` | Initial task handle creation |
| `icube_ai_agent_v3_create_retry_task_handle` | Retry task handle |
| `icube_ai_agent_v3_subagent_init_task_handle` | Sub-agent initialization |
| `icube_ai_agent_v3_hil_wait_for_tool_confirmation` | HIL tool confirmation wait |
| `icube_ai_agent_v3_call_tool_node` | Tool node invocation |
| `icube_ai_agent_pre_termination` | Pre-termination event |
| `icube_ai_agent_generate_image` | Image generation |
| `icube_ai_agent_image_process` | Image processing |
| `icube_ai_agent_lite_vm_startup` | Lite VM startup |
| `icube_ai_agent_context_usage_send` | Context usage reporting |
| `icube_ai_agent_vsock_request` | Vsock communication |
| `icube_ai_agent_lite_vm_stream_error` | VM stream error |
| `icube_ai_agent_schedule_execution` | Scheduled task execution |
| `icube_ai_agent_schedule_config` | Schedule configuration |
| `icube_ai_agent_schedule_disabled` | Schedule disabled |

---

## 89. Team Agent System

The Team Agent system enables multi-agent collaboration with backend-managed agent teams.

**Source:** `apps/icube_server_rs/modules/ai-agent/src/handler/agent.rs:235`

### 89.1 Backend Team Agent Structures

```rust
// Sub-agent in team
struct BackendTeamAgentSubAgent {
    // 2 elements - agent reference
}

// Create team agent response
struct BackendTeamAgentCreateResponse {
    // 6 elements - created agent details
}

// Remove team agent response
struct BackendTeamAgentRemoveResponse {
    // 5 elements - removal confirmation
}

// Team agent list item
struct BackendTeamAgentListItem {
    agent_env: String,
    last_updated_at: String,
    avatar_url: String,
    // 9 elements total
}

// Team agent list response
struct BackendTeamAgentListResponse {
    // 4 elements
}

// Team agent details
struct BackendTeamAgentDetailsItem {
    // 14 elements - comprehensive agent details
}

struct BackendTeamAgentDetailsResponse {
    // 4 elements
}
```

### 89.2 Team Agent Requests

```rust
struct TeamAgentListReq {
    search_key_word: String,
    sort_by: String,
    sort_order: String,
    // 2+ elements
}

struct TeamAgentDetailsReq {
    user_input_description: String,
    sub_agent_unique_name: String,
    sub_agent_description: String,
    // 1 element
}

struct TeamAgentSubTeamAgentRemoveRequest {
    // Remove sub-agent from team
}

struct BackendTeamAgentCreateRequest {
    // Create new team agent
}
```

### 89.3 Enterprise Agent Management

```rust
struct CreateOrUpdateAgentReqEnterpriseInstall {
    // Enterprise install params
}

struct EnterpriseInstall {
    // Enterprise installation config
}

struct EnterprisePublishReq {
    // Enterprise publish request
}

struct EnterpriseSubAgent {
    local_agent_id: String,
    mcp: String,
    sub_agent: String,
    // 2+ elements
}

struct GetAgentListReq {
    // 2 elements
}

struct GetAgentListRes {
    // Agent list response
}

struct GetAllSubAgentsRes {
    // All sub-agents response
}
```

---

## 90. Content Security Rules

**Source:** Dynamic config and content security service

```rust
struct ContentSecurityRuleDto {
    // 9 elements - rule definition
}

struct ContentSecurityRuleDetailDto {
    rule_detail_id: String,
    rule_detail_name: String,
    regex_pattern: String,
    // 5 elements total
}
```

---

## 91. Rule System

### 91.1 Rule Detail

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/ide_command/tool.rs:668`

```rust
struct RuleDetail {
    target_file_path: String,
    target_file_paths: Vec<String>,
    created_time: String,
    modified_time: String,
    workspace_folder: String,
    rule_scope_root: String,
    rule_source: String,
    is_complete: bool,
    // 9 elements total
}

struct GetRulesDetailsResponse {
    // 2 elements - rules list
}
```

### 91.2 File Rule

```rust
struct FileRule {
    processed_content: String,
    file_rules: Vec<String>,
    // 5 elements total
}
```

### 91.3 Query Rule

```rust
struct QueryRuleData {
    hash_type: String,
    // 7 elements total
}

struct QueryRuleAutoAttachItem {
    // 8 elements - auto-attach rule config
}

struct QueryRuleAutoAttachData {
    // 1 element
}
```

---

## 92. Skill System

### 92.1 Skill Frontmatter

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/skill/util.rs:168`

```rust
struct SkillFrontmatter {
    disable_model_invocation: bool,
    user_invocable: bool,
    allowed_tools: Vec<String>,
    custom_tools: Vec<String>,
    // YAML frontmatter for skill definitions
}

struct ToolYamlDefinition {
    // Tool definition in YAML format
}

struct ShadowKnowledgeFrontmatter {
    // Shadow knowledge definition
}
```

### 92.2 Skill Configuration

```rust
struct SkillAsAgentConfig {
    enable_avatar_creator: bool,
    // Skill-as-agent configuration
}

struct ChangedSkills {
    // Skills changed in operation
}

struct SkillInfo {
    // Skill information
}
```

---

## 93. Model Selection System

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/model/service.rs`

```rust
struct ModelSelectionModeConfig {
    // Model selection mode configuration
}

struct GetModelListByFunctionRequest {
    // Request models by function type
}

struct GetModelListByFunctionResponse {
    // Response with function-specific model list
}

struct FunctionModelList {
    // Models available for specific function
}

struct ModelContextWindowSize {
    // Context window size for model
}

struct SaasUsageRawMetaForPrompt {
    // SaaS usage metadata
}
```

---

## 94. Feishu/Lark Integration

### 94.1 Feishu Doc Info

```rust
struct FeishuDocInfo {
    // 2 elements - document info for Feishu integration
}

struct LarkCliDocsResponse {
    // 2 elements
}

struct LarkCliDocsData {
    // 2 elements
}
```

---

## 95. Model Detail Configuration

**Source:** Binary string analysis

```rust
struct ModelDetailConfig {
    temperature: f64,
    prompt_max_tokens: u32,
    ckg_prompt_max_tokens: u32,
    top_p: f64,
    top_k: u32,
    min_new_tokens: u32,
    repetition_penalty: f64,
    enabled_models: Vec<String>,
    threshold: f64,
    // Model-specific configuration
}

struct FornaxPromptConfig {
    // Fornax prompt configuration
}
```

---

## 96. Audit Logging

```rust
struct ReportAuditLogResponse {
    // Audit log report response
}

struct RequestWaitInQueueEvent {
    // 9 elements - queue wait event
}
```

---

## 97. DSL Agent Template

```rust
struct DSLAgentTemplate {
    // DSL-based agent template
}

struct GetDSLAgentTemplatesResponse {
    templates: Vec<DSLAgentTemplate>,
    // Template list response
}

struct WebUIFiles {
    go_mod_url: String,
    model_func_url: String,
    builtin_tools_url: String,
    web_view_html_url: String,
    // Web UI file URLs
}

struct FetchWebUIFilesRequest {
    yaml_version: String,
    // 1 element
}
```

---

## 98. Ralph Loop System

The Ralph Loop system manages iterative AI agent workflows with round-based execution.

**Source:** `apps/icube_server_rs/modules/ai-agent/src/handler/git/mod.rs:357`

```rust
// User input part for Ralph Loop
struct RalphLoopUserInputPart {
    // 4 elements - input components
}

// User input wrapper
struct RalphLoopUserInput {
    // 2 elements
}

// Full Ralph Loop context
struct RalphLoopContext {
    ralph_loop_round: u32,
    ralph_loop_max_round: u32,
    ralph_loop_document_paths: Vec<String>,
    ralph_loop_user_input_history: Vec<RalphLoopUserInput>,
    ralph_loop_task_last_turn_mark_done: bool,
    is_auto_continuation: bool,
    accumulated_input_tokens: u64,
    accumulated_output_tokens: u64,
    spec_dir_name: String,
    is_loop_done: bool,
    round_start_time: String,
    round_end_time: String,
    current_turn_all_mark_done: bool,
    // 13 elements total
}

struct RalphLoopReport {
    progress_doc_url: String,
    progress_doc_name: String,
    total_input_tokens: u64,
    total_output_tokens: u64,
    total_requests: u32,
    max_requests: u32,
    end_reason: String,
    // 8 elements total
}
```

---

## 99. Context Resolver System

The Context Resolver system manages context extraction and resolution for AI interactions.

### 99.1 Context Metadata

```rust
// Context metadata with 16 elements
struct ContextMeta {
    context_type: String,
    display_type: String,
    truncate_reason: String,
    estimate_included_tokens: u32,
    // 16 elements total
}

// Public context metadata with 15 elements
struct PublicContextMeta {
    // 15 elements - public-facing context info
}

// Token usage per display type
struct DisplayTypeTokenUsageItem {
    // 2 elements
}
```

### 99.2 Code Context

```rust
// Code selection symbol
struct CodeSelectionSymbol {
    // 5 elements - symbol info
}

// Code context region
struct CodeContextRegion {
    char_limit: u32,
    unique_str: String,
    lines: Vec<String>,
    first_line_index: u32,
    last_line_index: u32,
    is_complete: bool,
    // 7 elements total
}

// Context info
struct ContextInfo {
    // 6 elements - context metadata
}
```

### 99.3 Context Resolver

```rust
// Resolver result metadata
struct ContextResolverResultMetadata {
    above: String,
    below: String,
    outline_above: String,
    outline_below: String,
    // 2 elements (variants above/below/outline_above/outline_below)
}

// Resolver reference
struct ContextResolverReference {
    reference_type: String,
    terminal_id: String,
    context_info: ContextInfo,
    // 7 elements total
}

// Server context
struct ContextResolverServerContext {
    is_web_search: bool,
    is_selection: bool,
    is_select_code_before_chat: bool,
    last_select_time: String,
    last_turn_session: String,
}
```

---

## 100. Slash Command System

### 100.1 Slash Command Info

```rust
struct SlashCommandInfo {
    parameter_values: HashMap<String, String>,
    // 5 elements total
}

struct ResolvedSlashCommandDTO {
    // 5 elements - resolved command
}

struct QuerySlashCommandData {
    // 4 elements
}

struct QuerySlashCommandParameters {
    // Parameter validation
}
```

### 100.2 Mention System

The Mention system allows referencing external content in chat messages.

```rust
// Figma mention
struct MentionFigma {
    // 1 element - Figma reference
}

// Problem hash mention
struct MentionHashProblemItem {
    // 10 elements - problem details
}

// Problem file mention
struct MentionHashProblemFile {
    // 4 elements - file reference
}

// Attachment mention
struct MentionAttachment {
    // 1 element - attachment reference
}

// Image hash mention
struct MentionHashImage {
    // 2 elements - image reference
}

// Comment sheet selection
struct MentionCommentSheetSelection {
    // 2 elements
}

// Comment datasheet
struct MentionCommentDatasheet {
    // 4 elements
}

// Comment datatext page
struct MentionCommentDatatextPage {
    // 2 elements
}

// Comment datatext selection
struct MentionCommentDatatextSelection {
    // 2 elements
}

// Comment datatext
struct MentionCommentDatatext {
    // 3 elements
}
```

---

## 101. Diagnostic System

### 101.1 Diagnostic Structures

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/ide_command/tool.rs`

```rust
// Related information for diagnostics
struct DiagnosticRelatedInformation {
    // 3 elements - location, message, severity
}

// Full diagnostic
struct Diagnostic {
    // 6 elements - range, severity, source, message, etc.
}

// Get diagnostics params
struct GetDiagnosticsParams {
    tos_uri: String,
    local_path: String,
    // 1-2 elements
}

// Get diagnostics result
struct GetDiagnosticsResult {
    // 1 element - diagnostics list
}

struct GetDiagnosticsRightResult {
    // 5 elements
}

// File diagnostics
struct FileDiagnostics {
    // File-level diagnostics
}

struct FileDiagnosticsRef {
    // Reference to file diagnostics
}

struct DiagnosticInfo {
    // Diagnostic information
}

struct DiagnosticRange {
    // Range in document
}

struct DiagnosticPosition {
    // Position in document
}
```

---

## 102. Model Detail Configuration

**Source:** Binary string analysis

```rust
struct ModelDetailConfig {
    temperature: f64,
    prompt_max_tokens: u32,
    ckg_prompt_max_tokens: u32,
    top_p: f64,
    top_k: u32,
    min_new_tokens: u32,
    repetition_penalty: f64,
    enabled_models: Vec<String>,
    threshold: f64,
    // 12 elements total
}

// Fornax prompt configuration
struct FornaxPromptConfig {
    // Prompt configuration for Fornax
}
```

---

## 103. Environment Variables Reference

The following environment variables control Trae AI agent behavior. Critical for proxy implementation.

### 103.1 Core ICUBE Variables

| Variable | Description |
|----------|-------------|
| `ICUBE_MODULAR_DATA_DIR` | Modular data directory |
| `FILE_BASE_DIR` | Base file directory |
| `DB_PATH` | Database file path |
| `ICUBE_MANAGER_PID` | Manager process ID |
| `ICUBE_USER_DATA_DIR` | User data directory |
| `ICUBE_APP_SETTINGS_HOME` | App settings home |
| `LOCAL_MODEL_CONFIG_DIR` | Local model config directory |
| `LOCAL_IAC_DIR` | Local IAC directory |
| `RG_PATH` | Ripgrep binary path |
| `ICUBE_PRODUCT_QUALITY` | Product quality tier |
| `ICUBE_PRODUCT_PROVIDER` | Product provider |
| `ICUBE_PRODUCT_BRAND_NAME` | Brand name (Trae) |
| `ICUBE_VSCODE_VERSION` | VSCode version |
| `ICUBE_APP_CHANNEL` | App channel (stable/beta) |

### 103.2 Event & Telemetry Variables

| Variable | Description |
|----------|-------------|
| `ICUBE_EVENT_VERIFY_ENABLED` | Event verification enabled |
| `ICUBE_EVENT_VERIFY_HOST` | Event verification host |
| `OS_RELEASE` | OS release version |
| `IDE_ENVIRONMENT_ID` | IDE environment ID |
| `ARNOLD_WORKSPACE_ID` | Arnold workspace ID |
| `CLOUDIDE_CONFIG_LANGUAGE` | Cloud IDE language config |
| `IDE_LANG` | IDE language |
| `PROMPT_TEMPLATE_BASE_PATH` | Prompt template base path |
| `PORT0` | Primary port |

### 103.3 Network & CKG Variables

| Variable | Description |
|----------|-------------|
| `ICUBE_DEFAULT_HOST` | Default host |
| `ICUBE_USE_IPV6` | Enable IPv6 |
| `CKG_PORT` | CKG server port |
| `CKG_USE_AHA_IPC` | Use AHA IPC for CKG |

### 103.4 Database Pool Variables

| Variable | Description |
|----------|-------------|
| `ICUBE_ENABLE_DATABASE_BACKUP` | Enable database backup |
| `ICUBE_DATABASE_BACKUP_INTERVAL` | Backup interval |
| `ICUBE_ENABLE_DB_RW_SPLIT` | Enable read/write split |
| `ICUBE_DB_READ_POOL_MAX_CONNECTIONS` | Read pool max connections |
| `ICUBE_DB_READ_POOL_MIN_CONNECTIONS` | Read pool min connections |
| `ICUBE_DB_WRITE_POOL_MAX_CONNECTIONS` | Write pool max connections |
| `ICUBE_DB_WRITE_POOL_MIN_CONNECTIONS` | Write pool min connections |
| `ICUBE_DB_BUSY_TIMEOUT_MS` | DB busy timeout (ms) |
| `ICUBE_DB_POOL_ACQUIRE_TIMEOUT_SECS` | Pool acquire timeout (s) |
| `ICUBE_DB_POOL_MAX_LIFETIME_SECS` | Pool max lifetime (s) |

### 103.5 TRAE Feature Flags

| Variable | Description |
|----------|-------------|
| `TRAE_AI_AGENT_DEBUG_PAGE` | Debug page enabled |
| `TRAE_REMOTE_REGION` | Remote region |
| `TRAE_FORCE_TASK_STRATEGY` | Force task strategy |
| `TRAE_FORCE_LINT_ERROR_FIX_ONCE_AFTER_FINISH` | Auto-fix lint errors |
| `TRAE_DISABLE_PROMPT_SELECTED_CODE` | Disable selected code in prompt |
| `TRAE_FORCE_NATIVE_FUNCTION_CALL` | Force native function calling |
| `TRAE_FORCE_PARALLEL_TOOL_CALLING` | Force parallel tool calls |
| `TRAE_FORCE_NATIVE_KEEP_FINISH_TOOL` | Keep finish tool native |
| `TRAE_ENABLE_USER_MESSAGE_SIMPLIFY` | Simplify user messages |
| `TRAE_ENABLE_USE_SESSION_CONTEXT` | Use session context |
| `TRAE_FORCE_MERGE_EDIT_TOOL` | Force merge edit tool |
| `TRAE_V3_ENABLE_READ_TRUNCATION` | V3 read truncation |
| `TRAE_ENABLE_V3_OPTIMIZE_TOOL_CHOICE_STRATEGY` | Optimize tool choice |
| `TRAE_NFC_USE_ORIGINAL_TOOL_CALL_ID` | Use original tool call ID |
| `TRAE_ENABLE_V3_LLM_MESSAGE_USE_SEPARATE_TOOLCALL` | Separate tool calls |
| `TRAE_FORCE_ENABLE_NFC_PREFILL_AGENT_NAME` | Prefill agent name |
| `TRAE_V3_MAX_CONCURRENT_TASKS` | Max concurrent tasks |
| `TRAE_V3_CONCURRENT_TASK_TIMEOUT` | Concurrent task timeout |
| `TRAE_ENABLE_FILE_CHANGES` | Enable file changes |
| `TRAE_FORCE_V3_RENAME_CUSTOM_TOOL_APPLY_PATCH_NAME` | Rename apply_patch tool |
| `TRAE_DEBUG_RENDER` | Debug rendering |
| `TRAE_FORCE_ENABLE_CORE_MEMORY` | Force enable core memory |
| `TRAE_FORCE_ENABLE_SHALLOW_MEMENTO` | Force enable shallow memento |
| `TRAE_ENABLE_VIEW_FILE_AUTO_EXPAND` | Auto-expand view file |
| `TRAE_ENABLE_VIEW_FILE_TRUNCATED_AND_HINT` | Truncated file hints |
| `TRAE_VIEW_FILE_MAX_FILE_SIZE` | Max file size for view |
| `TRAE_ENABLE_VIEW_FILE_OUTLINE` | File outline enabled |
| `TRAE_ENABLE_EDIT_LINTER_ERROR` | Edit linter error |
| `TRAE_ENABLE_READ_OLD_LINTER_ERROR` | Read old linter errors |
| `TRAE_SLEEP_TIME_FOR_READ_OLD_LINTER_ERROR` | Sleep time for linter |
| `SIMULATE_SSE_NO_EVENT` | Simulate SSE no event |

### 103.6 Sandbox & Tool Variables

| Variable | Description |
|----------|-------------|
| `ENABLE_IPC_SERVER` | Enable IPC server |
| `SANDBOX_MODE` | Sandbox mode |
| `TRAE_TELEPORT_ENABLE` | Teleport enabled |
| `TRAE_STATIC_CLIENT_TYPE` | Static client type |
| `TRAE_GLOB_ENABLE_RIPGREP` | Use ripgrep for glob |
| `TRAE_GLOB_ENABLE_NO_IGNORE` | Glob without ignore |
| `TRAE_GREP_ENABLE_HIDDEN` | Grep hidden files |
| `TRAE_GREP_MAX_COLUMNS` | Max grep columns |
| `TRAE_GREP_POST_SORT` | Grep post-sort |
| `TRAE_RIPGREP_PARTIAL_ON_TIMEOUT` | Ripgrep partial on timeout |
| `TRAE_REMOTE_AGENT_HOOK_DISABLED` | Disable remote agent hooks |
| `TRAE_SANDBOX_NAME` | Sandbox name |
| `TRAE_ENABLE_COMMAND_EXIT_CODE_SEMANTICS` | Exit code semantics |
| `TRAE_COMPUTER_USE_MTC_TARGET` | Computer use MTC target |
| `TRAE_LIGHTWEIGHT_MODE` | Lightweight mode |

### 103.7 Development Variables

| Variable | Description |
|----------|-------------|
| `MARSCODE_DEV_MODE` | MarsCode dev mode |
| `MARSCODE_AI_AGENT_ENABLE_OTLP` | Enable OpenTelemetry |
| `MARSCODE_VERBOSE_LOG` | Verbose logging |
| `ICUBE_RUST_LOG_LEVEL` | Rust log level |
| `AI_NATIVE_ENVS_J_10_YS_J_4_Y` | AI native environment |

---

## 104. Chat Memory System

### 104.1 Chat Memory Structures

```rust
struct ChatMemoryConfig {
    force_chat_memory_only: bool,
    upgrade_core_memory_by_chat_memory: bool,
    enable_include_related_history_in_memory: bool,
    // 3 elements total
}

struct ChatMemoryWithHistoryConfig {
    // 1 element
}

struct ChatMemoryTriggerEvent {
    chat_memory_scene: String,
    force_update: bool,
    // 2 elements total
}

struct ChatMemoryItem {
    memory_content: String,
    memory_file_path: String,
}

struct ChatMemoryContext {
    user_profile: String,
    project_memory: String,
    recent_topics: Vec<String>,
    hash_folder_ls_path: String,
    hash_rules: String,
}
```

---

## 105. Application Configuration

```rust
struct ApplicationConfig {
    enable_solo_next: bool,
    enable_agent_process_v3: bool,
    enable_upgrade_all_sessions_to_v3: bool,
    enable_upgrade_session_by_solo_coder: bool,
    enable_upgrade_session_by_solo_builder: bool,
    agent_types_that_ignore_queue_event: Vec<String>,
    chat_memory_config: ChatMemoryConfig,
    // 7 elements total
}
```

---

## 106. GTM Collector Context

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/gtm/event.rs:38`

```rust
struct GtmCollectorContext {
    tea_config: String,
    login_scope: String,
    // 4 elements total
}
```

---

## 107. User Configuration System

### 107.1 User Configuration Item

```rust
struct UserConfigurationItem {
    review_on_commit: bool,
    show_notice: bool,
    with_history_enabled: bool,
    helper_enabled: bool,
    notification_shown: bool,
    enabled_folders: Vec<String>,
    import_claude_folders: bool,
    always_enabled: bool,
    // 32 elements total - extensive user preferences
}
```

### 107.2 Tenant User Config

```rust
struct TenantUserConfig {
    blacklist_repos: Vec<TenantUserConfigBlacklistRepo>,
    // 2 elements
}

struct TenantUserConfigBlacklistRepo {
    // 2 elements - repo identifier
}

struct GetTenantUserConfigResponse {
    config_info: String,
    mcp_whitelist_config: String,
    // 3 elements total
}

struct GetTenantUserConfigRequest {
    // Request params
}
```

### 107.3 Core Memory Incidental Configuration

```rust
struct CoreMemoryIncidentalConfiguration {
    should_display_core_memory_memory_panel: bool,
    is_all_model_enabled: bool,
    enabled_model_names: Vec<String>,
}

struct ModelInfo {
    // Model information
}
```

---

## 108. Error & Evaluation Config

```rust
struct ErrorLogReportConfig {
    // 2 elements - error logging configuration
}

struct EvaluationConfig {
    // 1 element - evaluation configuration
}

struct EvaluationTrafficControl {
    // Traffic control for evaluations
}
```

---

## 109. Virtual Path & Auto-Accept Config

```rust
struct VirtualPathConfig {
    // 1 element - virtual path configuration
}

struct AutoAccept {
    can_show_diff: bool,
    // Auto-accept configuration
}

struct MbRule {
    umb: String,
    // MB rule definition
}

struct MbConfig {
    config_name_list: Vec<String>,
    mb_rules: Vec<MbRule>,
    // MB configuration
}
```

---

## 110. Merge Context

```rust
struct MergeContext {
    // Merge operation context
}

struct ReviewAndResolve {
    // Review and resolve operations
}
```

---

## 115. Provider & Model Detail System

### 115.1 Provider Structure

```rust
struct Provider {
    // 10 elements - provider configuration
}

struct ProvidersListRequest {
    // Request to list providers
}

struct ProvidersListResponse {
    // 1 element - list of providers
}

struct ModelCommonResponse {
    // 3 elements - common model response
}
```

### 115.2 Model Detail Info

```rust
struct ModelDetailInfo {
    // 17 elements - comprehensive model details
}

struct ModelPromptConfig {
    // 3 elements - prompt configuration
}

struct ModelCustomConfig {
    // 11 elements - custom model configuration
}

struct ModelDetail {
    api_key_doc: String,
    model_list_doc: String,
    model_detail: String,
    billing_mode: String,
    provider_icon: String,
    // 2+ elements
}

struct ModelUpdateRequest {
    // 13 elements - model update request
}

struct ModelAddRequest {
    // 11 elements - add new model
}
```

### 115.3 Model Selection Modes

```rust
struct ModelSelectionModeConfig {
    // 8 elements - selection mode configuration
}

struct GetModelSelectionModesResponse {
    // 1 element
}

struct GetModelSelectionModesResponseData {
    mode_list: Vec<String>,
    // 1 element
}
```

### 115.4 Encrypted Prompt

```rust
struct ModelEcryptedPrompt {
    // 4 elements - encrypted prompt data
}

struct ModelConfigMeta {
    encrypted_prompt_set: Vec<ModelEcryptedPrompt>,
    // 9 elements total
}
```

---

## 116. Session Usage & Billing

### 116.1 Session Usage

```rust
struct SessionUsage {
    usage_time: String,
    use_max_mode: bool,
    amount_float: f64,
    cost_money_float: f64,
    remain_discount_times: u32,
    // 9 elements total
}

struct SessionUsageExtraInfo {
    output_token: u64,
    cache_read_token: u64,
    cache_write_token: u64,
    // 4 elements total
}

struct GetSessionUsageResponse {
    user_usage_group_by_session: Vec<SessionUsage>,
    // 1 element
}
```

### 116.2 Fee & Usage Events

```rust
struct FeeUsageEvent {
    // 8 elements - fee usage tracking
}

struct NotifyUsageEvent {
    // 5 elements - usage notification
}
```

---

## 117. Privacy & Authorization

### 117.1 Privacy Mode

```rust
struct OperatePrivacyModeRequest {
    switch: bool,
    // 1 element
}

struct OperatePrivacyModeResponse {
    // Privacy mode operation response
}

struct GetPrivacyModeResponse {
    privacy_status: String,
    // 1 element
}
```

### 117.2 Authorization

```rust
struct CheckAuthorizationRequest {
    // 1 element - authorization check
}

struct AuthorizationResultRequest {
    // 3 elements - authorization result
}

struct CheckAuthorizationResponse {
    need_authorization: bool,
    // Authorization check response
}
```

---

## 118. MCP Whitelist System

**Source:** MCP configuration

```rust
struct MCPWhitelist {
    arg: String,
    args_hash: String,
    config_json: String,
    // 11 elements total
}

struct MCPWhitelistConfigInfo {
    global_enable: bool,
    whitelists: Vec<MCPWhitelist>,
    // 2 elements
}
```

---

## 119. System Diagnosis

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/contextfs/resolver.rs:49`

### 119.1 Process Info

```rust
struct ProcessInfo {
    parent_pid: u32,
    root_pid: u32,
    handles: Vec<String>,
    extension_owner: ExtensionOwner,
    // 9 elements total
}

struct ExtensionOwner {
    // Extension owner info
}

struct CommandSchema {
    // 3 elements - command schema
}
```

### 119.2 Disk Info

```rust
struct DiskInfo {
    usage_ratio: f64,
    total_mb: u64,
    used_mb: u64,
    free_mb: u64,
    trae_total_mb: u64,
    trae_framework_mb: u64,
    trae_extensions_mb: u64,
    ai_agent_mb: u64,
    ai_server_mb: u64,
    worktree_mb: u64,
    // 10 elements total
}
```

### 119.3 System Resource Usage

```rust
struct SystemResourceUsage {
    // 3 elements - CPU, memory, disk usage
}

struct UnresponsiveExtensionInfo {
    extension_id: String,
    total_time_ms: u64,
    percentage: f64,
    profile_duration_ms: u64,
    // 5 elements total
}

struct RecentDiagnosisSnapshot {
    // 3 elements - snapshot data
}

struct RecentDiagnosisRecord {
    // 4 elements - diagnosis record
}

struct SystemDiagnosisReq {
    triggered_types: Vec<String>,
    // 11 elements total
}
```

---

## 120. Timing & Performance

### 120.1 Platform Timing Detail

```rust
struct PlatformTimingDetail {
    // 6 elements - platform timing breakdown
}
```

### 120.2 Timing Cost Event

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/llm/event.rs`

```rust
struct TimingCostEvent {
    check_risk: String,
    build_llm_prompt: String,
    // Server preprocessing
    server_preprocessing_detail: ServerPreprocessingDetail,
    post_security_check: String,
    // Server postprocessing
    server_postprocessing_detail: ServerPostprocessingDetail,
    // Timing breakdown
    preprocess_timing: String,
    first_token_timing: String,
    provider_first_token: String,
    network_latency: String,
    provider_network_latency: String,
    // Platform detail
    platform_detail: PlatformTimingDetail,
    middleware_processing_time: String,
    queue_timing: String,
    postprocess_timing: String,
    // Agent timing
    agent_preprocess_timing: String,
    agent_postprocess_timing: String,
    agent_middleware_timing: String,
    // Gateway timing
    gateway_preprocess_timing: String,
    gateway_server_processing_time: String,
    // Additional fields
    platform_first_token_timing: String,
    server_processing_time: String,
    first_sse_event_time: String,
    is_retry: bool,
    account_type: String,
    account_name: String,
    provider_model_name: String,
    // 20 elements total
}

struct ServerPreprocessingDetail {
    // Server preprocessing timing
}

struct ServerPostprocessingDetail {
    // Server postprocessing timing
}
```

### 120.3 Token Usage Event

```rust
struct TokenUsageEvent {
    // 9 elements - token usage tracking
}

struct ModelCallChainItem {
    error_stage: String,
    // 4 elements total
}
```

### 120.4 Queue Events

```rust
struct QueueBeginEvent {
    // 4 elements - queue begin
}

struct QueueEndEvent {
    // 3 elements - queue end
}
```

---

## 121. Chat Session Management (Remote)

### 121.1 Remote Session Data

```rust
struct RemoteChatSessionData {
    // Remote session data
}

struct RemoteChatMessageData {
    unrevertible_reason: String,
    // Remote message data
}

struct CreateChatSessionRequest {
    project_extra_info: String,
    auto_create_project: bool,
    create_reason: String,
    // Create session request
}

struct CreateChatSessionData {
    // Session creation data
}

struct CreateChatSessionResponse {
    // Session creation response
}
```

### 121.2 Session Operations

```rust
struct CommitSessionRequest {
    history_file_uri: String,
    version_snapshot: String,
    pre_termination: String,
    handoff: String,
    // Commit session request
}

struct CommitSessionResponse {
    // Commit response
}

struct FreezeChatSessionRequest {
    // Freeze session request
}

struct FreezeChatSessionResponse {
    // Freeze response
}

struct ThawChatSessionRequest {
    // Thaw session request
}

struct ThawChatSessionData {
    restored_status: String,
    // Thaw data
}

struct ThawChatSessionResponse {
    // Thaw response
}
```

### 121.3 Handoff

```rust
struct HandoffTarget {
    // Handoff target info
}

struct HandoffInfo {
    // Handoff information
}
```

### 121.4 Version Snapshot

```rust
struct VersionSnapshotInfo {
    version_type: String,
    version_ref: String,
    repo_uri: String,
    parent_ref: String,
    has_new_commit: bool,
}

struct RemoteSource {
    repo_name: String,
    // Remote source info
}

struct RemoteTarget {
    allocation_status: String,
    // Remote target info
}

struct RemoteSandboxInfo {
    explorer_url: String,
    vnc_url: String,
    vnc_template_url: String,
    environment_name: String,
    browser_use_sandbox: String,
    uploads_path: String,
}
```

### 121.5 History Sync

```rust
struct GetHistoryDownloadURLRequest {
    // Download URL request
}

struct GetHistoryDownloadURLData {
    // Download URL data
}

struct GetHistoryDownloadURLResponse {
    // Download URL response
}

struct GetHistoryUploadURLRequest {
    // Upload URL request
}

struct GetHistoryUploadURLData {
    // Upload URL data
}

struct GetHistoryUploadURLResponse {
    // Upload URL response
}

struct CheckHistoryExistsRequest {
    // Check exists request
}

struct CheckHistoryExistsData {
    exists: bool,
    // Check exists data
}

struct CheckHistoryExistsResponse {
    // Check exists response
}

struct BatchSyncHistoryRequest {
    visible_message_ids: Vec<String>,
    // Batch sync request
}

struct BatchSyncHistoryResponse {
    // Batch sync response
}
```

---

## 122. Tea Collector Context

```rust
struct TeaCollectorContext {
    // 4 elements - ByteDance telemetry context
}
```

---

## 123. Chat Fast Apply & Fix

### 123.1 Chat Fast Apply

```rust
struct ChatFastApplyRequest {
    editing_plan: String,
    editing_logic: String,
    edit_blocks: Vec<String>,
    code_before_real: String,
    // 8 elements total
}

struct ChatFastApplyResponse {
    show_message_from_server: String,
    // Fast apply response
}
```

### 123.2 Fix Search Replace

```rust
struct FixSearchReplaceApiRequest {
    // 8 elements - fix search replace request
}

struct FixSearchReplaceApiResponse {
    // Fix search replace response
}
```

---

## 123. Interrupt Reason System

The InterruptReason enum defines why an AI agent operation was interrupted.

```rust
enum InterruptReason {
    RetryWithResumeModel {
        // 2 elements - resume model retry
    },
    RetryWithFallbackModel {
        // 5 elements - fallback model retry
    },
    ToolConfirm {
        // 5 elements - tool confirmation required
    },
}
```

---

## 124. Commercial & Billing System

### 124.1 Commercial Payload

```rust
struct CommercialPayload {
    // 3 elements - commercial data
}

struct CommercialRemind {
    notification_type: String,
    commercial_remind: String,
}

struct CommercialExhaust {
    commercial_exhaust: String,
    queue: String,
    max_mode_usage: String,
    paygo_start: String,
    paygo_usage: String,
}

struct ContentFilterWarning {
    content_filter_warning: String,
}
```

### 124.2 Model Commercial Info

```rust
struct ModelCommercialInfo {
    // 2 elements - commercial model info
}

struct ModelSmartSelection {
    manual_usage: String,
    // 3 elements total
}

struct ModelSmartSelectionMeta {
    strategy: String,
    fallback_to_advance_model: String,
    entitlement_id: String,
    // 2+ elements
}
```

---

## 125. Docset System

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/docset/model.rs:583`

### 125.1 Docset Item

```rust
struct DocsetItemDTO {
    entry_point: String,
    index_time: String,
    relative_globs_to_load: Vec<String>,
    // 10 elements total
}

struct DocsetVersionInfo {
    should_update: bool,
    // 1 element
}

struct PageListItem {
    // 5 elements - page list item
}
```

### 125.2 Docset Requests

```rust
struct FetchOnlineDocsetDetailParams {
    // 2 elements
}

struct RetrieveDocsetRagParam {
    document_set_list: Vec<String>,
    force_refresh: bool,
    // 2+ elements
}

struct DocsetVirtualProjectInitRequestParams {
    user_prompt: String,
    // 2 elements
}

struct DocsetLocalFilesCreateRequestParams {
    // 3 elements
}

struct DocsetGetIndexStatusRequestParams {
    // 1 element
}

struct DocsetCancelIndexRequestParams {
    // 1 element
}

struct DocsetDeleteRequestParams {
    // 1 element
}

struct DocsetDocument {
    // 4 elements - document info
}

struct DocsetUrlCreateRequestParams {
    // URL-based docset creation
}
```

### 125.3 Docset References

```rust
struct DocsetReferenceData {
    // Reference data
}

struct NormalizedDocumentIndexStatus {
    // Normalized status
}

struct NormalizedProjectDocumentsIndexStatus {
    // Project document status
}

struct ExternalDocumentReferenceItem {
    // External document reference
}

struct EnterpriseDocReference {
    // Enterprise doc reference
}
```

### 125.4 Docset External Documents

```rust
struct DocsetExternalDocumentVariablesDTO {
    // 4 elements
}

struct DocsetExternalDocumentRelatedDocDTO {
    // 8 elements - related document info
}

struct ExternalDocument {
    // 4 elements
}
```

### 125.5 Docset Status

```rust
struct DocSetStatusListItem {
    document_set: String,
    document_page_list: Vec<PageListItem>,
    // 2+ elements
}

struct GetDocSetStatusResponse {
    detailed_status_list: Vec<DocSetStatusListItem>,
    // Status response
}

struct CheckShouldUpdateOfficialDocSetResponse {
    // Check update response
}

struct PullLatestOfficialDocSetResponse {
    // Pull latest response
}

struct QueryContextWrapperDTO {
    query_context: String,
    // Query context
}

struct DocsetChatHistoryItemDTO {
    item_list: Vec<String>,
    // Chat history item
}

struct RetrieveDocsetRagResponse {
    // RAG response
}
```

---

## 126. Content Filter System

```rust
struct ContentFilterEvent {
    // 4 elements - content filter event
}

struct PromptMetaFilterConfig {
    disable_prompt_fetching: bool,
    function_filters: Vec<String>,
    // Prompt meta filter
}
```

---

## 127. Post Compact Restore

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/plan/context_obtainer/post_compact_restore.rs:70`

```rust
struct PostCompactRestoreParams {
    // Compact restore parameters
}

struct PostCompactRestoreSkillParam {
    // 1 element - skill restore param
}

struct PostCompactRestoreFileParam {
    // 1 element - file restore param
}

struct PostCompactRestoreResult {
    // Compact restore result
}

struct PostCompactRestoreSkillResult {
    // Skill restore result
}

struct PostCompactRestoreFileResult {
    // File restore result
}
```

---

## 128. Persist User Message Context

```rust
struct PersistUserMessageContext {
    // 14 elements - persistent user message context
}
```

---

## 129. Agent Status & Lifecycle

### 129.1 Agent Status Events

```rust
struct AgentIdleEvent {
    // 6 elements - agent idle state
}

struct AgentStatusItem {
    // 3 elements - status item
}

struct AgentStatusEvent {
    // 1 element - status event
}

struct AgentWakeupEvent {
    // 3 elements - wakeup event
}

struct AgentResumeEvent {
    resume_agent_run_id: String,
    // 6 elements total
}

struct GetResumeAgentTaskStatusResponse {
    // 2 elements - resume status
}
```

### 129.2 Queue Events

```rust
struct PendingRequestDTO {
    // 6 elements - pending request
}

struct GetPendingResponse {
    // 2 elements - pending response
}

struct QueueBeginEvent {
    // 4 elements - queue begin
}

struct QueueEndEvent {
    // 3 elements - queue end
}

struct QueueContinueEvent {
    // 1 element - queue continue
}

struct RequestWaitInQueueEvent {
    // 9 elements - wait in queue
}
```

---

## 130. Notification System

### 130.1 User Notification

```rust
struct NotifyUserParams {
    // 2 elements - notify user params
}

struct NotifyUserResult {
    // Notify user result
}

struct NotifyButton {
    action_type: String,
    product_type: String,
    // 2 elements
}

struct NotifyVmHubDataRequest {
    // 1 element - VM hub data notification
}
```

### 130.2 State Notification

```rust
struct StateNotificationRequest {
    // State notification request
}

struct StateNotificationResponse {
    // State notification response
}
```

---

## 131. Wiki Status System

```rust
struct WikiStatus {
    // 7 elements - wiki status
}

struct GetWikiStatusResponse {
    // 9 elements - wiki status response
}

struct MetaStatusInfo {
    // 3 elements - meta status info
}
```

---

## 132. Hub Login & Config

```rust
struct HubLoginRequest {
    // Hub login request
}

struct HubChangeConfigRequest {
    // Hub config change request
}
```

---

## 133. Conversation Management

```rust
struct ConversationsResponse {
    cli_conversation_id: String,
    // Conversations response
}

struct RemoteConversationListMessagesRequest {
    cli_conversation_ids: Vec<String>,
    cli_id: String,
    // List messages request
}

struct ListMessagesResponse {
    // List messages response
}

struct BatchInsertMessagesRequest {
    // Batch insert messages
}

struct BatchInsertMessagesItem {
    // Batch insert item
}
```

---

## 134. VM Operations

```rust
struct VmOperateData {
    // VM operation data
}

struct AddAttachmentRequest {
    // Add attachment request
}

struct SendUserDecisionRequest {
    // Send user decision
}

struct DeleteMessageRequest {
    // Delete message request
}

struct WakeupSandboxRequest {
    // Wakeup sandbox request
}

struct ActionQueueRequest {
    // Action queue request
}

struct RevertMessageRequest {
    // Revert message request
}

struct PrefetchForAutoRequest {
    // Prefetch for auto request
}

struct RevertCheckRequest {
    // Revert check request
}
```

---

## 135. Core Data Structures

### 135.1 Context (23 elements)

```rust
struct Context {
    // 23 elements - full context for AI interactions
}
```

### 135.2 UserInput (15 elements)

```rust
struct UserInput {
    // 15 elements - user input data
}

struct ContextUserInput {
    unittest_target: String,
    hash_webs: String,
    // User input context
}
```

### 135.3 ChatTurn (10 elements)

```rust
struct ChatTurn {
    conversations: Vec<Message>,
    // 10 elements total
}

struct History {
    // 1 element - history data
}

struct Message {
    use_cache: bool,
    // 3 elements total
}

struct Multimedia {
    // 6 elements - multimedia content
}
```

### 135.4 Code Change

```rust
struct CodeChange {
    // 2 elements - code change info
}

struct AssistantResponseExtra {
    assistant_response_extra: String,
    is_cropped_last_time: bool,
    last_rendering_token_count: u32,
    last_rendering_token_limit: u32,
    rendered_token_count: u32,
    rendered_token_limit: u32,
    // 1 element
}
```

### 135.5 Render Input (10 elements)

```rust
struct RenderInput {
    variables: Vec<String>,
    toolcall_history: Vec<String>,
    multi_content: Vec<String>,
    intent_name: String,
    current_turn: String,
    token_usage_variable_keys: Vec<String>,
    // 10 elements total
}
```

### 135.6 File Changes

```rust
struct FileChangeInfo {
    content_snippet: String,
    // 2 elements
}

struct FilesChangesContext {
    delete_files_summary: String,
    update_files_summary: String,
    // 2 elements
}

struct FilesChangesSummary {
    // 2 elements
}
```

### 135.7 Stored Context

```rust
struct StoredUserContext {
    // 1 element
}

struct VersionInfo {
    // 3 elements - version info
}
```

---

## 136. Skill System

### 136.1 Recommended Skill (11 elements)

```rust
struct RecommendedSkill {
    // 11 elements - recommended skill
}

struct TrialSkillInfo {
    // 12 elements - trial skill info
}
```

### 136.2 Skill Recommendation

```rust
struct SkillRecommendResult {
    query_expansion: String,
    use_mock_url: String,
    force_enabled: String,
    req_top_k: String,
    req_extra_context: String,
    // 7 elements total
}

struct SkillRecommendResultItem {
    skill_url: String,
    icon_url: String,
    icon_url_origin: String,
    pinned: bool,
    installed_as_trial: bool,
    skill_content: String,
    trial_failure_reason: String,
    trial_folder_name: String,
    // 15 elements total
}
```

---

## 137. Schedule System

### 137.1 Schedule Tool Input (22 elements)

```rust
struct ScheduleToolInput {
    relative_time: String,
    absolute_time: String,
    schedule_id: String,
    task_type: String,
    task_data: String,
    agent_mode: String,
    start_time: String,
    end_time: String,
    // 22 elements total
}
```

### 137.2 Schedule Execution (14 elements)

```rust
struct ScheduleExecution {
    scheduled_task_name: String,
    // 14 elements total
}
```

### 137.3 Schedule Task Info (21 elements)

```rust
struct ScheduleTaskInfo {
    last_execution_status: String,
    last_execution_fail_reason: String,
    last_execution_chat_session_status: String,
    last_execution_chat_session_id: String,
    // 21 elements total
}
```

### 137.4 Schedule Result (10 elements)

```rust
struct ScheduleResult {
    available_actions: Vec<String>,
    tasks: Vec<ScheduleTaskInfo>,
    executions: Vec<ScheduleExecution>,
    // 10 elements total
}

struct ScheduleParams {
    // 9 elements - schedule parameters
}

struct TriggerConfig {
    // 4 elements - trigger configuration
}
```

---

## 138. Message System

### 138.1 Message Info (13 elements)

```rust
struct MessageInfo {
    notify_usage: bool,
    // 13 elements total
}

struct MessageSummary {
    // 1 element
}

struct MessageToolcall {
    already_emitted_generating_event: bool,
    already_emitted_run_event: bool,
    // 7 elements total
}
```

### 138.2 Message Confirm (15 elements)

```rust
struct MessageConfirmInfo {
    confirm_status: String,
    auto_confirm: bool,
    confirm_source: String,
    skip_reason: String,
    // 15 elements total
}

struct HooksPermissionResult {
    hooks_tool_call_name: String,
    hooks_event_name: String,
    deny_message: String,
    // 5 elements total
}

struct AgentStatus {
    // 2 elements - agent status
}
```

### 138.3 Message Plan Item (16 elements)

```rust
struct MessagePlanItem {
    // 16 elements - plan item
}
```

### 138.4 Todo System

```rust
struct TodoList {
    todos: Vec<TodoItem>,
    // 1 element
}

struct TodoItem {
    // 5 elements - todo item
}
```

---

## 139. File Operations

### 139.1 File Diff (7 elements)

```rust
struct FileDiff {
    before_content: String,
    after_content: String,
    insert_line_count: u32,
    delete_line_count: u32,
    // 7 elements total
}

struct MessageAiEditFileDiffList {
    file_diffs: Vec<FileDiff>,
    // 1 element
}
```

### 139.2 File Toolcall Data

```rust
struct FileToolcallData {
    history_run_mode: String,
    need_continue_write: bool,
    // 5 elements total
}

struct FileToolcallDataChange {
    rename_file_path: String,
    apply_model_name: String,
    linter_error: String,
    linter_error_result: String,
    old_diagnostic_result: String,
    new_diagnostic_result: String,
    // 11 elements total
}

struct FileToolcallDataChangeDiffInfo {
    replaceable_blocks: Vec<String>,
    // 3 elements
}

struct FileToolcallDataChangesWithStatus {
    // 1 element
}

struct FileToolcallDataChangeWithStatus {
    change: FileToolcallDataChange,
    change_time: String,
    // 5 elements total
}
```

### 139.3 Changed File Info

```rust
struct ChangedFileInfo {
    // 4 elements - changed file info
}
```

---

## 140. Tool Results

### 140.1 Toolcall Result (10 elements)

```rust
struct ToolcallResult {
    error_variant: String,
    render: String,
    is_truncated: bool,
    interrupt: String,
    // 10 elements total
}

struct ToolcallResultImage {
    detail: String,
    // 4 elements total
}
```

### 140.2 Run Command Result (23 elements)

```rust
struct RunCommandResult {
    send_to_command_status: String,
    run_command_to_bg_reason: String,
    shell_type: String,
    sandbox_trace_file: String,
    sandbox_dry_run_log: String,
    command_start_ms: u64,
    command_end_ms: u64,
    toolcall_output_path: String,
    total_bytes: u64,
    stdout_complete: bool,
    user_aborted: bool,
    tty_mode: String,
    // 23 elements total
}
```

### 140.3 Search Result

```rust
struct SearchResult {
    // 1 element
}

struct SearchResultMatches {
    // 2 elements
}

struct SearchResultMatchesLine {
    // 2 elements
}
```

---

## 141. Agent Finish & Apply

### 141.1 Agent Finish

```rust
struct AgentFinishParams {
    agent_toolcall_histories: Vec<String>,
    // 3 elements total
}
```

### 141.2 Apply Patch

```rust
struct ApplyPatchParams {
    // 2 elements - patch parameters
}
```

---

## 142. Manage Operations

### 142.1 Manage Operation (8 elements)

```rust
struct ManageOperation {
    // 8 elements - management operation
}
```

### 142.2 Operation Result (13 elements)

```rust
struct OperationResultItem {
    is_evicted: bool,
    evicted_title: String,
    evicted_content: String,
    evicted_keywords: Vec<String>,
    evicted_memento_id: String,
    // 13 elements total
}

struct ManageCoreMemoryParams {
    // 1 element
}

struct ManageCoreMemoryResult {
    evicted: Vec<OperationResultItem>,
    updated: Vec<OperationResultItem>,
    // 6 elements total
}
```

---

## 143. Run Command & MCP

### 143.1 Run Command Params (10 elements)

```rust
struct RunCommandParams {
    target_terminal: String,
    blocking: bool,
    is_blocking: bool,
    wait_ms_before_async: u32,
    // 10 elements total
}
```

### 143.2 Run MCP Service

```rust
struct RunMcpServiceParams {
    // 3 elements - MCP service params
}
```

---

## 144. Search & Regex

```rust
struct SearchByRegexParams {
    search_directory_or_file: String,
    // 2 elements
}

struct SearchCodebaseFile {
    information_request: String,
    target_directories: Vec<String>,
    // 3 elements
}

struct FileSearchParams {
    // 2 elements - file search params
}

struct FileItem {
    // 5 elements - file item
}

struct FileSearchResult {
    // 2 elements - search result
}
```

---

## 145. Edit File Operations

```rust
struct EditFileFastApplyParams {
    code_language: String,
    // 4 elements total
}

struct EditFileRenameParams {
    // 2 elements - rename params
}

struct EditFileUpdateParams {
    replace_blocks: Vec<String>,
    // 2 elements
}

struct EditFileUpdateContent {
    // 2 elements - update content
}

struct EditFileUpdateFcParams {
    // 3 elements - FC params
}
```

---

## 146. Finish & Products

```rust
struct FinishParams {
    // 1 element
}

struct FinishData {
    // 2 elements
}

struct FinishDataProducts {
    feishu_docs: Vec<FeishuDocInfo>,
    // 10 elements total
}

struct ScheduledTaskProduct {
    // 10 elements - scheduled task product
}

struct MergePrInfo {
    // 2 elements - PR info
}

struct MergeProducts {
    source_branch: String,
    target_branch: String,
    source_branch_hash: String,
    target_branch_hash: String,
    merge_base_hash: String,
    total_diff_info: String,
    file_diff_infos: Vec<MergeFileDiffInfo>,
    spr_info: String,
    // 8 elements total
}

struct MergeTotalDiffInfo {
    conflict_count: u32,
    changed_files_count: u32,
    // 4 elements total
}

struct MergeFileDiffInfo {
    is_conflict: bool,
    // 5 elements total
}

struct ChangedSkills {
    // 1 element
}

struct SkillInfo {
    folder_name: String,
    // 4 elements total
}

struct FinishDataPreview {
    // 1 element
}

struct ChangedFiles {
    // 2 elements
}

struct ChatAssistantTaskContent {
    // 3 elements
}

struct OptionFileToolcallDataChange {
    // 6 elements
}

struct OptionFileToolcallData {
    // 2 elements
}

struct StreamWriteParams {
    // 2 elements
}
```

---

## 147. Other Params

```rust
struct GetPreviewConsoleLogsParams {
    log_level: String,
    // 2 elements
}

struct InitEnvParams {
    // 2 elements - init env params
}

struct NoNeedExecuteParams {
    // 2 elements
}

struct OpenPreviewParams {
    // 2 elements - open preview params
}

struct ResponseToUserParams {
    // 1 element
}

struct RunAgentParams {
    // 2 elements - run agent params
}

struct RunAgentResult {
    // 1 element
}

struct DeleteFileParams {
    // 1 element
}

struct CheckCommandStatusParams {
    // 5 elements - command status params
}

struct DeployToRemoteParams {
    // 1 element
}
```

---

## 148. Browser Waiting

```rust
struct BrowserWaitingForUserInteractionParams {
    // 2 elements - browser waiting params
}
```

---

## 149. LLM Provider Protocol

### 149.1 Provider & Model Configuration

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/llm/dto.rs` and `llm-client` crate

The LLM Provider Protocol abstracts multiple AI backends behind a unified interface. Trae supports Anthropic, OpenAI, AWS Bedrock, Google Gemini, DeepSeek, OpenRouter, xAI, and custom model endpoints. This layer handles request/response serialization, token counting, tool call normalization, and streaming across heterogeneous APIs.

**Context:** Provider abstraction allows Trae to switch between model vendors transparently. The `LLMClientRequestRaw` struct normalizes diverse API formats into a single internal representation. Each provider has its own response parser that maps back to unified event types.

```rust
struct LLMClientRequestRaw {
    // 12 elements - model, messages, max_tokens, tools, usage, thinking, reasoning, inferenceConfig, anthropic_version
    // Key fields: model, messages(max_tokens|max_completion_tokens), tools, usage, thinking, reasoning(inferenceConfig|effort)
    // Contains: LLMClientThinkingRaw, LLMClientReasoningRaw, LLMClientCacheControl
}

struct LLMClientMessage {
    // 6 elements - role, content, name, tool_call_id, tool_calls, reasoning_content
}

struct LLMClientToolcallItem {
    // 4 elements - id, type, function, index
}

struct LLMClientFunctionCall {
    // 2 elements - name, arguments
}

struct LLMClientMessageExtraInfo {
    // 3 elements
}

struct LLMClientToolCall {
    // 5 elements - id, type, function, index, delta
}

struct LLMClientToolCallFunction {
    // 2 elements - name, arguments
}

struct NativeAnthropicUsage {
    // 4 elements - input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens
}

struct NativeLLMUsage {
    // 3 elements - prompt_tokens, completion_tokens, total_tokens
}

struct NativeOpenRouterLLMUsage {
    // 3 elements - prompt_tokens, completion_tokens, total_tokens
}

struct Provider {
    // 10 elements
}

struct ProvidersListResponse {
    // 1 element - provider list
}

struct ModelConfigInfo {
    // 12 elements
}

struct ModelDetailInfo {
    // 17 elements - basic model metadata including provider, capabilities
}

struct ModelPromptConfig {
    // 3 elements
}

struct ModelCustomConfig {
    // 11 elements
}

struct CustomModelTypeInfo {
    // 5 elements
}

struct ModelDetail {
    // 2 elements
}

struct ModelCommonResponse {
    // 3 elements
}

struct ModelConfigMeta {
    // 9 elements
}

struct ModelEcryptedPrompt {
    // 4 elements - encrypted prompt configuration
}

struct ModelSelectionModeConfig {
    // 8 elements - model selection strategy configuration
}

struct ModelDetailConfig {
    // 12 elements
}

struct DynamicAgenticAutoModelConfig {
    // 1 element
}

struct DynamicAgenticAutoModelConfigFallbackItem {
    // 4 elements - min_score, max_score
}

struct ModelCallChainItem {
    // 4 elements
}

struct LLMCustomModelRawMessageResponse {
    // 1 element
}
```

### 149.2 OpenAI Format Compatibility

Trae uses the OpenAI-compatible chat completions format for several providers, while also supporting native Anthropic and AWS Bedrock formats.

**Source:** `llm-client` crate provider modules

```rust
struct OpenAIRequest {
    // Standard OpenAI-compatible request: model, messages, max_tokens, tools, tool_choice, stream
}

struct OpenAITool {
    // function definition with name, description, parameters
}

struct OpenAIFunction {
    // function schema
}

struct OpenAIMessage {
    // role, content, tool_calls, tool_call_id
}

struct OpenAIToolCall {
    // 3 elements - id, type, function
}

struct OpenAIFunctionCall {
    // name, arguments
}

struct OpenAIStreamChunk {
    // streaming response chunks
}

struct OpenAIStreamChoice {
    // delta, finish_reason, index
}

struct OpenAIStreamDelta {
    // role, content, tool_calls
}

struct OpenAIStreamToolCall {
    // id, type, function, index
}

struct OpenAIStreamFunction {
    // name, arguments
}

struct OpenAIContentPart {
    // text or image_url content parts
}

struct OpenAIImageUrl {
    // url and detail
}
```

### 149.3 AWS Bedrock Integration

**Source:** `aws_sdk_bedrockruntime` and custom-model-proxy-client

Trae uses AWS Bedrock Converse Stream API for AWS-based model inference. AWS SSO/OIDC authentication is used for enterprise accounts.

```rust
// AWS Bedrock Converse Stream types
// Content types: text, tool_use, tool_result, content_filtered, guardrail_intervened
// Stop reasons: end_turn, tool_use, stop_sequence, content_filtered

struct AWSClientMessageContentBlockText {
    // text content block
}

struct AWSClientMessageContentBlockImage {
    // image content with source
}

struct AWSClientMessageImageBlock {
    // format, source
}

struct AWSClientMessageImageSource {
    // s3_location or bytes
}

struct AWSClientMessageImageS3Location {
    // uri, bucket_owner
}

struct AWSInferenceConfiguration {
    // max_tokens, temperature, top_p
}

// AWS SDK error types handled:
// ConverseStreamOutputError, ConverseStreamError
// InternalServerException, ModelStreamErrorException
// ValidationException, ThrottlingException
```

### 149.4 Google Gemini Integration

**Source:** `llm-client/src/provider/gemini.rs`

Trae supports Google Gemini 3, Gemini 3.1, and Gemini 3 Flash models. Uses the native Gemini API format with function calling and thinking/thought signatures.

```rust
struct LLMClientToolCallExtraContentGoogle {
    // thought_signature - Gemini-specific thought/thinking metadata
}
```

### 149.5 Custom Model Proxy

**Source:** `custom-model-proxy-client` crate

```rust
struct LLMCustomModelRawMessageResponse {
    // 1 element - raw response wrapper
}

struct GetCustomModelTypeConfigRequest {
    // 1 element
}

struct GetCustomModelTypeConfigResponse {
    // 1 element - model type info list
}

struct PersistCustomModelMeta {
    // 1 element
}

struct CustomModel {
    // 29 elements - full custom model definition
    // Includes: model_id, model_name, provider, base_url, api_key reference,
    // capabilities, rate limits, display_name, etc.
}
```

### 149.6 Model Endpoints

Trae routes to different providers via URL patterns:

```text
Endpoint patterns discovered:
- Anthropic: /v1/messages (native anthropic versioned format)
- OpenAI compatible: /v1/chat/completions
- DeepSeek: /models/chat/completions, /v1/models (model list)
- OpenRouter: /v1/chat/completions (with provider routing)
- AWS Bedrock: https://bedrock-runtime.{region}.amazonaws.com/model/{modelId}/invoke-with-response-stream
- AWS: https://bedrock.{region}.amazonaws.com (management plane)
- xAI: OpenAI-compatible format
```

---

## 150. AI Agent Event Protocol

### 150.1 LLM Stream Events

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/llm/event.rs`

The AI Agent emits structured events during LLM interaction. These represent the full lifecycle of a streaming AI response — from queue wait through token generation to completion, including tool calls, errors, and usage metrics. Events are serialized and sent over SSE or WebSocket to the IDE.

**Context:** Each chat turn generates a sequence of events: QueueBegin → (Metadata) → (Timing) → ToolCall/Output → Error/Done → FeeUsage. The IDE uses these events to render streaming responses, update UI, and track billing.

```rust
struct MetadataEvent {
    // 5 elements - request metadata: model, provider, timestamps
}

struct OutputEvent {
    // streaming text output with index
}

struct OutputEventToolCall {
    // 4 elements - tool call within output stream
}

struct OutputEventFunctionCall {
    // 2 elements - function call within output stream
}

struct ExtraInfoEvent {
    // 6 elements - supplementary info
}

struct SuggestedQuestion {
    // 1 element
}

struct SuggestedQuestionsEvent {
    // 1 element - list of suggested questions
}

struct TokenUsageEvent {
    // 9 elements - token usage breakdown
}

struct ErrorEvent {
    // 4 elements - error code, message, type, stack
}

struct DoneEvent {
    // 1 element - completion signal
}

struct QueueBeginEvent {
    // 4 elements - queue position, timestamp, estimated wait
}

struct QueueEndEvent {
    // 3 elements - queue end info
}

struct QueueContinueEvent {
    // 1 element - queue continuation
}

struct RequestWaitInQueueEvent {
    // 9 elements - full queue wait metadata
}

struct FeeUsageEvent {
    // 8 elements - billing/fee information
}

struct NotifyUsageEvent {
    // 5 elements - notify_type, remain_usage, button
}

struct TimingCostEvent {
    // full timing breakdown: preprocess, first_token, provider_latency, postprocess
}

struct ModelCallChainItem {
    // 4 elements - model call chain trace
    // Fields: error_stage
}
```

### 150.2 Tool Call Events

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/llm/event.rs`

```rust
struct ToolCallEvent {
    // 11 elements - tool_call_id, tool_name, input, status, timing, result
    // Fields: first_data, require_local_execution
}

struct ToolCallCancelEvent {
    // cancellation metadata
}

struct TaskCreatedEvent {
    // 2 elements - task_id, parent_id
}
```

### 150.3 Agent Lifecycle Events

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/llm/event.rs`

```rust
struct ThoughtEvent {
    // 8 elements - agent reasoning steps, thoughts, observations
}

struct TurnCompletionEvent {
    // 6 elements - turn summary
}

struct MissingHistoryEvent {
    // 1 element - indicates history gap
}

struct RequiredContextEvent {
    // 1 element - missing context marker
}

struct HistoryEvent {
    // 6 elements - history_data
}

struct SubAgentCreateEvent {
    // 6 elements - sub_agent metadata, parent info
}

struct AgentIdleEvent {
    // 6 elements - check_interval_ms
}

struct AgentStatusItem {
    // 3 elements
}

struct AgentStatusEvent {
    // 1 element - list of agent status items
}

struct AgentWakeupEvent {
    // 3 elements - resource_id, resource_type
}

struct AgentResumeEvent {
    // 6 elements - resume_agent_run_id
}
```

### 150.4 Context & Summary Events

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/llm/event.rs`

```rust
struct GenerateSummaryEvent {
    // 2 elements
}

struct CompactEvent {
    // 8 elements - compact_id
}

struct CompactFinishEvent {
    // 6 elements
}

struct ObtainContextEvent {
    // 2 elements - contexts, context_params
}

struct RevokeEvent {
    // 1 element
}

struct CloudContextUsageItem {
    // 4 elements
}

struct CloudContextUsageEvent {
    // cloud context usage summary
}

struct ChatMemoryTriggerEvent {
    // 2 elements - chat_memory_scene, force_update
}
```

### 150.5 Filter & Cache Events

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/llm/event.rs`

```rust
struct ContentFilterEvent {
    // 4 elements - filter type, reason, content, action
}

struct ToolCacheDataEvent {
    // 2 elements - groups
}

struct ToolCacheGroup {
    // 3 elements - group_name
}

struct ToolCacheItem {
    // 3 elements
}

struct ModelConfigEvent {
    // model configuration update event
}

struct LLMContentFilterWarningEvent {
    // 4 elements - hit_rule_id, hit_rule_name, execute_point
}
```

### 150.6 Platform Timing Details

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/llm/event.rs`

```rust
struct ServerPreprocessingDetail {
    // check_risk, build_llm_prompt
}

struct ServerPostprocessingDetail {
    // post_security_check
}

struct PlatformTimingDetail {
    // middleware_processing_time, queue_timing, postprocess_timing
    // Includes: preprocessing_detail, agent_preprocess_timing,
    // agent_postprocess_timing, agent_middleware_timing,
    // gateway_preprocess_timing, gateway_server_processing_time,
    // platform_detail, post_processing_detail,
    // platform_first_token_timing, server_processing_time,
    // first_sse_event_time, is_retry,
    // account_type, account_name, provider_model_name
}
```

### 150.7 SSE Event Types

The SSE stream uses the following named events to communicate AI progress to the client:

```text
SSE Event Names:
  sse.open      - Stream opened
  sse.delta     - Content delta (text or partially streamed tool calls)
  sse.end       - Stream complete (includes final usage data)
  sse.error     - Error occurred during streaming
  sse.cancel    - User or system cancelled the stream
  sse.heartbeat - Keepalive to detect stale connections
  sse.retry     - Retry notification after transient failure

Server-Side Processing Phases (TimingTrack for latency analysis):
  rs_01_chat_begin              - Request received
  rs_02_get_session             - Session lookup
  rs_03_get_history_messages    - History loading
  rs_04_create_message          - Message DB record created
  rs_05_create_snapshot         - Pre-chat snapshot taken
  rs_06_resolve_*               - Context resolution (model, diagnostics, editor, terminal, rules, lint, web search, browser selection, file diffs, slash commands)
  rs_07_create_task             - AI task created
  rs_08_create_turn             - Conversation turn opened
  rs_09_process_task            - Task processing begins
  rs_10_prepare_guideline_context - Guidelines loaded
  rs_11_ckg_retrieve_*          - CKG retrieval and indexing
  rs_12_list_*_tools            - Available tools enumerated
  rs_13_render_user_prompt      - Prompt rendered
  rs_16_llm_generate_plain_item - LLM inference called
  rs_18_llm_response_first_token - First token received from LLM
  rs_19_llm_response_done       - LLM response complete
  svr_01_queue_timing           - Queue wait time
  svr_02_preprocess_timing      - Preprocessing time
  svr_04_postprocess_timing     - Postprocessing time
  svr_10_first_sse_event_timing - Time to first SSE event
```

---

## 151. Hub Bridge Session Protocol

### 151.1 Remote Session Data

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/lite/typing.rs` and `handoff` module

The Hub Bridge synchronizes session state between the local IDE and remote cloud servers. This enables seamless handoff between devices and cloud-based AI processing. Sessions carry metadata about project context, VM sandboxes, and version control state.

**Context:** Sessions are created locally and synced to the Hub via the Frontier WebSocket protocol. Remote sessions mirror local state with additional cloud-specific fields (sandbox allocation, snapshot URLs, handoff tokens). The Hub Bridge also handles CLI-to-IDE session forwarding.

```rust
struct RemoteChatSessionData {
    // 23 elements - session_id, conversation_id, project_id, VM info,
    // sandbox allocation (RemoteSandboxInfo), history file URLs, handoff targets, timestamps
    // Includes: version_snapshot (VersionSnapshotInfo), pre_termination, handoff (HandoffInfo), auto_create_project
}

struct RemoteChatMessageData {
    // 38 elements - message_id, session_id, role, content, model,
    // tool_calls, attachments, timestamps, revert info
    // Includes: unrevertible_reason
}
```

### 151.2 Session Lifecycle Management

**Source:** Session handler modules

```rust
struct CreateChatSessionRequest {
    // 10 elements - main_folder, environment_id, initial_message, project_extra_info
}

struct CreateChatSessionData {
    // 5 elements - project_extra_info, auto_create_project, create_reason
}

struct CreateChatSessionResponse {
    // 4 elements - session_id, conversation_id, created
}

struct RemoteGetChatSessionResponse {
    // 3 elements
}

struct CommitSessionResponse {
    // 2 elements - history_file_uri, version_snapshot
}

struct FreezeChatSessionResponse {
    // 2 elements
}

struct ThawChatSessionData {
    // 1 element
}

struct ThawChatSessionResponse {
    // 3 elements - restored_status
}

struct GetHistoryDownloadURLRequest {}
struct GetHistoryDownloadURLData {}
struct GetHistoryDownloadURLResponse {}
struct GetHistoryUploadURLRequest {}
struct GetHistoryUploadURLData {}
struct GetHistoryUploadURLResponse {}
struct CheckHistoryExistsRequest { exists: bool }
struct CheckHistoryExistsData {}
struct CheckHistoryExistsResponse {}
struct GetMessagesRequest {}
struct RemoteGetMessagesData {}
struct RemoteGetMessagesResponse {}
struct BatchSyncHistoryRequest { visible_message_ids: Vec<id> }
struct BatchSyncHistoryResponse {}

struct ChatSessionListItem {
    // 14 elements - session metadata for list display
    // Fields: fs_server_url, vm_host_dir_mapping_list
}
```

### 151.3 Client & User Metadata

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/lite/typing.rs`

```rust
struct ClientInfo {
    // 38 elements - icube_language, icube_ai_language, request_traffic_type,
    // client_type, platform, version, extensions, OEM info
    // Extensive client identification for routing, analytics, and feature gating
}

struct UserInfo {
    // 10 elements - user_id, display_name, avatar, email, is_internal,
    // loginScope, enterprise_info
    // Fields: is_internal (ByteDance internal flag), loginScope, enterprise_info (EnterpriseInfo)
}

struct EnterpriseInfo {
    // 1 element
}

struct TerminalInfo {
    // 3 elements - maxTerminalCount, availableTerminals, defaultShellType
}

struct TerminalInfoItem {
    // 6 elements
}

struct ErrorResponse {
    // 4 elements - error_code, message, details
}
```

### 151.4 Handoff Protocol

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/handoff` module

```rust
struct HandoffDownSessionRequest {}
struct HandoffDownSessionData {
    // messages_restored, messages_archived, warnings
}

struct HandoffUpSessionRequest {}
struct HandoffUpSessionData {
    // lru, lfu, linear_decay, exponential_decay, hybrid_half_life, w_tinylfu
}

struct StateNotificationRequest {}
struct StateNotificationResponse {}
struct CancelResolveConflictsRequest {}
struct CancelResolveConflictsData {}

struct GetReturnToLocalSessionGitContextReq {}
struct GetReturnToLocalSessionGitContextResp {}

enum ReturnToLocalJwtStrategy {
    // Reuse, External
}

enum ReturnToLocalSessionSource {}
enum ReturnToLocalSessionTarget {}
```

### 151.5 Hub Bridge WebSocket Messages

**Source:** `prost` protocol buffer definitions

```rust
struct WsMessage {
    // 4 elements - message type, payload, metadata
}

struct WsProtoConfirmWsMessage {
    // 2 elements
}

struct RegisterCliResponse {
    // 1 element
}

struct HubRemoteConfig {
    // 17 elements - frontier_app_id, frontier_product_id, frontierUrl,
    // maxWsReconnectAttempts, wsReconnectDelaySecs, pollIntervalMs,
    // flushIntervalMs, flushCountThreshold, wsMsgSizeThreshold,
    // pushSync, pushConversationSize, pushMessageSize,
    // syncSessionChunkSize, maxSentMessageCache, cli, seq_num
}

// WebSocket message types for session sync:
// WsProtoCLI, WsProtoCliPushConversationsDelete, WsProtoCliPushDeleteMessages
// WsProtoSessionCreated, WsProtoSessionUpdated, WsProtoSessionDeleted
// WsProtoCliPushMessageDelete, WsProtoCliPushMessageRevert
// CliRequest, CliResponse, CreateTask, DeleteTask, BatchInsertEvents
```

---

## 152. Agent Context & @mention Protocol

### 152.1 AgentContext

**Source:** `apps/icube_server_rs/modules/ai-agent/src/handler/chat/query_parser.rs` and context resolver modules

The AgentContext captures the full IDE state for AI context building. It includes workspace structure, open files, terminal output, problem markers, lint errors, rule files, web search results, and user interaction history. This rich context enables the AI to understand the user's development environment without explicit description.

**Context:** Before each AI turn, Trae resolves the current context into a structured AgentContext. Context resolvers gather data from 20+ sources (current editor, terminal, problems, lint errors, rules, docs, web search, browser selection, file diffs, slash commands, etc.). The resolved context is rendered into the LLM prompt via a complex rendering pipeline.

```rust
struct AgentContext {
    // 43 elements - comprehensive IDE state snapshot for AI context building
    // Categories:
    //   Editor state: current editors, selections, visible ranges
    //   Terminal: active terminals, output buffers, shell type
    //   Problems: lint errors, build errors, warnings
    //   Rules: active rule files, custom instructions
    //   Docs: open documentation pages
    //   Web: browser elements, web search results
    //   History: recent file changes, chat history context
    //   User input: current prompt, @mentions, slash commands
    //   Review markers: code review comments, inline suggestions
}

struct WorkspaceContext {
    // 5 elements - platform (local/remote/cloud), workspace folders
}

struct ModelSmartSelection {
    // 3 elements
}

struct ModelSmartSelectionMeta {
    // 2 elements
}
```

### 152.2 @mention System

The `#` (hash) mention system allows users to reference specific artifacts in their prompts. Each mention type has a dedicated resolver and context structure.

**Source:** `query_parser.rs`

```rust
struct MentionContext {
    // 22 elements - only_mention flag + all hash reference types:
    // hash_symbols, hash_folders, hash_docs, hash_web_elements,
    // hash_logs, hash_figma, hash_lint_error_flag, hash_rule_files,
    // hash_problem_items, hash_problem_files, hash_attachments,
    // hash_images, hash_comment_data_sheets, hash_comment_data_texts,
    // hash_comment_data_markdowns, hash_agent_review_marker
}

struct MentionHashSymbol {
    // 6 elements - symbol reference (function, class, variable)
}

struct MentionHashFolders {
    // 2 elements - folder references
}

struct MentionHashFile {
    // 2 elements - file references (with path)
}

struct MentionHashRuleFile {
    // 7 elements - relatePath, rule file references
}

struct MentionHashDoc {
    // 7 elements - documentation references
}

struct MentionHashWeb {
    // 2 elements - web URL references
}

struct MentionHashWebElement {
    // 7 elements - relative_path, web element references
}

struct MentionHashLog {
    // 4 elements - terminal log references
}

struct MentionFigmaFile {}
struct MentionFigma {}

struct MentionHashProblemItem {
    // 10 elements - problem/lint references
}

struct MentionHashProblemFile {
    // 4 elements - problem file references
}

struct SlashCommandInfo {
    // 5 elements - parameter_values, slash command metadata
}

struct MentionAttachment {}

struct MentionHashImage {
    // 2 elements - image attachment
}

struct MentionCommentSheetSelection {
    // 2 elements - sheet data selection
}

struct MentionCommentDataSheet {
    // 4 elements - spreadsheet/table comment data
}

struct MentionCommentDataTextPage {}
struct MentionCommentDataTextSelection {}
struct MentionCommentDataText {
    // 3 elements - text comment data
}

struct MentionCommentDataMarkdownSelection {}
struct MentionCommentDataMarkdown {
    // 7 elements - full_content, markdown comment data
    // Fields: review_and_resolve (review|resolve)
}

struct MentionAgentReviewMarker {
    // 3 elements - AI review marker references
}
```

### 152.3 Editor & Terminal Context

**Source:** IDE context resolvers

```rust
struct TerminalContextVariable {
    // 5 elements - terminal state: working directory, command history, output
}

struct FileIdentInfo {
    // 2 elements
}

struct Language {
    // 2 elements - language_id
}

struct Position {
    // 2 elements - line, character
}

struct Range {
    // 4 elements - start_line, start_char, end_line, end_char
}

struct Selection {
    // 7 elements - text selection metadata
}

struct Document {
    // 10 elements - file document metadata
}

struct VSTextDocument {
    // 7 elements - VS Code specific text document
}

struct TextDocument {
    // 6 elements - generic text document
}

struct DocumentFromCommand {
    // 10 elements - command-generated document
}

struct EditorRange {
    // 4 elements - startLineNumber, startColumn, endLineNumber, endColumn
}

struct IFunctionsRange {
    // 8 elements - function range in editor
}

struct ForceToolCallInput {
    // 6 elements - node_type, start_index, end_index
}
```

---

## 153. CKG Embedding & Retrieval Protocol

### 153.1 Code Knowledge Graph (CKG) Methods

**Source:** `volo-gen` generated protobuf code, `protocol.CodeKG` service

The Code Knowledge Graph provides semantic code understanding through embedding-based retrieval. CKG powers features like "Find Relevant Code", intelligent code navigation, and context-aware suggestions. It uses gRPC (via Volo framework) with both IPC and TCP transport modes.

**Context:** CKG indexes code into a vector database with embeddings. Retrieval supports multiple recall strategies: user-specified, embedding similarity, user action trace, and git relevance. The CKG server runs as a separate process (ckg_server binary, ~44MB) and communicates via gRPC over the `protocol.CodeKG` service.

```text
CKG gRPC Methods (protocol.CodeKG/ prefix, 35 total):

  Ping                                    - Health check
  SetUp                                   - Initialize CKG service
  SetPrivacyMode                          - Toggle privacy/anonymization
  Init                                    - Initialize project index
  InitVirtualProjects                     - Virtual project indexing
  DocumentCreate                          - Index new document
  DocumentChange                          - Re-index changed document
  DocumentDelete                          - Remove from index
  DocumentSelect                          - Select document for indexing
  CursorMove                              - Update cursor position context
  GetBuildStatus                          - Query index build status
  GetDocumentsIndexStatus                 - Query specific document status
  CancelIndex                             - Cancel indexing operation
  DeleteIndex                             - Delete project index
  RetrieveCodeChunk                       - Search code by embedding similarity
  RetrieveRelation                        - Find code relations/dependencies
  RetrieveEntity                          - Find code entities (classes, functions)
  RetrieveRelevantSnippet                 - Semantic snippet search
  RerankSnippet                           - Re-rank search results for relevance
  RefreshToken                            - Refresh CKG auth token
  IsVersionMatched                        - Check CKG version compatibility
  ImportAnalysis                          - Import code analysis results
  FilesImportAnalysis                     - Batch file analysis import
  SearchCKGDB                             - Direct database search
  IsCKGEnabledForNonWorkspaceScenario     - Feature availability check
  GetFileOutline                          - Get file structure outline
  EmbeddingSearch                         - Vector embedding search
  RetrieveDocChunk                        - Retrieve documentation chunk
  CfsRead                                 - Read from content-addressable store
  CfsListDir                              - List directory in content-addressable store
  CfsResolve                              - Resolve content-addressable path
```

### 153.2 Retrieval Strategies

```text
Recall Types:
  RECALL_TYPE_USER_SPECIFIED                = User-specified explicit references
  RECALL_TYPE_EMBEDDING                     = Vector embedding similarity search
  RECALL_TYPE_RELATION_BY_USER_ACTION_TRACE = User navigation/action pattern
  RECALL_TYPE_RELATION_BY_GIT_RELEVANCE     = Git change relevance

Snippet Types:
  SNIPPET_TYPE_CODE                         = Code snippet
  SNIPPET_TYPE_FOLDER_TREE                  = Folder/directory structure
  SNIPPET_TYPE_FILE                         = Full file content
```

### 153.3 CKG Data Structures

**Source:** `volo-gen` generated protobuf types

```rust
struct EmbeddingVariable {
    // 5 elements - vector embedding with metadata (code snippet -> vector representation)
}

struct EmbeddingChunkVariable {
    // 5 elements - chunked embedding for large documents
}

struct CodeChunkVariable {
    // code chunk with range context
}

struct DocChunk {
    // documentation chunk
}

struct CodeVariable {
    // code entity with location info
}

struct FileVariable {
    // file metadata
}

struct ClassVariable {
    // class/type definition
}

struct MethodVariable {
    // method/function definition
}

struct FolderVariable {
    // folder/directory reference
}

struct TextVariable {
    // text content for embedding
}

struct SelectedMethodInfo {
    // method selection context
}

struct Member {
    // struct/class member
}

struct RefClassInfo {
    // referenced class info
}

struct RefTypeInfo {
    // reference type info
}

struct FileRule {
    // processed_content, file_rules
}

struct BrowserCodeVariable {
    // source_code
}

struct LogMessageVariable {
    // log entry
}

struct Entity {}
struct Reference {}
struct Snippet {}
struct Range {
    // code location range
}
struct Error {}
struct Empty {}
struct UsefulFileInfo {}

struct DocumentBuildStatus {
    // 3 elements
}

struct DocumentIndexStatus {
    // 3 elements
}

struct SetUpResponse {}
struct InitResponse {}
struct InitVirtualProjectsResponse {}
struct DeleteIndexResponse {}
struct CancelIndexResponse {}
struct RefreshTokenResponse {}
struct SetPrivacyModeResponse {}
struct GetFileOutlineResponse {}
struct IsCkgEnabledForNonWorkspaceScenarioResponse {}
struct FileTopLevelVariable {}
struct ClassTopLevelVariable {}

// CKG Slardar event payload types:
// CkgJrpcCallFailedPayload, CkgRetrievalSlardarEventParams
// CKGEventPayload with fields: ckg_err_code, ckg_action_code, ks_action_code
// ckg_method includes: documentAction, retrieveEntity, retrieveRelation,
// getBuildStatus, cancelIndex, deleteIndex, setUp
```

---

## 154. Lite VM Protocol

### 154.1 VM Lifecycle Management

**Source:** `apps/icube_server_rs/modules/ai-agent/src/domain/lite/typing.rs`

The Lite VM provides sandboxed execution environments for AI agent operations. VMs are created per-chat-session and support file system operations, command execution, and browser automation. The VM lifecycle includes creation, initialization (with progress tracking), operation, and cleanup.

**Context:** Lite VMs are allocated on remote hosts and accessed via WebSocket/VNC. Each VM has a sandboxed file system isolated from the host. The agent runs commands inside the VM, reads/writes files, and uses a browser running inside the VM for web automation. VM resources are managed via the remote sandbox infrastructure.

```rust
struct CreateProjectRequest {}
struct ListProjectsRequest {}
struct ListProjectsData {
    // project list
}
struct GetProjectRequest {}
struct GetProjectByFolderRequest {}
struct UpdateProjectRequest {}
struct DeleteProjectRequest {}

struct GetDiffViewRequest {}
struct DiffViewFileDiffInfo {}
struct DiffViewChangedFile {
    // insert/delete line counts
}
struct GetDiffViewData {
    // total_insert_line_count, total_delete_line_count
}

struct GetSessionProductsRequest {}
struct GetSessionProductsData {}
struct GetSessionProductsDataTool {
    // hostStatusData
}

struct CommitChatSessionRequest {}
struct FreezeChatSessionRequest {}
struct StopChatSessionRequest {}
struct DeleteChatSessionRequest {}
struct GetMessagesRequest {}
struct GetMessagesData {}
struct GetMessageByIdRequest {}
struct GetMessageByIdData {}

struct SendMessageRequest {
    // 10 elements - message content, model_config, attachments
}

struct SendMessageData {
    // message confirmation
}

struct SubscribeEventsRequest {}
struct SubscribeEventsResponse {}

struct ListChatSessionsRequest {
    // 6 elements - page_token, repo
}

struct ListChatSessionsData {
    // 3 elements - next_page_token
}

struct GetChatSessionRequest {
    // 1 element
}

struct TargetSandboxInfo {
    // cluster_name, pod_name
}

struct InitialMessage {}
```

### 154.2 VM Init & Status Events

```rust
struct VmInitProgressPayload {
    // stage, stage_message, stage_percentage
}

struct StatusChangedPayload {
    // old_status, new_status
}

struct VmOperateRequest {}
struct VmOperateResponseData {}
struct VmOperateResponse {}

// Lite VM State Events
enum StateEvent {
    session_created,
    session_updated,
    session_deleted,
    project_created,
    project_updated,
    project_deleted,
    message_deleted,
    message_reverted,
    scheduled_task_created,
    scheduled_task_updated,
    scheduled_task_deleted,
    scheduled_task_triggered,
    scheduled_task_execution_completed,
    scheduled_task_disabled,
}

// Pending task payload for Lite VM operations
enum PendingTaskPayload {
    CreateSession(SendMessageData),
    SendMessage(SendMessageData),
}
```

---

## 155. Tool Calling Protocol

### 155.1 LLM Client Tool Call System

**Source:** `llm-client` crate and tool handler modules

The Tool Calling Protocol normalizes tool calls across different AI providers. Each provider has its own tool call format (Anthropic: tool_use content blocks, OpenAI: tool_calls, AWS Bedrock: toolUse content blocks, Gemini: functionCall). The LLM client layer converts all formats to unified internal structures.

**Context:** Tools are defined using the OpenAI-compatible function definition format (name, description, parameters schema). The LLM client formats tools according to each provider's requirements. Tool call responses are parsed from provider-specific formats and normalized for the agent system.

```rust
struct LLMClientToolCall {
    // 5 elements - id, type, function, index, delta
    // Used for streaming tool call chunks (delta contains partial JSON)
}

struct LLMClientToolCallFunction {
    // 2 elements - name, arguments
}

struct LLMClientToolCallExtraContent {
    // additional content for tool calls
}

struct LLMClientToolCallExtraContentGoogle {
    // thought_signature - Gemini-specific
    // Gemini's thinking/chain-of-thought metadata attached to tool calls
}

struct RawLLMResponseToolCall {
    // 3 elements
}

struct RawLLMResponse {
    // 1 element
}

struct LLMClientTool {
    // tool definition
}

struct LLMClientToolFunction {
    // tool function signature
}
```

### 155.2 Provider-Specific Tool Calling

```rust
// Anthropic format
struct AnthropicTool {
    // name, description, input_schema (JSON Schema)
}

// OpenAI format
struct OpenAITool {
    // type, function (OpenAIToolFunction)
}

struct OpenAIToolFunction {
    // name, description, parameters (JSON Schema)
}

// AWS Bedrock format: tool_use content blocks
// Fields: toolUseId, name, input (JSON)

// Google Gemini format: functionCall content blocks
// Fields: name, args (JSON)

// Native Finish Reasons:
// end_turn, tool_use, stop_sequence, content_filtered
```

### 155.3 Tool Choice & Forcing

```rust
struct ToolChoiceFullMode {}
struct ToolChoiceToolItem {}

struct ForceToolCallInput {
    // 6 elements - node_type, start_index, end_index
    // Forces the LLM to call a specific tool based on context matching
}
```

### 155.4 Tool Call Metrics & Telemetry

**Source:** Slardar event parameters

```rust
struct AgentToolcallManualConfirmTeaParams {
    // toolcall_params, auto_run, auto_run_mode
}

struct PlanToolTokenUsageParams {
    // tool_calls_count, token usage metrics
    // Includes: real_output_token, real_reason_token, token_output_rate
}

struct AgentToolCallTeaParams {
    // run_duration, mcp_name, wait_duration, is_command_edited, is_block,
    // diff_insert_line_count, diff_delete_line_count, filename_extensions,
    // solo_chat_mode, has_virtual_paths, sandbox_awareness_enabled
}
```

### 155.5 Tool Call Cache System

```rust
struct ToolCacheDataEvent {
    // 2 elements - groups
}

struct ToolCacheGroup {
    // 3 elements - group_name
}

struct ToolCacheItem {
    // 3 elements
}

struct ToolCacheInfo {
    // tool_use_cache configuration for Anthropic prompt caching
}
```

---

## 156. Dynamic Config & A/B Testing Protocol

### 156.1 Application-Level Configuration

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/adapter/ide_command/dynamic_config.rs`

Trae uses a dynamic configuration system that supports real-time feature flag updates without restarting the IDE. Configuration is fetched from a remote server and cached locally. A/B testing is supported through experiment groups with configurable TTL.

**Context:** The `DynamicConfigICubeAppData` struct is the root configuration object that contains all feature flags and behavior-modifying knobs. Each subsystem has its own config struct nested within it. Config is fetched asynchronously via `DynamicConfigGeneratedFetch` and cached with configurable TTL. A/B experiments use function-based config fetching by name.

```rust
struct DynamicConfigICubeAppData {
    // Root configuration with 35+ subsystems:
    // feature_gates - Feature flag system for staged rollouts
    // snapshot_v2, snapshot_clean_up, snapshot_ignore - Snapshot system
    // auto_accept - Auto-accept code changes
    // agentic_flow_config - Agent flow control (max turns, etc.)
    // agentic_auto_model_config - Automatic model selection
    // agentic_summary_config - Context summarization
    // ai_features - AI behavior parameters (mcpToolLimit, etc.)
    // context_usage_chunk - Context window chunking
    // http_timeout_config - SSE retry/backoff config
    // solo_builder_config_name, error_log_report
    // agent_v3 - Agent V3 multi-agent system
    // evaluation_config, auto_run_config
    // sqlite_optimization - Database tuning
    // finish_collect_strategy
    // custom_model_fallback_config - Fallback behavior for custom models
    // mb_config, builtin_skill_mapping
    // chat_memory_with_history, chat_skill_recommend
    // virtual_path, hub_config, solo_vm_config
    // aigc_tag_config, prompt_meta_filter_config
    // skill_as_agent, generate_image
    // toolcall_output_persistence_visible
    // toolcall_output_persistence_default_enabled
}
```

### 156.2 AI Features Configuration

**Source:** Dynamic config AI features sub-system

```rust
struct DynamicConfigAiFeatures {
    // mcp_tool_limit (default: 40), mcp_token_limit (default: 8000),
    // mcp_token_limit_m8, mcp_tool_hard_cap
    // custom_prompt_token_limit, custom_prompt_token_limit_m8
    // disable_prompt_selected_code
    // fix_edit_file_size_limit
    // chat_message_query_limit, history_query_limit
    // server_history_cache_limit, server_history_sync_timeout_secs
    // enable_llm_utils_cloud
    // raw_rules_max_chars, snippet_content_max_char_count, category_content_max_char_count
    // tool_confirm_timeout_secs
    // schedule_task_max_count, schedule_min_interval_minutes

    // V3 Agent knobs:
    // solo_builder_config_name, solo_coder_disable_sub_agents
    // solo_coder_disable_plan_mode, solo_coder_cumulative_compaction_strategy
    // v3_parallel_agents_disabled, v3_max_concurrent_tasks
    // v3_concurrent_task_timeout
}
```

### 156.3 HTTP Timeout & Retry Configuration

```rust
struct HTTPTimeoutConfig {
    // http_response_header_timeout
    // http_sse_stream_timeout (noEventTimeout: 30000ms)
    // http_upstream_call_timeout
    // http_sse_no_event_timeout
    // max_retry_count (3), retry_timeout (1000ms),
    // retry_http_code [502, 503, 504]
    // internal_network_timeout
}
```

### 156.4 Context Usage Chunking

```rust
struct DynamicConfigContextUsageChunk {
    // max_items, max_bytes
}
```

### 156.5 A/B Testing Configuration

```rust
// Dynamic configuration fetchers by name:
// get_abtest_shallow_memento_with_fetch
// get_abtest_core_memory_with_fetch
// get_abtest_trae_knowledges_skill_with_fetch
// get_abtest_trae_code_review_skill_with_fetch
// get_abtest_trae_security_review_skill_with_fetch
// get_abtest_trae_debugger_skill_with_fetch
// get_abtest_trae_ui_code_design_skill_with_fetch

// Each uses DynamicConfigGeneratedFetch pattern:
// - Refreshes cache on request
// - Uses configurable TTL
// - Returns cached value or fetched value
// - Supports config_name and function parameter

struct ABTestTraeCodeReviewSkill {
    // Code review skill A/B test config
}

struct ABTestTraeSecurityReviewSkill {
    // Security review skill A/B test config
}

struct ABTestTraeUiCodeDesignSkill {
    // UI code design skill A/B test config
}

struct ABTestTraeKnowledgesSkill {
    // Knowledges skill A/B test config
}
```

### 156.6 Agent Flow & Behavior Configuration

```rust
struct DynamicAgenticFlowConfig {}

struct DynamicAgenticFlowConfigMatch {
    // max_plan_turns, max_left_turns
    // enable_user_prompt_cache, toolcall_cache_limit
}

struct DymanicAgenticSummaryConfig {
    // summary_message_token_limit
    // kept_history_token_limit, kept_history_message_limit
    // minimum_current_turn_token_usage
    // multimodal_summary_look_back_count
}

struct DynamicConfigAgentV3 {
    // 1 element - Agent V3 system flag
}

struct ChatMemoryWithHistoryConfig {}
struct ChatSkillRecommendConfig {}
struct VirtualPathConfig {}

struct SoloVMConfig {
    // fetch_max_connections
}

struct PromptMetaFilterConfig {
    // disable_prompt_fetching, function_filters
}

struct SnapshotV2 {
    // enable_v2, force_double_write
}
struct SnapshotCleanUp {}
struct SnapshotIgnore {
    // ignore_rule_list
}

struct CustomModelFallbackConfig {
    // poll_interval, flush_interval, max_send_retries
}
```

### 156.7 Model Extra Configuration (142 Parameters)

The AI Features system includes an extensive 142-parameter model extra configuration that controls every aspect of AI agent behavior:

```rust
struct ModelExtraConfig {
    // 142 elements - comprehensive AI behavior tuning knobs
    //
    // Category: Token & Context Limits
    //   v2_kept_history_token_limit, v2_kept_history_message_count_limit
    //   v2_current_turn_min_token_quota
    //   v2_multimodal_summary_look_back_count, v2_multimodal_per_message_token_limit
    //   v2_summary_message_token_limit
    //
    // Category: Rendering & View Files
    //   v2_render_by_dsl, v2_render_by_dsl_with_one_function
    //   v2_view_file_auto_expand, v2_view_file_truncated_and_hint
    //   v2_view_file_max_file_size_kb, v2_view_file_enable_outline
    //   v2_view_file_max_char_size
    //
    // Category: Search & Tool Calls
    //   v2_search_codebase_result_max_token
    //   v2_detect_hash_mention_file_linter_error
    //   v2_edit_file_linter_error, v2_read_old_linter_error_enabled
    //   run_command_output_char_count, run_command_max_blocking_ms
    //   run_command_default_timeout_ms
    //   max_duplicated_tool_calls, stop_duplicated_tool_calls
    //
    // Category: Native Function Call (NFC)
    //   native_function_call, nfc_force_use_edit_file_update
    //   parallel_tool_calling, nfc_use_original_tool_call_id
    //
    // Category: Compression & Memory
    //   v2_max_mode_enabled, v2_post_compress_enabled
    //   shallow_memento_disabled, core_memory_block_rough_max_token
    //   history_adapter_strategy
    //
    // Category: Agent V3
    //   v3_solo_coder_disable_sub_agents, v3_solo_coder_disable_plan_mode
    //   v3_solo_coder_cumulative_compaction_strategy
    //   v3_passive_compaction_user_perceptible
    //   v3_compaction_token_limit_ratio, v3_async_compaction_token_limit_ratio
    //   v3_micro_compact_trigger_token_ratio
    //   v3_max_concurrent_tasks, v3_concurrent_task_timeout
    //   v3_parallel_agents_disabled
    //
    // Category: File Operations
    //   v3_read_max_content_byte_size, v3_read_enable_truncation
    //   v3_grep_max_result_chars, v3_glob_enable_ripgrep
    //   replace_edit_tools_by_apply_patch
    //   v3_enable_multi_edit_tool
    //
    // Category: Cloud & Browser
    //   cloud_agent_snippet_content_max_char_count
    //   enable_browser_screenshot_auto_read
    //
    // Category: Read Dedup
    //   v3_file_read_state_cache_enabled, v3_read_dedup_enabled
    //   enable_read_enoent_path_suggestion
    //
    // Category: Core Memory
    //   enable_core_memory, disable_exit_plan_mode_tool
    //
    // Category: Tool Choice
    //   enable_nfc_prefill_agent_name
    //   v3_optimize_tool_choice_strategy
    //   v3_rename_custom_tool_apply_patch_name
}
```

---

## 157. Dynamic Configuration Loading

### 157.1 Configuration Fetch System

**Source:** `dynamic_config.rs`

Configuration is loaded dynamically from remote servers with cache refresh. The system supports A/B testing by function name.

```rust
// DynamicConfigGeneratedFetch pattern:
//   - Fetch by function name (get_abtest_*, get_dynamic_config_with_fetch)
//   - Cache with configurable TTL
//   - Async refresh on cache miss
//   - Fallback to default values on network failure

struct DynamicConfigData {
    // iCubeApp struct containing all subsystem configs
}

// TTL (Time-To-Live) values are configurable per-config:
//   - Standard config: 5 minutes
//   - A/B test config: 10 minutes
//   - Feature gates: 2 minutes (for fast rollouts)

struct DynamicConfigGenerateImage {
    // enable_stream
}

struct DynamicConfigLintError {
    // advanced_fix_once_after_finish
}

struct DynamicConfigTodoList {}

struct DynamicConfigDynamicUI {}
```

---

## 158. Additional Protocol Artifacts

### 158.1 Slardar Event Payloads (Telemetry)

**Source:** Slardar event definitions (~120+ metric events)

Trae tracks detailed telemetry through Slardar (internal metrics system). Events span the full AI agent lifecycle:

```text
Agent Events:
  IcubeAiAgentWsHandler, IcubeAiAgentApplyInvoke, IcubeAiAgentApplySearchReplace
  IcubeAiAgentTaskProposalFinish, IcubeAiAgentTaskProposalFirstToken
  IcubeAiAgentTaskProposalFinalToken, IcubeAiAgentTaskProposalIntent
  IcubeAiAgentTaskPlanAll, IcubeAiAgentTaskPlanSubAgents
  IcubeAiAgentTaskPlanFinish, IcubeAiAgentTaskPlanRetry
  IcubeAiAgentToolcall, IcubeAiAgentToolcallCustomEvent, IcubeAiAgentToolcallMcp

LLM Events:
  IcubeAiAgentModelLLMRenderTokenUsage, IcubeAiAgentModelLLMStream
  IcubeAiAgentModelLLMStreamFirstToken, IcubeAiCustomModelRequestBuilder
  IcubeAiAgentModelSync, IcubeAiAgentModelParse
  IcubeAiAgentModelDbCacheSave, IcubeAiAgentModelDbCacheMiss
  IcubeAiAgentModelListByFunction, IcubeAiAgentModelFallback

CKG Events:
  IcubeAiAgentCkgRetrieval, IcubeAiCkgRequest, IcubeAiCkgResolver
  IcubeAiAgentDocsetRetrieve, IcubeAiAgentCkgJrpcCallFailed

Agent V3 Events:
  IcubeAiAgentV3ExecuteMultiAgentTask, IcubeAiAgentV3ExecuteWorkflow
  IcubeAiAgentV3CreateAgent, IcubeAiAgentV3CreateInitialTaskHandle
  IcubeAiAgentV3HilWaitForToolConfirmation

Snapshot Events:
  IcubeAiAgentCreateSnapshot, IcubeAiAgentUpdateSnapshot
  IcubeAiAgentListSnapshot, IcubeAiAgentRevertSnapshot
  IcubeAiAgentStorageSnapshot, IcubeAiAgentDoubleWriteSnapshot

Model Events:
  IcubeAiAgentAutoModelSelectionFetchRemote, IcubeAiAgentAutoModelSelectionAwait
  IcubeAiAgentBootConfigAwait

Context/Memory:
  IcubeAiCoreMemOp, IcubeAiCoreMemEvict, IcubeAiCmForget, IcubeAiCmHit
  IcubeAiAgentPreTermination, PreTerminationStarted, PreTerminationCompleted

Misc:
  IcubeAiAgentWebSearch, IcubeAiAgentCrawlerContent, IcubeAiAgentLintErrorsContextResolved
  IcubeAiAgentCheckDiagnosis, IcubeAiAgentHistoryV2Save, IcubeAiAgentHistoryV2Load
  IcubeAiAgentReadDedup, IcubeAiAgentGenerateImage, IcubeAiAgentLiteVmStartup
  IcubeAiAgentScheduleExecution, IcubeAiAgentScheduleConfig
```

### 158.2 Authentication Artifacts

**Source:** AWS SDK SSO, OAuth2 flows

```rust
// AWS SSO/OIDC authentication types:
// SsoCredentialsProvider, SsoProviderConfig
// SsoTokenProvider, SsoTokenProviderError
// TokenProviderConfig (aws-config crate)
//
// Error types from AWS auth:
// BadExpirationTimeFromSsoOidc, ExpiredToken
// FailedToFormatDateTime, NoHomeDirectory
// CredentialsNotLoaded, ProviderTimedOut
// InvalidConfiguration, ProviderError, TokenNotLoaded
//
// IMDS (Instance Metadata Service) types:
// ImdsError, TtlToken, ImdsCommunicationError
// FailedToLoadToken, UnexpectedTokenError
//
// Credential provider chain types:
// HttpProviderAuth, CredentialsError
// ProfileDidNotContainCredentials, CredentialLoop
// InvalidCredentialSource, UnknownProvider
// FeatureNotEnabled, MissingSsoSession
// InvalidSsoConfig, NoProfilesDefined
```

### 158.3 Data Serialization Artifacts

**Source:** serde/sqlx crate types

```rust
// SQLite configuration artifacts discovered:
// PRAGMA key = (SQLCipher encryption key)
// PRAGMA cipher_store_pass = deprecated
// PRAGMA cipher = no longer supported
// PRAGMA rekey_cipher = no longer supported
// PRAGMA fast_kdf_iter = deprecated
// PRAGMA page_size = 4096
// PRAGMA cache_size = -2000
// PRAGMA mmap_size
// PRAGMA wal_autocheckpoint
// PRAGMA temp_store = MEMORY
// PRAGMA journal_mode = WAL
// PRAGMA synchronous = NORMAL
// PRAGMA busy_timeout
// PRAGMA query_only = ON
//
// sqlx-sqlite connection management:
// Pool configuration: max_connections, acquire_timeout, max_lifetime
// Read/Write split support: ICUBE_ENABLE_DB_RW_SPLIT
// Separate pool configs for read and write connections

// Cargo registry mirror:
// index.crates.io-1949cf8c6b5b557f (standard)
// rsproxy.cn (China mirror for build speed)
```

---
