# L09: Trae AI 完整通信链路全景分析

> 生成时间: 2026-06-03 ~14:00 GMT+8
> 分析版本: Trae IDE v2.3.30128
> 覆盖范围: Chat Webview → Extension Host → Main Process → ZMQ IPC → Rust Manager → ai-agent → Cloud API → 响应返回

---

## 0. 通信链路全景图

```
用户输入消息
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  L1: Chat Webview (Renderer Process)                                │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  @byted-icube/ai-modules-chat (React, 8305 lines)            │  │
│  │  技术栈: React + Katex + ReactDOM                             │  │
│  │  协议: Electron IPC (vscode API)                               │  │
│  │  postMessage / acquireVsCodeApi                               │  │
│  └───────────────┬───────────────────────────────────────────────┘  │
└──────────────────┼──────────────────────────────────────────────────┘
                   │ Electron IPC channel
                   │ Channel: "vscode:*" (vscode:getManagerInfo, etc.)
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  L2: Extension Host (插件进程)                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  @byted-icube 扩展集:                                        │  │
│  │  ├── ai-modules-chat      — AI 聊天功能                       │  │
│  │  ├── desktop-modules      — 桌面模块 (WebSocket ↔ Manager)    │  │
│  │  ├── trae-network-client  — NAPI-RS HTTP 客户端 (Rust)       │  │
│  │  ├── manager-sdk          — Manager SDK                       │  │
│  │  ├── webcomponents        — Web Components                    │  │
│  │  ├── slardar/tea          — 遥测                              │  │
│  │  ├── dynamic-config-sdk   — 动态配置                          │  │
│  │  └── bundled-deps         — 打包依赖                          │  │
│  │  协议: Electron ipcRenderer.invoke → ipcMain.handle            │  │
│  └───────────────┬───────────────────────────────────────────────┘  │
└──────────────────┼──────────────────────────────────────────────────┘
                   │ Electron IPC
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  L3: Electron Main Process (main.js)                                │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  iCube 平台模块:                                              │  │
│  │  ├── iCubeRustManager    — Rust Manager 进程生命周期管理      │  │
│  │  ├── iCubeAuth           — 认证 (OAuth2 PKCE + Token 刷新)    │  │
│  │  ├── frontier            — Hub Bridge 通信                    │  │
│  │  │   ├── FrontierConnection    — WebSocket 连接管理           │  │
│  │  │   ├── FrontierMessageSender — 消息发送                     │  │
│  │  │   ├── FrontierMessageHandler — 消息处理                    │  │
│  │  │   └── iCubeHandler         — iCube 协议 handler            │  │
│  │  ├── iCubeCrawler        — 浏览器自动化/爬虫                   │  │
│  │  └── bootService         — BootConfig 获取                    │  │
│  │                                                               │  │
│  │  通信方式 (双重):                                              │  │
│  │  1. AHA RPC (@aha-kit/ipc + @aha-kit/rpc)                    │  │
│  │     → ZMQ Dealer → ZMQ Router → ai-agent                     │  │
│  │     → JSON-RPC 2.0 over IPC Unix Socket                      │  │
│  │    地址: ipc:///tmp/aha/{serverName}.sock                     │  │
│  │                                                               │  │
│  │  2. manager-sdk WebSocket Client                              │  │
│  │     → ws://127.0.0.1:{PORT}/module/manager/1                  │  │
│  │     → 通过 Manager 路由到 ai-agent                            │  │
│  └───────────────┬───────────────────────────────────────────────┘  │
└──────────────────┼──────────────────────────────────────────────────┘
                   │ ZMQ Dealer-Router (IPC Unix Socket)
                   │ 或 WebSocket (127.0.0.1:{PORT})
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  L4: Rust Manager Process (manager binary)                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  ZMQ Router (服务端) — 接受所有模块连接                        │  │
│  │  ├── accept("ai-agent")     — LLM 推理                         │  │
│  │  ├── accept("ai")           — AI Completion (代码补全)         │  │
│  │  └── accept("ai-completion")— 更细粒度补全                    │  │
│  │                                                               │  │
│  │  WebSocket Server (Manager SDK)                               │  │
│  │  ws://127.0.0.1:{PORT}/module/manager/1                       │  │
│  │                                                               │  │
│  │  路由: 根据 RPC method name → 分发到对应模块                   │  │
│  │  协议: JSON-RPC 2.0 (由 AHA RPC 层封装)                       │  │
│  └───────────────┬───────────────────────────────────────────────┘  │
└──────────────────┼──────────────────────────────────────────────────┘
                   │ 内部 IPC (同进程内模块间)
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  L5: ai-agent (Rust Shared Library .so)                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  DDD 架构:                                                     │  │
│  │  ├── Handler 层: 注册所有 RPC method (sse.open, etc.)        │  │
│  │  ├── Service 层: ChatService, AgentService, SessionService    │  │
│  │  ├── Domain 层: ChatArgs(47字段), ChatMessageData(37/44字段) │  │
│  │  └── Infrastructure: HTTP Client (reqwest), WS (tungstenite) │  │
│  │                                                               │  │
│  │  完整处理流程:                                                 │  │
│  │  1. 接收 JSON-RPC request (method: sse.open)                  │  │
│  │  2. 构建 ChatArgs (47 fields)                                 │  │
│  │  3. 选择 Provider/Model (model_selection_strategy)            │  │
│  │  4. 渲染 Prompt 模板 (KV Store + PromptRenderer)              │  │
│  │  5. 构建 HTTP 请求 → Cloud API                                │  │
│  │  6. 接收 SSE 流 → 转发为 JSON-RPC stream notifications       │  │
│  └───────────────┬───────────────────────────────────────────────┘  │
└──────────────────┼──────────────────────────────────────────────────┘
                   │ HTTPS / WebSocket
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  L6: Cloud API Backend                                              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  主端点: POST /api/ide/v1/agents/runs                        │  │
│  │  备用: POST /api/ide/v1/chat                                  │  │
│  │  认证: x-cloudide-token + x-ide-token + Authorization: Bearer │  │
│  │  响应: SSE 流 (event: delta / end / error)                    │  │
│  │                                                               │  │
│  │  Hub Bridge (可选通道)                                         │  │
│  │  wss://hub.trae.ai/ws  (Frontier Protocol)                    │  │
│  │  Frontier 帧: {service, method, payload, headers}             │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. L1: Chat Webview → Extension Host

### 1.1 前端组件

Chat Webview 使用 `@byted-icube/ai-modules-chat` 包（`index.mjs`, 8305 行），这是一个 React 组件：
- 技术栈: React + Katex (数学公式渲染) + ReactDOM
- 内部使用了 `AIScene` 枚举: `Completion | MultiEdit | Test | ExplainCode | LintFix | Doc | EditCode | GenerateCode | Question | Search | NewBuilder`
- 遥测: 通过 `TeaReporter` 上报 AI 贡献事件

### 1.2 通信方式

Webview 通过标准的 **VS Code Webview API** 与 Extension Host 通信：

```
Renderer Process (Webview)
  │
  ├── acquireVsCodeApi() → 获取 vscode API 对象
  ├── vscode.postMessage({type, payload}) → 发送消息给 Extension Host
  │
  ▼
