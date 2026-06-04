# L04: Hub Bridge Frontier 协议与沙箱系统完整解析

> 生成时间: 2026-06-01 ~12:00 GMT+8  
> 分析版本: Trae IDE v2.3.30128

---

## 目录

1. [Hub Bridge 总览](#1-hub-bridge-总览)
2. [HubNetService 生命周期](#2-hubnetservice-生命周期)
3. [Frontier 帧协议](#3-frontier-帧协议)
4. [消息类型完整矩阵](#4-消息类型完整矩阵)
5. [Hub 端点完整映射](#5-hub-端点完整映射)
6. [WS ↔ HTTP 双模通信](#6-ws--http-双模通信)
7. [CLI 注册与心跳](#7-cli-注册与心跳)
8. [Domain Handoff 会话迁移](#8-domain-handoff-会话迁移)
9. [Lite 沙箱模式](#9-lite-沙箱模式)
10. [Sandbox 执行沙箱](#10-sandbox-执行沙箱)
11. [会话创建完整流程](#11-会话创建完整流程)
12. [HubRemoteConfig 完整配置](#12-hubremoteconfig-完整配置)

---

## 1. Hub Bridge 总览

Hub Bridge 是 Trae AI 的主要远程通信服务，用于本地 IDE 与云端之间的实时通信。采用 **Frontier 协议** 进行消息封装，支持 WebSocket 和 HTTP 双模式通信。

```
┌─────────────────────────────┐       Frontier Protocol        ┌─────────────────────┐
│  Trae IDE (Electron)       │ ◄═══════════════════════════►  │  Hub Bridge Server  │
│  ┌───────────────────────┐ │       WebSocket + HTTP         │  hub.trae.ai        │
│  │  FrontierWebSocket    │ │                                │  ┌─────────────────┐│
│  │  Client               │ │                                │  │  Session Mgr    ││
│  │  ├─ Auth Handshake    │ │                                │  │  Message Queue   ││
│  │  ├─ CLI Register      │ │                                │  │  Handoff Svc    ││
│  │  ├─ Heartbeat         │ │                                │  │  Lite VM Pool   ││
│  │  ├─ HTTP Poll/Push    │ │                                │  └─────────────────┘│
│  │  └─ Message Replay    │ │                                └─────────────────────┘
│  └───────────────────────┘ │
│                            │              ┌─────────────────────┐
│  其他 Hub 服务             │ ◄──────────► │  Other Hub Services │
│  ┌───────────────────────┐ │              │  conversation/      │
│  │  HTTP REST Client     │ │              │  clis/              │
│  └───────────────────────┘ │              │  wsmessages/         │
└─────────────────────────────┘              └─────────────────────┘
```

### 1.1 核心概念

| 概念 | 说明 |
|------|------|
| **Frontier** | 自定义二进制/text 帧协议，用于 WebSocket 层消息封装 |
| **Hub** | 消息路由和服务注册中心 |
| **CLI** | Hub 上的客户端实例标识 (cli_id) |
| **Frontier ID** | 连接标识 (frontier_id) |
| **Message Seq** | 顺序消息序号，用于确认和重放 |
| **Down Seq** | 服务端发出的消息序号 |
| **Domain Handoff** | 本地 ↔ 云端会话迁移机制 |
| **Lite Mode** | 云端 VM 沙箱执行模式 |

---

## 2. HubNetService 生命周期

### 2.1 完整通信流程

```
                    ┌─────────────────────────────────────────────────────┐
                    │              HubNetService 生命周期                  │
                    └─────────────────────────────────────────────────────┘

PHASE 1: REGISTRATION
────────────────────────────────────────────────────────────────────────────
  [HubNetService] register_hub request:
    { product_id: "trae",
      app_runtime_type: "electron",
      process_id:  "abcd1234",
      client_timestamp: 1735712345000 }

PHASE 2: FRONTIER URL DISCOVERY
────────────────────────────────────────────────────────────────────────────
  [HubNetService] frontier_url is None, re-fetching boot config
  [HubNetService] frontier_url: "wss://hub.trae.ai/ws", base_host: "hub.trae.ai"

PHASE 3: FRONTIER ID RECORDING
────────────────────────────────────────────────────────────────────────────
  [HubNetService] record_frontier_id: "f_uuid_v4"

PHASE 4: HTTP POLLING (Initial)
────────────────────────────────────────────────────────────────────────────
  [HubNetService] HTTP flush, messages from=0
  [HubNetService] HTTP polled 5 messages, no more

PHASE 5: WEBSOCKET CONNECTION
────────────────────────────────────────────────────────────────────────────
  [HubNetService] WS connect failed (attempt 1)    ← 可能重试
  [HubNetService] WS connected, replaying 3 remaining messages

PHASE 6: WEBSOCKET COMMUNICATION (Normal)
────────────────────────────────────────────────────────────────────────────
  [HubNetService] WS recv, down_seq=42, proto=WsProtoCLI
  [HubNetService] WS send 2 messages, from=17

PHASE 7: ERROR HANDLING
────────────────────────────────────────────────────────────────────────────
  [HubNetService] down_seq gap detected: expected 45, got 47
    → switching to HttpFallback
  [HubNetService] WS closed by remote
  [HubNetService] WS reconnect exhausted (5 attempts), falling back to HTTP
```

### 2.2 生命週期状态机

```
                ┌──────────┐
                │  INIT    │
                └────┬─────┘
                     │ register_hub()
                     v
                ┌──────────┐
                │REGISTERED│
                └────┬─────┘
                     │ fetch_frontier_url()
                     v
                ┌──────────┐
                │DISCOVERED│
                └────┬─────┘
                     │ record_frontier_id()
                     v
                ┌──────────┐
                │   ID     │
                └────┬─────┘
                     │ HTTP poll
                     v
         ┌───────────────────────┐
         │   HTTP_POLLING        │ ← ← ← ← ← ← ← ← ← ← ← ┐
         └───────────┬───────────┘                         │
                     │ WebSocket connect()                 │
                     v                                     │
         ┌───────────────────────┐     WS disconnect       │
         │  WS_CONNECTED         ├─────────────────────────┤
         │  (replay messages)    │     (重连)              │
         └───────────────────────┘                         │
                     │                                     │
                     │ WS closed / reconnect exhausted     │
                     v                                     │
         ┌───────────────────────┐     WS available        │
         │  HTTP_FALLBACK        ├─────────────────────────┘
         └───────────────────────┘
```

### 2.3 重连逻辑

```
maxReconnectAttempts: 5
reconnectDelay: 2000ms
backoffMultiplier: 2

每次重连逻辑:
  1. 等待 reconnectDelay
  2. 尝试 WebSocket 连接
  3. 成功 → replay 丢失消息
  4. 失败 → 指数退避，重试
  5. 达到 max → 切换到 HTTP 回退模式
```

---

## 3. Frontier 帧协议

### 3.1 FrontierFrame 结构

```rust
// Hub Bridge 核心帧结构
struct FrontierFrame {
    log_id: String,               // 请求追踪 ID (UUID)
    service: String,              // 目标服务名称 ("hub", "chat", "sync")
    payload_encoding: String,     // 负载编码 ("json" | "protobuf" | "raw")
    payload_type: String,         // 消息类型标识
    payload: Buffer,              // 编码后的负载数据
}
```

**FrontierHeader (扩展头，包含 server_timing)：**
```
FrontierHeader
  ├── log_id: String
  ├── service: String
  ├── payload_encoding: String
  ├── payload_type: String
  ├── log_id_new: String
  ├── server_timing: String
  ├── msg_id: String
  └── frame_type: String
```

### 3.2 Frontier 帧示例

```json
// 认证帧
{
    "log_id": "log_uuid_v4",
    "service": "auth_service",
    "payload_encoding": "json",
    "payload_type": "protobuf",
    "payload": {
        "type": "auth",
        "cli_id": "cli_abc123def456",
        "frontier_id": "f_uuid_v4",
        "app_id": "trae-ide",
        "product_id": "trae",
        "token": "Bearer eyJhbGciOi..."
    }
}

// 心跳帧
{
    "log_id": "log_uuid_v4",
    "service": "heartbeat_service",
    "payload_encoding": "json",
    "payload_type": "ping"
}

// 聊天消息帧
{
    "log_id": "log_uuid_v4",
    "service": "hub",           // 路由到 Hub 服务
    "payload_encoding": "protobuf",
    "payload_type": "chat",
    "payload": { "conversation_id": "...", "content": "..." }
}
```

### 3.3 Frontier 配置

```rust
struct FrontierConfig {
    frontier_id: String,              // 连接唯一标识
    frontier_url: String,             // WebSocket 端点 URL
    heartbeat_interval: u32,          // 心跳间隔 (ms)
    reconnect_delay: u32,             // 重连延迟 (ms)
    max_reconnect_attempts: u32,      // 最大重连次数
}
```

---

## 4. 消息类型完整矩阵

### 4.1 WebSocket Proto 消息类型

| 消息类型 | 方向 | 描述 |
|---------|------|------|
| `WsProtoCLI` | 双向 | CLI ↔ Hub 核心通信 |
| `WsProtoConfirm` | 双向 | 消息确认 |
| `WsProtoSessionCreated` | 下行 | 会话创建通知 |
| `WsProtoSessionUpdated` | 下行 | 会话更新通知 |
| `WsProtoSessionDeleted` | 下行 | 会话删除通知 |
| `WsProtoConfirmWsMessage` | 上行 | WebSocket 消息确认 (2 字段) |
| `WsProtoCliPushConversationsDelete` | 下行 | 推送删除会话 |
| `WsProtoCliPushDeleteMessages` | 下行 | 推送删除消息 |
| `WsProtoCliPushMessageDelete` | 下行 | 推送单条消息删除 |
| `WsProtoCliPushMessageRevert` | 下行 | 推送消息回退 |

### 4.2 Frontier 消息类型

| payload_type | 描述 |
|-------------|------|
| `auth` | 认证握手 |
| `chat` | 聊天消息转发 |
| `sync` | 状态同步 |
| `notification` | 推送通知 |
| `heartbeat` | 心跳保活 |
| `confirm` | 消息确认 |
| `replay` | 历史消息重放 |

### 4.3 Push 消息类型

| 类型 | 描述 |
|------|------|
| `PushConversationsDelete` | 会话删除事件 |
| `PushDeleteMessages` | 消息删除事件 |
| `PushMessageDelete` | 单条消息删除 |
| `PushMessageRevert` | 消息回滚 |
| `PushMessageSize` | 消息大小更新 |

### 4.4 SSE 消息类型 (聊天)

| 事件 | 说明 |
|------|------|
| `sse.open` | 流开始 |
| `sse.delta` | 数据增量块 |
| `sse.end` | 流结束 |
| `sse.error` | 错误 |
| `sse.cancel` | 取消 |
| `sse.retry` | 重试指示 |
| `sse.heartbeat` | 心跳 (30s 无数据时) |

### 4.5 SSE 数据内容类型

| type | 说明 |
|------|------|
| `message_start` | 消息开始 |
| `content_block_delta` | 内容块增量 |
| `content_block_stop` | 内容块结束 |
| `message_stop` | 消息结束 |
| `content_block_start` | 内容块开始 (包含 tool_use 等) |

---

## 5. Hub 端点完整映射

### 5.1 REST API 端点

| 方法 | 端点 | 用途 |
|------|------|------|
| POST | `/conversations` | 创建/同步对话 |
| GET | `/conversations` | 获取对话列表 |
| POST | `/conversations/tasks/batchInsert` | 批量插入任务 |
| POST | `/conversations/messages/batchInsertMulti` | 批量插入消息 |
| GET | `/conversations/clis/messages/list` | 获取 CLI 消息列表 |
| POST | `/clis/register` | CLI 注册 |
| POST | `/clis/unregister` | CLI 注销 |
| GET | `/wsmessages/poll` | HTTP 轮询新消息 |
| POST | `/wsmessages/push` | HTTP 推送消息 |
| GET | `/conversations/{id}` | 获取会话详情 |
| GET | `/conversations/{id}/messages` | 获取会话消息历史 |

### 5.2 WebSocket 端点

```
wss://hub.trae.ai/ws?frontier_id={id}&app_runtime_type=electron&process_id={pid}&client_timestamp={ts}
```

### 5.3 消息上下行格式

**上行 (IDE → Server)：**
```typescript
interface UpstreamMessage {
    seq_id: number;       // 发送端序号
    type: string;         // 消息类型
    payload: any;         // 消息负载
    timestamp: number;    // 时间戳
}
```

**下行 (Server → IDE)：**
```typescript
interface DownstreamMessage {
    down_seq: number;     // 服务端下发序号
    type: string;         // 消息类型
    payload: any;         // 消息负载
    timestamp: number;    // 时间戳
}
```

### 5.4 WebSocket 连接参数

```
frontier_id:      "f_uuid_v4"
app_runtime_type: "electron"
process_id:       "abcd1234"
client_timestamp: 1735712345000
```

---

## 6. WS ↔ HTTP 双模通信

### 6.1 模式切换决策

```
HTTP Polling (默认启动)
      │
      ├── WebSocket 可用 ──→ WebSocket 模式
      │
      ├── WebSocket 断开 ──→ 尝试重连 (最多 5 次)
      │                         │
      │                         ├── 成功 → 消息重放 → WebSocket
      │                         └── 失败 → HTTP Fallback
      │
      └── WebSocket 恢复 ──→ 从 HTTP 切回 WebSocket
```

### 6.2 消息重放

当 WebSocket 重连后，需要重放断开期间丢失的消息：

```
1. 记录 lastSeqId (最后收到的消息序号)
2. WebSocket 重连成功
3. 发送 replay 请求：from_seq = lastSeqId
4. Server 重放 lastSeqId+1 之后的所有消息
5. 恢复到正常通信
```

### 6.3 HTTP 轮询

```
GET /wsmessages/poll
  params: { frontier_id, from_down_seq_id, limit }

POST /wsmessages/push
  body: [{ seq_id, type, payload, timestamp }, ...]

轮询间隔: pollIntervalMs = configurable
批量推送间隔: flushIntervalMs
批量推送阈值: flushCountThreshold
```

### 6.4 序列号间隙检测

```
[HubNetService] down_seq gap detected: expected 45, got 47
  → 检测到序号不连续
  → 切换到 HTTP Fallback 模式
  → 通过 HTTP 轮询补齐丢失的消息
```

---

## 7. CLI 注册与心跳

### 7.1 CLI 注册

```rust
struct RegisterCliRequest {
    cli_id: String,            // CLI 唯一标识 (cli_xxxxx)
    frontier_id: String,       // Frontier 连接标识
    app_id: String,            // 应用标识 ("trae-ide")
    product_id: String,        // 产品标识 ("trae")
    process_id: String,        // 进程 ID
}

struct RegisterCliResponse {
    // 1 个字段 (可能是 status)
}
```

**注册流程：**
```
1. IDE 启动 → 生成 cli_id (cli_随机16字符)
2. POST /clis/register → { cli_id, frontier_id, app_id, product_id, process_id }
3. Server 返回注册确认
4. 后续所有消息使用 cli_id 进行路由
5. IDE 关闭 → POST /clis/unregister
```

### 7.2 CLI 心跳

```
CLI 通过 WebSocket 发送心跳：
  service: "heartbeat_service"
  payload: { "type": "ping" }

心跳间隔: 30s (默认)
如果心跳超时，Server 认为 CLI 断开
```

### 7.3 CLI 标识

```javascript
cli_id = "cli_" + random(16 chars, [a-z0-9])
frontier_id = UUID v4
```

---

## 8. Domain Handoff 会话迁移

### 8.1 DomainAuthMeta

```rust
struct DomainAuthMeta {
    sso_type: String,       // SSO 提供商类型
    sso_host: String,       // SSO 主机 URL
    auth_from: String,      // 认证来源
    api_base: String,       // API 基础 URL
    tenant_id: String,      // 租户 ID
    domain: String,         // 域标识
}
```

### 8.2 Handoff 域配置

```
handoff_domain_auth_solo_cn           — SOLO 中国区域认证
handoff_domain_auth_bytedance_internal — ByteDance 内部域认证
```

### 8.3 本地 → 云端 Handoff

```
1. IDE 请求 handoff，提供 session_id
2. Server 生成 handoff_token（短 TTL）
3. IDE 将 handoff_token 转发到云端 Agent
4. 云端验证 token → 接管会话
5. 本地 IDE → 云端 Agent 的会话迁移完成
```

### 8.4 云端 → 本地 Handoff

```
1. 云端 Agent 请求 handoff，提供 session_id
2. Server 生成 handoff_token
3. 云端 Agent 将 token 转发到本地 IDE
4. 本地 IDE 验证 token → 接管会话
5. 云端 Agent → 本地 IDE 的会话迁移完成
```

### 8.5 应用场景

```
┌───────────────┐                    ┌─────────────────┐
│  本地 IDE     │                    │  云端 Agent     │
│  (Lite Mode)  │                    │  (Full Mode)    │
└───────┬───────┘                    └────────┬────────┘
        │                                     │
        │  场景 1: 本地 → 云端                 │
        │  (功能不够时提升到云端)               │
        │  ├── handoff request ────────────►  │
        │  ├── handoff_token ───────────────► │
        │  └── 会话迁移 ───────────────────► │
        │                                     │
        │  场景 2: 云端 → 本地                 │
        │  (云端降级到本地)                    │
        │  ◄── handoff request ──────────────┤
        │  ◄── handoff_token ────────────────┤
        │  ◄── 会话迁移 ─────────────────────┤
        │                                     │
```

---

## 9. Lite 沙箱模式

### 9.1 概述

Lite Mode 是 Trae 的云端 VM 沙箱执行模式，提供轻量级的代码运行环境。

```
Domain: domain/lite/
├── typing.rs          // Lite 模式类型定义 (954 行)
├── work_vm_aha.rs     // Work VM AHA 实现 (281 行)
└── ...                // VM 管理、状态同步
```

### 9.2 Lite VM 生命周期

```
1. create_project → 分配 Lite VM
2. create_chat_session → 关联 VM 与会话
3. VM 初始化 → vm_init_progress / status_changed 事件
4. send_message → 在 VM 内执行
5. subscribe → 监听 VM 事件
6. 会话结束 → VM 销毁
```

### 9.3 Lite VM 事件

```rust
// Lite VM 事件
vm_init_progress    // VM 初始化进度
status_changed      // VM 状态变更

// VM 状态
CREATING → RUNNING → SUSPENDED → TERMINATED
```

### 9.4 Lite 模式配置

```javascript
// 特征配置
solo_vm_config: SoloVMConfig,
lite_mode_enabled: boolean,

// 聊天会话创建响应中包含
RemoteSandboxInfo: {
    // 沙箱分配信息
    sandbox_id: String,
    vm_type: String,
    resource_limits: {...},
}
```

### 9.5 Remote Chat Session Data

```rust
// CreateChatSessionResponse (23 字段)
struct CreateChatSessionResponse {
    session_id: String,
    conversation_id: String,
    project_id: String,
    VM info: Option<LiteVMInfo>,                   // Lite VM 分配信息
    sandbox_allocation: Option<RemoteSandboxInfo>, // 沙箱分配
    history_file_urls: Vec<String>,                // 历史文件 URL
    handoff_targets: Vec<HandoffTarget>,           // Handoff 目标
    timestamps: Timestamps,                        // 时间戳
    version_snapshot: Option<VersionSnapshotInfo>, // 版本快照信息
    pre_termination: Option<PreTerminationInfo>,   // 预终止信息
    auto_create_project: bool,                     // 自动创建项目
    // + 12 more fields
}
```

---

## 10. Sandbox 执行沙箱

### 10.1 概述

本地代码执行沙箱，确保 Agent 执行的命令不会对系统造成危害。

**二进制文件：**
- Linux: `trae-sandbox` (18MB)
- Windows: `sbox_sdk.dll` (1.9MB)
- macOS: (内置于 ai-agent 中)

### 10.2 沙箱特性

```
├── Linux: namespace 隔离 + Lite VM
│   ├── PID namespace
│   ├── Mount namespace
│   ├── Network namespace
│   ├── User namespace
│   └── cgroup 资源限制
│
├── Windows: Job Objects
│   ├── 进程组管理
│   ├── 资源限制 (CPU/内存)
│   └── 进程树管理
│
└── 通用控制:
    ├── sandbox_rw_list — 可读写文件路径列表
    ├── sandbox_ro_list — 只读文件路径列表
    ├── sandbox_network_config — 网络访问控制
    ├── sandbox_filesystem_config — 文件系统访问控制
    └── Command red list — 禁止执行的命令列表
```

### 10.3 Sandbox 错误

```
TRAE Sandbox Error: init failed
create_sandbox failed
sdk crash
process launch failed
process crashed
hit restricted
```

### 10.4 SandboxTraceEvent

```rust
struct SandboxTraceEvent {
    // 3 elements
}
```

### 10.5 配置

```javascript
sandbox_filesystem_config: SandboxConfig,
sandbox_network_config: SandboxConfig,

// 特征配置
enable_ai_sandbox_awareness: boolean,   // AI 沙箱感知
```

---

## 11. 会话创建完整流程

### 11.1 完整链路

```
用户输入消息 → AI 响应（包含 Lite/Full 沙箱决策）：

                    ┌─────────────────────────────────────┐
                    │       完整会话创建流程                │
                    └─────────────────────────────────────┘

1.  IDE 创建本地项目
    └── POST /api/ide/v1/agents/runs
        { session_id, query, chat_mode: "agent" }

2.  AI 后端决定会话模式：
    ├── Lite Mode (轻量 VM，快速响应)
    │   ├── Create Lite VM
    │   ├── 关联 VM ↔ 会话
    │   ├── 执行代码/工具调用
    │   └── 返回结果
    │
    └── Full Mode (完整云端 Agent)
        ├── 创建云端会话
        ├── 建立 Hub Bridge 连接
        ├── 跨区域数据同步
        └── 在线 LLM 推理

3.  Hub Bridge 同步:
    ├── local_session ↔ remote_session
    ├── project ↔ project
    └── messages ↔ messages

4.  Agent 执行:
    ├── Plan (规划)
    ├── Execute (执行)
    ├── Tool Calls (工具调用)
    └── Result (结果)

5.  会话终止:
    ├── 自动完成
    ├── 用户取消
    ├── 超时终止
    └── Didomain Handoff（如果需要升级/降级）
```

### 11.2 Hub Bridge 会话同步

```
1. create_chat_session → Hub 注册会话
   ├── /conversations POST
   └── /conversations/{id}/messages batchInsertMulti

2. send_message → Hub 转发消息
   ├── WebSocket 实时推送
   └── HTTP fallback 批量推送

3. Hub 管理:
   ├── 消息序列号 (seq_id)
   ├── 下行序列号 (down_seq)
   ├── 消息确认 (WsProtoConfirm)
   └── 消息重放 (replay)

4. 同步频率:
   ├── flushIntervalMs — 批量推送间隔
   ├── pushConversationSize — 会话推送数量限制
   ├── pushMessageSize — 消息推送数量限制
   └── syncSessionChunkSize — 会话同步块大小
```

---

## 12. HubRemoteConfig 完整配置

### 12.1 配置字段 (17 字段)

```rust
struct HubRemoteConfig {
    // 基础
    fp_id: String,                           // Frontier 协议 ID
    frontier_url: String,                    // Frontier WebSocket URL

    // 重连
    max_ws_reconnect_attempts: i32,          // 最大重连次数 (5)
    ws_reconnect_delay_secs: i32,            // 重连延迟 (秒)

    // HTTP 轮询
    default_empty_flush_count: i32,          // 默认空推送计数
    poll_interval_ms: i32,                   // 轮询间隔 (ms)
    flush_interval_ms: i32,                  // 推送间隔 (ms)
    flush_count_threshold: i32,              // 推送计数阈值

    // WebSocket 消息
    ws_msg_size_threshold: i32,              // WebSocket 消息大小阈值 (bytes)

    // Push Sync
    push_sync: bool,                         // 启用推同步
    push_conversation_size: i32,             // 推送会话大小限制
    push_message_size: i32,                  // 推送消息大小限制
    sync_session_chunk_size: i32,            // 会话同步块大小

    // Cache
    max_sent_message_cache: i32,             // 最大发送消息缓存

    // CLI
    cli: ...,                                // CLI 配置
    seq_num: ...,                            // 序列号
}
```

### 12.2 配置默认值推断

```
max_ws_reconnect_attempts:    5
ws_reconnect_delay_secs:      2
ws_msg_size_threshold:        65536  (64KB)
poll_interval_ms:             5000   (5s)
flush_interval_ms:            3000   (3s)
flush_count_threshold:        10
max_sent_message_cache:       1000
push_conversation_size:       50
push_message_size:            100
sync_session_chunk_size:      20
```

---

## 附录 A: 关键源码路径

```
ai-agent (Rust):
apps/icube_server_rs/modules/ai-agent/src/
  ├── infrastructure/transport/
  │   ├── hub_bridge/
  │   │   ├── sender.rs:100      // Hub Bridge 发送器
  │   │   └── ...
  │   └── aha_net/
  │       └── stream.rs          // AHA 网络流
  ├── domain/
  │   ├── lite/
  │   │   ├── typing.rs          // Lite 类型定义 (954 行)
  │   │   └── work_vm_aha.rs     // Work VM AHA (281 行)
  │   ├── handoff/
  │   │   ├── down/service.rs    // 下游 handoff
  │   │   └── ...
  │   └── hub/
  │       └── hook/trigger.rs:26 // Hub 触发器

IDE (JavaScript):
main.js / default.js
  ├── out-build/vs/code/electron-main/iCubeRustManager.js  // Manager 管理
  └── node_modules/@byted-icube/manager-sdk/web/rpcclient.js // SDK 客户端
```

---

> 本报告基于 ai-agent 二进制反编译 + 协议分析文档 + 前端脚本代码分析。
> 部分配置默认值为推断值，实际值可能因版本不同有所变化。