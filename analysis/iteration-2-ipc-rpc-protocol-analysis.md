# Trae IPC/RPC Protocol Analysis - Iteration 2

**Date**: 2026-05-30
**Focus**: @aha-kit IPC/RPC Module & JSON-RPC 2.0 Protocol

---

## Executive Summary

本次分析深入研究了 Trae IDE 的 IPC (Inter-Process Communication) 和 RPC (Remote Procedure Call) 机制。发现 Trae 使用 ZeroMQ (ZMQ) 作为底层传输层，结合自定义的 JSON-RPC 2.0 协议进行 AI 通信。

---

## 1. @aha-kit IPC 模块架构

### 1.1 模块结构

```
@aha-kit/
├── ipc/                    # IPC 核心模块
│   ├── dist/
│   │   ├── index-main.js   # 主进程入口
│   │   └── logger.js       # 日志模块
├── ipc-linux-arm64/        # Linux ARM64 平台实现
│   ├── dist/
│   │   ├── client.js       # IPC 客户端
│   │   ├── server.js       # IPC 服务端
│   │   ├── zmq-adapter.js  # ZMQ 适配器
│   │   ├── packet.js       # 数据包定义
│   │   ├── liveness.js     # 心跳检测
│   │   ├── control-message.js  # 控制消息
│   │   ├── message-pipe.js # 消息管道
│   │   └── zeromq/         # ZeroMQ 绑定
├── rpc/                    # RPC 模块
│   └── dist/
│       └── index.js        # RPC 实现
└── net/                    # 网络模块
    └── wrapper.js          # 网络包装器
```

### 1.2 ZeroMQ 传输层

```javascript
// ZMQ 适配器 - 支持两种实现
function loadRustZMQ() {
    return require('@aha-kit/zmq');  // Rust 实现 (首选)
}

function loadZeroMQ() {
    return require('./zeromq');  // 或 'zeromq' (备选)
}
```

**Socket 类型**: Dealer-Router 模式
- **Client**: Dealer Socket (带 routingId)
- **Server**: Router Socket (路由到不同客户端)

### 1.3 连接建立流程

```javascript
class AhaIpcConnectionImpl extends EventEmitter {
    #routingId = crypto.randomUUID();  // 唯一标识
    #socket = null;
    #ipcAddress = '';

    constructor(serverName, options) {
        // 1. 生成 IPC 地址
        this.#ipcAddress = generateIpcAddress(serverName, options?.runtimeDir);

        // 2. 创建 Dealer Socket
        const socket = new Dealer({
            routingId: this.#routingId,
        });

        // 3. 配置心跳
        socket.heartbeatInterval = ZMQ_HEARTBEAT_INTERVAL;
        socket.heartbeatTimeToLive = ZMQ_HEARTBEAT_TTL;
        socket.heartbeatTimeout = ZMQ_HEARTBEAT_TIMEOUT;

        // 4. 连接到服务端
        socket.connect(this.#ipcAddress);

        // 5. 创建 LivenessManager
        this.#livenessManager = new LivenessManager({...}, {
            send: (_id, message) => this.sendControlMessage(message)
        });

        // 6. 启动接收循环
        this.startReceive();
    }
}
```

---

## 2. 数据包格式

### 2.1 Packet 结构

```javascript
// Packet 类型
enum PacketType {
    User = "user",      // 用户消息
    Control = "control" // 控制消息
}

// Packet 结构
{
    version: 1,              // 协议版本
    id: string,              // 服务端 ID
    packet_type: "user" | "control",
    payload: any             // 消息内容
}
```

### 2.2 序列化/反序列化

```javascript
function serializePacket(packet) {
    return JSON.stringify(packet);
}

function deserializePacket(data) {
    const str = Buffer.isBuffer(data) ? data.toString('utf-8') : data;
    const packet = JSON.parse(str);
    if (typeof packet.version === 'number' &&
        typeof packet.id === 'string' &&
        typeof packet.packet_type === 'string') {
        return packet;
    }
    return null;
}
```

---

## 3. 心跳检测机制

### 3.1 LivenessManager

```javascript
enum PeerState {
    INIT = "INIT",
    CONNECTING = "CONNECTING",
    ALIVE = "ALIVE",
    SUSPECT = "SUSPECT",
    DEAD = "DEAD"
}

const DEFAULT_OPTIONS = {
    pingInterval: 1000,      // 1秒
    livenessTimeout: 3000,   // 3秒
    gracePeriod: 6000,       // 6秒
    disable: false,
};
```

### 3.2 心跳流程

```
Client                    Server
  │                         │
  │──── C_PING ────────────▶│
  │                         │
  │◀─── C_PONG ────────────│
  │                         │
  │ (markSeen: ALIVE)       │
```

### 3.3 控制消息

```javascript
const C_PING = "ping";
const C_PONG = "pong";
```

---

## 4. RPC 流式协议

### 4.1 Stream 通知前缀

```javascript
const STREAM_NOTIFICATION_PREFIX = 'rpc.stream.';
const STREAM_CANCEL_NOTIFICATION_PREFIX = 'rpc.stream.cancel.';
```

### 4.2 AhaStreamSender

```javascript
class AhaStreamSender extends AhaStream {
    streamId;
    chunkIndex = 0;
    isEnded = false;

    async write(chunk) {
        await this.connection.sendNotification({
            method: `${STREAM_NOTIFICATION_PREFIX}${this.streamId}`,
            meta: {
                stream: true,
                streamId: this.streamId,
                chunkIndex: this.chunkIndex++
            }
        }, {
            data: chunk
        });
    }

    async end(chunk) {
        await this.connection.sendNotification({
            method: `${STREAM_NOTIFICATION_PREFIX}${this.streamId}`,
            meta: {
                stream: true,
                streamId: this.streamId,
                chunkIndex: this.chunkIndex,
                done: true
            }
        }, {
            data: null
        });
    }
}
```