Extension Host (插件进程)
  │
  ├── window.addEventListener('message', handler) → 接收 Webview 消息
  └── panel.webview.onDidReceiveMessage → VS Code 提供的监听
```

### 1.3 关键发现

- Trae 的 Webview 被视为 VS Code 的扩展 Webview，使用标准的 `vscode.postMessage` API
- `@byted-icube/ai-modules-chat` 是 frontend-heavy 的 React 应用，打包为 8305 行 mjs
- `@byted-icube/desktop-modules` 提供桌面端 Webview 容器 (`index.css + index.mjs`)

---

## 2. L2: Extension Host → Main Process

### 2.1 架构

Extension Host（插件进程）通过 **Electron IPC** 与 Main Process 通信。模式是：

```
Extension Host
  │
  ├── ipcRenderer.invoke('channel', args) → Promise<result>
  │   └── Main Process: ipcMain.handle('channel', handler)
  │
  ├── ipcRenderer.on('channel', callback)  → 事件监听
  │   └── Main Process: ipcMain.emit('channel', data)
  │
  └── vscode.commands.executeCommand('commandId') → 命令执行
```

### 2.2 已知 IPC Channel

从 main.js 提取的路径分析:

| Channel Pattern | 用途 | 方向 |
|----------------|------|------|
| `vscode:getManagerInfo` | 获取 Manager 端口/状态 | Extension → Main |
| `vscode:webview` | Webview 管理 | Extension → Main |
| `vscode:*` | 通用 VS Code IPC | 双向 |

### 2.3 iCube 桥接

扩展通过 **ipcRenderer** 调用 Main Process 上的 iCube 服务：

```
Extension Host
  │
  ├── ipcRenderer.invoke("vscode:getManagerInfo")
  │   → 返回 Manager WebSocket 端口
  │
  ├── @byted-icube/manager-sdk
  │   → 通过 RpcWebSocketClient 连接 Manager
  │   → ws://127.0.0.1:{PORT}/module/manager/1?session_id={sessionId}
  │
  └── @byted-icube/trae-network-client (Rust NAPI)
      → HTTP 请求 (内部通过 NAPI-RS native binding)
      → trae-network-node.{platform}.node
