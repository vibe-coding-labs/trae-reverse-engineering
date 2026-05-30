# Trae AI Proxy - Quick Reference Card

## Critical Endpoints

### Authentication
```
POST /cloudide/api/v3/trae/CheckLogin
POST /cloudide/api/v3/trae/GetUserInfo
POST /cloudide/api/v3/trae/oauth/ExchangeToken
```

### Chat API
```
POST /api/ide/v1/chat
POST /api/ide/v1/llm_raw_chat
POST /api/ide/v2/llm_raw_chat
```

### Model API
```
GET  /api/ide/v1/model_list
GET  /api/ide/v1/providers
POST /api/ide/v1/add_custom_model
```

### Agent API
```
POST /api/ide/v1/agents/runs
POST /api/ide/v1/agents/runs/:id/tool_call_outputs
```

### Custom Model Proxy
```
WebSocket: wss://{host}/custom_model/tunnel/ws?tunnel_id={id}
HTTP:      POST /custom_model/tunnel/GetPending
HTTP:      POST /custom_model/tunnel/SubmitMessage
```

## Auth Headers

```http
x-cloudide-token: {token}
x-ide-token: {token}
Authorization: Bearer {jwt}
x-frontier-id: {frontier_id}
X-Model-Sk: {secret_key}
X-Model-Region: {aws_region}
```

## OAuth2 Providers

### Google
```
Auth:  https://accounts.google.com/o/oauth2/v2/auth
Token: https://oauth2.googleapis.com/token
```

### Supabase
```
Auth:  https://api.supabase.com/v1/oauth/authorize
Token: https://api.supabase.com/v1/oauth/token
ID:    SUPABASE_APP_CLIENT_ID
Secret: SUPABASE_APP_CLIENT_SECRET
```

### Trae Native
```
Check:  /cloudide/api/v3/trae/CheckLogin
Info:   /cloudide/api/v3/trae/GetUserInfo
Exchange: /cloudide/api/v3/trae/oauth/ExchangeToken
```

## SSE Events

```
message_start
content_block_start
content_block_delta
content_block_stop
message_stop
```

## JSON-RPC 2.0 Methods

### Client → Server
```
sse.open
sse.cancel
rpc.ping
rpc.close
```

### Server → Client
```
sse.delta
sse.end
sse.error
```

## Model Names

| Codex | Trae |
|-------|------|
| claude-3.5-sonnet | anthropic/claude-3.5 |
| gpt-4o | openai/gpt-5 |
| gpt-4o-mini | openai/gpt-5.2 |
| gemini-pro | google/gemini-3 |
| deepseek-coder | deepseek/deepseek-v3 |

## Rate Limit Headers

```http
X-RateLimit-Remaining: {count}
X-RateLimit-Reset: {timestamp}
X-RateLimit-Limit: {max}
```

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 401 | Unauthorized | Refresh token |
| 429 | Rate limited | Wait and retry |
| 502 | Bad gateway | Retry with backoff |
| 503 | Service unavailable | Retry with backoff |
| 504 | Gateway timeout | Retry with backoff |

## Retry Configuration

```
Count: 3
Timeout: 1000ms
Backoff: 2x multiplier
Codes: [502, 503, 504]
```

## Hardcoded UUIDs (Potential Client IDs)

```
6eefa01c-1036-4c7e-9ca5-d891f63bfcd8
850edec7-b9d0-48aa-99b5-67c888e282cd
```

## Boot Config Fields

```
agent, ckg, hub, tea, lite, teaWeb, slardar, ttnet, imageX,
cdnPrefix, hostTmpDir, storeRegion, ugApi, ppeEnv, ...
```

## WebSocket Protocol

### Connection
```
wss://{host}/custom_model/tunnel/ws?tunnel_id={tunnel_id}
```

### Heartbeat
```
Client: rpc.ping (timestamp)
Server: pong (server_timestamp)
Timeout: Stale heartbeat detected
```

### Reconnection
```
1. WebSocket closed → Attempt reconnect
2. Reconnect failed → HTTP fallback
3. HTTP idle timeout → Tunnel ends
```

## AWS Bedrock

### SDK
```
aws-sdk-bedrockruntime v1.92.0
aws-sdk-sso v1.72.0
aws-sdk-ssooidc v1.73.0
aws-sdk-sts v1.73.0
```

### Required Headers
```
Authorization: AWS credentials
X-Model-Sk: Model secret key
X-Model-Region: AWS region
```

## Database

### Encryption
```
Library: SQLCipher
Algorithm: AES-256
Check: SELECT sql FROM sqlite_master WHERE type='table'
```

### Paths
```
Main: /ai-chat/database.db
Snapshot: /ai-chat/snapshot
Env: ICUBE_MODULAR_DATA_DIR
```

## CLI Endpoints

```
/trae-cli/api/v1/llm/proxy
/api/ide/v1/cli/get_config_list
/trae/gtm/tob/api/v1/mcp_whitelist/list
```

## Implementation Priority

1. **Auth** → OAuth2 flow + token management
2. **Chat** → Core chat endpoints
3. **Stream** → SSE streaming
4. **Proxy** → Custom model proxy (WebSocket/HTTP)
5. **Translate** → Codex ↔ Trae format
6. **Deploy** → Proxy server
7. **Integrate** → Codex CLI

## Hub Bridge Endpoints

```
POST /clis/register          # Register CLI client
GET  /wsmessages/poll        # Poll for messages
POST /wsmessages/send_batch  # Send batch messages
POST /clis/requests/respond  # Respond to requests
```

## Hub Bridge Message Types

