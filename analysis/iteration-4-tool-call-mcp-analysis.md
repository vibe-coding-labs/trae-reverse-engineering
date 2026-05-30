# Trae Tool Call & MCP Analysis - Iteration 4

**Date**: 2026-05-30
**Focus**: Tool Call System, MCP Protocol, Agent Workflow

---

## Executive Summary

本次分析深入研究了 Trae 的工具调用系统和 MCP (Model Context Protocol) 协议。发现了完整的工具调用流程、MCP OAuth 认证机制以及 Agent 工作流。

---

## 1. 工具调用系统

### 1.1 可用工具列表

| 工具名 | 用途 |
|--------|------|
| `run_command` | 执行 shell 命令 |
| `grep` | 搜索文件内容 |
| `glob` | 按模式查找文件 |
| `read` | 读取文件内容 |
| `view_file` | 语法高亮查看文件 |
| `edit_file` | 编辑文件内容 |
| `create_file` | 创建新文件 |
| `delete_file` | 删除文件 |
| `apply_patch` | 应用代码补丁 |
| `web_search` | 网络搜索 |
| `web_fetch` | 获取网页内容 |
| `ask_user_question` | 询问用户 |
| `notify_user` | 发送通知 |
| `agent_finish` | 完成 Agent 执行 |
| `supabase_*` | Supabase 操作 |

### 1.2 工具调用事件结构

```rust
struct ToolCallEvent {
    toolcall_id: String,      // 唯一工具调用 ID
    tool_name: String,        // 工具名称
    arguments: Value,         // 工具参数
    result: Option<Value>,    // 工具结果
    error: Option<String>,    // 错误信息
    status: ToolCallStatus,   // pending, running, completed, failed
}
```

### 1.3 工具调用类型

```go
// CLI 中的工具调用类型
type ToolCallType string

// 工具调用内容
type ToolCallContent struct {
    Content  string
    Diff     string
    Terminal string
}

// 工具调用位置
type ToolCallLocation struct {
    // 文件位置信息
}

// 工具调用开始选项
type ToolCallStartOpt struct {
    // 选项配置
}
```

### 1.4 MCP 工具调用格式

```go
// MCP 工具定义
type MCPTool struct {
    ToolName  string                 `json:"tool_name" required:"true"`
    Arguments map[string]interface{} `json:"arguments" required:"true"`
}

// MCP 工具名称格式
// mcp__<server>__<tool>
// 例如: mcp__github__create_issue
```

---

## 2. MCP 协议

### 2.1 MCP 事件

| 事件名 | 用途 |
|--------|------|
| `icube_ai_mcp_call_tool` | 调用 MCP 工具 |
| `icube_ai_mcp_call_success` | MCP 调用成功 |
| `icube_ai_mcp_call_failed` | MCP 调用失败 |
| `icube_ai_mcp_oauth_flow_start` | OAuth 流程开始 |
| `icube_ai_mcp_oauth_flow_success` | OAuth 流程成功 |
| `icube_ai_mcp_oauth_flow_failed` | OAuth 流程失败 |
| `icube_ai_mcp_oauth_refresh_success` | OAuth 刷新成功 |
| `icube_ai_mcp_oauth_refresh_failed` | OAuth 刷新失败 |

### 2.2 MCP 工具发现

```javascript
// MCP 工具列表
tools/list

// MCP 工具调用
tools/call

// MCP 资源列表
roots/list

// MCP 资源读取
_ext/mcp/read_resource
```

### 2.3 MCP 配置

```json
{
    "mcpServers": {
        "github": {
            "command": "my-mcp-server",
            "args": ["-y", "my-mcp-server"],
            "env": {}
        }
    }
}
```

### 2.4 MCP OAuth 流程

```
1. mcp_oauth_flow_start
   ↓
2. 用户授权 (浏览器)
   ↓
3. mcp_oauth_flow_success / mcp_oauth_flow_failed
   ↓
4. Token 存储
   ↓
5. mcp_oauth_refresh_success / mcp_oauth_refresh_failed (定期刷新)
```

---

## 3. Agent 工作流

### 3.1 Agent 事件流

```
1. agent_create_project_error / agent_create_new_session_error
   ↓
2. agent_db_init / agent_db_error
   ↓
3. agent_task_plan_first_token
   ↓
4. agent_task_plan_sub_agents
   ↓
5. agent_task_plan_all
   ↓
6. agent_model_llm_stream_first_token
   ↓
7. agent_model_llm_stream
   ↓
8. agent_toolcall
   ↓
9. agent_run_mcp_request
   ↓
10. agent_run_mcp_success / agent_run_mcp_failed
    ↓
11. agent_task_plan_finish
    ↓
12. agent_task_plan_final_token
```

### 3.2 Agent 错误处理

| 事件 | 用途 |
|------|------|
| `agent_global_error` | 全局错误 |
| `agent_retry_error` | 重试错误 |
| `agent_send_chat_error` | 发送聊天错误 |
| `agent_react_error` | React 错误 |
| `agent_path_error` | 路径错误 |
| `agent_image_upload_error` | 图片上传错误 |
| `agent_with_md_error` | Markdown 错误 |
| `agent_plan_item_data_error` | 计划项数据错误 |