```

### 2.4 关键路径: Extension → Cloud API (直连)

存在一条**绕过 Manager 的直连路径**：

```
Extension Host
  │
  ├── @byted-icube/trae-network-client (NAPI-RS Rust 原生模块)
  │   ├── 内部 HTTP 客户端 (Rust reqwest)
  │   ├── 路径: `internal/index.js` → `.node` binding
  │   └── 用于不需要 Manager 路由的 HTTP 请求
  │
  └── 或通过 Electron net 模块 (Chromium 网络栈)
```

---

## 3. L3: Main Process → ZMQ IPC → Rust Manager

### 3.1 双重通信通道

Main Process 同时使用**两种协议**与底层服务通信：

```
┌─────────────────────────────────────────────┐
│           Electron Main Process              │
│                                             │
│  AHA RPC Client          Manager SDK Client │
│  ┌─────────────────┐    ┌────────────────┐  │
│  │ @aha-kit/rpc    │    │ manager-sdk    │  │
│  │ @aha-kit/ipc    │    │ WebSocket      │  │
│  │                 │    │                │  │
│  │ ZMQ Dealer ─────┼─── │ WS Client ────┼──│
│  └─────────────────┘    └────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │ ZMQ IPC Unix Socket         │ WebSocket
    │ ipc:///tmp/aha/{name}.sock  │ ws://127.0.0.1:{port}
    ▼                              ▼
┌───────────────────────────────────────┐
│         Rust Manager Process           │
│                                       │
│  ZMQ Router (服务端)   WS Server      │
│  ├── ai-agent          ├── /module/   │
│  ├── ai                │   manager/1  │
│  └── ai-completion     └──────────────│
└───────────────────────────────────────┘
```

### 3.2 AHA IPC (ZMQ) 详细信息

**包结构 (`@aha-kit/ipc`):**

```json
{
    "version": 1,
    "id": "{serverUUID}",
    "packet_type": "user" | "control",
    "payload": "{JSON-RPC message string}"
}
```

**地址生成:**
- Unix: `ipc:///tmp/aha/{serverName}.sock`
- Windows: `{TEMP}\\aha\\{serverName}.sock`
- 就绪标记文件: `/tmp/aha/{serverName}.sock.ready`

**Client 连接 (AhaIpcConnectionImpl):**
- `#routingId = crypto.randomUUID()` — 每次连接唯一路由 ID
- `#socket = new Dealer({...})` — ZMQ Dealer 类型
- 连接到 Router 绑定的 IPC 地址

### 3.3 AHA RPC (JSON-RPC 2.0) 详细信息

**请求格式:**

```json
{
    "jsonrpc": "2.0",
    "method": "sse.open",
    "params": { "stream_id": "uuid", "chat_args": {...} },
    "id": 1
}
```

**已知 RPC Methods:**

