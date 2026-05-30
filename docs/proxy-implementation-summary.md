# Trae AI Proxy Implementation Summary

## Overview

This document provides a comprehensive summary of the reverse engineering analysis of Trae IDE's AI communication protocol and authentication system. The goal is to enable proxying Trae's AI capabilities for use with Codex.

## Key Findings

### 1. Protocol Stack

| Layer | Protocol | Details |
|-------|----------|---------|
| Application | REST API | 60+ endpoints under `/api/ide/v1/` |
| Transport | HTTP + WebSocket | Dual-mode with automatic fallback |
| Streaming | SSE | Server-Sent Events for real-time responses |
| RPC | JSON-RPC 2.0 | Used for custom model proxy tunnel |
| Security | OAuth2/JWT | With PKCE, SQLCipher storage |

### 2. Core API Endpoints

#### Chat Endpoints
- `POST /api/ide/v1/chat` - Main chat completion
- `POST /api/ide/v1/llm_raw_chat` - Raw LLM chat
- `POST /api/ide/v2/llm_raw_chat` - V2 raw LLM chat
- `POST /api/ide/v1/chat_prompt` - Chat with prompt template

#### Model Endpoints
- `GET /api/ide/v1/model_list` - List available models
- `GET /api/ide/v1/providers` - List model providers
- `POST /api/ide/v1/add_custom_model` - Add custom model

#### Agent Endpoints
- `POST /api/ide/v1/agents/runs` - Start agent run
- `POST /api/ide/v1/agents/runs/:id/tool_call_outputs` - Submit tool outputs

### 3. Authentication System

#### OAuth2 Providers
1. **Google OAuth2**
   - Authorization: `https://accounts.google.com/o/oauth2/v2/auth`
   - Token: `https://oauth2.googleapis.com/token`

2. **Supabase OAuth**
   - Authorization: `https://api.supabase.com/v1/oauth/authorize`
   - Token: `https://api.supabase.com/v1/oauth/token`
   - Client ID: `SUPABASE_APP_CLIENT_ID`
   - Client Secret: `SUPABASE_APP_CLIENT_SECRET`

3. **Trae Native Auth**
   - Login Check: `/cloudide/api/v3/trae/CheckLogin`
   - User Info: `/cloudide/api/v3/trae/GetUserInfo`
   - Token Exchange: `/cloudide/api/v3/trae/oauth/ExchangeToken`

#### Token Storage
- **Database**: SQLCipher encrypted SQLite
- **Fields**: access_token, refresh_token, expired_at, refresh_expired_at, user_id, token_release_at, token_host

#### Auth Headers
```
x-cloudide-token: {token}
x-ide-token: {token}
Authorization: Bearer {jwt}
x-frontier-id: {frontier_id}
X-Model-Sk: {secret_key}
X-Model-Region: {aws_region}
```

### 4. Streaming Protocol

#### SSE Events
```
message_start          - Stream started
content_block_start    - Content block started
content_block_delta    - Content delta (streaming)
content_block_stop     - Content block completed
message_stop           - Stream completed
```

#### Custom Model Proxy (JSON-RPC 2.0)
```
Client → Server:
  sse.open      - Open new SSE stream
  sse.cancel    - Cancel active stream
  rpc.ping      - Heartbeat ping
  rpc.close     - Close connection

Server → Client:
  sse.delta     - Streaming content
  sse.end       - Stream completed
  sse.error     - Stream error
```

### 5. Model Support

| Provider | Models |
|----------|--------|
| Anthropic | Claude 3.5 |
| OpenAI | GPT-5, GPT-5.2, GPT-5.3, GPT-5.4 |
| Google | Gemini 3, Gemini 3.1, Gemini 3 Flash |
| DeepSeek | DeepSeek V3, DeepSeek V3.1 |
| Alibaba | Qwen 2.5, Qwen 32 |
| AWS | Bedrock Converse Stream API |