### 3.3 Agent 扩展

```go
// Agent 扩展请求
type AgentExtensionRequest struct {
    // 扩展配置
}

// Agent 扩展渲染
type AgentExtensionRender struct {
    // 渲染配置
}
```

---

## 4. 工具调用流程

### 4.1 完整流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Codex     │────▶│   Trae      │────▶│   LLM       │
│   CLI       │     │   Backend   │     │   Provider  │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     │  chat request      │                    │
     │───────────────────▶│  LLM request       │
     │                    │───────────────────▶│
     │                    │                    │
     │                    │  tool_use response │
     │                    │◀───────────────────│
     │  tool_use event    │                    │
     │◀───────────────────│                    │
     │                    │                    │
     │  tool_result       │                    │
     │───────────────────▶│  tool_result       │
     │                    │───────────────────▶│
     │                    │                    │
     │                    │  final response    │
     │                    │◀───────────────────│
     │  final response    │                    │
     │◀───────────────────│                    │
```

### 4.2 SSE 流式格式

```
// 内容块开始
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

// 文本增量
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

// 工具调用开始
data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"tool_xxx","name":"run_command","input":{}}}

// 工具调用增量
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\"command\":\"ls\"}"}}

// 内容块结束
data: {"type":"content_block_stop","index":1}

// 消息结束
data: {"type":"message_stop"}
```

### 4.3 工具结果提交

```json
// POST /api/ide/v1/agents/runs/:id/tool_call_outputs
{
    "type": "tool_result",
    "tool_use_id": "tool_xxx",
    "content": [
        {
            "type": "text",
            "text": "file1.txt\nfile2.txt"
        }
    ]
}
```

---

## 5. MCP 工具调用详情

### 5.1 MCP 工具定义

```go
// MCP 工具名称格式
// mcp__<server>__<tool>

// 示例
mcp__github__create_issue
mcp__github__list_repos
mcp__slack__send_message
mcp__database__query
```

### 5.2 MCP 工具调用

```json
// tools/call 请求
{
    "name": "mcp__github__create_issue",
    "arguments": {
        "repo": "owner/repo",
        "title": "Bug Report",
        "body": "Description..."
    }
}
```

### 5.3 MCP 工具发现

```json
// tools/list 响应
{
    "tools": [
        {
            "name": "create_issue",
            "description": "Create a GitHub issue",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo": { "type": "string" },
                    "title": { "type": "string" },
                    "body": { "type": "string" }
                },
                "required": ["repo", "title"]
            }
        }
    ]
}
```

---

## 6. 关键发现总结

### 6.1 工具调用

1. **18+ 内置工具**: 文件操作、搜索、执行、Web 等
2. **MCP 工具**: 动态发现和调用外部工具
3. **工具调用 ID**: 每个调用唯一标识
4. **状态追踪**: pending → running → completed/failed

### 6.2 MCP 协议

1. **OAuth 认证**: 完整的 OAuth 流程支持
2. **工具发现**: `tools/list` 动态获取工具列表
3. **工具调用**: `tools/call` 调用外部工具
4. **资源管理**: `roots/list` 管理资源

### 6.3 Agent 工作流

1. **计划生成**: `agent_task_plan_*` 事件
2. **子 Agent**: `agent_task_plan_sub_agents` 支持多 Agent
3. **工具调用**: `agent_toolcall` 事件
4. **MCP 集成**: `agent_run_mcp_*` 事件

---

## 7. Codex 集成建议

### 7.1 工具调用处理

```python
def handle_tool_call(tool_call):
    tool_id = tool_call['id']
    tool_name = tool_call['name']
    arguments = tool_call['input']

    # 执行工具
    if tool_name.startswith('mcp__'):
        result = call_mcp_tool(tool_name, arguments)
    else:
        result = execute_builtin_tool(tool_name, arguments)

    # 返回结果
    return {
        'type': 'tool_result',
        'tool_use_id': tool_id,
        'content': [{'type': 'text', 'text': result}]
    }
```

### 7.2 MCP 工具集成

```python
def call_mcp_tool(tool_name, arguments):
    # 解析工具名
    parts = tool_name.split('__')
    server = parts[1]
    tool = parts[2]

    # 调用 MCP 服务器
    response = mcp_client.call_tool(server, tool, arguments)
    return response
```

### 7.3 Agent 事件监听

```python
agent_events = [
    'agent_task_plan_first_token',
    'agent_task_plan_sub_agents',
    'agent_model_llm_stream',
    'agent_toolcall',
    'agent_run_mcp_request',
    'agent_run_mcp_success',
    'agent_task_plan_finish',
]
```

---

## 8. 下一步分析

### 8.1 待验证

1. [ ] MCP OAuth 的具体实现细节
2. [ ] 工具调用的并发控制机制
3. [ ] Agent 子任务的调度策略
4. [ ] 工具结果的格式化和验证

### 8.2 待实现

1. [ ] MCP 工具发现和调用
2. [ ] 工具调用结果处理
3. [ ] Agent 事件监听
4. [ ] 错误恢复机制
