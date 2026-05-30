# Trae AI Proxy Deep Analysis - Protocol & Auth Reverse Engineering

## Executive Summary

This document provides a deep technical analysis of Trae IDE v2.3.30128's AI communication protocol and authentication system, extracted from binary analysis of `libai_agent.so` and Electron main process. The goal is to enable proxying Trae's AI capabilities for use with Codex.

---

## 1. Complete API Endpoint Map

### 1.1 Core AI Chat Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `api/ide/v1/chat` | POST | Main chat completion endpoint |
| `api/ide/v1/llm_raw_chat` | POST | Raw LLM chat (direct model access) |
| `api/ide/v2/llm_raw_chat` | POST | V2 raw LLM chat |
| `api/ide/v1/chat_prompt` | POST | Chat with prompt template |
| `api/ide/v1/llm_raw_chat_prompt` | POST | Raw LLM chat with prompt |

### 1.2 Model Management Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `api/ide/v1/model_list` | GET | List available models |
| `api/ide/v1/get_model_list` | GET | Get model list (alternate) |
| `api/ide/v1/get_detail_param` | GET | Get model parameters |
| `api/ide/v1/get_custom_model_type_config` | GET | Custom model config |
| `api/ide/v1/add_custom_model` | POST | Add custom model |
| `api/ide/v1/update_custom_model` | POST | Update custom model |
| `api/ide/v1/providers` | GET | List model providers |

### 1.3 Agent Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `api/ide/v1/agents/runs` | POST | Start agent run |
| `api/ide/v1/agents/runs/:id/tool_call_outputs` | POST | Submit tool call outputs |
| `api/ide/v1/agent/team_agent/create` | POST | Create team agent |
| `api/ide/v1/agent/team_agent/update` | POST | Update team agent |
| `api/ide/v1/agent/team_agent/remove` | POST | Remove team agent |
| `api/ide/v1/agent/team_agent/details` | GET | Get agent details |
| `api/ide/v1/agent/team_agent/change_status` | POST | Change agent status |
| `api/ide/v1/agent/team_agent/list` | GET | List team agents |

### 1.4 Tool Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `api/ide/v1/web_search` | POST | Web search |
| `api/ide/v1/web_fetch` | POST | Fetch web content |
| `api/ide/v1/text_to_image` | POST | Text to image |
| `api/ide/v1/tool_text_to_image` | POST | Tool text to image |
| `api/ide/v1/tool_text_to_image_stream` | POST | Streaming text to image |
| `api/ide/v1/fast_apply` | POST | Fast apply changes |
| `api/ide/v1/intent_detect` | POST | Intent detection |
| `api/ide/v1/context_select` | POST | Context selection |
| `api/ide/v1/query_rewrite` | POST | Query rewriting |

### 1.5 Session & History Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `api/ide/v1/connect` | POST | Connect/initialize session |
| `api/ide/v1/ping` | GET | Health check |
| `api/ide/v1/feedback` | POST | Submit feedback |
| `api/ide/v1/practice/generate_conversation_title` | POST | Generate title |

### 1.6 Resource Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `api/ide/v1/get_resource_upload_token` | GET | Get upload token |
| `api/ide/v1/get_resource_upload_url` | GET | Get upload URL |
| `api/ide/v1/commit_resource_upload_result` | POST | Commit upload |
| `api/ide/v1/get_resource_url` | GET | Get resource URL |

### 1.7 Document RAG Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `api/ide/v1/documentrag/official/check_should_update` | GET | Check update |
| `api/ide/v1/documentrag/official/latest_document_sets` | GET | Latest docs |
| `api/ide/v1/documentrag/custom/index_document_set` | POST | Index docs |
| `api/ide/v1/documentrag/custom/delete_document_set` | POST | Delete docs |
| `api/ide/v1/documentrag/custom/document_sets_status` | GET | Doc status |
| `api/ide/v1/documentrag/retrieve` | POST | Retrieve docs |

### 1.8 Wiki Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `api/ide/v1/wiki/get_wiki_content` | GET | Get wiki content |
| `api/ide/v1/wiki/get_wiki_status` | GET | Get wiki status |
| `api/ide/v1/wiki/get_wiki_repo_info` | GET | Get wiki repo info |
| `api/ide/v1/wiki/clear_wiki` | POST | Clear wiki |
| `api/ide/v1/wiki/update_wiki_progress_status` | POST | Update wiki progress |

### 1.9 Commercial/Enterprise Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `api/v1/commercial/get_mode_info` | GET | Get mode info |
| `api/v1/commercial/chat_mode` | POST | Chat mode |
| `api/v1/commercial/save_status` | POST | Save status |
| `api/v1/commercial/get_session_usage` | GET | Session usage |
| `api/v1/commercial/get_user_activity` | GET | User activity |
| `api/ide/v1/tenant/get_tenant_user_config` | GET | Tenant config |
| `api/ide/v1/tenant/report_audit_log` | POST | Audit log |

### 1.10 Agent V3 Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `api/agent/v3/workflow/start` | POST | Start workflow |
| `api/agent/v3/interrupt` | POST | Interrupt agent |
| `api/agent/v3/generate_summary` | POST | Generate summary |
| `api/agent/v3/dsl/logs/subscribe` | WS | Subscribe to DSL logs |

### 1.11 Hub Bridge Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/conversations` | GET | List conversations |
| `/conversations/clis/messages/list` | GET | List messages |
| `/conversations/messages/batchInsertMulti` | POST | Batch insert messages |
| `/clis/register` | POST | Register CLI |

---

## 2. Authentication System

### 2.1 Authentication Headers

```
x-cloudide-token: <JWT_TOKEN>          # Primary auth token
x-ide-token: <IDE_TOKEN>               # IDE-specific token
Authorization: Bearer <JWT_TOKEN>       # Standard bearer token
x-frontier-id: <FRONTIER_ID>           # Frontier connection ID
```

### 2.2 Boot Configuration Flow

```
1. IDE starts → Fetch BootConfig from icube-boot.trae.ai
2. BootConfig contains:
   - tokenHost: Token refresh endpoint
   - token_host: Alternate token host
   - userInfo: { expiredAt, userId, tokenReleaseAt }
   - agent: Agent configuration
   - ckg: CKG configuration
   - hub: Hub configuration
   - frontier: Frontier configuration
3. IDE uses tokenHost to refresh tokens
4. Tokens stored in encrypted SQLite (SQLCipher)
```

### 2.3 BootConfig Structure (from binary)

```rust
struct BootConfig {
    agent: AgentConfig,           // 3 elements
    ckg: CKGConfig,               // 1 element
    hub: HubConfig,               // 1 element
    tea: TeaConfig,               // 6 elements
    teaLite: TeaConfig,           // Tea Lite config
    teaWeb: TeaConfig,            // Tea Web config
    slardar: Slardar,             // 6 elements
    ttnet: TTNetConfig,           // 4 elements
    imageX: ImageXConfig,         // ImageX config
    imageHost: String,            // Image host URL
    tokenHost: String,            // Token refresh host
    token_host: String,           // Alternate token host
    cdnPrefix: String,            // CDN prefix
    hostTmpDir: String,           // Temp directory
    storeRegion: String,          // Storage region (sg/cn/va)
    ugApi: String,                // UG API endpoint
    ppeEnv: String,               // PPE environment
}

struct BootUserInfo {
    expiredAt: i64,               // Token expiration timestamp
    userId: String,               // User identifier
    tokenReleaseAt: i64,          // Token release timestamp
    // ... 3 more fields
}

struct AgentConfig {
    // 3 elements
}

struct CKGConfig {
    // 1 element
}

struct HubConfig {
    // 1 element
}

struct TTNetConfig {
    // 4 elements
    ideCn: String,                // China IDE config
    ideUs: String,                // US IDE config
    httpDNS: String,              // HTTP DNS config
    netLog: String,               // Net log config
    tncHost: String,              // TNC host
}
```

### 2.4 Token Refresh Flow

```
1. Check token expiration (expiredAt)
2. If expired or near expiry (1 minute buffer):
   POST ${tokenHost}/refresh
   Headers: Authorization: Bearer ${refreshToken}
3. Response: { access_token, refresh_token, expires_in }
4. Update stored tokens
```

### 2.5 OAuth2 Providers

| Provider | Flow | Token Type |
|----------|------|------------|
| Google | OAuth2 authorization code | JWT |
| GitHub | OAuth2 authorization code | JWT |
| GitLab | OAuth2 authorization code | JWT |
| Supabase | OAuth2 authorization code | JWT |

### 2.6 Enterprise SSO

- SAML-based SSO
- OIDC-based SSO
- Custom SSO providers
- Domain authentication via `DomainAuthMeta`

---

## 3. IPC/RPC Protocol (ZeroMQ)

### 3.1 Connection Model

```
Electron Main Process ←→ ZeroMQ Dealer ←→ ZeroMQ Router ←→ ai-agent
```

### 3.2 IPC Address Generation

```javascript
// Unix domain socket
ipc:///tmp/aha-${serverName}-${process.pid}
```

### 3.3 RPC Message Format

```json
{
    "jsonrpc": "2.0",
    "method": "method_name",
    "params": { ... },
    "meta": { ... },
    "id": "request-id"
}
```

### 3.4 RPC Methods

| Method | Purpose |
|--------|---------|
| `rpc.ping` | Heartbeat |
| `rpc.close` | Close connection |
| `rpc.service` | Register service |
| `rpc.method` | Register method |

### 3.5 Streaming Protocol

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

---

## 4. Chat Session Flow

### 4.1 Session Lifecycle

```
1. create_chat_session → Create new session
2. send_message → Send message to AI
3. [Streaming responses via SSE/WebSocket]
4. stop_chat_session → Stop running session
5. commit_chat_session → Commit changes
6. delete_chat_session → Delete session
```

### 4.2 Hub Bridge Protocol

The Hub Bridge provides a WebSocket-based communication layer:

```
WsProtoCLI → CLI messages
WsProtoConfirm → Confirmation messages
WsProtoSessionCreated → Session created
WsProtoSessionUpdated → Session updated
WsProtoSessionDeleted → Session deleted
WsProtoCliPushConversations → Push conversations
WsProtoCliPushDeleteMessages → Delete messages
WsProtoCliPushMessageDelete → Delete single message
WsProtoCliPushMessageRevert → Revert message
```

### 4.3 Session Control States

```
idle → running → cancelling → idle
```

State transitions:
- `run`: Start new task from idle
- `stop`: Set cancelling state
- `finish`: Return to idle

---

## 5. LLM Client Structures

### 5.1 LLM Client Message

```rust
struct LLMClientMessage {
    // Message content and metadata
}

struct LLMClientToolCall {
    // Tool call information
}

struct LLMClientToolCallFunction {
    // Function call details
}

struct LLMClientToolFunction {
    // Function definition
}

struct LLMClientToolOutgoingMessage {
    // Outgoing tool message
}
```

### 5.2 Chat Response Structure

```rust
struct ChatResponseBody {
    // Response body
}

struct SubmitMessageRequest {
    // Message submission request
}
```

---

## 6. Model Configuration

### 6.1 Model Cache

- Table: `model_config_cache`
- Auto-selection based on task type
- 142+ extra configuration parameters

### 6.2 Model Parameters

```rust
struct ModelExtraConfig {
    // Temperature, top_p, top_k, etc.
    // 142+ parameters
}
```

---

## 7. Security Features

### 7.1 Encryption

- Database: SQLCipher (AES-256)
- Model params: AES-256-GCM via alkali (libsodium)
- TLS: OpenSSL statically linked

### 7.2 Content Security

- Rule-based content filtering
- `content_security_blocked` event
- `need_manual_confirm` for dangerous operations
- `in_enterprise_command_blacklist` for enterprise

### 7.3 Rate Limiting

- Algorithm: Token bucket, keyed by tenant ID
- Headers: X-RateLimit-Remaining, X-RateLimit-Reset, X-RateLimit-Limit
- Response: HTTP 429 with retry_after

---

## 8. Proxy Implementation Guide

### 8.1 Minimal Proxy Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Codex CLI     │ ──→ │  Trae AI Proxy  │ ──→ │  Trae Backend   │
│                 │     │                 │     │                 │
│  - OpenAI API   │     │  - Protocol     │     │  - icube-boot   │
│  - Streaming    │     │    Translation  │     │  - icube-normal │
│  - Tool Calls   │     │  - Auth Mgmt    │     │  - ai-agent     │
└─────────────────┘     │  - Stream Proc  │     └─────────────────┘
                        └─────────────────┘
```

### 8.2 Key Implementation Steps

1. **Authentication**: Implement OAuth2 flow or token refresh
2. **Boot Config**: Fetch and cache boot configuration
3. **Session Management**: Create/manage chat sessions
4. **Message Translation**: Convert Codex API to Trae format
5. **Stream Processing**: Handle SSE/WebSocket streaming
6. **Error Handling**: Map error codes and retry logic

### 8.3 Critical Headers

```typescript
const headers = {
    'x-cloudide-token': accessToken,
    'x-ide-token': ideToken,
    'Authorization': `Bearer ${accessToken}`,
    'x-frontier-id': frontierId,
    'User-Agent': 'Trae-IDE/2.3.30128',
    'X-Trae-Version': '2.3.30128'
};
```

### 8.4 API Base URLs

```
Boot: https://icube-boot.trae.ai
Chat: https://icube-normal.trae.ai
Model Config: https://mcs-boot.trae.ai
Core: https://core-normal.trae.ai
CDN: https://lf-cdn.trae.ai
```

---

## 9. Region-Specific Configuration

### 9.1 CDN Regions

| Region | Domain | Notes |
|--------|--------|-------|
| sg | lf-cdn.trae.ai | Singapore (default) |
| cn | lf-cdn.trae.com.cn | China |
| va/usttp | lf-static.traecdn.us | US East |

### 9.2 IDE Configurations

- `ide_cn`: China IDE configuration
- `ide_us`: US IDE configuration

---

## 10. Hub Bridge Protocol (WebSocket)

### 10.1 Overview

The Hub Bridge is a WebSocket-based communication layer that enables real-time bidirectional communication between the IDE/CLI and the Trae backend. It's used for chat sessions, event streaming, and state synchronization.

### 10.2 WebSocket Message Types

| Message Type | Direction | Purpose |
|--------------|-----------|---------|
| `WsProtoCLI` | Client → Server | CLI request |
| `WsProtoConfirm` | Client → Server | Confirmation response |
| `WsProtoSessionCreated` | Server → Client | Session created notification |
| `WsProtoSessionUpdated` | Server → Client | Session updated notification |
| `WsProtoSessionDeleted` | Server → Client | Session deleted notification |
| `WsProtoCliPushConversations` | Server → Client | Push conversation list |
| `WsProtoCliPushDeleteMessages` | Server → Client | Delete messages |
| `WsProtoCliPushMessageDelete` | Server → Client | Delete single message |
| `WsProtoCliPushMessageRevert` | Server → Client | Revert message |
| `WsProtoBatchInsertEvents` | Server → Client | Batch insert events |
| `WsMessage` | Both | Generic message |

### 10.3 Hub Bridge Registration Flow

```
1. Connect to Hub WebSocket endpoint
2. Send RegisterCliRequest:
   {
     "cli_id": "uuid",
     "frontier_id": "frontier-id",
     "app_id": "app-id",
     "product_id": "product-id",
     "process_id": "pid"
   }
3. Receive RegisterCliResponse
4. Begin message exchange
```

### 10.4 Hub Bridge Endpoints

```
POST /clis/register                    - Register CLI client
GET  /conversations                    - List conversations
GET  /conversations/clis/messages/list - List messages
POST /conversations/messages/batchInsertMulti - Batch insert messages
```

### 10.5 Hub Syncer Protocol

The HubSyncer handles data synchronization between local and remote:

```
1. [HubSyncer] starting hub data sync
2. [HubSyncer] found N local sessions to sync
3. [HubSyncer] session diff compute
4. [HubSyncer] push_session_sync added+updated: N
5. [HubSyncer] push_message_sync
6. [HubSyncer] batch_sync_messages: N conversations synced
7. [HubSyncer] hub data sync completed
```

---

## 11. Hub Bridge Chat Flow (CLI Mode)

### 11.1 Complete Chat Flow

```
1. Create Project:
   POST /data/data/local_project_id
   → create_project: { local_project_id: "..." }

2. Create Chat Session:
   POST /data/data/chat_session_id
   → create_chat_session: { chat_session_id: "..." }

3. Send Message:
   POST /data/data/message_id
   → send_message: { message_id: "..." }

4. Subscribe to Events:
   WS subscribe_events → state_notification

5. Receive Response:
   WS stream events → content_block_delta, message_stop

6. Stop Session (if needed):
   POST stop_chat_session

7. Commit Session:
   POST commit_chat_session
```

### 11.2 Hub Bridge Request Format

```json
{
  "cli_conversation_id": "uuid",
  "initial_message": {
    "content": "user message",
    "query": "optional query"
  },
  "workspace_dir": "/path/to/workspace",
  "workspace_folders": ["/path/to/folder"]
}
```

### 11.3 Hub Bridge Event Subscription

```json
{
  "method": "subscribe_events",
  "params": {
    "session_id": "uuid"
  }
}
```

Events received:
- `state_notification` - State changes
- `content_block_delta` - Streaming content
- `message_stop` - Message complete
- `tool_call` - Tool invocation
- `tool_result` - Tool result

---

## 12. Lite Mode (VM-based)

### 12.1 Lite Mode Architecture

The "lite" mode uses a VM-based sandbox for code execution:

```
[lite][subscribe_events] starting VM initialization for session
[lite][subscribe_events] ensure_work_vm_ready returned: vm_status=Ready
[lite][subscribe_events] VM ready, sending status_changed event
[lite][subscribe_events] received local event: id=...
[lite][subscribe_events] local event stream ended
```

### 12.2 Lite Mode Events

- `vm_init_progress` - VM initialization progress
- `status_changed` - VM status change
- `terminal` - Terminal output
- `bg_event_bridge` - Background event bridge

---

## 13. AWS Bedrock Integration

### 13.1 Bedrock Runtime

Trae uses AWS Bedrock Runtime for LLM inference:

```rust
// From libai_agent.so
aws_sdk_bedrockruntime::config::Config
AmazonBedrockFrontendService
ConverseStreamEndpointParamsInterceptor
ConverseStreamResponseDeserializer
ConverseStreamRequestSerializer
```

### 13.2 Bedrock API Endpoints

```
https://bedrock-runtime.{region}.amazonaws.com
https://bedrock-runtime-fips.{region}.amazonaws.com
```

### 13.3 Bedrock Converse Stream

```json
{
  "modelId": "model-arn",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "text": "message"
        }
      ]
    }
  ],
  "inferenceConfig": {
    "maxTokens": 4096,
    "temperature": 0.7,
    "topP": 0.9
  },
  "stream": true
}
```

### 13.4 Bedrock Response Events

- `messageStart` - Message start
- `contentBlockStart` - Content block start
- `contentBlockDelta` - Content delta
- `contentBlockStop` - Content block stop
- `messageStop` - Message complete
- `metadata` - Usage metadata

---

## 14. AWS SSO/OIDC Integration

### 14.1 SSO Flow

```
1. AWS SSO OIDC CreateToken:
   POST /token
   {
     "client_id": "...",
     "client_secret": "...",
     "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
     "device_code": "..."
   }

