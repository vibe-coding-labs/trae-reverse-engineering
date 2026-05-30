# Trae AI Service Events & IPC Configuration - Iteration 3

**Date**: 2026-05-30
**Focus**: AI Service Events, IPC Socket Configuration, RPC Stream Handling

---

## Executive Summary

本次分析发现了 Trae IDE 中 91 个 iCubeAI 事件，涵盖聊天、Agent、MCP、工具调用等完整生命周期。同时深入分析了 IPC Socket 地址生成机制和 RPC 流式处理细节。

---

## 1. iCubeAI 事件系统 (91 个事件)

### 1.1 聊天核心事件

| 事件名 | 用途 |
|--------|------|
| `icube_ai_chat_view_init` | 聊天视图初始化 |
| `icube_ai_chat_request` | 聊天请求发送 |
| `icube_ai_chat_first_token` | 首个 token 接收 |
| `icube_ai_chat_token_usage` | Token 使用统计 |
| `icube_ai_chat_cancel_request` | 取消聊天请求 |
| `icube_ai_chat_fps` | 聊天性能指标 |
| `icube_ai_chat_global_error` | 全局错误 |
| `icube_ai_chat_message_convert_error` | 消息转换错误 |
| `icube_ai_chat_crawler_task` | 爬虫任务 |
| `icube_ai_waiting_next_message` | 等待下一条消息 |

### 1.2 会话管理事件

| 事件名 | 用途 |
|--------|------|
| `icube_ai_init_session` | 初始化会话 |
| `icube_ai_migrate_chat_history` | 迁移聊天历史 |
| `icube_ai_append_msg_first_token` | 追加消息首个 token |

### 1.3 Agent 事件

| 事件名 | 用途 |
|--------|------|
| `icube_ai_agent_create_new_session_error` | 创建会话错误 |
| `icube_ai_agent_create_project_error` | 创建项目错误 |
| `icube_ai_agent_db_error` | 数据库错误 |
| `icube_ai_agent_db_init` | 数据库初始化 |
| `icube_ai_agent_extension_render` | 扩展渲染 |
| `icube_ai_agent_extension_request` | 扩展请求 |
| `icube_ai_agent_fast_apply_search_and_replace_result` | 快速应用结果 |
| `icube_ai_agent_global_error` | Agent 全局错误 |
| `icube_ai_agent_image_upload_error` | 图片上传错误 |
| `icube_ai_agent_image_upload_request` | 图片上传请求 |
| `icube_ai_agent_model_llm_render_token_usage` | 模型 Token 使用 |
| `icube_ai_agent_model_llm_stream` | 模型 LLM 流 |
| `icube_ai_agent_model_llm_stream_first_token` | 模型首个 Token |
| `icube_ai_agent_path_error` | 路径错误 |
| `icube_ai_agent_plan_item_data_error` | 计划项数据错误 |
| `icube_ai_agent_react_error` | React 错误 |
| `icube_ai_agent_retry_error` | 重试错误 |
| `icube_ai_agent_send_chat_error` | 发送聊天错误 |
| `icube_ai_agent_task_plan_all` | 任务计划全部 |
| `icube_ai_agent_task_plan_final_token` | 任务计划最终 Token |
| `icube_ai_agent_task_plan_finish` | 任务计划完成 |
| `icube_ai_agent_task_plan_first_token` | 任务计划首个 Token |
| `icube_ai_agent_task_plan_sub_agents` | 子 Agent 计划 |
| `icube_ai_agent_toolcall` | 工具调用 |
| `icube_ai_agent_with_image` | 包含图片 |
| `icube_ai_agent_with_md_error` | Markdown 错误 |

### 1.4 MCP 事件