| Method | 用途 | 方向 |
|--------|------|------|
| `sse.open` | 打开 SSE 流（发起 AI 请求） | Client → Server |
| `sse.cancel` | 取消 SSE 流 | Client → Server |
| `rpc.ping` | 心跳检测 | 双向 |
| `rpc.close` | 关闭连接 | 双向 |
| `rpc.service` | 注册服务 | Server → Client |
| `rpc.method` | 注册方法 | Server → Client |

**流式响应 (JSON-RPC notification):**

```json
{
    "jsonrpc": "2.0",
    "method": "rpc.stream.{streamId}",
    "params": { "data": "base64_encoded_chunk" },
    "meta": { "stream": true, "streamId": "uuid", "chunkIndex": 0, "done": false }
}
```

### 3.4 Manager SDK WebSocket 通信

Manager 还提供 WebSocket Server，地址为 `ws://127.0.0.1:{PORT}/module/manager/1?session_id={sessionId}`：

```json
{
    "msg_type": "execute_command",
    "payload": "...",
    "stream_id": "..."
}
```

命令类型:
| `msg_type` | 用途 |
|-----------|------|
| `execute_command` | 执行管理命令 |
| `execute_command_result` | 命令执行结果 |
| `icube.event.aiSlardarReport` | 遥测报告 |
| `error` | 错误响应 |

---

## 4. L4: Rust Manager Process

### 4.1 进程信息

| 属性 | 值 |
|------|-----|
| 二进制路径 | `{appRoot}/bin/manager` |
| 库路径 | `{appRoot}/bin/lib` |
| 日志 | `{userDataDir}/ModularData/manager_{out,err,panic}.log` |
| PID 文件 | `{pid}.manager.pid` |
| 端口范围 | 51000+ |
| 关闭超时 | 999999999 秒 (极长, 持久运行) |

### 4.2 模块注册表

```javascript
{
    completionServer: 'ai-completion',  // AI 代码补全
    chatServer:       'ai',            // AI 聊天 (标准)
    agentServer:      'ai-agent',      // AI Agent (带工具调用)
}
```

通过环境变量 `ICUBE_DISABLED_MODULES` 可禁用模块。

### 4.3 路由逻辑

Manager 收到 JSON-RPC 请求后，根据 `method` 的前缀路由到对应模块：
- `sse.open` / `sse.cancel` → ai-agent
- `complete` / `completion` → ai-completion
- 其他 → 根据注册表匹配

---

## 5. L5: ai-agent (Rust)

### 5.1 架构概述

ai-agent 是一个 Rust 共享库（`libai-agent.so`, 127MB），DDD（领域驱动设计）架构：

```
┌─────────────────────────────────────────────┐
│  Handler 层 (RPC method 注册)               │
│  ├── sse::open → handle_chat_request       │
│  ├── sse::cancel → handle_cancel           │
│  └── ...                                    │
├─────────────────────────────────────────────┤
│  Service 层                                  │
│  ├── ChatService     — 对话管理             │
│  ├── SessionService  — 会话生命周期         │
│  ├── AgentService    — Agent 编排            │
│  ├── PromptService   — 模板渲染              │
│  └── ToolService     — 工具调用              │
├─────────────────────────────────────────────┤
│  Domain 层                                    │
│  ├── ChatArgs (47 fields)                    │
│  ├── ChatMessageData (37/44 fields)          │
│  ├── SendMsgToChatArgs (13 fields)           │
│  ├── ModelSelectionStrategy                  │
│  └── PromptTemplate                          │
├─────────────────────────────────────────────┤
│  Infrastructure 层                            │
│  ├── HTTP Client (reqwest)                   │
│  ├── WebSocket Client (tokio-tungstenite)    │
│  ├── SQLCipher Database                      │
│  ├── KV Store (prompt 模板缓存)              │
│  └── Token Manager                           │
└─────────────────────────────────────────────┘
```

### 5.2 请求处理流程