### 4.3 流式数据格式

```json
{
    "method": "rpc.stream.{streamId}",
    "meta": {
        "stream": true,
        "streamId": "uuid",
        "chunkIndex": 0,
        "done": false
    },
    "params": {
        "data": "chunk content"
    }
}
```

---

## 5. JSON-RPC 2.0 协议 (Custom Model Proxy)

### 5.1 请求方法

| 方法 | 方向 | 用途 |
|------|------|------|
| `sse.open` | Client → Server | 打开新的 SSE 流 |
| `sse.cancel` | Client → Server | 取消活动的 SSE 流 |
| `rpc.ping` | 双向 | 心跳检测 |
| `rpc.close` | Client → Server | 关闭连接 |

### 5.2 响应类型

| 类型 | 用途 |
|------|------|
| `sse.delta` | 流式内容增量 |
| `sse.end` | 流完成 |
| `sse.error` | 流错误 |

### 5.3 消息格式

```json
// 请求
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "sse.open",
    "params": {
        "model": "gpt-5",
        "messages": [...],
        "stream": true
    }
}

// 响应
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "stream_id": "uuid"
    }
}

// 流式数据
{
    "jsonrpc": "2.0",
    "method": "sse.delta",
    "params": {
        "stream_id": "uuid",
        "data": {
            "choices": [{
                "delta": {"content": "Hello"},
                "index": 0
            }]
        }
    }
}
```

---

## 6. 隧道协议

### 6.1 连接 URL

```
wss://{host}/custom_model/tunnel/ws?tunnel_id={tunnel_id}
```

### 6.2 隧道生命周期

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

### 6.3 HTTP 回退

当 WebSocket 不可用时，使用 HTTP 轮询：

```
POST /custom_model/tunnel/GetPending
POST /custom_model/tunnel/SubmitMessage
```

---

## 7. 关键发现

### 7.1 IPC 机制

1. **ZeroMQ Dealer-Router**: 高性能异步消息传递
2. **UUID RoutingId**: 每个客户端唯一标识
3. **心跳检测**: 1秒间隔，3秒超时，6秒宽限期
4. **JSON 序列化**: 所有消息使用 JSON 格式

### 7.2 RPC 流式

1. **Stream 通知**: `rpc.stream.{streamId}` 前缀
2. **Chunk 索引**: 每个 chunk 递增索引
3. **完成标记**: `done: true` 表示流结束
4. **取消机制**: `rpc.stream.cancel.{streamId}`

### 7.3 JSON-RPC 2.0

1. **标准兼容**: 完全兼容 JSON-RPC 2.0 规范
2. **SSE 扩展**: 自定义 `sse.*` 方法
3. **双向心跳**: `rpc.ping`/`rpc.close`
4. **流式响应**: `sse.delta`/`sse.end`/`sse.error`

---

## 8. Codex 集成建议

### 8.1 最简路径

```
Codex CLI
    ↓ (HTTP POST)
/trae-cli/api/v1/llm/proxy
    ↓ (JSON-RPC 2.0)
Custom Model Proxy
    ↓ (WebSocket/HTTP)
LLM Provider
```

### 8.2 实现优先级

1. **P0**: `/trae-cli/api/v1/llm/proxy` 端点 (OpenAI 兼容)
2. **P1**: OAuth2 认证流程
3. **P2**: JSON-RPC 2.0 流式处理
4. **P3**: WebSocket 隧道协议

### 8.3 关键代码

```python
# Python 示例 - 调用 LLM Proxy
import requests

response = requests.post(
    "https://icube-normal.trae.ai/trae-cli/api/v1/llm/proxy",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    },
    json={
        "model": "gpt-5",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        data = line.decode('utf-8')
        if data.startswith('data: '):
            chunk = json.loads(data[6:])
            if chunk == '[DONE]':
                break
            content = chunk['choices'][0]['delta'].get('content', '')
            print(content, end='')
```

---

## 9. 下一步分析

### 9.1 待验证

1. [ ] IPC 地址生成算法 (`generateIpcAddress`)
2. [ ] RPC 方法调用的具体格式
3. [ ] 错误处理和重试机制
4. [ ] 认证 token 在 IPC 中的传递方式

### 9.2 待实现

1. [ ] ZeroMQ 客户端连接
2. [ ] JSON-RPC 2.0 消息构建
3. [ ] SSE 流式解析
4. [ ] 心跳检测和重连

---

## 10. 技术细节附录

### 10.1 ZMQ 常量

```javascript
ZMQ_HEARTBEAT_INTERVAL  // 心跳间隔
ZMQ_HEARTBEAT_TTL       // 心跳生存时间
ZMQ_HEARTBEAT_TIMEOUT   // 心跳超时
```

### 10.2 控制消息

```javascript
C_PING = "ping"
C_PONG = "pong"
```

### 10.3 包类型

```javascript
PacketType.User = "user"
PacketType.Control = "control"
```

### 10.4 Peer 状态

```javascript
PeerState.INIT = "INIT"
PeerState.CONNECTING = "CONNECTING"
PeerState.ALIVE = "ALIVE"
PeerState.SUSPECT = "SUSPECT"
PeerState.DEAD = "DEAD"
```