### 6. Custom Model Proxy Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   Tunnel    │────▶│  Provider   │
│  (IDE)      │◀────│  (Server)   │◀────│  (LLM API)  │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     │ WebSocket/HTTP     │ HTTP/WS            │
     │ JSON-RPC 2.0       │ OpenAI format      │
     │───────────────────▶│───────────────────▶│
     │                    │                    │
     │ SSE Stream         │ SSE Stream         │
     │◀───────────────────│◀───────────────────│
```

#### WebSocket URL
```
wss://{host}/custom_model/tunnel/ws?tunnel_id={tunnel_id}
```

#### HTTP Fallback
```
POST /custom_model/tunnel/GetPending
POST /custom_model/tunnel/SubmitMessage
```

### 7. Hardcoded UUIDs

Two UUIDs found near API endpoints (potential client IDs):
- `6eefa01c-1036-4c7e-9ca5-d891f63bfcd8`
- `850edec7-b9d0-48aa-99b5-67c888e282cd`

### 8. Boot Configuration

```rust
struct BootConfig {
    agent: AgentConfig,        // Agent configuration
    ckg: CKGConfig,           // Code Knowledge Graph
    hub: HubConfig,           // Hub Bridge
    tea: Tea,                 // Analytics
    slardar: Slardar,         // Telemetry
    ttnet: TTNetConfig,       // Network
    imageX: ImageXConfig,     // Image service
    cdnPrefix: String,        // CDN URL
    hostTmpDir: String,       // Temp directory
    storeRegion: String,      // Storage region
    // ... 7 more fields
}
```

## Implementation Roadmap

### Phase 1: Authentication Proxy
1. Implement OAuth2 flow (Google, Supabase, Trae native)
2. Token management (secure storage, auto-refresh)
3. Auth header injection

### Phase 2: API Proxy
1. Core chat endpoints
2. Model management
3. Agent endpoints

### Phase 3: Streaming Proxy
1. SSE streaming support
2. Custom model proxy (WebSocket/HTTP)
3. JSON-RPC 2.0 protocol

### Phase 4: Codex Integration
1. Format translation (Codex ↔ Trae)
2. Model name mapping
3. Error handling and retries

## Technical Specifications

### Rate Limiting
- Algorithm: Token bucket
- Headers: X-RateLimit-Remaining, X-RateLimit-Reset, X-RateLimit-Limit
- Response: HTTP 429 with retry_after

### Retry Logic
- Count: 3 retries
- Timeout: 1000ms
- Backoff: 2x multiplier
- Codes: 502, 503, 504

### Security
- Database: SQLCipher (AES-256)
- Model Params: AES-256-GCM encryption
- TLS: OpenSSL statically linked
- Token: JWT with signature verification

## Source Code References

### Binary Analysis
- `libai_agent.so` - 127MB Rust shared library (main AI agent)
- `trae-cli` - Go binary (CLI tool)
- `main.js` - Electron main process

### Source Paths
- `apps/icube_server_rs/modules/ai-agent/src/` - Main AI agent
- `apps/icube_server_rs/crates/custom-model-proxy-client/src/` - Custom model proxy
- `apps/icube_server_rs/crates/ai-config/src/` - Configuration
- `apps/icube_server_rs/crates/llm-client/src/provider/` - LLM providers

### Analysis Files
- `analysis/trae-ai-proxy-deep-analysis.md` - Comprehensive protocol analysis
- `analysis/ai-protocol-analysis.md` - IPC/RPC protocol analysis
- `analysis/trae-proxy-implementation-guide.md` - Implementation guide

## Next Steps

1. **Extract OAuth2 credentials** from binary
2. **Test authentication flow** with real endpoints
3. **Implement WebSocket tunnel** for custom model proxy
4. **Build format translator** between Codex and Trae
5. **Deploy proxy server** for testing
6. **Integrate with Codex CLI**

## Conclusion

The Trae IDE uses a sophisticated AI communication protocol with:
- OAuth2 authentication with multiple providers
- HTTP + WebSocket dual-mode transport
- SSE streaming for real-time responses
- JSON-RPC 2.0 for custom model proxy
- AWS Bedrock for LLM inference

The proxy implementation should follow the phased approach, starting with authentication and gradually adding API proxy, streaming, and Codex integration capabilities.

---

## Appendix A: Hub Bridge Protocol Details

### Registration Flow

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

### Message Types

| Type | Direction | Purpose |
|------|-----------|---------|
| `WsProtoCLI` | Server→Client | CLI message |
| `WsProtoConfirm` | Client→Server | Confirm receipt |
| `WsProtoSessionCreated` | Server→Client | Session created |
| `WsProtoSessionUpdated` | Server→Client | Session updated |
| `WsProtoSessionDeleted` | Server→Client | Session deleted |
| `WsProtoCliPushConversations` | Server→Client | Push conversations |
| `WsProtoCliPushDeleteMessages` | Server→Client | Delete messages |

### Frontier Frame Structure

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

### Hub Remote Configuration

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

## Appendix B: Complete Struct Definitions

### OpenAI-Compatible Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `OpenAIRequest` | 7 | Main chat request |
| `OpenAITool` | 2 | Tool definition |
| `OpenAIFunction` | 3 | Function definition |
| `OpenAIMessage` | 4 | Message |
| `OpenAIToolCall` | 3 | Tool call |
| `OpenAIFunctionCall` | 2 | Function call |
| `OpenAIContentPart` | 3 | Content part |
| `OpenAIImageUrl` | 1 | Image URL |

### JSON-RPC 2.0 Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `JsonRpcMessage` | 4 | JSON-RPC message |
| `SseOpenParams` | 2 | SSE open parameters |
| `SseCancelParams` | 3 | SSE cancel parameters |
| `RpcCloseParams` | 3 | RPC close parameters |
| `RpcPingParams` | - | RPC ping parameters |

### Boot Configuration Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `BootConfig` | 17 | Main boot configuration |
| `AgentConfig` | 3 | Agent configuration |
| `Tea` | 6 | Analytics config |
| `Slardar` | 6 | Telemetry config |
| `TTNetConfig` | 4 | Network config |
| `HubRemoteConfig` | 17 | Hub remote configuration |

### Chat Session Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `ChatArgs` | 47 | Chat arguments |
| `ChatMessageData` | 37/44 | Chat message data |
| `ChatTurnContext` | 20 | Chat turn context |
| `ChatTurnTokenUsage` | 13 | Chat turn token usage |

### LLM Client Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `LLMClientFunctionCall` | 2 | Function call |
| `LLMClientToolcallItem` | 4 | Tool call item |
| `LLMClientToolCall` | 5 | Tool call |
| `LLMClientToolCallFunction` | 2 | Tool call function |

### Model Configuration Structures

| Struct | Elements | Purpose |
|--------|----------|---------|
| `ModelExtraConfig` | 142 | Model extra configuration |
| `CustomModel` | 29 | Custom model |
| `ModelConfigInfo` | 12 | Model config info |
| `ModelDetailInfo` | 17 | Model detail info |

---

## Appendix C: Database Schema

### Encryption

- **Library**: SQLCipher
- **Algorithm**: AES-256
- **Check**: `SELECT sql FROM sqlite_master WHERE type='table'`
- **Status**: Database is encrypted by default

### Key Tables

| Table | Purpose |
|-------|---------|
| `model_config_cache` | Model configuration cache |
| `agent` | Agent definitions |
| `chat_turn` | Chat turns |
| `chat_message` | Chat messages |
| `core_memory` | Core memory entries |
| `history_v2` | History records |
| `chat_session` | Chat sessions |
| `todo_list` | Todo list items |

### Model Config Cache Schema

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

### Database Connection

```rust
// Connection options
sqlx::SqliteConnectOptions::new()
  .journal_mode(SqliteJournalMode::Wal)
  .busy_timeout(Duration::from_millis(5000))
  .pragma("key", encryption_key)