```
1. 接收 JSON-RPC request: sse.open
   │
2. 解析 ChatArgs (47 fields):
   │  ├── session_id: String
   │  ├── conversation_id: String
   │  ├── chat_mode: "agent" | "normal" | "fast"
   │  ├── agent_type: Option<String>
   │  ├── model_name: Option<String>
   │  ├── model_config: ModelConfig
   │  ├── messages: Vec<ChatMessageData>
   │  ├── tools: Vec<ToolDef>
   │  ├── max_tokens: u32
   │  ├── temperature: f32
   │  └── ... (37 more fields)
   │
3. Prompt 渲染:
   │  ├── PromptRenderer 从 KV Store 加载模板
   │  ├── 注入 history_user_input, context, system_prompt
   │  ├── 支持 AES-256-GCM 加密模板
   │  └── 11 种 Prompt Key (plan_v2, agents, master_agent, ...)
   │
4. 模型选择:
   │  ├── 根据 model_selection_strategy 选择 Provider
   │  ├── 检查 Provider 可用性 (client_connect)
   │  └── 确定最终 model_name + provider
   │
5. 构建 HTTP 请求:
   │  ├── URL: POST /api/ide/v1/agents/runs
   │  ├── Headers: x-cloudide-token, x-ide-token, Authorization
   │  ├── Body: { session_id, query, chat_mode, model_config }
   │  └── Stream: true (SSE)
   │
6. 发送请求到 Cloud API
   │
7. 接收 SSE 响应流:
   │  ├── event: sse.delta → 内容块
   │  ├── event: sse.end → 完成
   │  ├── event: sse.error → 错误
   │  └── JSON-RPC stream notification 转发回 Main Process
```

### 5.3 Provider 模型选择

从 `POST /api/ide/v1/providers` (L08 测试确认) 可知当前支持 25 个供应商：

| Provider | 示例模型 |
|----------|---------|
| anthropic | claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5 |
| deepseek | deepseek-v4-pro, deepseek-v4-flash |
| byteplus | seed-2-0-pro-260328, seed-2-0-lite-260228 |
| volcengine | doubao-seed-2-0-code-preview-260215 |
| aliyuncs | qwen3-coder-plus, qwen3-coder-flash |
| bigmodel | glm-5, glm-5.1 |
| Kimi-Global | kimi-k2.5 |
| +19 个更多 | |

---

## 6. L6: Cloud API

### 6.1 端点矩阵

| 端点 | 方法 | 状态 (L08) | 用途 |
|------|------|-----------|------|
| `/api/ide/v1/agents/runs` | POST | 200 (quota 5003) | 主要 Agent 聊天 |
| `/api/ide/v1/chat` | POST | 200 (code 4001) | 旧版聊天 (参数格式不兼容) |
| `/api/ide/v2/llm_raw_chat` | POST | 400 | 原始 LLM (可能已废弃) |
| `/api/ide/v1/llm_raw_chat` | POST | 400 | 原始 LLM (可能已废弃) |
| `/api/ide/v1/providers` | POST | 200 ✅ | 供应商列表 |
| `/api/ide/v1/model_list` | GET/POST | 500 | 模型列表 (损坏) |

### 6.2 请求结构（对比）

**我们脚本发送的 (works for agents/runs):**
```json
{
    "session_id": "s_hex12",
    "query": "用户消息",
    "chat_mode": "agent",
    "model_config": { "model_name": "claude-sonnet-4-6", "max_tokens": 1024 }
}
```

**IDE 实际发送的 (猜测 /api/ide/v1/chat 所需):**
```json
{
    "session_id": "s_hex12",
    "conversation_id": "c_hex12",
    "messages": [{"role": "user", "content": "消息"}],
    "chat_mode": "agent",
    "model_config": { "model_name": "...", "max_tokens": 4096, "temperature": 0.7 },
    "tools": [{"type": "function", "function": {"name": "...", "description": "..."}}],
    "stream": true
}
```

**可能缺失字段导致 `4001`:** `conversation_id` 和 `messages` 数组格式

### 6.3 SSE 响应格式

```
event: delta
data: {"type": "content_block_delta", "delta": {"text": "Hello"}}

event: delta
data: {"type": "content_block_delta", "delta": {"text": " world"}}

event: end
data: {"type": "message_stop"}

event: error
data: {"code": 5003, "message": "We're sorry, your agent running quota limit is exceeded."}
```