| 事件名 | 用途 |
|--------|------|
| `icube_ai_agent_run_mcp_failed` | MCP 运行失败 |
| `icube_ai_agent_run_mcp_request` | MCP 运行请求 |
| `icube_ai_agent_run_mcp_skipped` | MCP 运行跳过 |
| `icube_ai_agent_run_mcp_success` | MCP 运行成功 |
| `icube_ai_mcp_oauth_flow_failed` | MCP OAuth 流程失败 |
| `icube_ai_mcp_oauth_flow_start` | MCP OAuth 流程开始 |
| `icube_ai_mcp_oauth_flow_success` | MCP OAuth 流程成功 |
| `icube_ai_mcp_oauth_refresh_failed` | MCP OAuth 刷新失败 |
| `icube_ai_mcp_oauth_refresh_success` | MCP OAuth 刷新成功 |

### 1.5 其他事件

| 事件名 | 用途 |
|--------|------|
| `icube_ai_apply_diff` | 应用差异 |
| `icube_ai_apply_finished` | 应用完成 |
| `icube_ai_asr_*` | 语音识别相关 |
| `icube_ai_fastapply_first_token` | 快速应用首个 Token |

---

## 2. IPC Socket 配置

### 2.1 Socket 地址生成

```javascript
// IPC 目录
const AHA_IPC_DIR = 'aha';

// 目录路径
function getIpcDir(runtimeDir) {
    if (runtimeDir) return path.join(runtimeDir, AHA_IPC_DIR);
    if (process.env.AHA_RUNTIME_DIR) return path.resolve(process.env.AHA_RUNTIME_DIR, AHA_IPC_DIR);

    // 默认路径
    if (process.platform === 'win32') return path.join(os.tmpdir(), AHA_IPC_DIR);
    return path.join('/tmp', AHA_IPC_DIR);
}

// 地址生成
function generateIpcAddress(name, runtimeDir) {
    const safeName = sanitizeName(name);  // 只允许字母数字._-
    const ahaDir = getIpcDir(runtimeDir);
    ensureDir(ahaDir);
    const socketPath = path.join(ahaDir, `${safeName}.sock`);
    return `ipc://${socketPath}`;
}
```

### 2.2 Socket 路径示例

```
# Linux/macOS
ipc:///tmp/aha/ai-agent.sock
ipc:///tmp/aha/ckg-server.sock
ipc:///tmp/aha/trae-sandbox.sock

# Windows
ipc://C:\Users\{user}\AppData\Local\Temp\aha\ai-agent.sock

# 自定义目录
ipc://{runtimeDir}/aha/{name}.sock
```

### 2.3 Marker 文件

```javascript
// 就绪标记文件
function markerPathFromAddress(ipcAddress) {
    const prefix = 'ipc://';
    const p = ipcAddress.slice(prefix.length);
    return `${p}.ready`;  // /tmp/aha/ai-agent.sock.ready
}
```

---

## 3. RPC 流式处理详解

### 3.1 Stream Sender

```javascript
class AhaStreamSender extends AhaStream {
    streamId;        // UUID
    chunkIndex = 0;  // 递增索引
    isEnded = false;

    // 写入数据块
    async write(chunk) {
        await this.connection.sendNotification({
            method: `rpc.stream.${this.streamId}`,
            meta: {
                stream: true,
                streamId: this.streamId,
                chunkIndex: this.chunkIndex++
            }
        }, { data: chunk });
    }

    // 结束流
    async end(chunk) {
        await this.connection.sendNotification({
            method: `rpc.stream.${this.streamId}`,
            meta: {
                stream: true,
                streamId: this.streamId,
                chunkIndex: this.chunkIndex,
                done: true
            }
        }, { data: null });
    }

    // 错误处理
    async error(err) {
        await this.connection.sendNotification({
            method: `rpc.stream.${this.streamId}`,
            meta: {
                stream: true,
                streamId: this.streamId,
                chunkIndex: this.chunkIndex,
                done: true
            }
        }, { error: RPCError.serialize(err) });
    }

    // 取消
    cancel() {
        this.emit('cancel');
    }
}
```

### 3.2 Stream Receiver

```javascript
class AhaStreamReceiver extends AhaStream {
    streamId;
    timeoutTimer;
    lastChunkTime = Date.now();
    timeout;

    // 收集所有数据
    async collect() {
        const chunks = [];
        this.on('data', (chunk) => chunks.push(chunk));
        this.on('end', () => resolve(chunks));
        this.on('error', (err) => reject(err));
        return promise;
    }