```
WsProtoCLI                    # CLI message
WsProtoConfirm                # Confirm receipt
WsProtoSessionCreated         # Session created
WsProtoSessionUpdated         # Session updated
WsProtoSessionDeleted         # Session deleted
WsProtoCliPushConversations   # Push conversations
WsProtoCliPushDeleteMessages  # Delete messages
```

## Regional Configuration

| Region | Config Key | Domain |
|--------|------------|--------|
| China | `ide_cn` | `icube-normal.trae.com.cn` |
| US | `ide_us` | `icube-normal.trae.ai` |

## Key Struct Definitions

### OpenAI Compatible
```
OpenAIRequest (7 elements)
OpenAITool (2), OpenAIFunction (3)
OpenAIMessage (4), OpenAIToolCall (3)
OpenAIFunctionCall (2)
```

### JSON-RPC 2.0
```
JsonRpcMessage (4)
SseOpenParams (2), SseCancelParams (3)
RpcCloseParams (3), RpcPingParams
```

### Boot Configuration
```
BootConfig (17 elements)
AgentConfig (3), Tea (6), Slardar (6)
TTNetConfig (4), HubRemoteConfig (17)
```

### Chat Session
```
ChatArgs (47 elements)
ChatMessageData (37/44)
ChatTurnContext (20)
ChatTurnTokenUsage (13)
```

## Database Tables

```
model_config_cache    # Model configuration cache
agent                 # Agent definitions
chat_turn             # Chat turns
chat_message          # Chat messages
core_memory           # Core memory entries
history_v2            # History records
chat_session          # Chat sessions
todo_list             # Todo list items
```

## Authentication Protocol (from main.js)

### Trae Native Auth Endpoints

```
POST ${tokenHost}/cloudide/api/v3/trae/CheckLogin     # Check login status
POST ${tokenHost}/cloudide/api/v3/trae/GetUserInfo     # Get user info
POST ${tokenHost}/cloudide/api/v3/trae/oauth/ExchangeToken  # Refresh token
```

### CheckLogin Request

```json
// Headers: x-cloudide-token, Content-Type: application/json
// Body:
{
  "IDEVersion": "{appVersion}",
  "ReqSource": "IDE" | "Lite",
  "GetAIPayHost": true
}
// Response: { "code": 0, "Result": { "IsLogin": true, "MigrateToSG": false } }
```

### ExchangeToken Request

```json
// Headers: Content-Type: application/json
// Body:
{
  "ClientID": "6eefa01c-1036-4c7e-9ca5-d891f63bfcd8",
  "RefreshToken": "{refreshToken}",
  "ClientSecret": "-",
  "UserID": ""
}
// Response: { "code": 0, "Result": { "Token": "...", "RefreshToken": "...", "TokenExpireAt": "..." } }
```

### UUID Client ID

```
6eefa01c-1036-4c7e-9ca5-d891f63bfcd8
```

### Supabase OAuth

```
Authorization: https://api.supabase.com/v1/oauth/authorize
Token: https://api.supabase.com/v1/oauth/token
Client ID: SUPABASE_APP_CLIENT_ID
Client Secret: SUPABASE_APP_CLIENT_SECRET
Token Storage: ./supabase-token.json
Timeout: 30 minutes
```

### Error Codes (RefreshTokenInvalid)

```
20324, 20101, 20315, 20125, 20126
```

## Custom Model Proxy Protocol

### Source Files (custom-model-proxy-client crate)

```
builder.rs          # Tunnel builder
connection.rs       # Connection management (274+ lines)
tunnel.rs           # Main tunnel logic (942+ lines)
stream_manager.rs   # Stream lifecycle (572+ lines)
message_handler.rs  # JSON-RPC handling (243+ lines)
websocket.rs        # WebSocket transport (323+ lines)
ws_transport.rs     # WebSocket wrapper (114+ lines)
http_transport.rs   # HTTP fallback (313+ lines)
retry.rs            # Retry logic (345+ lines)
default_handler.rs  # Default SSE handler (328+ lines)
aws_handler.rs      # AWS Bedrock handler (965+ lines)
```

### JSON-RPC Structs

```
JsonRpcMessage       # JSON-RPC 2.0 request/response
JsonRpcResponse      # JSON-RPC 2.0 response
JsonRpcError         # JSON-RPC 2.0 error
HttpRequest          # HTTP request wrapper
SseOpenParams        # sse.open parameters
SseOpenPayload       # sse.open payload
SseCancelParams      # sse.cancel parameters
RpcCloseParams       # rpc.close parameters
RpcPingParams        # rpc.ping parameters
SseDeltaParams       # sse.delta parameters
SseEndParams         # sse.end parameters
SseErrorParams       # sse.error parameters
SseErrorData         # sse.error data
PendingRequestDTO    # Pending request (HTTP fallback)
GetPendingResponse   # GetPending response
MessageResult        # Message result
SubmitMessageResponse # SubmitMessage response
FallbackPollResponse # Fallback poll response
FallbackPushResponse # Fallback push response
```

### Tunnel Status Messages

```
SSE stream created: {stream_id}
Sending sse.delta: {data}
Sending sse.end: {stream_id}
Sending sse.error: {error}
[Tunnel] WebSocket closed, will switch to HTTP fallback
[Tunnel] WebSocket restored successfully
[Tunnel] HTTP fallback idle timeout, will end this Tunnel
[Tunnel] Tunnel shutdown gracefully
Stale heartbeat detected: last ping was {ms}ms ago
```

### Hub Bridge Sequence Numbers

```
frontier_id={id}
device_id={id}
from_down_seq_id={seq}
limit={count}
[HubNetService] down_seq gap detected: expected {expected}, switching to HttpFallback
[HubNetService] skip dup down_seq={seq}
```