### 6.4 认证头

```http
x-cloudide-token: <JWT access_token>
x-ide-token: <JWT access_token>
Authorization: Bearer <JWT access_token>
Content-Type: application/json
```

Token 来源: BootConfig 获取 tokenHost → ExchangeToken API → JWT

---

## 7. 响应回传路径

```
Cloud API (SSE stream)
    │
    ▼
ai-agent (Rust)
    │  SSE events → JSON-RPC stream notifications
    │  {
    │    "jsonrpc": "2.0",
    │    "method": "rpc.stream.{streamId}",
    │    "params": { "data": "delta_content" },
    │    "meta": { "stream": true, "chunkIndex": N, "done": false }
    │  }
    ▼
Rust Manager (ZMQ Router → WebSocket)
    │  ZMQ Router 接收 stream notification
    │  → 转发到 Main Process ZMQ Dealer
    ▼
Main Process (main.js)
    │  AHA RPC 接收 stream notification
    │  → 解析 JSON-RPC
    │  → 通过 Electron IPC 发送到 Extension Host
    │  ipcMain → ipcRenderer
    ▼
Extension Host
    │  接收 IPC 事件
    │  → 转换数据格式
    │  → 通过 webview.postMessage() 发送到 Renderer
    ▼
Chat Webview (React)
    │  window.addEventListener('message', handler)
    │  → 解析 content_block_delta
    │  → 追加到对话渲染 (React state update)
    ▼
用户看到 AI 回复
```

### 7.1 各层数据转换

| 层 | 入格式 | 出格式 |
|----|--------|--------|
| Cloud API → ai-agent | SSE: `event: delta\ndata: {...}` | JSON-RPC notification |
| ai-agent → Manager | JSON-RPC stream notification | 同左 (透传) |
| Manager → Main Process | ZMQ multicast (JSON-RPC) | Electron IPC event |
| Main Process → Extension | Electron IPC | `webview.postMessage()` |
| Extension → Webview | `postMessage(portMessage)` | JS Event |
| Webview → 用户 | React 渲染 | DOM/Markdown |

---

## 8. 关键参数汇总

### 启动环境变量 (32 个 ICUBE_*)

| 变量 | 示例值 | 用途 |
|------|--------|------|
| `ICUBE_PROXY_HOST` | `127.0.0.1` 或 `::1` | IPC 代理主机 |
| `ICUBE_PROXY_PORT` | `51000` | Manager WebSocket 端口 |
| `ICUBE_USE_IPV6` | `true`/`false` | IP 版本选择 |
| `ICUBE_CODEMAIN_SESSION` | UUID | 会话标识 |
| `ICUBE_MODULAR_DATA_DIR` | `{userData}/ModularData` | 模块数据目录 |
| `ICUBE_DISABLED_MODULES` | `""` | 禁用的模块列表 |
| `ICUBE_PRODUCT_TYPE` | `desktop` | 产品类型 |
| `ICUBE_MAIN_PPID` | `{pid}` | 父进程 PID |

### ZMQ IPC 参数

| 参数 | 值 |
|------|-----|
| 传输协议 | `ipc://` (Unix Socket) |
| 套接字类型 | Dealer (客户端) / Router (服务端) |
| Socket 路径 | `/tmp/aha/{serverName}.sock` |
| 心跳间隔 | 可配置, 默认值见 `@aha-kit/ipc` constants |
| 路由 ID | UUID v4 (每次连接随机生成) |
| 消息序列化 | JSON 字符串 |
| 包版本 | 1 |

### Cloud API 参数

| 参数 | 值 |
|------|-----|
| Chat Host (SG) | `https://coresg-normal.trae.ai` |
| Token Host (SG) | `https://api-sg-central.trae.ai` |
| Token 刷新 | `POST /cloudide/api/v3/trae/oauth/ExchangeToken` |
| ClientID | `ono9krqynydwx5` |
| SSE 事件 | `delta`, `end`, `error` |
| 错误码 5003 | "agent running quota limit exceeded" |
| 错误码 4001 | "param is invalid" |