```

---

## Appendix D: Regional Configuration

| Region | Config Key | Domain |
|--------|------------|--------|
| China | `ide_cn` | `icube-normal.trae.com.cn` |
| US | `ide_us` | `icube-normal.trae.ai` |

### UUID Client IDs

Two hardcoded UUIDs found near API endpoints:
- `6eefa01c-1036-4c7e-9ca5-d891f63bfcd8`
- `850edec7-b9d0-48aa-99b5-67c888e282cd`

These are likely OAuth2 client IDs or application identifiers.

---

## Appendix E: Authentication Protocol Details (from main.js)

### Trae Native Auth Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `${tokenHost}/cloudide/api/v3/trae/CheckLogin` | POST | Check login status |
| `${tokenHost}/cloudide/api/v3/trae/GetUserInfo` | POST | Get user info |
| `${tokenHost}/cloudide/api/v3/trae/oauth/ExchangeToken` | POST | Refresh token |

### CheckLogin Request Format

```json
// Headers: x-cloudide-token, Content-Type: application/json
// Timeout: 30 seconds
{
  "IDEVersion": "{appVersion}",
  "ReqSource": "IDE" | "Lite",
  "GetAIPayHost": true
}

// Response:
{
  "code": 0,
  "Result": {
    "IsLogin": true,
    "MigrateToSG": false
  }
}
```

### ExchangeToken Request Format

```json
// Headers: Content-Type: application/json
// Timeout: 60 seconds
{
  "ClientID": "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8",
  "RefreshToken": "{refreshToken}",
  "ClientSecret": "-",
  "UserID": ""
}

