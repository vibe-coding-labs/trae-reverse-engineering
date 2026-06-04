# Trae 完整通信协议与架构分析报告

> 生成时间: 2026-06-01 10:15 GMT+8  
> 分析版本: Trae IDE v2.3.30128

---

## 目录

1. [总体架构概览](#1-总体架构概览)
2. [进程模型与启动流程](#2-进程模型与启动流程)
3. [AHA IPC 层（ZMQ Dealer-Router）](#3-aha-ipc-层zmq-dealer-router)
4. [AHA RPC 层（JSON-RPC 2.0）](#4-aha-rpc-层json-rpc-20)
5. [Rust Manager 进程](#5-rust-manager-进程)
6. [Manager SDK 通信层](#6-manager-sdk-通信层)
7. [活动检测（Liveness）系统](#7-活动检测liveness系统)
8. [流式传输系统](#8-流式传输系统)
9. [认证系统](#9-认证系统)
10. [聊天 API 调用链](#10-聊天-api-调用链)
11. [Hub Bridge 协议](#11-hub-bridge-协议)
12. [关键配置与常量](#12-关键配置与常量)
13. [通信流程图](#13-通信流程图)

---

## 1. 总体架构概览

Trae IDE 的架构分为四层：

```
+-------------------------------------------------------------------+
|  Electron Renderer Process (UI)                                    |
|  +-------------------------------------------------------------+  |
|  |  iCube AI Chat UI / Workbench                               |  |
|  |  (React/Vue Components)                                     |  |
|  +-------------------------------------------------------------+  |
+-------------------------------------------------------------------+
          |  Electron IPC (ipcMain.handle / ipcRenderer.invoke)
          |  Channel: "vscode:*" (vscode:getManagerInfo, etc.)
          v
+-------------------------------------------------------------------+
|  Electron Main Process                                            |
|  +-------------------------------------------------------------+  |
|  |  AHA RPC (JSON-RPC 2.0)                                     |  |
|  |  +-- AHA IPC (ZMQ Dealer) --+                                |  |
|  |  |  connect("ai-completion") |                                |  |
|  |  |  connect("ai")           |                                |  |
|  |  |  connect("ai-agent")     |                                |  |
|  |  +--------------------------+                                |  |
|  |                                                              |  |
|  |  manager-sdk (WebSocket)                                     |  |
|  |  +-- RpcWebSocketClient -----+                               |  |
|  |  |  ws://127.0.0.1:{PORT}    |                               |  |
|  |  +---------------------------+                               |  |
|  +-------------------------------------------------------------+  |
+-------------------------------------------------------------------+
          |  ZMQ Dealer-Router  /  WebSocket
          v
+-------------------------------------------------------------------+
|  Rust Manager Process (manager)                                   |
|  +-------------------------------------------------------------+  |
|  |  AHA IPC Server (ZMQ Router)                                |  |
|  |  +-- accept("ai-completion")  +  +-- Router socket          |  |
|  |  +-- accept("ai")             |  |  bind(ipc:///tmp/aha/..) |  |
|  |  +-- accept("ai-agent")       |  +--------------------------+  |
|  |  +---------------------------+                                 |  |
|  |  +-- Manager SDK WebSocket Server --------------------------+  |  |
|  |  |  ws://127.0.0.1:{PORT}   ↔  RPC calls                   |  |  |
|  |  +----------------------------------------------------------+  |  |
|  |                                                              |  |
|  |  Modules (loaded via env ICUBE_DISABLED_MODULES):            |  |
|  |  - ai-agent : LLM 推理、会话管理                              |  |
|  |  - ai       : AI Completion（补全）                           |  |
|  |  - ai-completion : 更细粒度的 completion                     |  |
|  +-------------------------------------------------------------+  |
+-------------------------------------------------------------------+
          |
          v
+-------------------------------------------------------------------+
|  Backend APIs (HTTPS)                                             |
|  - icube-normal.trae.ai (Chat)                                    |
|  - coresg-normal.trae.ai (SG Chat)                                |
|  - mcs-boot.trae.ai (Model Config)                                |
|  - token.trae.ai (Auth)                                           |
+-------------------------------------------------------------------+
```

---

## 2. 进程模型与启动流程

### 2.1 iCubeRustManager

核心类：`iCubeRustManager`（`iCubeRustManager.js`，在 `default.js` 的 `cX` 模块中定义）

**启动流程：**

```
1. Main Process ready
2. iCubeRustManager.init()
   ├── 生成 codeMainSession (UUID)
   ├── 检查 isBuilt / ICUBE_MANAGER_BASE_DIR
   ├── 检查 setup 是否完成
   └── 调用 startManager()

3. startManager(args, env)
   ├── 找可用端口 (portfinder: 51000+)
   ├── 设置环境变量:
   │   ICUBE_PROXY_HOST     = "127.0.0.1" 或 "::1"
   │   ICUBE_PROXY_PORT     = {port}
   │   ICUBE_USE_IPV6       = "true"/"false"
   │   ICUBE_ELECTRON_PATH  = process.execPath
   │   ICUBE_CODEMAIN_SESSION = {UUID}
   │   ICUBE_MACHINE_ID     = {machineId}
   │   ICUBE_BUILD_VERSION  = {version}
   │   ICUBE_QUALITY        = {quality}
   │   ICUBE_BUILD_TIME     = {date}
   │   ICUBE_PROVIDER       = {provider}
   │   ICUBE_APP_VERSION    = {appVersion}
   │   ICUBE_VSCODE_VERSION = {vscodeVersion}
   │   RUST_LOG             = "info" | "trace"
   │   RG_PATH              = {ripgrep binary}
   │   ICUBE_PRODUCT_TYPE   = "desktop"
   │   ICUBE_USER_DATA_DIR  = {userDataDir}
   │   ICUBE_MODULE_LOG_TO_FILE = "true"
   │   ICUBE_MODULE_PID_DIR = {pidDir}
   │   ICUBE_MANAGER_PID_FILE = {pid}.manager.pid
   │   ICUBE_MANAGER_LOG_DIR = {logsDir}
   │   ICUBE_MAIN_PPID      = {ppid}
   │   ICUBE_FORCE_RANDOM_PORT = "true"
   │   ICUBE_MODULAR_DATA_DIR = {ModularData dir}
   │   ICUBE_GLOBAL_STORAGE_DIR = {globalStorage dir}
   │   ICUBE_DISABLED_MODULES = {disabled modules}
   │   ... (many more)
   ├── spawn("manager", { detached: true })
   └── 通过 IPC handler "vscode:getManagerInfo" 暴露端口信息
```

### 2.2 模块注册表

```javascript
// default.js 47826
const MODULE_REGISTRY = {
    completionServer: 'ai-completion',  // AI 代码补全
    chatServer:       'ai',            // AI 聊天
    agentServer:      'ai-agent',      // AI Agent
};
```

模块可以通过环境变量 `ICUBE_DISABLED_MODULES` 禁用（逗号分隔），
或者在 `nativeAppConfig.dsc` 中配置。

---

## 3. AHA IPC 层（ZMQ Dealer-Router）

### 3.1 基础架构

**包名:** `@aha-kit/ipc-linux-x64` (平台特定，还有 `@aha-kit/ipc` 通用层)  
**库:** `@aha-kit/zmq` (Rust 实现) / `zeromq` (C++ 实现)  
**模式:** Dealer-Router (客户端-服务器)

### 3.2 地址生成

```javascript
// utils.js
function generateIpcAddress(serverName, runtimeDir) {
    const safeName = sanitizeName(serverName);
    const ahaDir = getIpcDir(runtimeDir);  // /tmp/aha/
    const socketPath = path.join(ahaDir, `${safeName}.sock`);
    return `ipc://${socketPath}`;
}
```

- Unix: `/tmp/aha/{serverName}.sock`
- Windows: `{TEMP}\aha\{serverName}.sock`
- 标记文件: `/tmp/aha/{serverName}.sock.ready`

### 3.3 数据包结构

```javascript
// packet.js
{
    version: 1,          // 当前版本号
    id: "{server UUID}", // 服务器端 ID，客户端用于验证
    packet_type: "user" | "control",  // 用户消息或控制消息
    payload: "{JSON-RPC string}"      // JSON 字符串
}
```

- **User 包**: 常规 JSON-RPC 消息
- **Control 包**: 控制消息（心跳、关闭等）

### 3.4 客户端连接

```javascript
// client.js
class AhaIpcConnectionImpl {
    #routingId = crypto.randomUUID();  // 路由 ID (ZMQ identity)
    #socket = new Dealer({            
        routingId: this.#routingId,
        heartbeatInterval: 1000,       // ZMQ_HEARTBEAT_INTERVAL
        heartbeatTimeout: 3000,        // ZMQ_HEARTBEAT_TIMEOUT
    });
    #ipcAddress = "ipc:///tmp/aha/{name}.sock";
    
    // 接收循环：for await...of
    startReceive() {
        for await (const frames of this.#socket) {
            const packet = deserializePacket(frames[-1]);
            if (packet.packet_type === "control") {
                this.handleControlMessage(packet.payload);
            } else {
                this.emit('message', packet.payload);  // 触发 message 事件
            }
        }
    }
    
    // 发送
    send(message) {
        const packet = createPacket(serverId, "user", message);
        this.#socket.send([serializePacket(packet)]);
    }
}
```

### 3.5 服务器端

```javascript
// server.js
class AhaIpcServerImpl {
    #ipcAddress = "ipc:///tmp/aha/{name}.sock";
    #connections = {};  // routingId → AhaIpcRecvConnectionImpl
    
    listenRequest() {
        for await (const [identity, message] of this.#socket) {
            const packet = deserializePacket(message);
            let conn = this.#connections[routingId];
            if (!conn) {
                conn = new AhaIpcRecvConnectionImpl(identity, this);
                this.#connections[routingId] = conn;
                this.emit('connect', conn);
            }
            conn.receive(packet.payload);  // 触发 'message' 事件
        }
    }
    
    send(id, type, payload) {
        const packet = createPacket(this.#id, type, payload);
        this.#socket.send([Buffer.from(id), serializePacket(packet)]);
    }
}
```

### 3.6 心跳配置

```javascript
// constants.js
ZMQ_HEARTBEAT_INTERVAL = 1000;  // 1秒
ZMQ_HEARTBEAT_TTL      = 3000;  // 3秒
ZMQ_HEARTBEAT_TIMEOUT  = 3000;  // 3秒
```

---

## 4. AHA RPC 层（JSON-RPC 2.0）

### 4.1 包结构

**包名:** `@aha-kit/rpc`

**连接:** 包装 `AHA IPC` 连接，提供 JSON-RPC 2.0 接口

**请求格式:**
```json
{
    "jsonrpc": "2.0",
    "method": "method_name",
    "params": [...param array...] | {...param object...},
    "meta": { ... },
    "id": "0"
}
```

**响应格式:**
```json
{
    "jsonrpc": "2.0",
    "id": "0",
    "result": ...,
    "meta": { ... }
}
```

### 4.2 标准错误码

```javascript
JSONRPC_ERRORS = {
    PARSE_ERROR:      { code: -32700 },
    INVALID_REQUEST:  { code: -32600 },
    METHOD_NOT_FOUND: { code: -32601 },
    INVALID_PARAMS:   { code: -32602 },
    INTERNAL_ERROR:   { code: -32603 }
}
```

### 4.3 流式扩展

```javascript
// 流通知前缀
STREAM_NOTIFICATION_PREFIX = 'rpc.stream.';
STREAM_CANCEL_NOTIFICATION_PREFIX = 'rpc.stream.cancel.';
```

**流式请求/响应流程：**
```
Client                                     Server
  │                                          │
  ├─ sendStreamRequest("method", params) ──► │
  │                                          ├─ 创建 AhaStreamSender
  │  ◄── { streamId: "uuid" } ──────────────┤
  │                                          │
  │  ◄── notification: "rpc.stream.{id}" ───┤  (data chunks)
  │  ◄── notification: "rpc.stream.{id}" ───┤  (done: true)
  │                                          │
  └─ notification: "rpc.stream.cancel.{id}"─►│  (可选取消)
```

**流通知格式：**
```json
// 数据块
{
    "method": "rpc.stream.{streamId}",
    "meta": {
        "stream": true,
        "streamId": "{uuid}",
        "chunkIndex": 0,
        "done": false
    },
    "params": { "data": "..." }
}

// 结束块
{
    "meta": {
        "stream": true,
        "streamId": "{uuid}",
        "chunkIndex": 1,
        "done": true
    },
    "params": { "data": null, "error": null }
}

// 取消
{
    "method": "rpc.stream.cancel.{streamId}",
    "params": { "streamId": "{uuid}", "reason": "..." }
}
```

### 4.4 API

**Connection 类主要方法：**
- `sendRequest(method, ...params)` → Promise 返回结果
- `sendStreamRequest(method, ...params)` → 返回 AhaStreamReceiver
- `sendNotification(method, ...params)` → 不期待响应
- `onRequest(method, callback)` → 注册请求处理
- `onNotification(method, callback)` → 注册通知处理
- `onStreamRequest(method, callback)` → 注册流请求处理
- `createStreamSender(streamId)` → 创建流发送端

---

## 5. Rust Manager 进程

### 5.1 进程启动参数

Manager 通过 `child_process.spawn()` 启动：
- 可执行文件: `{appRoot}/bin/manager` (或 `manager.exe` on Windows)
- 环境变量: 见上方 2.1 节
- 标准输入: pipe (可写 "exit\n" 来关闭)
- 分离模式: `detached: true`

### 5.2 Manager 通信方式

Manager 有两种通信通道：

1. **AHA IPC (ZMQ Dealer-Router)**
   - 端点: `ipc:///tmp/aha/ai-agent.sock` (每个模块一个)
   - 用于模块间通信

2. **Manager SDK WebSocket**
   - 监听在随机端口 (51000+)
   - 用于 Electron 主进程 ↔ Manager 的 RPC 通信
   - 端点: `ws://127.0.0.1:{PORT}` (或 `ws://[::1]:{PORT}`)
   - 协议: MsgPack 二进制编码的 JSON-RPC

### 5.3 错误上报

```javascript
// 错误事件名称
"icube_rust_error"   // 一般错误
"icube_rust_warn"    // 警告
// via Slardar (@byted-icube/slardar)
```

---

## 6. Manager SDK 通信层

### 6.1 RPC WebSocket Client

**包名:** `@byted-icube/manager-sdk`  
**文件:** `web/rpcclient.js` (649KB，包含 RPC, WebSocket, 认证, 加密等)

**核心类:**
- `RpcWebSocketClient` (rpcclient.js) - 基于 WebSocket 的 RPC 客户端
- `ReconnectingWebSocketClient` - 自动重连的 WebSocket 客户端
- `ExchangeConnector` - Hub Bridge 连接器
- `PseudoWebSocket` - 将 EventStream 包装为 WebSocket 接口

### 6.2 RpcWebSocketClient (1078.js)

```
RpcWebSocketClient extends EventEmitter
  ├── ws: ReconnectingWebSocketClient
  ├── requestId: number (自增)
  ├── pendingRequests: Map<id, {resolve, reject, timeoutId}>
  └── msgQueue: Uint8Array[]
```

**消息编码:** MsgPack 二进制 (基于 msgpackr 库)

**调用流程:**
```
1. client.call(method, params) 
2.  ├── 分配 requestId
3.  ├── 编码: msgpack.encode({ method, params, id })
4.  ├── 发送到 WebSocket
5.  ├── 等待响应 (pendingRequests)
6.  └── 返回结果 (或 reject 错误)
```

**消息接收:** 
```
1. WebSocket message 事件 → push 到 msgQueue
2. messageGenerator() 异步迭代 → 解码 msgpack
3. handleMessage(data) → 
   └── 有 id: 匹配 pendingRequests → resolve/reject
   └── 无 id (通知): emit(method, params)
```

### 6.3 ReconnectingWebSocketClient (4421.js)

```javascript
class ReconnectingWebSocketClient extends EventEmitter {
    maxReconnectAttempts: 0,        // 0 = 无限
    reconnectDelay: 300,            // 初始 300ms
    reconnectMaxDelay: 8000,        // 最大 8s
    exponential backoff: 2^attempt  // 指数退避
}
```

**事件:**
- `open` - 连接建立
- `message` - 收到消息 (Uint8Array)
- `error` - 发生错误
- `close` - 连接关闭

### 6.4 Server Info 与模块端口映射

**server_info RPC** 返回端口映射表：
```javascript
{
    // module_port → 端口/连接信息
    "ai/0": { connections: [{ socket: { port: 12345 } }] },
    "ai-agent/0": { connections: [{ socket: { port: 12346 } }] },
    "ai-completion/0": { ... }
}
```

**连接/端口获取:** `callJSONRpc()` 自动调用 `server_info` 并缓存结果

### 6.5 RPC 方法

| 方法 | 用途 | 参数 |
|------|------|------|
| `json_rpc` | 通用 JSON-RPC 调用 | JSON-RPC 请求 |
| `stream_rpc` | 流式 RPC 调用 | RPC + onData/onEnd 回调 |
| `ws_rpc` | WebSocket 隧道 | 返回 socket_path |
| `ws_input` | 向 WebSocket 隧道写入 | socket_path, req |
| `ping` | 心跳 | 自定义参数 |
| `server_info` | 获取服务器信息 | - |

### 6.6 WebSocket 隧道 (PseudoWebSocket)

通过 `ws_rpc` 在 Electron 侧创建 WebSocket 隧道的包装：
```
调用 ws_rpc → 返回 { socket_path }
          ↓
创建 PseudoWebSocket (包装 EventStream)
          ↓
发送数据: ws_input({ socket_path, req: [...bytes...] })
接收数据: 通过 stream_data 事件
关闭: ws_input({ socket_path, op_code: 8 })  // 8 = Close
```

---

## 7. 活动检测（Liveness）系统

### 7.1 LivenessManager (liveness.js)

```
PeerState 状态机:
  INIT → CONNECTING → ALIVE → SUSPECT → DEAD
         ↑                       |
         +--- 收到消息时重置 -----+
```

**默认配置：**
```javascript
DEFAULT_OPTIONS = {
    pingInterval: 1000,       // 心跳间隔 1 秒
    livenessTimeout: 3000,    // 超时判定 3 秒
    gracePeriod: 6000,        // 新客户端宽限期 6 秒
    disable: false
}
```

**控制消息：**
```
__C_PING__          = '__C_PING__'          // 心跳 ping
__C_PONG__          = '__C_PONG__'          // 心跳 pong
__C_SERVER_SHUTDOWN__ = '__C_SERVER_SHUTDOWN__'  // 服务器关闭
__C_CONNECTION_REJECT__ = '__C_CONNECTION_REJECT__'  // 连接拒绝
```

**系统挂起检测：**
- 检测 `now - lastTick > pingInterval * 5`
- 暂停所有超时检查
- 进入宽限期，避免误判 DEAD

### 7.2 IPC 层心跳 (ZMQ)

ZMQ 原生心跳：
```
heartbeatInterval: 1000ms    // ZMQ 级别心跳间隔
heartbeatTimeout: 3000ms     // ZMQ 级别心跳超时
```

### 7.3 Manager SDK 心跳

```
Manager SDK ping → Server pong
每隔 15000ms (keepAliveTimeout) 发送一次
用于 WebSocket 连接保活
```

---

## 8. 流式传输系统

### 8.1 AhaStream 体系

```javascript
AhaStream (abstract)
  ├── OrderedLazyStream     // 有序懒加载流
  └── EventStream           // 简单事件流 (591.js)

AhaStreamSender            // 发送端
  ├── write(chunk)          // 发送数据块
  ├── end(chunk?)           // 结束流
  └── error(err)            // 发送错误

AhaStreamReceiver          // 接收端
  ├── collect()             // 收集所有数据
  ├── close(reason)         // 关闭流
  └── timeout: number       // 超时时间 (默认 -1 = 无超时)
```

### 8.2 OrderedLazyStream

- 缓冲区排序，保证数据有序
- 支持 `data`, `end`, `error`, `finished` 事件
- `read()` 方法返回 Promise
- 内存友好：只有有消费者时才处理
- 按需消费：auto-start

### 8.3 EventStream (591.js)

```javascript
class EventStream extends DisposableStore {
    dataEmitter: Emitter     // data 事件
    endEmitter: Emitter      // end 事件
    openEmitter: Emitter     // open 事件
    
    cork()/uncork()          // 暂停/恢复流
    write(data, callback)    // 写入数据
    flush(data, callback)/destroy()  // 刷新/销毁
}
```

---

## 9. 认证系统

### 9.1 认证层级

```
User Login (OAuth2 PKCE)
  → 获取 Refresh Token
     → ExchangeToken("ClientID", "RefreshToken", "ClientSecret", "UserID")
        → 获取 Access Token (JWT)
           → 调用 API (x-cloudide-token, Authorization: Bearer)
```

### 9.2 Token 端点

| 区域 | Token Host |
|------|-------------|
| US | https://token.trae.ai |
| CN | https://token.trae.com.cn |
| SG | https://api-sg-central.trae.ai |

### 9.3 认证头

```javascript
headers = {
    "x-cloudide-token": accessToken,
    "x-ide-token": accessToken,
    "Authorization": "Bearer " + accessToken,
    "Content-Type": "application/json"
}
```

---

## 10. 聊天 API 调用链

### 10.1 完整链路

```
UI (Renderer) → ipcRenderer.invoke("vscode:icubeSendChat", ...) 
  → Main Process → ipcMain.handle("vscode:*", ...) 
    → AHA RPC / Manager SDK 
      → Rust Manager 
        → ai-agent 模块 
          → HTTP API (agents/runs)
            → 后端 LLM 服务
```

### 10.2 Chat API 端点

| 端点 | 用途 | 方法 |
|------|------|------|
| `/api/ide/v1/agents/runs` | 发送聊天消息 | POST |
| `/api/ide/v2/llm_raw_chat` | 直接 LLM 调用 | POST |
| `/api/ide/v1/model_list` | 模型列表 | POST |

### 10.3 核心消息类型

| 类型 | 描述 |
|------|------|
| `message_start` | 消息开始 |
| `content_block_delta` | 内容增量 |
| `content_block_stop` | 内容块结束 |
| `message_stop` | 消息结束 |
| `error` | 错误事件 |

### 10.4 Electron IPC 通道

通过 `ipcMain.handle()` 注册的通道（668+ 个）：
```
vscode:getLastWorkspace
vscode:startSetup
vscode:changeSetupState
vscode:login
vscode:setTitleBarOverlay
vscode:getManagerInfo
vscode:fetchShellEnv
vscode:registerAuxiliaryWindow
vscode:login
vscode:installMarscodeCli
vscode:setupTheme
vs:code:notifyZoomLevel
... (others for sandbox, crawler, etc.)
```

**icube/AI 相关通道：**
```
vscode:sandbox::main-invoke-getAiRegion
vscode:sandbox::main-invoke-getAppMetadata
vscode:sandbox::main-invoke-getUserInfo
vscode:sandbox::main-invoke-login
vscode:sandbox::main-send-logout
vscode:sandbox::main-refresh-userinfo
vscode:sandbox::main-broadcast-icubeAgentChange
vscode:sandbox::main-broadcast-icubeModelManagementChange
```

---

## 11. Hub Bridge 协议

### 11.1 ExchangeConnector

用于 Hub Bridge 的 WebSocket 连接器，支持自动重连：

```javascript
ExchangeConnector {
    ws: WebSocket,
    msgQueue: [...],
    msgBarrier: Barrier,
    reconnectTimeout: 500ms,
}
```

**特性：**
- 自动重连
- MsgPack 编码
- 基于 Barrier 的异步消息队列
- 支持 JSON 和 MsgPack 两种序列化

### 11.2 Hub Bridge 消息类型

```
WsProtoCLI              - CLI 协议消息
WsProtoConfirm          - 确认消息
WsProtoSessionCreated   - 会话创建
WsProtoSessionUpdated   - 会话更新
WsProtoSessionDeleted   - 会话删除
```

---

## 12. 关键配置与常量

### 12.1 Manager 环境变量

| 变量 | 示例值 | 用途 |
|------|--------|------|
| `ICUBE_PROXY_HOST` | `127.0.0.1` | WebSocket 监听地址 |
| `ICUBE_PROXY_PORT` | `51000+` | WebSocket 监听端口 |
| `ICUBE_USE_IPV6` | `false` | 是否使用 IPv6 |
| `ICUBE_MODULAR_DATA_DIR` | `~/.config/Trae/ModularData` | 模块数据目录 |
| `ICUBE_GLOBAL_STORAGE_DIR` | `~/.config/Trae/User/globalStorage` | 全局配置目录 |
| `ICUBE_DISABLED_MODULES` | `ai,ai-completion` | 禁用的模块 |
| `ICUBE_MAIN_PPID` | `12345` | Electron 主进程 PID |
| `ICUBE_RUST_LOG_LEVEL` | `info` | Rust 日志级别 |
| `ICUBE_FORCE_RANDOM_PORT` | `true` | 强制随机端口 |
| `ICUBE_MODULE_PID_DIR` | `{ModularData}/pids` | PID 文件目录 |
| `ICUBE_MANAGER_LOG_DIR` | `{logsHome}/Modular` | 日志目录 |
| `ICUBE_CODEMAIN_SESSION` | `UUID` | 会话标识 |

### 12.2 AHA IPC 常量

| 常量 | 值 |
|------|-----|
| IPC 目录 | `/tmp/aha/` |
| Socket 文件名 | `{name}.sock` |
| 标记文件 | `{name}.sock.ready` |
| 包版本 | `1` |
| ZMQ 心跳间隔 | `1000ms` |
| ZMQ 心跳 TTL | `3000ms` |
| ZMQ 心跳超时 | `3000ms` |
| 服务器重试次数 | `5` |

### 12.3 Liveness 配置

| 参数 | 默认值 |
|------|--------|
| pingInterval | `1000ms` |
| livenessTimeout | `3000ms` |
| gracePeriod | `6000ms` |

### 12.4 Manager SDK 配置

| 参数 | 默认值 |
|------|--------|
| reconnectDelay | `300ms` |
| reconnectMaxDelay | `8000ms` |
| maxReconnectAttempts | `0` (无限) |
| keepAliveTimeout | `15000ms` |
| 编码协议 | `MsgPack` |

---

## 13. 通信流程图

### 13.1 完整初始化流程

```
Electron Main                      Rust Manager
    │                                    │
    ├─ portfinder: 找到可用端口 ──       │
    ├─ 设置环境变量 (30+ 个)             │
    ├─ spawn("manager") ──────────────►  │
    │                                    ├─ 加载模块配置
    │                                    ├─ 启动 AHA IPC 服务器 (3 个)
    │                                    │   ├─ ZMQ Router bind("ai-agent")
    │                                    │   ├─ ZMQ Router bind("ai")
    │                                    │   └─ ZMQ Router bind("ai-completion")
    │                                    ├─ 启动 WebSocket 服务器
    │                                    │   └─ 监听 127.0.0.1:{PORT}
    │  ◄── spawn 完成 ─────────────────┤
    │                                    │
    ├─ Manager SDK 连接 WebSocket ────►  │
    │  ws://127.0.0.1:{PORT}             │
    │                                    │
    ├─ call("server_info") ──────────►   │
    │  ◄── { ports map } ───────────────┤
    │                                    │
    ├─ call("ping") ──────────────►      │
    │  ◄── pong ────────────────────────┤
    │                                    │
    ├─ AHA IPC 客户端连接 ────────►     │
    │  Dealer connect("ai-agent")        │
    │  Dealer connect("ai")              │
    │  Dealer connect("ai-completion")   │
    │                                    │
    └── 就绪 ──────────────────────────  │
```

### 13.2 聊天消息流

```
UI (Renderer)                Main Process              Rust Manager          API Server
    │                            │                         │                    │
    │ click "发送"              │                         │                    │
    │                            │                         │                    │
    ├─ ipcRenderer.invoke() ──► │                         │                    │
    │  "vscode:openAIChat"      │                         │                    │
    │                            │                         │                    │
    │                            ├─ RPC call ──────────►  │                    │
    │                            │  "agents/runs"          │                    │
    │                            │  via AHA IPC 或 WS      │                    │
    │                            │                         ├─ HTTP POST ──────► │
    │                            │                         │  /api/ide/v1/      │
    │                            │                         │  agents/runs        │
    │                            │                         │                    │
    │                            │                         │  ◄── SSE stream ──┤
    │                            │  ◄── stream chunks ────┤                    │
    │                            │                         │                    │
    │  ◄── stream data ────────┤                         │                    │
    │                            │                         │                    │
    │ render response           │                         │                    │
    │                            │                         │                    │
```

---

## 附录 A：关键文件路径

```
IDE 提取:
data/ide/linux-x64/extracted/resources/app/
  ├── node_modules/
  │   ├── @aha-kit/ipc/dist/           ← AHA IPC 通用层
  │   ├── @aha-kit/ipc-linux-x64/dist/ ← AHA IPC 平台实现
  │   │   ├── client.js                ← Dealer 客户端
  │   │   ├── server.js                ← Router 服务器
  │   │   ├── zmq-adapter.js           ← ZMQ 适配器 (Rust/C++ fallback)
  │   │   ├── packet.js                ← 数据包协议
  │   │   ├── liveness.js              ← 活动检测
  │   │   ├── control-message.js       ← 控制消息
  │   │   ├── utils.js                 ← 工具 (地址生成)
  │   │   └── constants.js             ← 常量
  │   ├── @aha-kit/rpc/dist/index.js   ← JSON-RPC 2.0 实现
  │   ├── @aha-kit/zmq/               ← Rust ZMQ (可选)
  │   └── @byted-icube/manager-sdk/    ← Manager SDK
  │       ├── web/rpcclient.js         ← Web RPC 客户端 (649KB)
  │       └── node/rpcclient.js        ← Node RPC 客户端 (649KB)
  ├── out/vs/code/electron-main/
  │   ├── main.js (1.2MB, default.js 61K行)  ← 主进程代码
  │   │   ├── iCubeRustManager                ← Manager 管理
  │   │   ├── iCubeAuthManagementService      ← 认证
  │   │   └── iCubeSandboxService             ← 沙箱
  │   └── workbench/                          ← UI 工作台
  └── extensions/                             ← 扩展
      ├── byted-icube.*/                      ← Trae 特定扩展
      └── git-ai.git-ai-vscode/              ← Git AI 辅助

分析文件:
analysis/
  ├── ai-protocol-analysis.md          ← AI 协议分析 (12K 行)
  ├── iteration-*.md                   ← 迭代分析报告
  └── trae-ai-proxy-deep-analysis.md   ← 代理深度分析
```

---

## 附录 B：术语表

| 缩写 | 全称 | 说明 |
|------|------|------|
| AHA | @aha-kit | Trae 的自研 IPC/RPC 框架 |
| ZMQ | ZeroMQ | 高性能异步消息库 |
| IP | Internet Protocol | 互联网协议 |
| IPC | Inter-Process Communication | 进程间通信 |
| RPC | Remote Procedure Call | 远程过程调用 |
| SSE | Server-Sent Events | 服务器推送事件 |
| DDD | Domain-Driven Design | 领域驱动设计 |
| MCP | Model Context Protocol | 模型上下文协议 |
| COI | Cross-Origin Isolation | 跨域隔离 |
| COOP | Cross-Origin Opener Policy | 跨域打开者策略 |
| COEP | Cross-Origin Embedder Policy | 跨域嵌入者策略 |

---

> 本报告基于 Trae IDE v2.3.30128 的逆向分析结果，描述了当前的通信协议和架构设计。
> 实际实现可能会因版本更新有所变化。