---

## 9. 完整时序图

```
用户                    Chat Webview           Extension Host          Main Process           Rust Manager          ai-agent             Cloud API
 │                          │                      │                       │                      │                     │                     │
 │  输入消息                 │                      │                       │                      │                     │                     │
 │─────────────────────────►│                      │                       │                      │                     │                     │
 │                          │                      │                       │                      │                     │                     │
 │                          │ vscode.postMessage() │                       │                      │                     │                     │
 │                          │─────────────────────►│                       │                      │                     │                     │
 │                          │                      │                       │                      │                     │                     │
 │                          │                      │ ipcRenderer.invoke()  │                      │                     │                     │
 │                          │                      │─── (vscode:* channel)►│                      │                     │                     │
 │                          │                      │                       │                      │                     │                     │
 │                          │                      │                       │ ZMQ Dealer.send()     │                     │                     │
 │                          │                      │                       │── sse.open ──────────►│                     │                     │
 │                          │                      │                       │   (JSON-RPC 2.0)      │                     │                     │
 │                          │                      │                       │                      │  Router → ai-agent   │                     │
 │                          │                      │                       │                      │─────────────────────►│                     │
 │                          │                      │                       │                      │                     │                     │
 │                          │                      │                       │                      │                     │ HTTP POST            │
 │                          │                      │                       │                      │                     │── agents/runs ──────►│
 │                          │                      │                       │                      │                     │                     │
 │                          │                      │                       │                      │                     │     SSE stream       │
 │                          │                      │                       │                      │                     │◄─────────────────────│
 │                          │                      │                       │                      │                     │                     │
 │                          │                      │                       │                      │ JSON-RPC stream notif│                     │
 │                          │                      │                       │◄──────────────────────│◄────────────────────│                     │
 │                          │                      │                       │                      │                     │                     │
 │                          │                      │  ipcRenderer.send()   │                      │                     │                     │
 │                          │                      │◄──────────────────────│                      │                     │                     │
 │                          │                      │                       │                      │                     │                     │
 │                          │  webview.postMsg()   │                       │                      │                     │                     │
 │                          │◄─────────────────────│                       │                      │                     │                     │
 │                          │                       │                      │                     │                     │                     │
 │  看到回复 ◄──────────────│                       │                      │                     │                     │                     │
```

---

## 10. 关键发现总结

### 架构特点

1. **双重通信通道**: Main Process 同时通过 AHA IPC (ZMQ) 和 Manager SDK (WebSocket) 与底层通信
2. **ZMQ Dealer-Router**: 通过 `/tmp/aha/` 下的 Unix Socket 实现 IPC，JSON-RPC 2.0 编码
3. **Manager 进程**: Rust 实现的中央路由，管理 ai-agent / ai / ai-completion 三个模块
4. **Webview 直连扩展**: 使用标准的 VS Code Extension Webview API (`acquireVsCodeApi` + `postMessage`)
5. **NAPI-RS 原生模块**: `trae-network-client` 是一个 Rust NAPI 绑定，提供 HTTP 客户端能力

### 认证路径

```
BootConfig (icube-boot.trae.ai)
    → tokenHost discovery
    → ExchangeToken API (refresh_token → access_token JWT)
    → x-cloudide-token header 注入每个 HTTP 请求
    → ai-agent 用此 token 调用 Cloud API
```

### 配额限制

- 当前 `agent running quota` (code 5003) 是所有 agents/runs 类请求的全局限制
- 配额按 TenantID (`7o2d894p7dr0o4`) 计算
- 影响所有 25 个供应商的全部模型
- /api/ide/v1/chat 端点返回 code 4001 (参数格式不兼容，非配额问题)

### 未解决的细节

- `/api/ide/v1/chat` 要求的 exact payload 结构（缺失 `conversation_id` + `messages` 数组格式）
- ZMQ heartbeat 参数的具体值
- Frontier Hub Bridge 帧的 protobuf 编码细节
- 沙箱 (trae-sandbox) 的内部虚拟机结构