// Response:
{
  "code": 0,
  "Result": {
    "Token": "{accessToken}",
    "RefreshToken": "{newRefreshToken}",
    "TokenExpireAt": "{isoDateString}"
  }
}
```

### Supabase OAuth Flow

1. Start local server on random port (17788-17792)
2. Open browser to authorization URL:
   ```
   https://api.supabase.com/v1/oauth/authorize?client_id={CLIENT_ID}&redirect_uri=http%3A%2F%2Flocalhost%3A{PORT}%2Fcallback&response_type=code&state=%7B%7D
   ```
3. User authorizes in browser
4. Supabase redirects to localhost callback with code
5. Exchange code for token at `https://api.supabase.com/v1/oauth/token`
6. Store token in `./supabase-token.json`

### Error Codes

The following error codes trigger `RefreshTokenInvalid` error (user logged out):
- 20324
- 20101
- 20315
- 20125
- 20126

### Token Refresh Logic

1. Check token expiration
2. If expired or about to expire → call `refreshToken()`
3. If `RefreshTokenInvalid` error → user logged out
4. Otherwise → update token in storage

### Token Storage

**SQLCipher Database:**
- Database: encrypted SQLite with AES-256
- Fields: access_token, refresh_token, expired_at, refresh_expired_at, user_id, token_release_at, token_host

**Supabase Token:**
- File: `./supabase-token.json`
- Format: JSON with access_token, refresh_token, etc.

---

## Appendix F: Custom Model Proxy Protocol

### Source Files

The tunnel implementation spans 12 source files in `custom-model-proxy-client` crate:

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

### JSON-RPC 2.0 Structs

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

### HTTP Fallback Structs

| Struct | Purpose |
|--------|---------|
| `PendingRequestDTO` | Pending request from server |
| `GetPendingResponse` | Response from GetPending |
| `MessageResult` | Result of message processing |
| `SubmitMessageResponse` | Response from SubmitMessage |
| `FallbackPollResponse` | Response from HTTP polling |
| `FallbackPushResponse` | Response from HTTP push |

### Tunnel Connection Flow

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