    // 超时检查
    startTimeoutCheck() {
        if (this.timeout <= 0) return;
        this.timeoutTimer = setInterval(() => {
            const elapsed = Date.now() - this.lastChunkTime;
            if (elapsed > this.timeout) {
                this.emit('error', new RPCError(-32000, `Stream timeout`));
                this.dispose();
            }
        }, 1000);
    }

    // 关闭流
    close(reason) {
        this.connection.cancelStreamRequest(this.streamId, reason);
    }
}
```

### 3.3 流式消息格式

```json
// 数据块
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

// 结束标记
{
    "method": "rpc.stream.{streamId}",
    "meta": {
        "stream": true,
        "streamId": "uuid",
        "chunkIndex": 10,
        "done": true
    },
    "params": {
        "data": null
    }
}

// 错误
{
    "method": "rpc.stream.{streamId}",
    "meta": {
        "stream": true,
        "streamId": "uuid",
        "chunkIndex": 5,
        "done": true
    },
    "params": {
        "error": {
            "code": -32000,
            "message": "Stream timeout",
            "data": { "streamId": "uuid" }
        }
    }
}
```

---

## 4. 心跳配置常量

```javascript
ZMQ_HEARTBEAT_INTERVAL = 1000;  // 1秒
ZMQ_HEARTBEAT_TTL = 3000;       // 3秒
ZMQ_HEARTBEAT_TIMEOUT = 3000;   // 3秒
```

---

## 5. 错误码

```javascript
JSONRPC_ERRORS = {
    PARSE_ERROR: { code: -32700 },
    INVALID_REQUEST: { code: -32600 },
    METHOD_NOT_FOUND: { code: -32601 },
    INVALID_PARAMS: { code: -32602 },
    INTERNAL_ERROR: { code: -32603 }
};

// 自定义错误码
-32000: Stream timeout
```

---

## 6. 关键发现总结

### 6.1 事件系统

1. **91 个 iCubeAI 事件**: 覆盖完整 AI 生命周期
2. **事件分类**: 聊天、Agent、MCP、工具、语音、应用
3. **错误事件**: 详细的错误分类和处理
4. **性能事件**: FPS、Token 使用、首个 Token 延迟

### 6.2 IPC 配置

1. **Socket 路径**: `/tmp/aha/{name}.sock`
2. **地址格式**: `ipc:///tmp/aha/{name}.sock`
3. **Marker 文件**: `{name}.sock.ready` 表示就绪
4. **环境变量**: `AHA_RUNTIME_DIR` 可自定义目录

### 6.3 RPC 流式

1. **Chunk 索引**: 递增，用于顺序控制
2. **完成标记**: `done: true` 表示流结束
3. **超时机制**: 可配置超时时间
4. **取消机制**: 通过 `rpc.stream.cancel.{streamId}`

---

## 7. Codex 集成建议

### 7.1 监听事件

```python
# 监听聊天事件
events = [
    'icube_ai_chat_request',      # 请求发送
    'icube_ai_chat_first_token',  # 首个 Token
    'icube_ai_chat_token_usage',  # Token 使用
    'icube_ai_chat_cancel_request',  # 取消请求
]
```

### 7.2 流式处理

```python
# 处理 RPC 流式数据
def handle_stream(stream_id, chunk_index, data, done):
    if done:
        return  # 流结束
    process_chunk(data)
```

### 7.3 错误处理

```python
# 错误码处理
error_codes = {
    -32700: "Parse Error",
    -32600: "Invalid Request",
    -32601: "Method Not Found",
    -32602: "Invalid Params",
    -32603: "Internal Error",
    -32000: "Stream Timeout",
}
```

---

## 8. 下一步分析

### 8.1 待验证

1. [ ] 事件触发的具体时机和参数
2. [ ] Agent 工具调用的完整流程
3. [ ] MCP OAuth 认证流程
4. [ ] 语音识别 (ASR) 集成

### 8.2 待实现

1. [ ] 事件监听和处理
2. [ ] 流式数据收集
3. [ ] 错误恢复机制
4. [ ] 性能监控