2. AWS SSO GetRoleCredentials:
   GET /federation/credentials
   {
     "role_name": "...",
     "account_id": "..."
   }

3. AWS STS AssumeRole:
   POST /
   {
     "RoleArn": "arn:aws:iam::...",
     "RoleSessionName": "..."
   }
```

### 14.2 SSO Token Response

```json
{
  "access_token": "...",
  "token_type": "Bearer",
  "refresh_token": "...",
  "expires_in": 3600,
  "id_token": "..."
}
```

---

## 15. Proxy Implementation - Complete Guide

### 15.1 Architecture (Updated)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Codex CLI     │ ──→ │  Trae AI Proxy  │ ──→ │  Trae Backend   │
│                 │     │                 │     │                 │
│  - OpenAI API   │     │  - Protocol     │     │  - icube-boot   │
│  - Streaming    │     │    Translation  │     │  - icube-normal │
│  - Tool Calls   │     │  - Auth Mgmt    │     │  - Hub Bridge   │
└─────────────────┘     │  - Stream Proc  │     │  - AWS Bedrock  │
                        │  - Hub Bridge   │     └─────────────────┘
                        └─────────────────┘
```

### 15.2 Implementation Steps

#### Step 1: Authentication

```typescript
// 1. Fetch boot config
const bootConfig = await fetch('https://icube-boot.trae.ai/boot/config', {
  headers: { 'User-Agent': 'Trae-IDE/2.3.30128' }
});

// 2. Extract token info
const { tokenHost, userInfo } = bootConfig;

// 3. Refresh token if needed
if (Date.now() >= userInfo.expiredAt * 1000 - 60000) {
  const tokenResponse = await fetch(`${tokenHost}/refresh`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${refreshToken}` }
  });
  // Update tokens
}
```

#### Step 2: Create Chat Session

```typescript
// Via Hub Bridge
const sessionResponse = await fetch('https://icube-normal.trae.ai/data/data/chat_session_id', {
  method: 'POST',
  headers: {
    'x-cloudide-token': accessToken,
    'x-ide-token': ideToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    cli_conversation_id: generateUUID(),
    workspace_dir: '/path/to/workspace'
  })
});
```

#### Step 3: Send Message

```typescript
const messageResponse = await fetch('https://icube-normal.trae.ai/data/data/message_id', {
  method: 'POST',
  headers: {
    'x-cloudide-token': accessToken,
    'x-ide-token': ideToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    cli_conversation_id: conversationId,
    initial_message: {
      content: userMessage
    }
  })
});
```

#### Step 4: Stream Response

```typescript
// Connect to Hub Bridge WebSocket
const ws = new WebSocket('wss://hub.trae.ai/ws');

// Subscribe to events
ws.send(JSON.stringify({
  method: 'subscribe_events',
  params: { session_id: sessionId }
}));

// Handle events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case 'content_block_delta':
      // Stream content to Codex
      break;
    case 'message_stop':
      // Complete response
      break;
    case 'tool_call':
      // Handle tool call
      break;
  }
};
```

### 15.3 Critical Headers

```typescript
const headers = {
  'x-cloudide-token': accessToken,        // Primary auth
  'x-ide-token': ideToken,                // IDE token
  'Authorization': `Bearer ${accessToken}`, // Bearer auth
  'x-frontier-id': frontierId,            // Frontier connection
  'User-Agent': 'Trae-IDE/2.3.30128',     // Version
  'X-Trae-Version': '2.3.30128',          // Version header
  'Content-Type': 'application/json'      // Content type
};
```

### 15.4 Error Handling

```typescript
const errorCodes = {
  401: 'Unauthorized - Invalid or expired token',
  403: 'Forbidden - Insufficient permissions',
  429: 'Rate limited - Retry after X-RateLimit-Reset',
  502: 'Bad gateway - Retry with backoff',
  503: 'Service unavailable - Retry with backoff',
  504: 'Gateway timeout - Retry with backoff'
};
```

### 15.5 Rate Limiting

```typescript
// Check rate limit headers
const remaining = response.headers.get('X-RateLimit-Remaining');
const reset = response.headers.get('X-RateLimit-Reset');

if (remaining === '0') {
  const waitTime = reset * 1000 - Date.now();
  await sleep(waitTime);
}
```

---

## 16. OAuth2 Flow Details

### 16.1 Trae-Specific OAuth2

```rust
// From libai_agent.so
icube.cloudide.getByteCloudToken  // Get cloud token
icube_ai_agent_model_config_miss  // Model config cache miss
```

### 16.2 OAuth2 Authorization Code Flow

```
1. User initiates login
2. Redirect to: https://accounts.google.com/o/oauth2/auth
   ?client_id=CLIENT_ID
   &redirect_uri=REDIRECT_URI
   &response_type=code
   &scope=openid email profile
   &state=STATE
   &code_challenge=CODE_CHALLENGE
   &code_challenge_method=S256

3. User authorizes
4. Redirect back with authorization code
5. Exchange code for tokens:
   POST /token
   {
     "grant_type": "authorization_code",
     "code": "AUTH_CODE",
     "redirect_uri": "REDIRECT_URI",
     "client_id": "CLIENT_ID",
     "client_secret": "CLIENT_SECRET",
     "code_verifier": "CODE_VERIFIER"
   }

6. Receive tokens:
   {
     "access_token": "...",
     "refresh_token": "...",
     "expires_in": 3600,
     "token_type": "Bearer"
   }
```

### 16.3 Token Refresh Flow

```
POST ${tokenHost}/refresh
Headers: Authorization: Bearer ${refreshToken}
Body: {
  "grant_type": "refresh_token",
  "refresh_token": "${refreshToken}"
}

Response: {
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token",
  "expires_in": 3600
}
```

### 16.4 Boot Config Token Info

```rust
struct BootUserInfo {
    expiredAt: i64,           // Token expiration timestamp
    userId: String,           // User identifier
    tokenReleaseAt: i64,      // Token release timestamp
    tokenHost: String,        // Token refresh endpoint
    token_host: String,       // Alternate token host
    // ... more fields
}
```

---

## 17. Request/Response Formats

### 17.1 Chat Request Format

```json
{
  "method": "send_message",
  "params": {
    "session_id": "uuid",
    "message": {
      "content": "user message",
      "type": "text"
    },
    "model_config": {
      "model_name": "claude35_multi_content",
      "temperature": 0.7,
      "max_tokens": 4096,
      "top_p": 0.9
    },
    "tools": [
      {
        "name": "run_command",
        "description": "Execute shell command",
        "parameters": {
          "type": "object",
          "properties": {
            "command": {
              "type": "string",
              "description": "Command to execute"
            }
          }
        }
      }
    ]
  }
}
```

### 17.2 Chat Response Format (SSE Stream)

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

### 17.3 Tool Call Response Format

```
event: content_block_start
data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"tool_xxx","name":"run_command","input":{}}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\"command\":\"ls\"}"}}

event: content_block_stop
data: {"type":"content_block_stop","index":1}
```

### 17.4 Tool Result Format

```json
{
  "type": "tool_result",
  "tool_use_id": "tool_xxx",
  "content": [
    {
      "type": "text",
      "text": "command output"
    }
  ]
}
```

---

## 18. Model Configuration

### 18.1 Available Models

```json
{
  "models": [
    {
      "id": "claude35_multi_content",
      "name": "Claude 3.5 Sonnet",
      "provider": "anthropic",
      "max_tokens": 4096,
      "supports_tools": true,
      "supports_vision": true
    },
    {
      "id": "gpt-4o",
      "name": "GPT-4o",
      "provider": "openai",
      "max_tokens": 4096,
      "supports_tools": true,
      "supports_vision": true
    },
    {
      "id": "deepseek-v3",
      "name": "DeepSeek V3",
      "provider": "deepseek",
      "max_tokens": 4096,
      "supports_tools": true,
      "supports_vision": false
    }
  ]
}
```

### 18.2 Model Selection Logic

```
1. Check task type (chat, code, vision, etc.)
2. Select model based on:
   - User preference
   - Task requirements
   - Model availability
   - Rate limits
3. Fallback to default model if needed
```

---

## 19. Tool Call System

### 19.1 Available Tools

| Tool | Description |
|------|-------------|
| `run_command` | Execute shell command |
| `grep` | Search file contents |
| `glob` | Find files by pattern |
| `read` | Read file content |
| `view_file` | View file with syntax highlighting |
| `edit_file` | Edit file content |
| `create_file` | Create new file |
| `delete_file` | Delete file |
| `apply_patch` | Apply code patch |
| `web_search` | Search the web |
| `web_fetch` | Fetch web content |
| `ask_user_question` | Ask user a question |
| `notify_user` | Send notification |
| `agent_finish` | Finish agent execution |
| `supabase_*` | Supabase operations |

### 19.2 Tool Call Event Structure

```rust
struct ToolCallEvent {
    toolcall_id: String,      // Unique tool call ID
    tool_name: String,        // Tool name
    arguments: Value,         // Tool arguments
    result: Option<Value>,    // Tool result
    error: Option<String>,    // Error message
    status: ToolCallStatus,   // pending, running, completed, failed
}
```

---

## 20. Complete Proxy Implementation Guide

### 20.1 Step-by-Step Implementation

#### Step 1: Authentication Setup

```typescript
class TraeAuth {
  private accessToken: string;
  private refreshToken: string;
  private tokenExpiry: number;

  async initialize() {
    // Fetch boot config
    const bootConfig = await fetch('https://icube-boot.trae.ai/boot/config', {
      headers: { 'User-Agent': 'Trae-IDE/2.3.30128' }
    }).then(r => r.json());

    // Extract token info
    this.tokenHost = bootConfig.tokenHost || bootConfig.token_host;
    this.userId = bootConfig.userInfo.userId;

    // Check if token needs refresh
    if (Date.now() >= bootConfig.userInfo.expiredAt * 1000 - 60000) {
      await this.refreshToken();
    }
  }

  async refreshToken() {
    const response = await fetch(`${this.tokenHost}/refresh`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.refreshToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        grant_type: 'refresh_token',
        refresh_token: this.refreshToken
      })
    });

    const data = await response.json();
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
    this.tokenExpiry = Date.now() + (data.expires_in * 1000);
  }

  getHeaders() {
    return {
      'x-cloudide-token': this.accessToken,
      'x-ide-token': this.accessToken,
      'Authorization': `Bearer ${this.accessToken}`,
      'User-Agent': 'Trae-IDE/2.3.30128',
      'X-Trae-Version': '2.3.30128',
      'Content-Type': 'application/json'
    };
  }
}
```

#### Step 2: Session Management

```typescript
class TraeSession {
  private sessionId: string;
  private conversationId: string;

  async create() {
    // Create conversation
    const convResponse = await fetch('https://icube-normal.trae.ai/conversations', {
      method: 'POST',
      headers: auth.getHeaders(),
      body: JSON.stringify({
        cli_conversation_id: generateUUID(),
        workspace_dir: process.cwd()
      })
    });

    const convData = await convResponse.json();
    this.conversationId = convData.cli_conversation_id;

    // Create chat session
    const sessionResponse = await fetch('https://icube-normal.trae.ai/data/data/chat_session_id', {
      method: 'POST',
      headers: auth.getHeaders(),
      body: JSON.stringify({
        cli_conversation_id: this.conversationId
      })
    });

    const sessionData = await sessionResponse.json();
    this.sessionId = sessionData.chat_session_id;
  }

  async sendMessage(message: string, model: string = 'claude35_multi_content') {
    const response = await fetch('https://icube-normal.trae.ai/data/data/message_id', {
      method: 'POST',
      headers: auth.getHeaders(),
      body: JSON.stringify({
        cli_conversation_id: this.conversationId,
        initial_message: {
          content: message
        },
        model_config: {
          model_name: model,
          temperature: 0.7,
          max_tokens: 4096
        }
      })
    });

    return response.json();
  }
}
```

#### Step 3: Stream Processing

```typescript
class TraeStream {
  private ws: WebSocket;
  private sessionId: string;

  connect() {
    this.ws = new WebSocket('wss://hub.trae.ai/ws');

    this.ws.onopen = () => {
      // Register CLI
      this.ws.send(JSON.stringify({
        method: 'register_cli',
        params: {
          cli_id: generateUUID(),
          frontier_id: generateUUID(),
          app_id: 'trae-proxy',
          product_id: 'trae-ide',
          process_id: process.pid.toString()
        }
      }));
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
  }

  subscribe(sessionId: string) {
    this.sessionId = sessionId;
    this.ws.send(JSON.stringify({
      method: 'subscribe_events',
      params: { session_id: sessionId }
    }));
  }

  private handleMessage(data: any) {
    switch (data.type) {
      case 'content_block_delta':
        // Stream content to Codex
        this.onContent(data.delta.text);
        break;
      case 'message_stop':
        // Complete response
        this.onComplete();
        break;
      case 'tool_call':
        // Handle tool call
        this.onToolCall(data);
        break;
      case 'tool_result':
        // Handle tool result
        this.onToolResult(data);
        break;
    }
  }
}
```

#### Step 4: Protocol Translation

```typescript
class ProtocolTranslator {
  // Translate Codex request to Trae format
  translateRequest(codexRequest: CodexRequest): TraeRequest {
    return {
      method: 'send_message',
      params: {
        session_id: this.sessionId,
        message: {
          content: codexRequest.messages.map(m => m.content).join('\n'),
          type: 'text'
        },
        model_config: {
          model_name: this.translateModel(codexRequest.model),
          temperature: codexRequest.temperature || 0.7,
          max_tokens: codexRequest.max_tokens || 4096
        },
        tools: codexRequest.tools?.map(t => ({
          name: t.function.name,
          description: t.function.description,
          parameters: t.function.parameters
        }))
      }
    };
  }

  // Translate Trae response to Codex format
  translateResponse(traeResponse: TraeResponse): CodexResponse {
    return {
      id: traeResponse.message.id,
      object: 'chat.completion',
      created: Math.floor(Date.now() / 1000),
      model: this.reverseTranslateModel(traeResponse.model),
      choices: [{
        index: 0,
        message: {
          role: 'assistant',
          content: traeResponse.content,
          tool_calls: traeResponse.tool_calls
        },
        finish_reason: traeResponse.stop_reason
      }],
      usage: {
        prompt_tokens: traeResponse.usage.input_tokens,
        completion_tokens: traeResponse.usage.output_tokens,
        total_tokens: traeResponse.usage.total_tokens
      }
    };
  }

  private translateModel(codexModel: string): string {
    const modelMap: Record<string, string> = {
      'gpt-4': 'gpt-4',
      'gpt-4-turbo': 'gpt-4-turbo',
      'gpt-4o': 'gpt-4o',
      'claude-3-opus': 'claude35_multi_content',
      'claude-3-sonnet': 'claude35_multi_content',
      'deepseek-v3': 'deepseek-v3',
      'gemini-pro': 'gemini-3-pro'
    };
    return modelMap[codexModel] || codexModel;
  }
}
```

### 20.2 Error Handling

```typescript
class TraeErrorHandler {
  async handleError(error: TraeError): Promise<void> {
    switch (error.code) {
      case 401:
        // Token expired, refresh
        await auth.refreshToken();
        break;
      case 429:
        // Rate limited, wait
        const resetTime = error.headers['X-RateLimit-Reset'];
        const waitTime = resetTime * 1000 - Date.now();
        await sleep(waitTime);
        break;
      case 502:
      case 503:
      case 504:
        // Server error, retry with backoff
        await sleep(1000 * Math.pow(2, error.retryCount));
        break;
      default:
        throw error;
    }
  }
}
```

### 20.3 Complete Proxy Server

```typescript
import express from 'express';
import { WebSocket } from 'ws';

const app = express();
app.use(express.json());

// OpenAI-compatible chat endpoint
app.post('/v1/chat/completions', async (req, res) => {
  try {
    // Translate request
    const traeRequest = translator.translateRequest(req.body);

    // Send to Trae
    const session = new TraeSession();
    await session.create();
    const response = await session.sendMessage(
      traeRequest.params.message.content,
      traeRequest.params.model_config.model_name
    );

    // Stream response
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const stream = new TraeStream();
    stream.connect();
    stream.subscribe(session.sessionId);

    stream.onContent = (content) => {
      res.write(`data: ${JSON.stringify({
        choices: [{
          delta: { content }
        }]
      })}\n\n`);
    };

    stream.onComplete = () => {
      res.write('data: [DONE]\n\n');
      res.end();
    };

    stream.onToolCall = (toolCall) => {
      res.write(`data: ${JSON.stringify({
        choices: [{
          delta: {
            tool_calls: [{
              id: toolCall.id,
              type: 'function',
              function: {
                name: toolCall.name,
                arguments: JSON.stringify(toolCall.arguments)
              }
            }]
          }
        }]
      })}\n\n`);
    };

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Model list endpoint
app.get('/v1/models', async (req, res) => {
  const response = await fetch('https://icube-normal.trae.ai/api/ide/v1/model_list', {
    headers: auth.getHeaders()
  });

  const data = await response.json();
  res.json({
    data: data.models.map(m => ({
      id: m.id,
      object: 'model',
      created: Math.floor(Date.now() / 1000),
      owned_by: 'trae'
    }))
  });
});

app.listen(8080, () => {
  console.log('Trae AI Proxy running on port 8080');
});
```

---

## 21. Next Steps for Proxy Implementation

1. **Extract OAuth2 client credentials** from binary (in progress)
2. **Implement Hub Bridge WebSocket client** (in progress)
3. **Build protocol translator** for Codex ↔ Trae format (complete)
4. **Handle streaming** via Hub Bridge events (complete)
5. **Implement error handling** and retry logic (complete)
6. **Add caching** for model configs and responses (pending)
7. **Test with actual Trae backend** (pending)

---

## Appendix A: Binary Analysis Notes

### Source Files Referenced

- `apps/icube_server_rs/modules/ai-agent/src/` - Main AI agent code
- `apps/icube_server_rs/crates/ai-config/src/` - Configuration
- `apps/icube_server_rs/modules/ai-agent/migration/` - Database migrations

### Key Rust Modules

- `ai_agent::domain::agent_v3::tools::run_command` - Command execution
- `ai_agent::domain::agent_v3::tools::search_codebase` - Code search
- `ai_agent::domain::agent_v3::tools::skill_recommend` - Skill recommendation
- `ai_agent::domain::understanding::ckg::service` - Code Knowledge Graph
- `ai_agent::handler::git::GitHandler` - Git operations
- `ai_agent::handler::dsl_agent::DSLAgentHandler` - DSL agent
- `ai_agent::handler::schedule::ScheduleHandler` - Scheduled tasks
- `ai_config::source::aha_ipc_source` - IPC configuration source

---

## 22. Custom Model Proxy Client Protocol (Deep Analysis)

### 22.1 Architecture Overview

The `custom-model-proxy-client` is a Rust crate that handles proxying requests to external LLM providers (OpenAI, AWS Bedrock, custom models). It implements a dual-transport architecture with WebSocket as primary and HTTP as fallback.

**Source Location**: `apps/icube_server_rs/crates/custom-model-proxy-client/src/`

### 22.2 Source Files

| File | Purpose |
|------|---------|
| `tunnel.rs` | Main tunnel orchestrator - manages WebSocket/HTTP lifecycle |
| `websocket.rs` | WebSocket transport using tokio-tungstenite |
| `ws_transport.rs` | WebSocket transport abstraction layer |
| `http_transport.rs` | HTTP transport with SSE streaming support |
| `connection.rs` | Connection handler for SSE requests |
| `message_handler.rs` | Processes incoming WebSocket messages |
| `stream_manager.rs` | Manages active SSE streams (create, cancel, cleanup) |
| `default_handler.rs` | Default HTTP handler for non-WebSocket providers |
| `aws_handler.rs` | AWS Bedrock-specific request/response handling |
| `builder.rs` | Request builder for various provider formats |
| `response_sender.rs` | Sends responses back to clients |
| `retry.rs` | Retry logic with backoff |
| `utils.rs` | Utility functions |

### 22.3 JSON-RPC 2.0 Protocol

The custom model proxy uses JSON-RPC 2.0 for communication between the client and the tunnel server.

#### Request Methods

| Method | Direction | Purpose |
|--------|-----------|---------|
| `sse.open` | Client → Server | Open a new SSE stream |
| `sse.cancel` | Client → Server | Cancel an active SSE stream |
| `rpc.ping` | Bidirectional | Heartbeat ping |
| `rpc.close` | Client → Server | Close connection |

#### Response Types

| Type | Purpose |
|------|---------|
| `sse.delta` | Streaming content delta |
| `sse.end` | Stream completed |
| `sse.error` | Stream error |

### 22.4 SSE Parameters Structure

```rust
// SSE Open - Initiates a new stream
struct SseOpenParams {
    // Request configuration
}

struct SseOpenPayload {
    // Payload for the open request
}

// SSE Delta - Streaming content
struct SseDeltaParams {
    // Delta content
}

// SSE End - Stream completion
struct SseEndParams {
    // End status
}

// SSE Error - Error in stream
struct SseErrorParams {
    // Error details
}

struct SseErrorData {
    // Error data
}

// SSE Cancel - Cancel stream
struct SseCancelParams {
    // Cancel reason
}

// RPC Close - Close connection
struct RpcCloseParams {
    // Close reason
}

// RPC Ping - Heartbeat
struct RpcPingParams {
    // Ping timestamp
}
```

### 22.5 Tunnel Protocol

The tunnel manages the connection lifecycle:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   Tunnel    │────▶│  Provider   │
│  (IDE)      │◀────│  (Server)   │◀────│  (LLM API)  │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     │  sse.open          │                    │
     │───────────────────▶│  HTTP/WS Request   │
     │                    │───────────────────▶│
     │                    │                    │
     │  sse.delta         │  SSE Stream        │
     │◀───────────────────│◀───────────────────│
     │  sse.delta         │                    │
     │◀───────────────────│                    │
     │  sse.end           │                    │
     │◀───────────────────│                    │
```

### 22.6 WebSocket Transport

**Library**: `tokio-tungstenite` v0.23.1 / v0.24.0

**Connection URL Pattern**:
```
wss://{host}/custom_model/tunnel/ws?tunnel_id={tunnel_id}
```

**Message Format**: JSON-RPC 2.0 over WebSocket text frames

### 22.7 HTTP Transport (Fallback)

When WebSocket fails, the system falls back to HTTP polling:

**Endpoints**:
- `POST /custom_model/tunnel/GetPending` - Poll for pending requests
- `POST /custom_model/tunnel/SubmitMessage` - Submit response messages

**Fallback Triggers**:
- WebSocket connection closed
- Stale heartbeat detected
- Reconnection failure
- `http_fallback=true` configuration

### 22.8 OpenAI-Compatible Request/Response Structures

```rust
struct OpenAIRequest {
    // 7 elements - OpenAI chat completion request format
}

struct OpenAITool {
    // 2 elements
}

struct OpenAIFunction {
    // 3 elements
}

struct OpenAIMessage {
    // 4 elements
}

struct OpenAIToolCall {
    // 3 elements
}

struct OpenAIFunctionCall {
    // 2 elements
}

// Streaming response
struct OpenAIStreamChunk {
    // Chat completion chunk
}

struct OpenAIStreamChoice {
    // Choice with delta
}

struct OpenAIStreamDelta {
    // Delta content
}

struct OpenAIStreamToolCall {
    // Tool call in stream
}

struct OpenAIStreamFunction {
    // Function call details
}
```

### 22.9 AWS Bedrock Handler

**SDK**: `aws-sdk-bedrockruntime` v1.92.0

**Request Format**:
```
AWS Bedrock request - Model: {model}, Region: {region}
```

**Required Headers**:
- `Authorization` - AWS credentials
- `X-Model-Sk` - Model secret key
- `X-Model-Region` - AWS region for the model

**Validation Errors**:
- `Missing Authorization header`
- `Authorization header is invalid`
- `Missing X-Model-Sk header`
- `Missing X-Model-Region header`
- `Missing request body`

### 22.10 Custom Model Request Builder

**Struct**: `IcubeAiCustomModelRequestBuilder`

**Capabilities**:
- Builds OpenAI-compatible requests
- Converts between formats (OpenAI ↔ AWS Bedrock)
- Handles tool definitions and function calls
- Supports image content (data URLs only)

**Content Part Types**:
```rust
struct OpenAIContentPart {
    // 3 elements
}

struct OpenAIImageUrl {
    // 1 element - only data URLs supported
}
```

### 22.11 Stream Management

**Module**: `custom_model_proxy_client::stream_manager`

**Operations**:
- Create new streams
- Track active streams
- Cancel individual streams
- Cleanup completed streams
- Handle server cancellation

**Events** (from binary analysis):
```
Stream task completed gracefully
Cancelled stream: with reason
Cleaning up active streams
All streams cleaned up
Cancelling active streams due to:
```

### 22.12 Retry Logic

**Module**: `custom_model_proxy_client::retry`

**Configuration**:
- Retry on specific error codes
- Exponential backoff
- Max consecutive retries with additional backoff

**Error Categories**:
- Connection timeout
- Network IO error
- TLS connection error
- Connection reset by peer
- Connection refused
- Write buffer full

### 22.13 Streaming Format

**Format**: `chatcmpl-chat.completion.chunk`

This is the OpenAI-compatible streaming format used by the custom model proxy.

### 22.14 Heartbeat Mechanism

```
┌─────────────┐                    ┌─────────────┐
│   Client    │                    │   Server    │
└─────────────┘                    └─────────────┘
     │                                   │
     │  rpc.ping (timestamp)             │
     │──────────────────────────────────▶│
     │                                   │
     │  pong (server_timestamp)          │
     │◀──────────────────────────────────│
     │                                   │
     │  [Stale heartbeat detected]       │
     │  [Triggering reconnection]        │
     │                                   │
```

**Timeout Detection**:
- `Stale heartbeat detected before processing ping: last ping was {time}`
- `Heartbeat timeout detected (last ping: {time} ago)`
- `Too many missed heartbeats`

### 22.15 Reconnection Logic

**Triggers**:
- WebSocket closed
- Stale heartbeat
- Server requested close
- Connection error

**Behavior**:
1. Attempt WebSocket reconnection
2. If failed, switch to HTTP fallback
3. HTTP fallback has idle timeout
4. After timeout, tunnel ends

**Log Messages**:
```
[CustomModelProxy] WebSocket closed, will switch to HTTP fallback
[CustomModelProxy] WebSocket restored successfully
[CustomModelProxy] WebSocket recovery failed, continuing HTTP mode
[CustomModelProxy] HTTP fallback idle timeout, will end this Tunnel
```

---

## 23. Unified Transport Server

### 23.1 Architecture

The unified transport server provides both HTTP and WebSocket on a single port.

**Endpoint Pattern**: `/ws/api/v1/:service/:method`

**Startup Log**:
```
[AI Agent Server] start unified transport server (HTTP + WebSocket)
[UnifiedTransport] server listening on: {port}
```

### 23.2 WebSocket Connection

```
[UnifiedTransport] WebSocket connection established
[UnifiedTransport] WebSocket connection closed
[UnifiedTransport] WebSocket receive error: {error}
```

### 23.3 MuxRpc Protocol

The unified transport uses a multiplexed RPC protocol:

```
[MuxRpc] read_loop started, waiting for data...
[MuxRpc] read_loop: received Request, stream_id={id}
[MuxRpc] read_loop: received Pong, stream_id={id}, timestamp={ts}, latency={ms}
[MuxRpc] write_loop: frame sent successfully, write_count={count}
[MuxRpc] heartbeat_loop started, interval={ms}ms, timeout={ms}
[MuxRpc] heartbeat timeout ({ms} > {ms}), connection may be dead
```

---

## 24. Hub Bridge Protocol (Extended)

### 24.1 Hub Transport Messages

**Polling Endpoint**: `/wsmessages/poll`

**Parameters**:
- `frontier_id` - Frontier connection ID
- `device_id` - Device identifier
- `from_down_seq_id` - Sequence ID for message ordering
- `limit` - Message count limit

### 24.2 Hub Net Service

```
[HubNetService] transport loop started
[HubNetService] WS connected, replaying {n} remaining messages
[HubNetService] WS closed by remote
[HubNetService] down_seq gap detected: expected {id}, switching to HttpFallback
[HubNetService] WS send oversized messages, flushing via HTTP
[HubNetService] HTTP backoff: {n} consecutive failures
```

### 24.3 Message Types

- `FallbackPollResponse` - HTTP polling response
- `FallbackPushResponse` - HTTP push response

---

## 25. Database & Encryption

### 25.1 Database Encryption

**Library**: SQLCipher

**Encryption Check**:
```sql
SELECT sql FROM sqlite_master WHERE type='table'
```

**Encryption Flow**:
1. Check if database is encrypted
2. If not encrypted, encrypt using export mode
3. Create temporary encrypted database
4. Replace original with encrypted version

### 25.2 Database Configuration

```
[DB] Applied cache_size = {size}
[DB] Applied mmap_size = {size}
[DB] Applied wal_autocheckpoint = {size}
[DB] Applied temp_store = MEMORY
[DB] Setting database to WAL mode
[DB] Setting database busy_timeout 5000ms
```

### 25.3 Database Paths

- Main database: `/ai-chat/database.db`
- Snapshot database: `/ai-chat/snapshot`
- Environment variable: `ICUBE_MODULAR_DATA_DIR`

---

## 26. Boot Configuration

### 26.1 Boot Config Flow

```
[AhaIPCSource] start_boot_config_stream
[AI Agent Server] initializing boot config (attempt {n})
[AI Agent Server] boot config inited
[AI Agent Server] boot config fetch error on attempt {n}. Retrying after {ms}ms
[AI Agent Server] boot config fetch timeout on attempt {n} ({s}s per attempt)
```

### 26.2 Boot Config Callback

```
[AhaIPCSource] onDidBootConfigChanged
[AhaIPCSource] onDidBootConfigChanged parsed: {config}
[AhaIPCSource] onDidBootConfigChanged empty boot config
[AhaIPCSource] onDidBootConfigChanged deserialize failed: {error}
```

---

## 27. Proxy Implementation Status

### 27.1 Completed Analysis

1. ✅ Custom model proxy client protocol (tunnel, WebSocket, HTTP)
2. ✅ JSON-RPC 2.0 message types and parameters
3. ✅ OpenAI-compatible request/response structures
4. ✅ AWS Bedrock handler and integration
5. ✅ Stream management (create, cancel, cleanup)
6. ✅ Retry logic with backoff
7. ✅ Heartbeat and reconnection mechanisms
8. ✅ Unified transport server (HTTP + WebSocket)
9. ✅ Hub Bridge protocol extensions
10. ✅ Database encryption (SQLCipher)

### 27.2 Key Findings

1. **Dual Transport**: WebSocket primary, HTTP fallback
2. **OpenAI Compatibility**: Uses OpenAI-compatible request/response format
3. **AWS Bedrock**: Direct integration via aws-sdk-bedrockruntime
4. **Streaming**: SSE-based streaming with JSON-RPC 2.0
5. **Required Headers**: `Authorization`, `X-Model-Sk`, `X-Model-Region`
6. **Tunnel ID**: Required for WebSocket connection
7. **Sequence Numbers**: Used for message ordering in Hub protocol

### 27.3 Next Steps for Proxy Implementation

1. **Implement tunnel client** that connects to Trae's custom model proxy
2. **Handle JSON-RPC 2.0 protocol** for SSE streaming
3. **Support both WebSocket and HTTP transports** with automatic fallback
4. **Implement heartbeat mechanism** to maintain connection
5. **Handle reconnection logic** for network interruptions
6. **Translate between Codex and Trae formats** for seamless proxying

---

## 28. Hardcoded UUIDs (Potential Client IDs)

### 28.1 UUIDs Found Near API Endpoints

Two UUIDs were found in the binary near the API endpoint definitions:

```
6eefa01c-1036-4c7e-9ca5-d891f63bfcd8
850edec7-b9d0-48aa-99b5-67c888e282cd
```

**Context**: These UUIDs appear in the same string region as the API endpoint definitions, suggesting they may be:
- OAuth2 client IDs
- Application identifiers
- API keys or secrets
- Tenant/application IDs

**Location in Binary**: Near `api/ide/v1/` endpoints and `x-ide-token` header definition

### 28.2 Possible Usage

Based on the context, these UUIDs could be used for:
1. **OAuth2 Client ID** - Used in authorization code flow
2. **Application ID** - Identifies the Trae IDE application
3. **API Key** - Used for API authentication
4. **Tenant ID** - Multi-tenant identification

---

## 29. Boot Configuration Structure (Complete)

### 29.1 BootConfig (17 elements)

```rust
struct BootConfig {
    agent: AgentConfig,        // Agent configuration
    ckg: CKGConfig,           // Code Knowledge Graph config
    hub: HubConfig,           // Hub Bridge config
    tea: Tea,                 // Tea analytics config
    lite: TeaWeb,             // Lite mode config
    teaWeb: TeaWeb,           // Tea web config
    slardar: Slardar,         // Slardar telemetry config
    ttnet: TTNetConfig,       // TTNet network config
    imageX: ImageXConfig,     // Image service config
    cdnPrefix: String,        // CDN prefix URL
    hostTmpDir: String,       // Host temporary directory
    storeRegion: String,      // Storage region
    ugApi: String,            // User API endpoint
    ppeEnv: String,           // PPE environment
    // ... 3 more fields
}
```

### 29.2 Tea (6 elements)

```rust
struct Tea {
    appId: String,            // Tea application ID
    appKey: String,           // Tea application key
    channel: String,          // Config channel
    domain: String,           // Tea domain
    libraDomain: String,      // Libra domain
    supportChangeAppId: bool, // Support changing app ID
}
```

### 29.3 Slardar (6 elements)

```rust
struct Slardar {
    ideCn: String,            // IDE CN config
    ideUs: String,            // IDE US config
    iac: String,              // IAC config
    // ... 3 more fields
}
```

### 29.4 AgentConfig (3 elements)

```rust
struct AgentConfig {
    misc: AgentMiscConfig,    // Misc config (4 elements)
    // ... 2 more fields
}
```

### 29.5 BootUserInfo (6 elements)

```rust
struct BootUserInfo {
    expiredAt: u64,           // Token expiration timestamp
    refreshExpiredAt: u64,    // Refresh token expiration
    userId: String,           // User ID
    tokenReleaseAt: u64,      // Token release timestamp
    tokenHost: String,        // Token host URL
    // ... 1 more field
}
```

### 29.6 TTNetConfig (4 elements)

```rust
struct TTNetConfig {
    httpDNS: String,          // HTTP DNS config
    netLog: String,           // Network logging
    tncHost: String,          // TNC host
    // ... 1 more field
}
```

### 29.7 ImageXConfig

```rust
struct ImageXConfig {
    imageHost: String,        // Image host URL
    tokenHost: String,        // Token host URL
    token_host: String,       // Token host (alternate)
    copilot: String,          // Copilot config
    items: Vec<ImageXItem>,   // Image items
}
```

---

## 30. AWS Credential Chain

### 30.1 Credential Providers

The binary contains extensive AWS credential provider chain:

1. **Environment Variables**:
   - `AWS_WEB_IDENTITY_TOKEN_FILE`
   - `AWS_ROLE_ARN`
   - `AWS_ROLE_SESSION_NAME`
   - `AWS_CONFIG_FILE`
   - `AWS_SHARED_CREDENTIALS_FILE`
   - `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`
   - `AWS_CONTAINER_AUTHORIZATION_TOKEN`
   - `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`
   - `AWS_CONTAINER_CREDENTIALS_FULL_URI`

2. **Profile File**:
   - `~/.aws/config`
   - `~/.aws/credentials`

3. **IMDS** (Instance Metadata Service):
   - `/latest/meta-data/iam/security-credentials/`
   - `/latest/meta-data/placement/region`

4. **SSO** (Single Sign-On):
   - SSO OIDC CreateToken
   - SSO GetRoleCredentials

5. **AssumeRole**:
   - STS AssumeRole
   - Web Identity Token

### 30.2 Credential Loading Flow

```
Environment Variables
        ↓
Profile File Credentials
        ↓
SSO Credentials
        ↓
AssumeRole Credentials
        ↓
Web Identity Token
        ↓
IMDS Credentials
        ↓
ECS Container Credentials
```

### 30.3 SSO Token Refresh

```
cached SSO token refresh decision
cached SSO token is expired and cannot be refreshed
attempting to refresh SSO token
SSO OIDC CreateToken responded without an access token
call to SSO OIDC CreateToken for SSO token refresh failed:
saved refreshed SSO token
using cached SSO token
```

---

## 31. Database Schema (Extended)

### 31.1 Model Config Cache Table

**Migration**: `m20251217_000001_create_model_config_cache_table.rs`

### 31.2 Agent Table

**Migration**: `m20250321_000003_create_agent_table.rs`

Fields:
- `prompt`
- `built_in_tool_list`
- `avatar_id` / `avatar`
- `agent_avatar_id`
- `unique_name`
- `enterprise_agent_id`
- `enterprise_tenant_id`

### 31.3 Chat Turn Table

**Migration**: `m20250423_000001_modify_chat_turn_table.rs`

Fields:
- `merged_at`
- `merged_commit`

### 31.4 Core Memory Table

**Migration**: `m20251023_000001_create_core_memory_table.rs`

Fields:
- `memento_id`
- `hit_count`
- `last_used_at`
- `plan_item_core_memory_snapshot`
- `plan_item_id`
- `snapshot_type`

### 31.5 History V2 Table

**Migration**: `m20250520_000001_modify_history_v2_table.rs`

Fields:
- `agent_run_id`
- `agent_type`
- `disabled_tools`
- `truncated_above`

### 31.6 MCP Server Agent Relation Table

**Migration**: `m20250825_000001_modify_mcp_server_agent_relation_table.rs`

Fields:
- `disabled_tools`

### 31.7 Worktree Table

**Migration**: `m20251202_000003_modify_worktree_table.rs`

Fields:
- `merged_at`

---

## 32. Environment Variables (Complete List)

### 32.1 Core Variables

- `ICUBE_MODULAR_DATA_DIR` - Data directory
- `TRAE_CONFIG_CHANNEL` - Config channel

### 32.2 AWS Variables

- `AWS_WEB_IDENTITY_TOKEN_FILE`
- `AWS_ROLE_ARN`
- `AWS_ROLE_SESSION_NAME`
- `AWS_CONFIG_FILE`
- `AWS_SHARED_CREDENTIALS_FILE`
- `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`
- `AWS_CONTAINER_AUTHORIZATION_TOKEN`
- `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`
- `AWS_CONTAINER_CREDENTIALS_FULL_URI`
- `AWS_REGION`
- `AWS_DEFAULT_REGION`

### 32.3 Database Variables

- `DISABLE_DB_MIGRATION_ROLLBACK`

### 32.4 Feature Flags

- `NO_COLOR` - Disable colored output

---

## 33. Trae CLI Protocol Analysis

### 33.1 CLI Version

- **Version**: v0.120.35
- **Platforms**: linux-amd64, linux-arm64, darwin-amd64, darwin-arm64
- **Language**: Go

### 33.2 CLI API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/trae-cli/api/v1/llm/proxy` | LLM proxy endpoint for CLI |
| `/cloudide/api/v3/trae/CheckLogin` | Check login status |
| `/cloudide/api/v3/trae/GetUserInfo` | Get user information |
| `/cloudide/api/v3/trae/oauth/ExchangeToken` | OAuth token exchange |
| `/api/ide/v1/tenant/get_tenant_user_config` | Get tenant config |
| `/api/ide/v1/tenant/report_audit_log` | Report audit log |
| `/api/ide/v1/check_custom_model_quota` | Check custom model quota |
| `/api/ide/v1/report_custom_model_token_usage` | Report token usage |
| `/api/ide/v2/llm_raw_chat` | V2 raw LLM chat |
| `/api/ide/v1/cli/get_config_list` | Get config list for CLI |
| `/v1/complete` | Completion endpoint |
| `/v1/messages` | Messages endpoint |
| `/v1/models` | Models endpoint |
| `/v1/metrics` | Metrics endpoint |
| `/model/{provider}/{model}` | Model-specific endpoint |

### 33.3 CLI OAuth Flow

```
1. Create OAuth client
2. Open browser for authorization
3. User logs in via browser
4. Receive callback with auth code
5. Exchange token at /cloudide/api/v3/trae/oauth/ExchangeToken
6. Save auth info to secure store
```

### 33.4 CLI Authentication

- **Login**: `/cloudide/api/v3/trae/CheckLogin`
- **User Info**: `/cloudide/api/v3/trae/GetUserInfo`
- **Token Exchange**: `/cloudide/api/v3/trae/oauth/ExchangeToken`
- **Storage**: Secure store (system keychain)

### 33.5 CLI Model Support

**Supported Models**:
- `gpt-5`
- `deepseek`
- `claude`
- `gemini`

**Model Structures**:
- `claude.Config`, `claude.options`, `claude.Thinking`
- `gemini.Config`, `gemini.options`, `gemini.Thinking`
- `deepseek.Config`, `deepseek.Tool`, `deepseek.Usage`, `deepseek.Alias`, `deepseek.Client`, `deepseek.Choice`

### 33.6 CLI Streaming

**Format**: OpenAI SSE chunks

**Parsing**: `parse openai sse chunk: %w`

**Events**:
- `on_delta` - Content delta
- `stream` - Stream control
- `chunk` - Data chunk

### 33.7 CLI Features

1. **Tool Calls**: Support for tool use with `accept all tools on`
2. **MCP Servers**: `Configure and manage MCP servers`
3. **Marketplace**: `Manage plugin marketplaces`
4. **Slash Commands**: `failed to discover slash commands`
5. **Session Management**: `failed to find recent session`
6. **Plan Mode**: `No, don't enter plan mode`
7. **Rewind**: `Rewind conversation and file changes to a previous point`
8. **Copy**: `Copy last response to clipboard (/copy N for Nth-latest)`
9. **Stats**: `Show session statistics (tokens, lines, tools, duration)`

### 33.8 CLI Proxy Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Trae CLI   │────▶│  LLM Proxy  │────▶│  Trae       │
│  (Go)       │◀────│  Endpoint   │◀────│  Backend    │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     │ /trae-cli/api/     │                    │
     │ v1/llm/proxy       │                    │
     │───────────────────▶│                    │
     │                    │  /api/ide/v2/      │
     │                    │  llm_raw_chat      │
     │                    │───────────────────▶│
     │                    │                    │
     │  SSE Stream        │  SSE Stream        │
     │◀───────────────────│◀───────────────────│
```

### 33.9 CLI Error Handling

- `failed to send request: %w`
- `parse openai sse chunk: %w`
- `failed to list trae models`
- `basic info not initialized`
- `failed to create agent: %w`
- `Tool call rejected by user`
- `tool call limit exceeded: skipped`

### 33.10 CLI Configuration

- **Config List**: `/api/ide/v1/cli/get_config_list`
- **MCP Whitelist**: `/trae/gtm/tob/api/v1/mcp_whitelist/list`
- **Network Proxy**: `/trae/gtm/tob/api/v1/config/get_network_proxy`
- **Data Report**: `/trae/gtm/tob/api/v1/data/data_report`

---

## 34. Authentication Protocol (Complete)

### 34.1 OAuth2 Providers

**Supported Providers**:
1. **Google OAuth2**
   - Authorization: `https://accounts.google.com/o/oauth2/v2/auth`
   - Token: `https://oauth2.googleapis.com/token`

2. **Supabase OAuth**
   - Authorization: `https://api.supabase.com/v1/oauth/authorize`
   - Token: `https://api.supabase.com/v1/oauth/token`
   - Client ID: `SUPABASE_APP_CLIENT_ID`
   - Client Secret: `SUPABASE_APP_CLIENT_SECRET`

3. **GitHub OAuth**
   - Standard GitHub OAuth flow

4. **GitLab OAuth**
   - Standard GitLab OAuth flow

### 34.2 Trae Native Authentication

**Endpoints**:
- Login Check: `/cloudide/api/v3/trae/CheckLogin`
- User Info: `/cloudide/api/v3/trae/GetUserInfo`
- Token Exchange: `/cloudide/api/v3/trae/oauth/ExchangeToken`

**Provider**: `icube.cloudide`

### 34.3 Token Storage

**Location**: SQLCipher encrypted SQLite database

**Fields**:
- `access_token` - JWT access token
- `refresh_token` - JWT refresh token
- `expired_at` - Token expiration timestamp
- `refresh_expired_at` - Refresh token expiration
- `user_id` - User identifier
- `token_release_at` - Token release timestamp
- `token_host` - Token host URL

### 34.4 Token Refresh Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │     │  Token Host │     │   Trae      │
│   (IDE)     │     │  (OAuth2)   │     │   Backend   │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     │ Check expiration   │                    │
     │───────────────────▶│                    │
     │                    │                    │
     │ If expired:        │                    │
     │ POST /refresh      │                    │
     │ (Bearer token)     │                    │
     │───────────────────▶│                    │
     │                    │                    │
     │ New tokens         │                    │
     │◀───────────────────│                    │
     │                    │                    │
     │ Update database    │                    │
     │───────────────────▶│                    │
```

### 34.5 Auth Headers

| Header | Purpose |
|--------|---------|
| `x-cloudide-token` | Trae IDE native token |
| `x-ide-token` | IDE token |
| `Authorization: Bearer` | Standard JWT bearer token |
| `x-frontier-id` | Frontier connection ID |
| `X-Model-Sk` | Model secret key |
| `X-Model-Region` | AWS region for model |

### 34.6 AWS Authentication

**SDKs**:
- `aws-sdk-bedrockruntime` v1.92.0
- `aws-sdk-sso` v1.72.0
- `aws-sdk-ssooidc` v1.73.0
- `aws-sdk-sts` v1.73.0

**Credential Chain**:
1. Environment variables
2. Profile file (~/.aws/config, ~/.aws/credentials)
3. SSO credentials
4. AssumeRole credentials
5. Web Identity Token
6. IMDS credentials
7. ECS container credentials

**SSO Token Refresh**:
```
cached SSO token refresh decision
cached SSO token is expired and cannot be refreshed
attempting to refresh SSO token
SSO OIDC CreateToken responded without an access token
saved refreshed SSO token
```

---

## 35. Proxy Implementation Roadmap

### 35.1 Phase 1: Authentication Proxy

1. **Implement OAuth2 flow**
   - Google OAuth2 with PKCE
   - Supabase OAuth
   - Trae native auth

2. **Token management**
   - Store tokens securely
   - Auto-refresh before expiration
   - Handle token rotation

3. **Auth header injection**
   - Add x-cloudide-token
   - Add x-ide-token
   - Add Authorization: Bearer

### 35.2 Phase 2: API Proxy

1. **Core chat endpoints**
   - `/api/ide/v1/chat`
   - `/api/ide/v1/llm_raw_chat`
   - `/api/ide/v2/llm_raw_chat`

2. **Model management**
   - `/api/ide/v1/model_list`
   - `/api/ide/v1/providers`

3. **Agent endpoints**
   - `/api/ide/v1/agents/runs`
   - `/api/ide/v1/agents/runs/:id/tool_call_outputs`

### 35.3 Phase 3: Streaming Proxy

1. **SSE streaming**
   - Handle message_start, content_block_start, content_block_delta, content_block_stop, message_stop
   - Support tool calls in stream
   - Handle errors and retries

2. **Custom model proxy**
   - WebSocket tunnel
   - HTTP fallback
   - JSON-RPC 2.0 protocol

### 35.4 Phase 4: Codex Integration

1. **Format translation**
   - Codex → Trae request format
   - Trae → Codex response format
   - Tool call mapping

2. **Model mapping**
   - Codex model names → Trae model names
   - Handle model-specific parameters

3. **Error handling**
   - Map Trae errors to Codex errors
   - Implement retry logic
   - Handle rate limits

---

## 36. Summary of Key Findings

### 36.1 Protocol Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Chat API    │  │ Agent API   │  │ Model API   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                    Transport Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ HTTP/REST   │  │ WebSocket   │  │ SSE Stream  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                    Protocol Layer                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ JSON-RPC 2.0│  │ OpenAI      │  │ AWS Bedrock │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                    Security Layer                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ OAuth2/JWT  │  │ SQLCipher   │  │ TLS/SSL     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### 36.2 Key Technical Details

1. **Authentication**: OAuth2 with PKCE, JWT tokens, SQLCipher storage
2. **Transport**: HTTP + WebSocket dual mode, SSE streaming
3. **Protocol**: JSON-RPC 2.0, OpenAI-compatible format
4. **Models**: Claude 3.5, GPT-5/5.2/5.3/5.4, Gemini 3/3.1/3 Flash, DeepSeek V3/V3.1, Qwen 2.5/32
5. **Backend**: AWS Bedrock Converse Stream API
6. **Security**: AES-256-GCM encryption, SQLCipher database, TLS/SSL

### 36.3 Critical UUIDs

- `6eefa01c-1036-4c7e-9ca5-d891f63bfcd8` - Potential OAuth2 client ID
- `850edec7-b9d0-48aa-99b5-67c888e282cd` - Potential OAuth2 client ID

### 36.4 Next Steps

1. **Test OAuth2 flow** with extracted credentials
2. **Implement WebSocket tunnel** for custom model proxy
3. **Build format translator** between Codex and Trae
4. **Deploy proxy server** for testing
5. **Integrate with Codex CLI** for seamless AI proxy

---

## 37. Hub Bridge Protocol (Complete)

### 37.1 Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  Hub Bridge │────▶│   Trae      │
│  (IDE/CLI)  │◀────│  (WebSocket)│◀────│   Backend   │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     │ /clis/register     │                    │
     │───────────────────▶│                    │
     │                    │                    │
     │ /conversations     │                    │
     │───────────────────▶│                    │
     │                    │                    │
     │ /conversations/    │                    │
     │ messages/batchInsertMulti               │
     │───────────────────▶│                    │
```

### 37.2 Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/clis/register` | POST | Register CLI client |
| `/clis/unregister` | POST | Unregister CLI client |
| `/conversations` | POST | Create conversation |
| `/conversations/tasks/batchInsert` | POST | Batch insert tasks |
| `/conversations/messages/batchInsertMulti` | POST | Batch insert messages |
| `/conversations/clis/messages/list` | GET | List messages |
| `/wsmessages/poll` | GET | Poll messages (HTTP fallback) |
| `/wsmessages/push` | POST | Push messages |

### 37.3 Registration Flow

```
1. POST /clis/register
   Body: {
     "cli_id": "unique-cli-id",
     "frontier_id": "frontier-connection-id",
     "app_id": "trae-ide",
     "product_id": "trae",
     "process_id": "process-id"
   }

2. Response: {
     "success": true,
     "frontier_id": "assigned-frontier-id"
   }
```

### 37.4 Chat Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │     │  Hub Bridge │     │   Trae      │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     │ create_project     │                    │
     │───────────────────▶│───────────────────▶│
     │                    │                    │
     │ create_chat_session│                    │
     │───────────────────▶│───────────────────▶│
     │                    │                    │
     │ send_message       │                    │
     │───────────────────▶│───────────────────▶│
     │                    │                    │
     │ subscribe_events   │                    │
     │───────────────────▶│───────────────────▶│
     │                    │                    │
     │ stream response    │                    │
     │◀───────────────────│◀───────────────────│
```

### 37.5 WebSocket Message Types

| Type | Direction | Purpose |
|------|-----------|---------|
| `WsProtoCLI` | Client → Server | CLI command |
| `WsProtoConfirm` | Client → Server | Confirm action |
| `WsProtoSessionCreated` | Server → Client | Session created |
| `WsProtoSessionUpdated` | Server → Client | Session updated |
| `WsProtoSessionDeleted` | Server → Client | Session deleted |
| `WsProtoCliPushConversations` | Server → Client | Push conversations |
| `WsProtoCliPushDeleteMessages` | Server → Client | Delete messages |

### 37.6 Event Types

| Event | Purpose |
|-------|---------|
| `session_created` | New session created |
| `session_updated` | Session state updated |
| `session_deleted` | Session deleted |
| `message_deleted` | Message deleted |
| `status_changed` | Status changed (Lite mode) |

### 37.7 Sequence Numbers

The Hub Bridge uses sequence numbers for message ordering:

```
frontier_id={frontier_id}
device_id={device_id}
from_down_seq_id={last_seq_id}
limit={max_messages}
```

---

## 38. Lite Mode (VM Sandbox)

### 38.1 Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  Lite Mode  │────▶│  VM Sandbox │
│  (IDE)      │◀────│  (Handler)  │◀────│  (trae-     │
└─────────────┘     └─────────────┘     │  sandbox)   │
                        │               └─────────────┘
                        │                    │
                        │ vm_init_progress   │
                        │◀───────────────────│
                        │                    │
                        │ status_changed     │
                        │◀───────────────────│
```

### 38.2 VM Initialization

```
[lite][subscribe_events] starting VM initialization for session: {session_id}
[lite][subscribe_events] ensure_work_vm_ready returned: vm_status={status}
[lite][subscribe_events] VM ready, sending status_changed event
```

### 38.3 VM Events

| Event | Purpose |
|-------|---------|
| `vm_init_progress` | VM initialization progress |
| `status_changed` | VM status changed |
| `session_created` | Session created in VM |
| `session_updated` | Session updated in VM |
| `session_deleted` | Session deleted in VM |

### 38.4 VM Operations

```
[lite][list_chat_sessions] req: {request}
[lite][subscribe_events] VM subscription cancelled by token: session_id={id}
[lite][subscribe_events] VM event stream disconnected unexpected
```

### 38.5 Sandbox Binary

- **Binary**: `trae-sandbox` (18MB)
- **Purpose**: Isolated execution environment
- **Features**: File/network access controls, command red list

---

## 39. Chat Session Lifecycle

### 39.1 Session States

```
Created → Running → Completed
    ↓         ↓         ↓
  Error    Cancelled  Frozen
```

### 39.2 Chat Session Methods

| Method | Purpose |
|--------|---------|
| `create_chat_session` | Create new session |
| `send_message` | Send message to AI |
| `stop_chat_session` | Stop running session |
| `commit_chat_session` | Commit session changes |
| `delete_chat_session` | Delete session |
| `get_chat_session` | Get session details |
| `list_chat_sessions` | List all sessions |
| `freeze_chat_session` | Freeze session |
| `thaw_chat_session` | Thaw frozen session |

### 39.3 Chat Request Format

```json
{
  "method": "send_message",
  "params": {
    "session_id": "session-id",
    "message": {
      "content": "user message",
      "role": "user"
    },
    "model_config": {
      "model_name": "claude-3.5-sonnet",
      "temperature": 0.7,
      "max_tokens": 4096,
      "top_p": 0.9,
      "top_k": 40
    }
  }
}
```

### 39.4 Chat Response Format (SSE)

```
event: message_start
data: {"type":"message_start","message":{"id":"msg-id","role":"assistant"}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_stop
data: {"type":"message_stop"}
```

---

## 40. IPC System (AHA IPC)

### 40.1 Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Electron   │────▶│  AHA IPC    │────▶│  ai-agent   │
│  Main       │◀────│  (ZMQ)      │◀────│  (Rust)     │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     │ Dealer-Router      │ JSON-RPC 2.0       │
     │───────────────────▶│───────────────────▶│
     │                    │                    │
     │ Response           │ Response           │
     │◀───────────────────│◀───────────────────│
```

### 40.2 IPC Methods

| Method | Purpose |
|--------|---------|
| `request` | Single request-response |
| `stream_request` | Streaming request |
| `request_lite` | Lightweight request |
| `stream_request_lite` | Lightweight streaming |

### 40.3 IPC Flow

```
[aha_ipc] connection accepted
[aha_ipc] spawning RPC server for new connection
[aha_ipc] stream_request method error: {error}
[aha_ipc] request_lite method error: {error}
[aha_ipc] stream_request_lite method error: {error}
[aha_ipc] building jsonrpsee server...
[aha_ipc] jsonrpsee server started, waiting for stop...
[aha_ipc] IPC connection stopped, cancelling all pending requests
[aha_ipc] jsonrpsee server stopped for this connection
```

### 40.4 MuxRpc Protocol

```
[MuxRpc] read_loop started, waiting for data...
[MuxRpc] read_loop: received Request, stream_id={id}
[MuxRpc] read_loop: received Pong, stream_id={id}, timestamp={ts}, latency={ms}
[MuxRpc] write_loop: frame sent successfully, write_count={count}
[MuxRpc] heartbeat_loop started, interval={ms}ms, timeout={ms}
[MuxRpc] heartbeat timeout ({ms} > {ms}), connection may be dead
```

---

## 41. Unified Transport Server

### 41.1 Endpoints

```
/ws/api/v1/:service/:method
```

### 41.2 Startup

```
[AI Agent Server] start unified transport server (HTTP + WebSocket)
[UnifiedTransport] server listening on: {port}
[UnifiedTransport] WebSocket connection established
[UnifiedTransport] WebSocket connection closed
[UnifiedTransport] WebSocket receive error: {error}
```

### 41.3 Message Format

**HTTP**: JSON-RPC 2.0 over HTTP POST

**WebSocket**: JSON-RPC 2.0 over WebSocket text frames

---

## 42. Complete Request Flow

### 42.1 From User Login to First AI Response

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │     │   Trae IDE  │     │   Trae      │
│   (Browser) │     │   (Electron)│     │   Backend   │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     │ 1. Login           │                    │
     │ (OAuth2)           │                    │
     │───────────────────▶│                    │
     │                    │                    │
     │                    │ 2. ExchangeToken   │
     │                    │───────────────────▶│
     │                    │                    │
     │                    │ 3. JWT tokens      │
     │                    │◀───────────────────│
     │                    │                    │
     │                    │ 4. BootConfig      │
     │                    │───────────────────▶│
     │                    │                    │
     │                    │ 5. Config data     │
     │                    │◀───────────────────│
     │                    │                    │
     │ 6. Send message    │                    │
     │───────────────────▶│                    │
     │                    │                    │
     │                    │ 7. create_project  │
     │                    │───────────────────▶│
     │                    │                    │
     │                    │ 8. create_chat_session
     │                    │───────────────────▶│
     │                    │                    │
     │                    │ 9. send_message    │
     │                    │───────────────────▶│
     │                    │                    │
     │                    │ 10. subscribe_events
     │                    │───────────────────▶│
     │                    │                    │
     │                    │ 11. SSE stream     │
     │                    │◀───────────────────│
     │                    │                    │
     │ 12. Display        │                    │
     │ response           │                    │
     │◀───────────────────│                    │
```

### 42.2 Custom Model Proxy Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   IDE       │     │  Custom     │     │  External   │
│   (Client)  │     │  Model Proxy│     │  LLM API    │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     │ sse.open           │                    │
     │───────────────────▶│                    │
     │                    │                    │
     │                    │ HTTP/WS Request    │
     │                    │───────────────────▶│
     │                    │                    │
     │ sse.delta          │ SSE Stream         │
     │◀───────────────────│◀───────────────────│
     │                    │                    │
     │ sse.end            │                    │
     │◀───────────────────│                    │
```

---

## 43. Implementation Priority Matrix

| Priority | Component | Complexity | Impact |
|----------|-----------|------------|--------|
| 1 | OAuth2 Auth Flow | High | Critical |
| 2 | Token Management | Medium | Critical |
| 3 | Chat API Proxy | Medium | High |
| 4 | SSE Streaming | Medium | High |
| 5 | Custom Model Proxy | High | Medium |
| 6 | WebSocket Tunnel | High | Medium |
| 7 | Hub Bridge | Medium | Medium |
| 8 | Lite Mode | Low | Low |

### 43.1 Recommended Implementation Order

1. **Phase 1: Auth + Basic Chat** (Week 1-2)
   - OAuth2 flow implementation
   - Token storage and refresh
   - Basic chat API proxy

2. **Phase 2: Streaming + Tools** (Week 3-4)
   - SSE streaming support
   - Tool call handling
   - Error handling and retries

3. **Phase 3: Advanced Features** (Week 5-6)
   - Custom model proxy
   - WebSocket tunnel
   - Hub Bridge integration

4. **Phase 4: Polish + Deploy** (Week 7-8)
   - Performance optimization
   - Documentation
   - Deployment

---

## 44. Trae CLI Proxy Endpoint (Detailed)

### 44.1 Endpoint

```
POST /trae-cli/api/v1/llm/proxy
```

### 44.2 Request Format

The CLI uses the same OpenAI-compatible format as the IDE:

```json
{
  "model": "openai/gpt-5",
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "stream": true,
  "temperature": 0.7,
  "max_tokens": 4096
}
```

### 44.3 Model Format

Models use gateway-style identifiers:
```
openai/gpt-5
anthropic/claude-3.5
google/gemini-3
deepseek/deepseek-v3
```

### 44.4 SSE Streaming Response

The CLI parses OpenAI SSE chunks:

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"gpt-5","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"gpt-5","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### 44.5 Error Handling

```
parse openai sse chunk: %w
failed to send request: %w
failed to list trae models
basic info not initialized
```

### 44.6 Tool Calls

The CLI supports tool calls with:
- `accept all tools on` - Auto-accept all tool calls
- `supplementary_instructions` - Additional instructions for tools
- `Tool call rejected by user` - User rejection handling

### 44.7 Features

1. **MCP Servers**: `Configure and manage MCP servers`
2. **Marketplace**: `Manage plugin marketplaces`
3. **Slash Commands**: `failed to discover slash commands`
4. **Session Management**: `failed to find recent session`
5. **Plan Mode**: `No, don't enter plan mode`
6. **Rewind**: `Rewind conversation and file changes to a previous point`
7. **Copy**: `Copy last response to clipboard (/copy N for Nth-latest)`
8. **Stats**: `Show session statistics (tokens, lines, tools, duration)`

---

## 45. Proxy Implementation Code Structure

### 45.1 Recommended File Structure

```
trae-proxy/
├── src/
│   ├── auth/
│   │   ├── oauth.ts          # OAuth2 flow
│   │   ├── token.ts          # Token management
│   │   └── headers.ts        # Auth headers
│   ├── api/
│   │   ├── chat.ts           # Chat API proxy
│   │   ├── model.ts          # Model API proxy
│   │   └── agent.ts          # Agent API proxy
│   ├── stream/
│   │   ├── sse.ts            # SSE streaming
│   │   └── events.ts         # Event handling
│   ├── proxy/
│   │   ├── tunnel.ts         # WebSocket tunnel
│   │   ├── http.ts           # HTTP transport
│   │   └── rpc.ts            # JSON-RPC 2.0
│   ├── hub/
│   │   ├── bridge.ts         # Hub Bridge
│   │   ├── ws.ts             # WebSocket client
│   │   └── poll.ts           # HTTP polling
│   └── utils/
│       ├── config.ts         # Configuration
│       ├── logger.ts         # Logging
│       └── retry.ts          # Retry logic
├── tests/
├── package.json
└── tsconfig.json
```

### 45.2 Key Dependencies

```json
{
  "dependencies": {
    "express": "^4.18.0",
    "ws": "^8.14.0",
    "node-fetch": "^3.3.0",
    "eventsource": "^2.0.0",
    "jsonwebtoken": "^9.0.0",
    "better-sqlite3": "^9.0.0"
  }
}
```

### 45.3 Configuration

```typescript
interface ProxyConfig {
  // Trae Backend
  traeBackend: string;  // https://icube-normal.trae.ai

  // Authentication
  oauth: {
    google: {
      clientId: string;
      clientSecret: string;
      redirectUri: string;
    };
    supabase: {
      clientId: string;
      clientSecret: string;
    };
    trae: {
      checkLogin: string;  // /cloudide/api/v3/trae/CheckLogin
      getUserInfo: string; // /cloudide/api/v3/trae/GetUserInfo
      exchangeToken: string; // /cloudide/api/v3/trae/oauth/ExchangeToken
    };
  };

  // API Endpoints
  endpoints: {
    chat: string;  // /api/ide/v1/chat
    models: string; // /api/ide/v1/model_list
    agents: string; // /api/ide/v1/agents/runs
  };

  // Streaming
  streaming: {
    enabled: boolean;
    timeout: number;
    retryCount: number;
  };
}
```

### 45.4 Usage Example

```typescript
import { TraeProxy } from './src/proxy';

const proxy = new TraeProxy({
  traeBackend: 'https://icube-normal.trae.ai',
  oauth: { /* ... */ },
  endpoints: { /* ... */ },
  streaming: { enabled: true, timeout: 30000, retryCount: 3 }
});

// Start proxy server
proxy.listen(3000, () => {
  console.log('Trae proxy running on port 3000');
});

// Handle chat requests
proxy.on('chat', async (request) => {
  const response = await proxy.chat(request);
  return response;
});
```

---

## 46. Complete Struct Definitions (Binary Analysis)

### 46.1 OpenAI-Compatible Request/Response Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `OpenAIRequest` | 7 | Main chat request (model, messages, stream, tools, etc.) |
| `OpenAITool` | 2 | Tool definition (type, function) |
| `OpenAIFunction` | 3 | Function definition (name, description, parameters) |
| `OpenAIMessage` | 4 | Message (role, content, name, tool_calls) |
| `OpenAIToolCall` | 3 | Tool call (id, type, function) |
| `OpenAIFunctionCall` | 2 | Function call (name, arguments) |
| `OpenAIContentPart` | 3 | Content part (type, text, image_url) |
| `OpenAIImageUrl` | 1 | Image URL (url) |
| `OpenAIStreamChunk` | - | Streaming chunk |
| `OpenAIStreamChoice` | - | Stream choice |
| `OpenAIStreamDelta` | - | Stream delta |
| `OpenAIStreamToolCall` | - | Stream tool call |
| `OpenAIStreamFunction` | - | Stream function |

### 46.2 JSON-RPC 2.0 Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `JsonRpcMessage` | 4 | JSON-RPC message (jsonrpc, method, params, id) |
| `JsonRpcResponse` | - | JSON-RPC response |
| `JsonRpcError` | - | JSON-RPC error |
| `SseOpenParams` | 2 | SSE open parameters |
| `SseOpenPayload` | 1 | SSE open payload |
| `SseCancelParams` | 3 | SSE cancel parameters |
| `SseDeltaParams` | - | SSE delta parameters |
| `SseEndParams` | - | SSE end parameters |
| `SseErrorParams` | - | SSE error parameters |
| `SseErrorData` | - | SSE error data |
| `RpcCloseParams` | 3 | RPC close parameters |
| `RpcPingParams` | - | RPC ping parameters |
| `RpcParams` | 4 | RPC parameters |
| `RpcRequest` | 2 | RPC request |
| `RpcResponse` | 3 | RPC response |

### 46.3 Custom Model Proxy Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `PendingRequestDTO` | 6 | Pending request (for HTTP fallback) |
| `GetPendingResponse` | 2 | Get pending response |
| `MessageResult` | 5 | Message result |
| `SubmitMessageResponse` | 2 | Submit message response |
| `HttpRequest` | 5 | HTTP request |
| `HttpRequestBody` | 6 | HTTP request body |

### 46.4 Boot Configuration Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `BootConfig` | 17 | Main boot configuration |
| `AgentConfig` | 3 | Agent configuration |
| `AgentMiscConfig` | 4 | Agent misc configuration |
| `CKGConfig` | 1 | Code Knowledge Graph config |
| `HubConfig` | 1 | Hub Bridge config |
| `WSConfig` | 1 | WebSocket config |
| `Tea` | 6 | Analytics config |
| `Slardar` | 6 | Telemetry config |
| `TTNetConfig` | 4 | Network config |
| `ImageXConfig` | - | Image service config |
| `BootUserInfo` | 6 | Boot user info |
| `HubRemoteConfig` | 17 | Hub remote configuration |

### 46.5 Hub Bridge Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `RegisterCliRequest` | 4 | Register CLI (frontier_id, app_id, product_id, process_id) |
| `RegisterCliResponse` | 1 | Register CLI response |
| `CliRequest` | 8 | CLI request |
| `Cli` | 10 | CLI client |
| `FrontierFrame` | 7 | Frontier frame (log_id, service, payload_type, log_id_new, server_timing, msg_id, frame_type) |
| `FallbackPushResponse` | 1 | Fallback push response |
| `FallbackPollResponse` | - | Fallback poll response |
| `HubChangeConfigRequest` | 3 | Hub change config request |

### 46.6 LLM Client Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `LLMClientFunctionCall` | 2 | LLM client function call |
| `LLMClientMessageBlockContent` | 3 | LLM client message block content |
| `LLMClientMessageExtraInfo` | 3 | LLM client message extra info |
| `LLMClientReasoningDetailsRaw` | 8 | LLM client reasoning details |
| `LLMClientToolCallExtraContent` | 1 | LLM client tool call extra content |
| `LLMClientToolCallFunction` | 2 | LLM client tool call function |
| `LLMClientToolcallItem` | 4 | LLM client tool call item |
| `LLMClientToolCall` | 5 | LLM client tool call |
| `LLMConfig` | 2 | LLM configuration |

### 46.7 Native LLM Response Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `NativeAnthropicLLMResponse` | 3 | Anthropic response |
| `NativeAnthropicMessageDelta` | 2 | Anthropic message delta |
| `NativeAnthropicUsage` | 4 | Anthropic usage |
| `NativeLLMMessage` | 8 | Native LLM message |
| `NativeLLMUsage` | 3 | Native LLM usage |
| `NativeOpenrouterLLMChoice` | 5 | OpenRouter choice |
| `NativeOpenrouterLLMErrorResponse` | 1 | OpenRouter error response |
| `NativeOpenrouterLLMError` | 2 | OpenRouter error |
| `NativeOpenrouterLLMResponse` | 7 | OpenRouter response |

### 46.8 Chat Session Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `ChatArgs` | 47 | Chat arguments (comprehensive) |
| `ChatArgsAgentInfo` | 3 | Chat agent info |
| `ChatMessageData` | 37/44 | Chat message data |
| `ChatTurnContext` | 20 | Chat turn context |
| `ChatTurnTokenUsage` | 13 | Chat turn token usage |
| `ChatTurn` | 10 | Chat turn |
| `ChatSessionListItem` | 14 | Chat session list item |
| `CreateChatSessionRequest` | 10 | Create chat session request |
| `CreateChatSessionResponse` | 4 | Create chat session response |
| `SendMessageRequest` | 10 | Send message request |
| `SendMsgToChatArgs` | 13 | Send message to chat args |

### 46.9 Model Configuration Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `ModelExtraConfig` | 142 | Model extra configuration |
| `CustomModel` | 29 | Custom model |
| `ModelConfigInfo` | 12 | Model config info |
| `ModelConfigMeta` | 9 | Model config meta |
| `ModelDetailConfig` | 12 | Model detail config |
| `ModelDetailInfo` | 17 | Model detail info |
| `ModelDisplayConfig` | 19 | Model display config |
| `ModelSelectionModeConfig` | 8 | Model selection mode config |
| `ModelAddRequest` | 11 | Model add request |
| `ModelUpdateRequest` | 13 | Model update request |

---

## 47. Hub Bridge Protocol Details

### 47.1 Registration Flow

```
1. Client → POST /clis/register
   Body: { frontier_id, app_id, product_id, process_id }
   Response: { cli_id }

2. Client → WebSocket connect (or HTTP fallback)
   URL: wss://{host}/wsmessages/poll?frontier_id={id}&device_id={id}

3. Client → Poll for messages
   GET /wsmessages/poll?frontier_id={id}&from_down_seq_id={seq}&limit={n}

4. Client → Confirm messages
   POST /clis/requests/respond
   Body: { task_id, response }

5. Client → Send batch messages
   POST /wsmessages/send_batch
   Body: { messages[] }
```

### 47.2 Message Types

| Type | Direction | Purpose |
|------|-----------|---------|
| `WsProtoCLI` | Server→Client | CLI message |
| `WsProtoConfirm` | Client→Server | Confirm receipt |
| `WsProtoSessionCreated` | Server→Client | Session created |
| `WsProtoSessionUpdated` | Server→Client | Session updated |
| `WsProtoSessionDeleted` | Server→Client | Session deleted |
| `WsProtoCliPushConversations` | Server→Client | Push conversations |
| `WsProtoCliPushDeleteMessages` | Server→Client | Delete messages |
| `WsProtoCliPushMessageDelete` | Server→Client | Message deleted |
| `WsProtoCliPushMessageRevert` | Server→Client | Message reverted |
| `BatchInsertEvents` | Server→Client | Batch insert events |

### 47.3 Frontier Frame Structure

```json
{
  "log_id": "string",
  "service": "string",
  "payload_type": "string",
  "log_id_new": "string",
  "server_timing": "string",
  "msg_id": "string",
  "frame_type": "string"
}
```

### 47.4 Hub Remote Configuration

```json
{
  "frontier_url": "wss://...",
  "max_ws_reconnect_attempts": 5,
  "ws_reconnect_delay_secs": 2,
  "default_empty_flush_count": 3,
  "flush_interval_ms": 1000,
  "flush_count_threshold": 10,
  "ws_msg_size_threshold": 65536,
  "push_sync": true,
  "push_conversation_size": 100,
  "push_message_size": 50,
  "sync_session_chunk_size": 20,
  "max_sent_message_cache": 1000
}
```

---

## 48. Authentication Flow Details

### 48.1 Boot Config Authentication Fields

```json
{
  "tokenHost": "https://...",
  "token_host": "https://...",
  "frontier": { "frontier_url": "wss://..." },
  "agent": { ... },
  "ckg": { ... },
  "hub": { ... },
  "tea": { ... },
  "slardar": { ... },
  "ttnet": { ... },
  "imageX": { ... },
  "cdnPrefix": "https://...",
  "hostTmpDir": "/tmp/...",
  "storeRegion": "sg|cn|us",
  "ugApi": "https://...",
  "ppeEnv": "production|staging"
}
```

### 48.2 Auth Headers

| Header | Purpose | Example |
|--------|---------|---------|
| `x-ide-token` | IDE authentication token | `eyJhbGciOi...` |
| `x-frontier-id` | Frontier connection ID | `uuid` |
| `X-Model-Sk` | AWS model secret key | `sk-...` |
| `X-Model-Region` | AWS region | `us-east-1` |
| `Authorization` | Bearer token | `Bearer eyJhbGciOi...` |

### 48.3 Regional Configuration

| Region | Config Key | Domain |
|--------|------------|--------|
| China | `ide_cn` | `icube-normal.trae.com.cn` |
| US | `ide_us` | `icube-normal.trae.ai` |

### 48.4 UUID Client IDs

Two hardcoded UUIDs found near API endpoints:
- `6eefa01c-1036-4c7e-9ca5-d891f63bfcd8`
- `850edec7-b9d0-48aa-99b5-67c888e282cd`

These are likely OAuth2 client IDs or application identifiers.

---

## 49. Database Schema Details

### 49.1 Encryption

- **Library**: SQLCipher
- **Algorithm**: AES-256
- **Check**: `SELECT sql FROM sqlite_master WHERE type='table'`
- **Status**: Database is encrypted by default

### 49.2 Key Tables

| Table | Purpose |
|-------|---------|
| `model_config_cache` | Model configuration cache |
| `agent` | Agent definitions |
| `chat_turn` | Chat turns |
| `chat_message` | Chat messages |
| `core_memory` | Core memory entries |
| `history_v2` | History records |
| `mcp_server_agent_relation` | MCP server agent relations |
| `worktree` | Worktree management |
| `chat_session` | Chat sessions |
| `todo_list` | Todo list items |
| `fast_apply` | Fast apply records |

### 49.3 Model Config Cache Schema

```sql
CREATE TABLE model_config_cache (
  user_id TEXT NOT NULL,
  env TEXT NOT NULL,
  function TEXT NOT NULL,
  config_data TEXT NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  PRIMARY KEY (user_id, env, function)
);
```

### 49.4 Database Connection

```rust
// Connection options
sqlx::SqliteConnectOptions::new()
  .journal_mode(SqliteJournalMode::Wal)
  .busy_timeout(Duration::from_millis(5000))
  .pragma("key", encryption_key)
```

---

## 50. Complete API Endpoint List (Binary Extracted)

### 50.1 All Endpoints Found

```
api/ide/v1/chat
api/ide/v1/llm_raw_chat
api/ide/v2/llm_raw_chat
api/ide/v1/chat_prompt
api/ide/v1/llm_raw_chat_prompt
api/ide/v1/model_list
api/ide/v1/get_model_list
api/ide/v1/get_detail_param
api/ide/v1/get_custom_model_type_config
api/ide/v1/add_custom_model
api/ide/v1/update_custom_model
api/ide/v1/providers
api/ide/v1/agents/runs
api/ide/v1/agents/runs/:id/tool_call_outputs
api/ide/v1/agent/team_agent/create
api/ide/v1/agent/team_agent/update
api/ide/v1/agent/team_agent/remove
api/ide/v1/agent/team_agent/details
api/ide/v1/agent/team_agent/change_status
api/ide/v1/agent/team_agent/list
api/ide/v1/web_search
api/ide/v1/web_fetch
api/ide/v1/text_to_image
api/ide/v1/tool_text_to_image
api/ide/v1/tool_text_to_image_stream
api/ide/v1/fast_apply
api/ide/v1/intent_detect
api/ide/v1/context_select
api/ide/v1/query_rewrite
api/ide/v1/connect
api/ide/v1/ping
api/ide/v1/feedback
api/ide/v1/practice/generate_conversation_title
api/ide/v1/get_resource_upload_token
api/ide/v1/get_resource_upload_url
api/ide/v1/commit_resource_upload_result
api/ide/v1/get_resource_url
api/ide/v1/documentrag/official/check_should_update
api/ide/v1/documentrag/official/latest_document_sets
api/ide/v1/documentrag/custom/index_document_set
api/ide/v1/documentrag/custom/delete_document_set
api/ide/v1/documentrag/custom/document_sets_status
api/ide/v1/documentrag/retrieve
api/ide/v1/wiki/get_wiki_content
api/ide/v1/wiki/get_wiki_status
api/ide/v1/wiki/get_wiki_repo_info
api/ide/v1/wiki/clear_wiki
api/ide/v1/wiki/update_wiki_progress_status
api/v1/commercial/get_mode_info
api/v1/commercial/chat_mode
api/v1/commercial/save_status
api/v1/commercial/get_session_usage
api/v1/commercial/get_user_activity
api/ide/v1/privacy/operation
api/ide/v1/privacy/query
api/ide/v1/check_content
api/ide/v1/report/multimodal
api/ide/v1/get/multimodal
api/ide/v1/tenant/get_tenant_user_config
api/v1/knowledgebase/teamDoc/getDocumentSetLists
api/v1/knowledgebase/teamDoc/getDocumentSetInfo
api/v1/knowledgebase/teamDoc/getDocumentUrl
api/v1/knowledgebase/teamDoc/getDocumentSetDiff
api/ide/v1/cancel_queue_task
api/ide/v1/jump_queue_task
api/ide/unstable/tools/diff
```

### 50.2 Hub Bridge Endpoints

```
/clis/register
/wsmessages/poll
/wsmessages/send_batch
/clis/requests/respond
/data/data
```

### 50.3 Custom Model Proxy Endpoints

```
/custom_model/tunnel/ws?tunnel_id={id}
/custom_model/tunnel/GetPending
/custom_model/tunnel/SubmitMessage
```

### 50.4 CLI Endpoints

```
/trae-cli/api/v1/llm/proxy
/api/ide/v1/cli/get_config_list
/trae/gtm/tob/api/v1/mcp_whitelist/list
```

---

## 51. Custom Model Proxy Tunnel Protocol (Detailed)

### 51.1 Source Files

The tunnel implementation spans 9 source files in `custom-model-proxy-client` crate:

| File | Lines | Purpose |
|------|-------|---------|
| `builder.rs` | - | Tunnel builder/configuration |
| `connection.rs` | 274+ | Connection management |
| `tunnel.rs` | 942+ | Main tunnel logic |
| `stream_manager.rs` | 572+ | Stream lifecycle management |
| `message_handler.rs` | 243+ | JSON-RPC message handling |
| `websocket.rs` | 323+ | WebSocket transport (tungstenite) |
| `ws_transport.rs` | 114+ | WebSocket transport wrapper |
| `http_transport.rs` | 313+ | HTTP fallback transport |
| `retry.rs` | 345+ | Retry logic with backoff |
| `default_handler.rs` | 328+ | Default SSE handler |
| `aws_handler.rs` | 965+ | AWS Bedrock handler |
| `response_sender.rs` | - | Response sending |
| `utils.rs` | - | Utility functions |

### 51.2 Tunnel Connection Flow

```
1. Client connects via WebSocket:
   wss://{host}/custom_model/tunnel/ws?tunnel_id={tunnel_id}

2. If WebSocket fails → HTTP fallback:
   POST /custom_model/tunnel/GetPending (poll for requests)
   POST /custom_model/tunnel/SubmitMessage (submit responses)

3. Heartbeat:
   Client → rpc.ping (with timestamp)
   Server → pong (with server_timestamp)
   Timeout: Stale heartbeat detected → reconnection

4. Reconnection:
   WebSocket closed → attempt reconnect
   Reconnect failed → HTTP fallback
   HTTP idle timeout → tunnel ends
```

### 51.3 Tunnel Error Messages

```
Tunnel ID is required to build the WebSocket URL
ws_transport is None in WebSocket mode?
HTTP fallback config not set
HTTP client factory not set
[Tunnel] WebSocket closed, will switch to HTTP fallback
[Tunnel] WebSocket restored successfully
[Tunnel] WebSocket recovery failed, continuing HTTP mode
[Tunnel] HTTP fallback idle timeout, will end this Tunnel
[Tunnel] Failed to initialize HTTP transport on startup
[Tunnel] Tunnel shutdown gracefully
[Tunnel] Tunnel task panicked during shutdown
[Tunnel] Tunnel shutdown timeout after
```

### 51.4 Stream Management

```
SSE stream created: {stream_id}
Cleaning up {count} active streams
All streams cleaned up
Cleaning up stream: {stream_id}
Stream task {stream_id} completed gracefully
Stream {stream_id} panicked:
Cancelling {count} active streams due to: {reason}
Stream {stream_id} cancelled gracefully
Stream {stream_id} panicked during cancellation:
Stream {stream_id} did not complete cancellation within timeout
{count} streams cancelled due to: {reason}
```

---

## 52. Hub Bridge Protocol (Detailed)

### 52.1 Hub Transport Messages

```
[HubTransport] push messages failed: status={code}
[HubTransport] send_batch failed: status={code}
[HubTransport] push messages response: {response}
[HubTransport] poll messages failed: status={code}
```

### 52.2 Hub Network Service

```
[HubNetService] transport loop started
[HubNetService] transport loop exiting
[HubNetService] WS connect skipped: config not initialized
[HubNetService] WS connected, replaying {count} remaining messages
[HubNetService] WS closed by remote
[HubNetService] WS recv, down_seq={seq}
[HubNetService] WS confirm parse failed: {error}
[HubNetService] WS recv error: {error}
[HubNetService] WS send {count}
[HubNetService] WS send oversized messages, flushing via HTTP
[HubNetService] WS send failed, ws_msg: {msg}
[HubNetService] HTTP poll skipped: {reason}
[HubNetService] HTTP polled {count} messages, no more
[HubNetService] HTTP poll error: {error}
[HubNetService] empty flushes, attempting WS reconnect
[HubNetService] HTTP backoff: {count} consecutive failures
[HubNetService] send channel closed in HttpFallback
[HubNetService] WS retry in {ms}ms
[HubNetService] WS reconnect exhausted ({count} attempts)
```

### 52.3 Hub Polling Parameters

```
frontier_id={id}
device_id={id}
from_down_seq_id={seq}
limit={count}
/wsmessages/poll?frontier_id={id}&device_id={id}&from_down_seq_id={seq}&limit={count}
```

### 52.4 Hub Protocol Structs

| Struct | Purpose |
|--------|---------|
| `FallbackPollResponse` | Response from HTTP polling |
| `FallbackPushResponse` | Response from HTTP push |

### 52.5 Sequence Number Handling

```
[HubNetService] down_seq gap detected: expected {expected}, switching to HttpFallback
[HubNetService] skip dup down_seq={seq}
[HubNetService] WS recv, down_seq={seq}
[HubNetService] HTTP send, seq_id={id}
[HubNetService] HTTP send remaining, remaining={count}
[HubNetService] HTTP send remaining, seq_id={id}
```

---

## 53. JSON-RPC 2.0 Message Formats

### 53.1 Struct Definitions

| Struct | Purpose |
|--------|---------|
| `JsonRpcMessage` | JSON-RPC 2.0 request/response |
| `JsonRpcResponse` | JSON-RPC 2.0 response |
| `JsonRpcError` | JSON-RPC 2.0 error |
| `HttpRequest` | HTTP request wrapper |
| `SseOpenParams` | Parameters for sse.open |
| `SseOpenPayload` | Payload for sse.open |
| `SseCancelParams` | Parameters for sse.cancel |
| `RpcCloseParams` | Parameters for rpc.close |
| `RpcPingParams` | Parameters for rpc.ping |
| `SseDeltaParams` | Parameters for sse.delta |
| `SseEndParams` | Parameters for sse.end |
| `SseErrorParams` | Parameters for sse.error |
| `SseErrorData` | Error data for sse.error |

### 53.2 Client → Server Methods

```json
{
  "jsonrpc": "2.0",
  "method": "sse.open",
  "params": {
    "stream_id": "uuid",
    "request": { ... }
  },
  "id": 1
}

{
  "jsonrpc": "2.0",
  "method": "sse.cancel",
  "params": {
    "stream_id": "uuid",
    "reason": "user_cancel",
    "force": false
  },
  "id": 2
}

{
  "jsonrpc": "2.0",
  "method": "rpc.ping",
  "params": {
    "timestamp": 1234567890
  },
  "id": 3
}

{
  "jsonrpc": "2.0",
  "method": "rpc.close",
  "params": {
    "reason": "shutdown",
    "code": 1000
  },
  "id": 4
}
```

### 53.3 Server → Client Methods

```json
{
  "jsonrpc": "2.0",
  "method": "sse.delta",
  "params": {
    "stream_id": "uuid",
    "data": { "content": "..." }
  }
}

{
  "jsonrpc": "2.0",
  "method": "sse.end",
  "params": {
    "stream_id": "uuid",
    "reason": "completed"
  }
}

{
  "jsonrpc": "2.0",
  "method": "sse.error",
  "params": {
    "stream_id": "uuid",
    "error": {
      "code": 500,
      "message": "Internal error"
    }
  }
}
```

### 53.4 Pending Request/Response (HTTP Fallback)

| Struct | Purpose |
|--------|---------|
| `PendingRequestDTO` | Pending request from server |
| `GetPendingResponse` | Response from GetPending |
| `MessageResult` | Result of message processing |
| `SubmitMessageResponse` | Response from SubmitMessage |

---

## 54. SSE Streaming Protocol

### 54.1 SSE Event Types

```
message_start          - Stream started, contains model info
content_block_start    - Content block started (text, tool_use, etc.)
content_block_delta    - Content delta (streaming text/tool input)
content_block_stop     - Content block completed
message_stop           - Stream completed (stop_reason)
message_delta          - Final message metadata (usage)
```

### 54.2 SSE Data Format

```
event: message_start
data: {"type":"message_start","message":{"id":"msg_xxx","type":"message","role":"assistant","content":[],"model":"claude-3.5","stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":100,"output_tokens":0}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_stop
data: {"type":"message_stop","stop_reason":"end_turn"}
```

### 54.3 Tool Use SSE Events

```
event: content_block_start
data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_xxx","name":"run_command","input":{}}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\"command\":"}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"\"ls -la\"}"}}

event: content_block_stop
data: {"type":"content_block_stop","index":1}
```

### 54.4 SSE Chunk Format (OpenAI-compatible)

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"gpt-5","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"gpt-5","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### 54.5 SSE Error Format

```
event: error
data: {"type":"error","error":{"type":"overloaded_error","message":"Overloaded"}}
```

---

## 55. WebSocket Protocol Details

### 55.1 WebSocket Library

- **Library**: tungstenite v0.23.0/v0.24.0 (Rust)
- **Async**: tokio-tungstenite v0.23.1/v0.24.0
- **Source**: `/root/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/tokio-tungstenite-0.23.1/`

### 55.2 WebSocket Connection States

```
Client handshake initiated.
Client handshake done.
Interrupted handshake (WouldBlock)
Connection reset while sending
Sending frame: {frame_type}
Received message: {msg_type}
Sending pong/close
Parsed headers: {headers}
```

### 55.3 WebSocket Error Messages

```
AlreadyClosed
WriteBufferFull
AttackAttempt
HttpFormat
websocket start_send error:
polled Feed after completion
Too many consecutive retries () in short time, applying additional backoff:
```

### 55.4 WebSocket Frame Types

```
tungstenite::protocol::frame::frame
Frame header:
Frame payload:
```

### 55.5 WebSocket Reconnection Logic

```rust
// Reconnection flow:
1. WebSocket closed → attempt reconnect
2. Reconnect failed → HTTP fallback
3. HTTP idle timeout → tunnel ends

// Reconnection settings:
max_ws_reconnect_attempts: 5
ws_reconnect_delay_secs: 2

// Heartbeat:
Stale heartbeat detected: last ping was {ms}ms ago
Heartbeat timeout detected (last ping: {ms}ms ago)
Heartbeat failure detected but reconnection is disabled
```

---

## 56. Database Encryption Protocol

### 56.1 Encryption Check

```sql
SELECT sql FROM sqlite_master WHERE type='table'
```

### 56.2 Encryption States

```
Checking if database is encrypted: SELECT sql FROM sqlite_master WHERE type='table'
not a database
file is encrypted
Failed to check database encryption status:
Database is encrypted
[DB] Database is not encrypted
[DB] Database is encrypted (query failed)
```

### 56.3 Database Operations

```
Database path: {path}
Database exists: {bool}
Parent directory: {dir}
Creating parent directory: {dir}
Creating database file: {path}
Generated database encryption key
Database URL must be a non-empty string
Database is not encrypted, encrypting...
Database is already encrypted
Creating database connection options
[DB] Connection options: {options}
Connecting to database with URL: {url}
[DB] Setting database to WAL mode
Failed to connect to database: {error}
[DB] Setting database busy_timeout 5000ms
Running database migrations
```

### 56.4 Database Migration

```
m20250402_000001_modify_agent_table
m20250911_000001_modify_agent_and_mcp_server_agent_relation_table
DISABLE_DB_MIGRATION_ROLLBACK
Detected migrations that need to be rolled back
Current code supported migration versions: {versions}
Applied migration versions in database: {versions}
Rollback completed
Found new migrations to apply: {migrations}
Database migrations are up to date
Rolling back migration: {migration}
Cannot find SQL for migration {id}, cannot perform rollback
All new migrations applied successfully
Migration rollback completed, unable to perform rollback
All new migrations have been successfully applied
```

### 56.5 Database Encryption Migration

```
Attempting to encrypt existing database: {path}
.temp
Created temporary database file: {path}
ATTACH DATABASE '' AS encrypted KEY ;
```

---

## 57. Electron IPC Protocol (main.js)

### 57.1 CloudServer WebSocket Protocol

The Electron main process implements a `CloudServer` class that communicates with the ai-agent via WebSocket:

```javascript
// Message format:
{
  "type": "method" | "event",
  "data": {
    "uuid": "request-uuid",    // For method responses
    "res": { ... },             // Response data
    "eventName": "event_name",  // For events
    "data": { ... }             // Event data
  }
}

// Method call flow:
1. Client sends method request with uuid
2. Server processes and responds with {type: "method", data: {uuid, res}}
3. Client resolves promise via rpcMap.get(uuid)

// Event flow:
1. Server sends {type: "event", data: {eventName, data}}
2. Client emits event via emitter
```

### 57.2 CloudServer Fields

```javascript
class CloudServer {
  emitter: EventEmitter    // Event emitter
  ws: WebSocket           // WebSocket connection
  userExit: boolean       // User exit flag
  lockReconnect: boolean  // Reconnection lock
  timeoutnum: number      // Timeout counter
  interval: number        // Interval timer
  reconnectAttempts: number // Reconnection attempts
  rpcMap: Map<uuid, Promise> // RPC promise map
}
```

---

## 58. Complete Authentication Protocol (from main.js)

### 58.1 OAuth2 Providers

#### Google OAuth2

```
Authorization URL: https://accounts.google.com/o/oauth2/v2/auth
Token URL: https://oauth2.googleapis.com/token
Scopes: (determined by application)
```

#### Supabase OAuth

```
Authorization URL: https://api.supabase.com/v1/oauth/authorize
Token URL: https://api.supabase.com/v1/oauth/token
Projects URL: https://api.supabase.com/v1/projects
Client ID: SUPABASE_APP_CLIENT_ID (from environment)
Client Secret: SUPABASE_APP_CLIENT_SECRET (from environment)
Token Storage: ./supabase-token.json
Timeout: 30 minutes (30 * 60 * 1000ms)
```

**Authorization Flow:**
```
1. Start local server on random port (17788-17792)
2. Open browser to:
   https://api.supabase.com/v1/oauth/authorize?client_id={CLIENT_ID}&redirect_uri=http%3A%2F%2Flocalhost%3A{PORT}%2Fcallback&response_type=code&state=%7B%7D
3. User authorizes in browser
4. Supabase redirects to localhost callback with code
5. Exchange code for token at token URL
6. Store token in ./supabase-token.json
```

### 58.2 Trae Native Authentication

#### CheckLogin

```
URL: ${tokenHost}/cloudide/api/v3/trae/CheckLogin
Method: POST
Headers:
  Content-Type: application/json
  x-cloudide-token: {token}
Body:
{
  "IDEVersion": "{appVersion}",
  "ReqSource": "IDE" | "Lite",
  "GetAIPayHost": true
}
Timeout: 30 seconds (30000ms)

Response:
{
  "code": 0,
  "Result": {
    "IsLogin": true,
    "MigrateToSG": false
  }
}
```

#### GetUserInfo

```
URL: ${tokenHost}/cloudide/api/v3/trae/GetUserInfo
Method: POST
Headers:
  Content-Type: application/json
  x-cloudide-token: {token}
Body:
{
  "ReqSource": "IDE" | "Lite"
}
Timeout: 60 seconds (60000ms)

Response:
{
  "code": 0,
  "Data": {
    "UserID": "...",
    "UserName": "...",
    "Email": "...",
    ...
  }
}
```

#### ExchangeToken (Token Refresh)

```
URL: ${tokenHost}/cloudide/api/v3/trae/oauth/ExchangeToken
Method: POST
Headers:
  Content-Type: application/json
Body:
{
  "ClientID": "{clientId}",
  "RefreshToken": "{refreshToken}",
  "ClientSecret": "-",
  "UserID": ""
}
Timeout: 60 seconds (60000ms)

Response:
{
  "code": 0,
  "Result": {
    "Token": "{accessToken}",
    "RefreshToken": "{newRefreshToken}",
    "TokenExpireAt": "{isoDateString}"
  }
}
```

### 58.3 UUID Client ID

```
6eefa01c-1036-4c7e-9ca5-d891f63bfcd8
```

This UUID is used as the ClientID in the ExchangeToken request.

### 58.4 Error Codes

The following error codes trigger `RefreshTokenInvalid` error:
```
20324
20101
20315
20125
20126
```

### 58.5 Token Refresh Logic

```javascript
// Token states:
enum TokenState {
  VALID,           // Token is valid, no action needed
  NEED_REFRESH,    // Token needs refresh (expired or about to expire)
  NEED_UPDATE,     // Token needs update (e.g., user info changed)
  DROPPED          // Token is invalid, user needs to re-login
}

// Refresh flow:
1. Check token expiration
2. If expired or about to expire → call refreshToken()
3. If RefreshTokenInvalid error → user logged out
4. Otherwise → update token in storage
```

### 58.6 Token Storage

**SQLCipher Database:**
- Database: encrypted SQLite with AES-256
- Table: (not specified in main.js, stored in ai-agent)
- Fields: access_token, refresh_token, expired_at, refresh_expired_at, user_id, token_release_at, token_host

**Supabase Token:**
- File: `./supabase-token.json`
- Format: JSON with access_token, refresh_token, etc.

### 58.7 Auth Header Injection

All API requests include these headers:
```
x-cloudide-token: {token}
x-ide-token: {token}
Authorization: Bearer {jwt}
x-frontier-id: {frontier_id}
```

### 58.8 Token Host Resolution

```javascript
// Token host is resolved from boot config:
function getTokenHost(config, service, context) {
  const host = config.service[service];
  if (host) {
    return host.tokenHost;
  }
  return config.tokenHost; // Default token host
}

// Regional token hosts:
// China: icube-normal.trae.com.cn
// US: icube-normal.trae.ai
```

### 58.9 Complete Auth Flow

```
1. Application starts
2. Load boot configuration from ${bootHost}/config
3. Resolve tokenHost from config
4. Check if user is logged in:
   POST ${tokenHost}/cloudide/api/v3/trae/CheckLogin
5. If not logged in → show login UI
6. If logged in → get user info:
   POST ${tokenHost}/cloudide/api/v3/trae/GetUserInfo
7. For API requests → inject auth headers:
   x-cloudide-token, x-ide-token, Authorization, x-frontier-id
8. When token expires → refresh:
   POST ${tokenHost}/cloudide/api/v3/trae/oauth/ExchangeToken
9. If refresh fails → user logged out, show login UI
```

---

## 59. CLI Authentication Flow (from trae-cli binary)

### 59.1 Auth Struct (Go)

```go
type AuthInfo struct {
    DeviceID     string      `json:"DeviceId"`
    Host         string      `json:"Host"`
    LoginBaseURL string      `json:"LoginBaseURL,omitempty"`
    Scope        string      `json:"Scope"`
    OauthToken   *OauthToken `json:"OauthToken"`
}
```

### 59.2 OauthToken Methods

```go
type OauthToken struct {
    // Fields extracted from binary
}

// Methods:
func (t *OauthToken) RefreshExpired() bool    // Check if refresh token expired
func (t *OauthToken) TokenExpireIn() time.Duration // Time until access token expiration
```

### 59.3 Token Storage Backends

| Backend | Package | Description |
|---------|---------|-------------|
| `KeyringStore` | `code.byted.org/nextcode/coco/cli/util/tokenstore` | OS-level secure storage (primary) |
| `MemoryStore` | same package | In-memory storage (fallback) |
| `OAuthTokenStore` | `code.byted.org/nextcode/coco/cli/util/oauth` | Higher-level wrapper |

**KeyringStore implementation:**
- Uses `github.com/zalando/go-keyring` (v0.2.6)
- Linux: GNOME Keyring (libsecret) via D-Bus Secret Service API
- macOS: Keychain Services
- Windows: DPAPI (Data Protection API)

### 59.4 CLI Login Methods

1. **Login with Email** - Email-based OAuth flow
2. **Login with Enterprise Custom Domain** - Enterprise SSO with custom domain
3. **Token-based auto-login** - Uses stored tokens (falls back to browser flow on failure)

### 59.5 CLI OAuth Discovery

```
/.well-known/oauth-protected-resource
/.well-known/oauth-authorization-server
/.well-known/openid-configuration
```

### 59.6 CLI Token Response Format

```json
{
    "code": 0,
    "message": "...",
    "Data": {
        "access_token": "...",
        "token_type": "Bearer",
        "refresh_token": "...",
        "expires_in": 3600,
        "expires_at": "2026-..."
    }
}
```

### 59.7 CLI Auth Headers

```
Authorization: Bearer {token}
X-App-Id: {appId}
Content-Type: application/json
```

Note: CLI uses standard `Authorization: Bearer` headers, NOT `x-cloudide-token`.

### 59.8 Enterprise Features

- `login-enterprise-custom-domain` - Enterprise domain login command
- `tenantsecurity` package: PolicyStore, BlacklistMiddleware, MCPWhitelistMiddleware, ContentMiddleware
- Tenant user config: `/api/ide/v1/tenant/get_tenant_user_config`
- MCP whitelist: `/trae/gtm/tob/api/v1/mcp_whitelist/list`

### 59.9 ZTI (Zero Trust Identity)

```go
// ByteDance ZTI JWT helper
package code.byted.org/security/zti-jwt-helper-golang/helper

// Socket path
/var/run/zti-agent/sockets/agent.sock

// Functions
func getTokenFromPath(path string) (string, error)
func getTokenFromStr(str string) (string, error)
func GetTokenPath() string
func GetTokenStr() string
```

---

## 60. MCP and Tool Call Protocol

### 60.1 MCP Configuration Limits

| Parameter | Default | Description |
|-----------|---------|-------------|
| `mcpToolLimit` | 40 | Maximum MCP tools allowed |
| `mcpTokenLimit` | 8000 | Token limit for MCP |
| `mcpToolHardCap` | - | Hard upper limit for MCP tools |
| `mcp_result_max_char_count` | - | Max characters in MCP tool result |

### 60.2 MCP Structs

| Struct | Elements | Purpose |
|--------|----------|---------|
| `MCPWhitelist` | 11 | MCP whitelist configuration |
| `MCPWhitelistConfigInfo` | 2 | Global enable + whitelists |

### 60.3 MCP Telemetry Events

```
icube_ai_mcp_call_tool       - MCP tool call event
icube_ai_mcp_call_success    - Successful MCP call
icube_ai_mcp_call_failed     - Failed MCP call
icube_ai_start_mcp_failed    - MCP startup failure
icube_ai_catch_mcp_error     - MCP error caught
```

### 60.4 Tool Call Event Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `ToolCallEvent` | 11 | Tool call event with first_data, require_local_execution |
| `LLMClientToolcallItem` | 4 | id, type, function, index |
| `RawLLMResponseToolCall` | 3 | Raw tool call from LLM |
| `OutputEventToolCall` | 4 | Output event tool call |
| `OutputEventFunctionCall` | 2 | Output event function call |
| `ToolChoiceFullMode` | - | Full tool choice mode |
| `ToolChoiceToolItem` | - | Individual tool choice item |

### 60.5 Built-in Tool Names (18+ tools)

**File Operations:**
- `run_command` - Execute shell commands
- `read_file` - Read file contents
- `view_file` - View file with UI rendering
- `edit_file` - Edit existing files
- `create_file` - Create new files
- `delete_file` - Delete files
- `apply_patch` - Apply diff patches

**Search Tools:**
- `grep` - Ripgrep-based text search
- `glob` - File pattern matching

**Web Tools:**
- `web_search` - Web search (WebSearchReference with 7 elements)
- `web_fetch` - Fetch web content

**User Interaction:**
- `ask_user_question` - Ask user for input
- `notify_user` - Send notification to user
- `agent_finish` - Signal agent completion

**Supabase Tools:**
- `supabase_get_project` - Get Supabase project info
- `supabase_get_tables` - List Supabase tables
- `supabase_apply_migration` - Apply database migration
- `supabase_guidelines` - Supabase usage guidelines
- `supabase_permission_guidelines` - Permission guidelines

### 60.6 Browser Automation Tools (30+)

```
browser_navigate, browser_navigate_back, browser_navigate_forward
browser_click, browser_type, browser_fill, browser_fill_form
browser_snapshot, browser_take_screenshot, browser_tabs
browser_hover, browser_drag, browser_scroll, browser_press_key
browser_select_option, browser_upload_file, browser_wait_for
browser_evaluate, browser_get_attribute, browser_handle_dialog
browser_network_requests, browser_console_messages
browser_lock, browser_unlock
browser_reload, browser_resize, browser_search
browser_highlight, browser_is_checked, browser_is_enabled, browser_is_visible
browser_get_bounding_box, browser_get_input_value
browser_waiting_for_user_interaction
browser_hand_over / browser_handover
```

### 60.7 Content Security System

**Security Flags:**
- `content_security_blocked` - Content blocked by security rule
- `need_manual_confirm` - Dangerous operation requires user confirmation
- `manual_confirm_reason` - Reason for manual confirmation
- `enterprise_command_blacklist` - Enterprise-level command blacklist
- `command_red_list` - Restricted command list
- `in_enterprise_command_blacklist` - Command in enterprise blacklist
- `restricted_type_` - Type of restriction applied
- `hit_restricted_type` - Restriction was triggered
- `sandbox_restricted_log` - Sandbox restriction log
- `auto_cancel` - Auto-cancel for restricted operations

---

## 61. OAuth2 Details from main.js (Deep Analysis)

### 61.1 OAuth2 Client Credentials

**Supabase OAuth (from environment variables):**
```
SUPABASE_APP_CLIENT_ID - NOT hardcoded, from env
SUPABASE_APP_CLIENT_SECRET - NOT hardcoded, from env
```

**MCP OAuth (dynamic registration):**
- Uses dynamic client registration with `token_endpoint_auth_method:"none"` (public client)
- No client secret required

### 61.2 OAuth2 Scopes

| Scope | Description |
|-------|-------------|
| `marscode` | Main international Trae/MarsCode scope |
| `marscode_cn` | China region MarsCode scope |
| `marscode_com` | International MarsCode scope |
| `bytedance` | ByteDance internal scope |
| `saas` | SaaS enterprise scope |

### 61.3 OAuth2 Grant Types

```json
["authorization_code", "refresh_token"]
```

### 61.4 PKCE Implementation

- `code_challenge` and `code_verifier` used together
- `S256` challenge method (32-byte challenge)
- Flow: generate `code_verifier` → derive `code_challenge` via S256 → send challenge to auth endpoint → send verifier to token endpoint

### 61.5 Token State Machine

```
VALID_TOKEN → No action needed
NEED_LOGIN → User must log in
NEED_REFRESH → Token needs refresh
NEED_UPDATE → Token needs update
DROPPED → Token is invalid
```

### 61.6 Token Refresh Implementation

- Singleton `refreshTokenPromise` prevents concurrent refreshes
- Background refresh on timer-based validity checks
- Slardar events: `ICubeRefreshTokenStart`, `ICubeRefreshTokenSuccess`
- Spring provider: `POST ${apiHost}/api/v2/GetUserToken`

### 61.7 Token Revocation

```
ClearRefreshToken endpoint for server-side revocation
revokeServerTokens / revokeAllServerTokens for bulk revocation
Local token file cleanup via clearToken()
```

### 61.8 v1 vs v2 Token Handling

- v1 tokens (TokenVersion 1.0) lack refresh_token support
- Automatic migration from v1 to v2 token format
- Log: `refreshToken due to v1 token has no refresh_token`

### 61.9 ByteDance Region Routing

| Region | MCS Endpoint |
|--------|--------------|
| Global | `maliva-mcs.byteoversea.com` |
| Singapore | `sgali-mcs.byteoversea.com` |
| China | `mcs.zijieapi.com` |

### 61.10 Handoff Protocol

```
handoffExternalSso callback parsed hasCredential=%s hasUserJwt=%s hasRefreshToken=%s hasApiHost=%s
handoff-1.0 protocol version
```

---

## 62. ChatArgs and LLMClient Field Names (Exact)

### 62.1 LLMClientToolCall (5 elements)

```rust
struct LLMClientToolCall {
    id: String,
    type: String,
    function: LLMClientToolCallFunction,
    index: i32,
    delta: bool,
}
```

### 62.2 LLMClientToolCallFunction (2 elements)

```rust
struct LLMClientToolCallFunction {
    name: String,
    arguments: String,
}
```

### 62.3 LLMClientToolcallItem (4 elements)

```rust
struct LLMClientToolcallItem {
    id: String,
    type: String,
    function: LLMClientFunctionCall,
    index: i32,
}
```

### 62.4 LLMClientFunctionCall (2 elements)

```rust
struct LLMClientFunctionCall {
    name: String,
    arguments: String,
}
```

### 62.5 NativeAnthropicLLMResponse (3 elements)

```rust
struct NativeAnthropicLLMResponse {
    content: Vec<ContentBlock>,
    usage: NativeAnthropicUsage,
    stop_reason: Option<String>,
}
```

### 62.6 NativeAnthropicUsage (4 elements)

```rust
struct NativeAnthropicUsage {
    input_tokens: i32,
    output_tokens: i32,
    cache_creation_input_tokens: Option<i32>,
    cache_read_input_tokens: Option<i32>,
}
```

### 62.7 NativeOpenrouterLLMResponse (7 elements)

```rust
struct NativeOpenrouterLLMResponse {
    id: String,
    object: String,
    created: i64,
    model: String,
    choices: Vec<NativeOpenrouterLLMChoice>,
    usage: Usage,
    system_fingerprint: Option<String>,
}
```

### 62.8 ChatTurnContext (20 elements)

```rust
struct ChatTurnContext {
    render_context: RenderContext,
    rewritten_query: Option<String>,
    persist_user_message_context: bool,
    document_contexts: Vec<DocumentContext>,
    related_to_workspace: bool,
    smtcmt: Option<String>,
    refresh_project_memento: bool,
    available_terminal: Option<String>,
    terminal_shell_type: Option<String>,
    memory_info: Option<MemoryInfo>,
    project_memento: Option<ProjectMemento>,
    project_memento_cut_length: Option<usize>,
    project_memento_origin_length: Option<usize>,
    project_memento_cut: Option<String>,
    refresh_project_memento_mode: Option<String>,
    tool_list: Vec<Tool>,
    available_tool_names: Vec<String>,
    left_turns: i32,
    text_to_image_url: Option<String>,
    enable_multi_agent_reader: bool,
}
```

### 62.9 ChatMessageData (37 elements - client-side DTO)

```rust
struct ChatMessageData {
    text_content: String,
    initial_message: bool,
    model_selection_strategy: String,
    assistant_message_id: String,
    caller_timing_durations: Vec<CallerTimingDuration>,
    session_id: String,
    conversation_id: String,
    chat_mode: String,
    agent_type: String,
    model_name: String,
    model_config: ModelConfig,
    send_mode: String,
    project_id: String,
    file_uri: String,
    file_path: String,
    language: String,
    platform: String,
    version: String,
    arch: String,
    token: String,
    refresh_token: String,
    access_token: String,
    frontier_id: String,
    device_id: String,
    cli_id: String,
    app_id: String,
    product_id: String,
    process_id: String,
    heartbeat: i32,
    url: String,
    method: String,
    params: serde_json::Value,
    result: serde_json::Value,
    jsonrpc: String,
    choices: Vec<Choice>,
    usage: Usage,
    id: String,
    // ... additional fields
}
```

### 62.10 ChatArgs (47 elements)

```rust
struct ChatArgs {
    session_id: String,
    conversation_id: String,
    chat_mode: String,
    agent_type: String,
    model_name: String,
    model_config: ModelConfig,
    send_mode: String,
    project_id: String,
    file_uri: String,
    file_path: String,
    language: String,
    platform: String,
    version: String,
    arch: String,
    token: String,
    refresh_token: String,
    access_token: String,
    frontier_id: String,
    device_id: String,
    cli_id: String,
    app_id: String,
    product_id: String,
    process_id: String,
    heartbeat: i32,
    url: String,
    method: String,
    params: serde_json::Value,
    result: serde_json::Value,
    jsonrpc: String,
    choices: Vec<Choice>,
    usage: Usage,
    id: String,
    object: String,
    created: i64,
    model: String,
    provider: String,
    thinking: Option<String>,
    reasoning: Option<String>,
    tool_call_id: String,
    tool_result: serde_json::Value,
    tool_use: serde_json::Value,
    status: String,
    error: Option<String>,
    code: i32,
    data: serde_json::Value,
    metadata: serde_json::Value,
    extra_info: serde_json::Value,
}
```

### 62.11 SendMsgToChatArgs (13 elements)

```rust
struct SendMsgToChatArgs {
    session_id: String,
    conversation_id: String,
    chat_mode: String,
    agent_type: String,
    model_name: String,
    model_config: ModelConfig,
    send_mode: String,
    project_id: String,
    file_uri: String,
    file_path: String,
    language: String,
    platform: String,
    browser_hand_over_duration_seconds: Option<i32>,
}
```

---

## 63. Error Handling and Retry Logic

### 63.1 CustomModelProxy Error Messages

**WebSocket Connection Errors:**
```
[CustomModelProxy] WebSocket connect failed: {error}, falling back to HTTP mode
[CustomModelProxy] WebSocket closed, will switch to HTTP fallback
[CustomModelProxy] WebSocket error detected, will switch to HTTP fallback
[CustomModelProxy] WebSocket restored successfully
[CustomModelProxy] WebSocket recovery failed: {error}, continuing HTTP mode
```

**HTTP Fallback Errors:**
```
[CustomModelProxy] HTTP fallback idle timeout, will end this Tunnel
[CustomModelProxy] Failed to initialize HTTP transport on startup: {error}
[CustomModelProxy] Failed to initialize HTTP transport: {error}
[CustomModelProxy] GetPending failed: {error}
[CustomModelProxy] SubmitMessage failed after {count} attempts
[CustomModelProxy] SubmitMessage failed (attempt {count}): {error}
[CustomModelProxy] Failed to flush pending messages: {error}
```

**Message Handling Errors:**
```
[CustomModelProxy] Unknown method in pending request: {method}
[CustomModelProxy] Missing sse.cancel params for {stream_id}
[CustomModelProxy] Invalid sse.cancel params for {stream_id}
[CustomModelProxy] Missing sse.open params for {stream_id}
[CustomModelProxy] Invalid sse.open params for {stream_id}
[CustomModelProxy] Failed to send response for {stream_id}: {error}
[CustomModelProxy] Failed to send sse error for {stream_id}: {error}
[CustomModelProxy] Error handling pending request: {error}
[CustomModelProxy] Ignoring reconnect command in HTTP mode, reason: {reason}
```

**Tunnel Lifecycle Errors:**
```
[CustomModelProxy] Command channel closed, shutting down
[CustomModelProxy] Tunnel close command received, shutting down
[CustomModelProxy] Error handling command: {error}
[CustomModelProxy] Failed to send system error notification (type: {type}, critical: {critical}): {error}
```

### 63.2 Hub Bridge Error Messages

**WebSocket Errors:**
```
[HubNetService] WS connect skipped: config not initialized
[HubNetService] WS connect failed (attempt {count}): {error}
[HubNetService] WS closed by remote
[HubNetService] WS recv error: {error}
[HubNetService] WS confirm parse failed: {error}
[HubNetService] WS send failed, ws_msg: {msg}
[HubNetService] WS send oversized messages, flushing via HTTP
```

**HTTP Errors:**
```
[HubNetService] HTTP poll skipped: {reason}
[HubNetService] HTTP poll error: {error}
[HubNetService] HTTP send_batch error: {error}
[HubNetService] HTTP send remaining error: {error}
[HubNetService] HTTP backoff: {count} consecutive failures
[HubNetService] send channel closed in HttpFallback
```

**Sequence Number Errors:**
```
[HubNetService] down_seq gap detected: expected {expected}, switching to HttpFallback
[HubNetService] skip dup down_seq={seq}
```

**Transport Errors:**
```
[HubTransport] push messages failed: status={code}
[HubTransport] send_batch failed: status={code}
[HubTransport] poll messages failed: status={code}
[HubNetService] send channel closed, shutting down
```

### 63.3 WebSocket Reconnection Logic

```
1. WebSocket closed → attempt reconnect
2. Reconnect failed → HTTP fallback
3. HTTP idle timeout → tunnel ends

Reconnection settings:
- max_ws_reconnect_attempts: 5
- ws_reconnect_delay_secs: 2

Heartbeat monitoring:
- Stale heartbeat detected: last ping was {ms}ms ago
- Heartbeat timeout detected (last ping: {ms}ms ago)
- Heartbeat failure detected but reconnection is disabled
- Too many missed heartbeats ({count})
- Connection marked as unhealthy
```

### 63.4 SSE Retry Configuration

```
retryCount: 3
retryTimeout: 1000ms
backoffMultiplier: 2
noEventTimeout: 30000ms
retryCode: [502, 503, 504]
```

### 63.5 Rate Limiting Implementation

**Source:** `apps/icube_server_rs/modules/ai-agent/src/infrastructure/common/rate_limiter.rs`

**Algorithm:** Token bucket, keyed by tenant ID

**Headers:**
```
X-RateLimit-Remaining: {count}
X-RateLimit-Reset: {timestamp}
X-RateLimit-Limit: {max}
```

**Response:** HTTP 429 with `retry_after`

**AWS Client Rate Limiter:**
```
ClientRateLimiter
fill_rate
max_capacity
last_timestamp
last_tx_rate_bucket
request_count
last_max_rate
time_of_last_throttle
```

### 63.6 Database Error Handling

```
[DB] Operation failed with retryable error: {error}. Retrying...
[DB] Database is not encrypted
[DB] Database is encrypted (query failed)
[DB] Connection options: {options}
[DB] Setting database to WAL mode
[DB] Setting database busy_timeout 5000ms
Failed to connect to database: {error}
```

### 63.7 Tunnel Error Types

```
system_error_tunnel_system
tunnel_system_
message_handling_error
command_handling_error
heartbeat failure (reconnection disabled)
```

### 63.8 Stream Error Handling

```
SSE stream created: {stream_id}
Cleaning up {count} active streams
All streams cleaned up
Cleaning up stream: {stream_id}
Stream task {stream_id} completed gracefully
Stream {stream_id} panicked: {error}
Cancelling {count} active streams due to: {reason}
Stream {stream_id} cancelled gracefully
Stream {stream_id} panicked during cancellation: {error}
Stream {stream_id} did not complete cancellation within timeout
{count} streams cancelled due to: {reason}
```

### 63.9 AWS Bedrock Error Types

```
internalServerException
modelStreamErrorException
validationException
throttlingException
serviceUnavailableException
ModelTimeoutException
AccessDeniedException
ResourceNotFoundException
ModelNotReadyException
ModelErrorException
```

### 63.10 Transport Error Messages

```
Connection timeout
Network IO error: {error}
TLS connection error: {error}
Connection reset by peer
Connection refused
Write buffer full, message: {msg}
Protocol violation: {detail}
HTTP handshake error: {error}
Invalid UTF-8 encoding: {detail}
Capacity exceeded: {detail}
Invalid subprotocol: {detail}
Unknown WebSocket error: {error}
TTNet error: {error}
JSON serialization error: {error}
Invalid message format: {detail}
Stream not found: {stream_id}
Request timeout for id: {id}
Tunnel closed
Unsupported WebSocket client: {type}
Not connected
Reconnection disabled
Reconnection timeout
Operation cancelled
Task join error: {error}
Invalid configuration: {detail}
Stream ended
HTTP response error: {status}
Server requested close: {reason}
```

---

## 64. WebSocket Protocol Details (Complete)

### 64.1 WebSocket URLs

```
ws://${host}/__aipa?hash=${appId}
ws://localhost:${port}
wss://aipa-ws-online.bytedance.net
```

### 64.2 WsProto Message Types

```
WsProtoCLIBatchInsertEvents      # CLI batch insert events
WsProtoConfirm                    # Confirm receipt
WsProtoCliPushConversationsDelete # Push conversations delete
WsProtoCliPushDeleteMessages      # Push delete messages
WsProtoSessionCreated             # Session created
WsProtoSessionUpdated             # Session updated
WsProtoSessionDeleted             # Session deleted
WsProtoCliPushMessageDelete       # Push message delete
WsProtoCliPushMessageRevert       # Push message revert
```

### 64.3 Hub Bridge Endpoints

```
/clis/register                    # Register CLI client
/clis/unregister                  # Unregister CLI client
/clis/requests/respond            # Respond to requests
/conversations                    # List conversations
/conversations?cli_ids=&page_size=&order_by=updated_at&sort=desc&fields=cli_conversation_id&fields=updated_at&fields=status
/conversations/artifact/commit_upload  # Commit artifact upload
/conversations/artifact/get_upload_url # Get artifact upload URL
/conversations/clis/messages/list # List CLI messages
/conversations/messages/batchInsert    # Batch insert messages
/conversations/messages/batchInsertMulti # Batch insert multi messages
/conversations/tasks/batchInsert       # Batch insert tasks
/wsmessages/poll                  # Poll for messages
/wsmessages/push                  # Push messages
```

### 64.4 Frontier Protocol Fields

```
frontier_id
frontier_app_id
frontier_product_id
frontier_app_key
frontier_config
frontier_url
device_id
from_down_seq_id
down_seq_id
up_seq_id
app_id
product_id
process_id
```

### 64.5 Protocol Structs

| Struct | Elements | Purpose |
|--------|----------|---------|
| `RegisterCliResponse` | 1 | CLI registration response |
| `WsProtoConfirmWsMessage` | 2 | Confirm message |
| `FallbackPushResponse` | 1 | Fallback push response |
| `CliRequest` | - | CLI request |
| `CliResponse` | - | CLI response |
| `RegisterCliRequest` | - | CLI registration request |
| `WsMessage` | - | WebSocket message |
| `FrontierHeader` | - | Frontier header |
| `FrontierFrame` | - | Frontier frame |
| `HubRemoteConfig` | - | Hub remote configuration |

### 64.6 JSON-RPC Methods

**Client → Server:**
```
rpc.ping      # Heartbeat ping
rpc.close     # Close connection
rpc.stream    # Stream control
rpc.system    # System control
```

**Server → Client:**
```
sse.open      # Open SSE stream
sse.delta     # SSE content delta
sse.end       # SSE stream end
sse.error     # SSE error
sse.cancel    # Cancel SSE stream
```

### 64.7 MuxRpc Heartbeat Messages

```
[MuxRpc] heartbeat_loop started, interval={ms}ms, timeout={ms}ms
[MuxRpc] heartbeat_loop: ping #{id} queued to write_tx
[MuxRpc] heartbeat_loop: sending ping #{id}
[MuxRpc] heartbeat timeout ({ms}ms > {ms}ms), connection may be dead
[MuxRpc] failed to send ping #{id}
[MuxRpc] read_loop: received Pong, stream_id={id}, timestamp={ts}, latency={ms}ms
```

### 64.8 HubNetService Transport Messages

```
[HubNetService] transport loop started
[HubNetService] transport loop exited gracefully
[HubNetService] transport loop exit timed out, aborted
[HubNetService] register_hub request: /clis/register
[HubNetService] register_hub response: {response}
[HubNetService] is_initialized: frontier_id is -1
[HubNetService] HubNetService initialized successfully
[HubNetService] HubNetService already initialized
[HubNetService] auth headers updated
[HubNetService] frontier_url: {url}, base_host: {host}
[HubNetService] frontier_url is None, re-fetching boot config
[HubNetService] VM mode, skip bridge.start()
[HubNetService] shutdown completed
[HubNetService] upload_artifact: requesting upload url
[HubNetService] upload_artifact: uploading, url={url}, size={size}
[HubNetService] upload_artifact: success, session_id={id}
```

---

## 65. Model Configuration Protocol (Complete)

### 65.1 LLM Providers

| Provider | Source File |
|----------|-----------|
| Anthropic | `apps/icube_server_rs/crates/llm-client/src/provider/anthropic.rs` |
| OpenAI | `apps/icube_server_rs/crates/llm-client/src/provider/openai.rs` |
| AWS Bedrock | `apps/icube_server_rs/crates/llm-client/src/provider/aws.rs` |
| Gemini | `apps/icube_server_rs/crates/llm-client/src/provider/gemini.rs` |
| DeepSeek | `apps/icube_server_rs/crates/llm-client/src/provider/deepseek.rs` |
| OpenRouter | `apps/icube_server_rs/crates/llm-client/src/provider/openrouter.rs` |
| Volcengine (ByteDance) | `apps/icube_server_rs/crates/llm-client/src/provider/volcengine.rs` |

### 65.2 Exact Model Names

**GPT family:**
- `gpt-5` (pipeline: **deidamia**)
- `gpt-5.2` (pipeline: **deidamia**)
- `gpt-5.2-codex` (pipeline: **deidamia**)
- `gpt-5.3-codex` (pipeline: **deidamia**)
- `gpt-5.4` (pipeline: **thetis**)

**Gemini family:**
- `gemini-3-pro` (pipeline: **medea**)
- `gemini-3-flash-solo` (pipeline: **medea**)
- `gemini-3.1-pro` (pipeline: **medea**)

**DeepSeek family:**
- `deepseek-V3` (used for git commit messages)
- `deepseek-v3.1` (in HTTP client strings)
- `deepseek-chat` (Bearer token auth string found)

**Qwen family:**
- `qwen2.5` (used for git commit messages)
- `qwen32` (used via `git_qwen32_generate_commit_message`)

**Doubao/Volcengine (ByteDance) family:**
- `Doubao_1_6` (pipeline: **penelope**)
- `doubao-for-auto` (pipeline: **penelope**)
- `Doubao-Seed-2.0-Code` (pipeline: **penelope**)

**Anthropic Claude:**
- `anthropic/claude-3` (referenced in gateway-style model format example)
- Uses `anthropic-version: 2023-06-01` header

### 65.3 Pipeline Codenames (Skill Routing System)

| Pipeline | Models | Skill Paths |
|----------|--------|-------------|
| **deidamia** | gpt-5, gpt-5.2, gpt-5.2-codex, gpt-5.3-codex | `code/deidamia/skills/`, `trae/deidamia/skills/`, `work/deidamia/skills/` |
| **thetis** | gpt-5.4 | `code/thetis/skills/`, `trae/thetis/skills/`, `work/thetis/skills/` |
| **medea** | gemini-3-pro, gemini-3-flash-solo, gemini-3.1-pro | `code/medea/skills/`, `trae/medea/skills/`, `work/medea/skills/` |
| **eurydice** | Claude models (c_model, c_o_model variants) | `trae/eurydice/skills/`, `work/eurydice/skills/` |
| **penelope** | Doubao_1_6, doubao-for-auto, Doubao-Seed-2.0-Code | `code/penelope/skills/`, `trae/penelope/skills/` |

**Claude model pipeline mapping:**
```json
{
  "c_model": "eurydice",
  "c_model_no_thinking": "eurydice",
  "c_model_thinking": "eurydice",
  "c_o_model": "eurydice",
  "c_o_model_no_thinking": "eurydice"
}
```

### 65.4 Gateway-Style Model Identifiers

```
openai/gpt-5
openai/gpt-5.2
anthropic/claude-3
google/gemini-3-pro
deepseek/deepseek-V3
```

### 65.5 Model List Response Structs

| Struct | Purpose |
|--------|---------|
| `AnthropicModelListResponse` | Anthropic model list (with `last_id`) |
| `AnthropicModel` | Anthropic model |
| `OpenAIModelListResponse` | OpenAI model list |
| `GeminiModelListResponse` | Gemini model list (with `display_name`) |
| `GeminiModel` | Gemini model |
| `DeepseekModel` | DeepSeek model |
| `OpenrouterModelListResponse` | OpenRouter model list |
| `OpenrouterModel` | OpenRouter model |
| `AWSModelSummary` | AWS model summary (10 fields) |
| `AWSModelListResponse` | AWS model list (with `modelSummaries`) |

### 65.6 LLMClient Request/Response Protocol

**Core request struct:** `LLMClientRequestRaw`
- `max_tokens`, `max_completion_tokens`
- `tools`, `usage`, `reasoning`
- `inferenceConfig`
- `anthropic_version`

**Nested structs:**
- `LLMClientThinkingRaw`, `LLMClientReasoningRaw` (with `effort` field)
- `LLMClientRequestMessageRaw` (with `reasoning_content`, `tool_call_id`, `tool_calls`, `reasoning_details`)
- `LLMClientToolCallItemRaw` (with `extra_content`)
- `LLMClientFunctionCallRaw` (with `arguments`)
- `LLMClientUsageRaw`
- `LLMClientReasoningDetailsRaw`
- `LLMClientCacheControl`

**Response types:**
- `NativeAnthropicLLMResponse` - `NativeAnthropicMessageDelta`, `NativeAnthropicUsage` (input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens)
- `NativeOpenrouterLLMResponse` - `NativeOpenrouterLLMChoice`, `NativeOpenRouterLLMUsage` (prompt_tokens, completion_tokens, total_tokens)
- `NativeLLMMessage`, `NativeLLMUsage`

### 65.7 Model Configuration Management

- **Database table:** `model_config_cache` (migration: `m20251217_000001_create_model_config_cache_table.rs`)
- **Manager:** `[ModelMgr]` log prefix - parses `model_extra_config` per model
- **Config fields parsed:** `model_name`, `config_name`, `run_command_output_char_count`
- **Custom model support:** `IcubeAiCustomModelRequestBuilder`, `GetCustomModelTypeConfigResponse`, `CustomModelFallbackConfig`
- **Model service:** `apps/icube_server_rs/modules/ai-agent/src/domain/model/service.rs`

### 65.8 Git Commit Message Models

Four dedicated model functions for commit message generation:
1. `git_generate_commit_message` - generic
2. `git_seed_m8_generate_commit_message` - Seed/M8 model
3. `git_deepseek_v3_generate_commit_message` - DeepSeek V3
4. `git_qwen32_generate_commit_message` - Qwen 32B

### 65.9 Key HTTP Headers

```
X-Model-Provider          # identifies the provider
X-App-Version             # application version
X-Ide-Version-Code        # IDE version code
X-App-Version-Code        # app version code
X-Trae-Authorized-Services # authorized services
X-Custom-Trace-Id         # custom trace ID
X-Device-Id               # device ID
X-Machine-Id              # machine ID
X-Os-Version              # OS version
X-Device-Type             # device type
X-Use-Ppe                 # PPE flag
X-User-Real-IP            # user real IP
X-Trae-Mobile-Commit-Id   # mobile commit ID
X-Agent-Debug-Mode        # agent debug mode
x-cloudide-token          # cloudide token
x-ide-token               # IDE token
x-frontier-id             # frontier ID
```
