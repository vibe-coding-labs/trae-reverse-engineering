# L07: Prompt 模板系统、Agent 生命周期与 Team Agent 联合分析

> 生成时间: 2026-06-01 ~12:30 GMT+8  
> 分析版本: Trae IDE v2.3.30128

---

## 目录

1. [Prompt 模板系统](#1-prompt-模板系统)
2. [Prompt 渲染流程](#2-prompt-渲染流程)
3. [Agent V3 配置矩阵](#3-agent-v3-配置矩阵)
4. [子代理系统](#4-子代理系统)
5. [Team Agent 团队代理](#5-team-agent-团队代理)
6. [Agent 终止与生命周期](#6-agent-终止与生命周期)
7. [Hook 事件系统](#7-hook-事件系统)
8. [工具调用与 MCP 完整链](#8-工具调用与-mcp-完整链)
9. [Core Memory 核心记忆系统](#9-core-memory-核心记忆系统)
10. [Agent API 端点索引](#10-agent-api-端点索引)

---

## 1. Prompt 模板系统

### 1.1 总体架构

Prompt 模板系统采用 **KV 存储** + **场景渲染器** 的设计模式，支持多版本管理和加密。

```
┌──────────────────────────────────────────────────────────────────┐
│                     Prompt 模板系统架构                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  存储层:                                                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  KV Store (database/kv_cache)                               │  │
│  │  │                                                         │  │
│  │  │  key = "{prompt_key}:{version}:{label}"                  │  │
│  │  │  value = "{prompt_content}"                              │  │
│  │  │                                                         │  │
│  │  │  支持: AES-256-GCM 加密 (ModelEcryptedPrompt)            │  │
│  │  └─────────────────────────────────────────────────────────│  │
│  │                                                              │
│  ├── 远端同步 (动态配置)                                        │
│  ├── 本地缓存 (model_config_cache 表)                           │
│  └── 内置默认 (编译进二进制)                                    │
│                                                                  │
│  渲染层:                                                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  PromptRenderer                                             │  │
│  │  ├── history_user_input: Vec<String>   ← 历史用户输入      │  │
│  │  ├── history: Vec<String>              ← 对话历史          │  │
│  │  ├── context (AgentContext 43 fields)  ← 上下文注入        │  │
│  │  ├── system_prompt                    ← 系统提示词         │  │
│  │  └── tool_descriptions                ← 工具描述列表       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  模板查询:                                                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  PromptTemplateQueryItem (2 字段)                            │  │
│  │  PromptTemplateInfo (5 字段)                                 │  │
│  │  ├── prompt_key: String                                      │  │
│  │  ├── prompt_version: String                                  │  │
│  │  ├── prompt_label: String                                    │  │
│  │  ├── prompt_list: Vec<PromptTemplateItem> (2 字段)          │  │
│  │  └── + 1 more field                                          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Prompt Key 完整列表 (11 种)

| Key | 用途 | 说明 |
|-----|------|------|
| `plan_v2` | 规划提示词 | 用于 Plan V2 模式的任务规划 |
| `agents` | Agent 初始化提示词 | 通用 Agent 行为定义 |
| `master_agent` | 主 Agent 提示词 | 协调子代理的调度行为 |
| `search_agent` | 搜索 Agent 提示词 | 代码/网络搜索行为 |
| `compact_prompt` | 压缩提示词 | 对话历史压缩策略 |
| `custom_sub_agent` | 自定义子 Agent 提示词 | 用户定义的子代理行为 |
| `multimodal_video` | 多模态视频提示词 | 视频内容理解 |
| `document_agent` | 文档 Agent 提示词 | 文档阅读和分析 |
| `project_preparation_agent` | 项目准备 Agent 提示词 | 新项目初始设置 |
| `web_development_agent` | Web 开发 Agent 提示词 | 前端/后端开发 |
| `resource_diagnosis` | 资源诊断提示词 | 诊断运行中资源 |

### 1.3 模板元数据结构

```rust
struct PromptTemplateMetadata {
    // 1 要素 - 模板元数据
}

struct PromptTemplateInfo {
    prompt_key: String,           // 模板键
    prompt_version: String,       // 模板版本
    prompt_label: String,         // 模板标签
    prompt_list: Vec<PromptTemplateItem>,  // 模板项目列表
    // + 1 more field
}

struct PromptTemplateItem {
    // 2 要素 - 单个模板项
}

struct PromptTemplateQueryItem {
    // 2 要素 - 模板查询项
}

struct ModelPromptConfig {
    client_connect: bool,          // 客户端连接模式
    custom_model_id: String,       // 自定义模型 ID
    is_custom_base_url: bool,      // 是否为自定义 Base URL
}

struct ModelEcryptedPrompt {
    // 4 要素 - AES-256-GCM 加密的提示词
}
```

### 1.4 模板获取逻辑

```
┌──────────────────────────────────────────────────────────────────┐
│                     模板获取优先级                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 检查动态配置:                                                │
│     ├── disable_prompt_fetching: boolean                         │
│     ├── function_filters: Vec<String>                            │
│     └── prompt_meta_filter_config: PromptMetaFilterConfig        │
│                                                                  │
│  2. 从远端获取模板 (如果启用)                                    │
│     ├── 成功 → 缓存到本地 KV Store                               │
│     └── 失败 → 使用本地缓存或内置默认                             │
│                                                                  │
│  3. 从本地数据库加载:                                             │
│     ├── database.db / model_config_cache 表                      │
│     ├── key = prompt_key:version                                 │
│     └── 加密模板用 ModelEcryptedPrompt 解密                       │
│                                                                  │
│  4. 使用内置默认模板 (编译时固化的)                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Prompt 渲染流程

### 2.1 rs_13_render_user_prompt 完整过程

```
rs_13_render_user_prompt: Prompt 渲染
══════════════════════════════════════════════════════════════════

输入:
├── prompt_key (例如 "plan_v2")
├── AgentContext (43 字段)
├── history_user_input (历史用户输入)
├── history (对话历史)
└── tool_descriptions (工具描述)

渲染步骤:
1. 获取模板
   ├── 按 prompt_key 查询 KV Store
   └── 获取 PromptTemplateInfo

2. 注入变量
   ├── {{context}}       → AgentContext 渲染结果
   ├── {{history}}       → 格式化的对话历史
   ├── {{tools}}         → 工具描述 (JSON Schema)
   ├── {{user_input}}    → 当前用户输入
   ├── {{language}}      → 界面语言
   └── {{workspace}}     → 工作区信息

3. 组装消息
   ├── system: {system prompt}
   ├── user: {rendered user prompt}
   └── (可选) assistant: {历史回复}

4. 后处理
   ├── 压缩 (如 compact_prompt 模式)
   ├── Token 截断 (v3_compaction_token_limit_ratio)
   └── 安全检查 (Content Security)

5. 输出
   └── Vec<LLMClientRequestMessageRaw> → 发送给 LLM

输出:
├── 渲染后的用户提示词 (String)
└── 最终 LLM 请求消息列表
```

### 2.2 提示词渲染上下文来源 (20+ 解析器)

```
rs_06_resolver_* 系列 (在 rs_13 之前执行)

上下文解析器:
├── browser_selection  → 当前浏览器选择内容
├── current_editor     → 当前编辑器文件内容
├── custom_rules       → 项目自定义规则
├── diagnostic         → 诊断信息
├── doc                → 打开文档内容
├── file_diff          → 文件差异
├── lint_error         → Lint 错误详细信息
├── log_message        → 日志输出
├── metadata           → 文件元数据
├── problem            → 问题面板条目
├── project_labels     → 项目标签
├── selection          → 编辑器中选中的文本
├── slash_command      → Slash 命令参数
├── terminal           → 终端输出
├── user_interaction   → 用户交互记录
├── user_message       → 用户原始消息
└── websearch          → 网络搜索结果

→ 合并为 AgentContext (43 字段)
→ 传递给 rs_13_render_user_prompt
```

### 2.3 消息组装格式

```rust
// LLM 请求消息格式
struct LLMClientRequestMessageRaw {
    role: String,                    // "system" | "user" | "assistant"
    content: Vec<ContentBlock>,      // 内容块
    // ... 更多字段
}

// 内容块
enum ContentBlock {
    Text(String),
    ToolUse(ToolUseBlock),
    ToolResult(ToolResultBlock),
    Image(ImageBlock),
}
```

---

## 3. Agent V3 配置矩阵

### 3.1 完整配置参数 (60+)

从动态配置中提取的 Agent V3 特定配置参数：

```javascript
{
    // ─── 子代理控制 ───
    v3_solo_coder_disable_sub_agents: boolean,         // 禁用子代理
    v3_sub_agent_route_enable: boolean,                 // 子代理路由
    v3_sub_agent_summary_return_after_error: boolean,   // 子代理错误后返回摘要
    v3_sub_agent_model_config_names: string[],          // 子代理模型配置

    // ─── 规划控制 ───
    v3_solo_coder_disable_plan_mode: boolean,           // 禁用规划模式

    // ─── 并行执行 ───
    v3_parallel_agents_disabled: boolean,               // 禁用并行 Agent
    v3_max_concurrent_tasks: number,                    // 最大并发任务数
    v3_concurrent_task_timeout: number,                 // 并发任务超时

    // ─── 压缩与截断 ───
    v3_solo_coder_cumulative_compaction_strategy: string, // 累积压缩策略
    v3_solo_coder_compaction_restore_reading_nums: number, // 压缩恢复读取数
    v3_compaction_token_limit_ratio: number,             // 压缩 Token 比例
    v3_async_compaction_token_limit_ratio: number,       // 异步压缩 Token 比例
    v3_micro_compact_trigger_token_ratio: number,        // 微压缩触发比例
    v3_micro_compact_kept_token: number,                 // 微压缩保留 Token
    v3_micro_compact_min_token: number,                  // 微压缩最小 Token

    // ─── 工具限制 ───
    v3_ls_max_result_chars: number,                     // ls 最大结果字符数
    v3_read_max_content_byte_size: number,               // 读取最大字节数
    v3_read_enable_truncation: boolean,                  // 启用读取截断
    v3_read_enable_start_end_line: boolean,              // 启用起止行
    v3_snippet_content_max_char_count: number,           // 片段最大字符数
    v3_grep_max_result_chars: number,                    // grep 最大结果字符数
    v3_grep_default_output_mode: string,                 // grep 默认输出模式
    v3_grep_enable_hidden: boolean,                      // grep 包含隐藏文件
    v3_grep_max_columns: number,                         // grep 最大列数
    v3_grep_post_sort: boolean,                          // grep 后排序
    v3_ripgrep_partial_on_timeout: boolean,              // ripgrep 超时部分结果
    v3_max_toolcall_chars: number,                       // 工具调用最大字符
    v3_search_codebase_max_tokens: number,               // 代码库搜索最大 Token
    v3_file_read_state_cache_enabled: boolean,           // 文件读取状态缓存
    v3_read_dedup_enabled: boolean,                      // 读取去重
    v3_use_view_files_tool: boolean,                     // 使用查看文件工具

    // ─── 工具选择 ───
    v3_optimize_tool_choice_strategy: string,            // 工具选择优化策略
    v3_custom_tool_list: string[],                       // 自定义工具列表

    // ─── 功能开关 ───
    v3_enable_skill_tool: boolean,                       // 启用技能工具
    v3_enable_knowledge_tool: boolean,                   // 启用知识工具
    v3_enable_web_fetch_tool: boolean,                   // 启用网络抓取工具
    v3_enable_file_diff_resolver: boolean,               // 启用文件差异解析器
    v3_solo_coder_only_single_chat: boolean,             // 仅单次聊天

    // ─── 被动行为 ───
    v3_passive_compaction_user_perceptible: boolean,     // 用户可见的被动压缩
}
```

### 3.2 配置分类

```
                           Agent V3 配置体系
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
         子代理控制         规划/执行           工具系统
            │                  │                  │
   ┌────────┴────────┐  ┌─────┴──────┐   ┌──────┴──────┐
   │ v3_sub_agent    │  │ disable    │   │ v3_ls       │
   │ .route_enable   │  │ _plan_mode │   │ .max_result │
   │ v3_sub_agent    │  │            │   │ v3_read     │
   │ .model_config   │  └────────────┘   │ .max_content│
   │ disable_sub_    │                   │ v3_grep.*   │
   │ agents          │                   │ v3_ripgrep.*│
   └─────────────────┘                   └─────────────┘
            │                  │                  │
        Token 管理         压缩管理           并行执行
            │                  │                  │
   ┌────────┴────────┐  ┌─────┴──────┐   ┌──────┴──────┐
   │ v3_compaction  │  │ cumulativ  │   │ v3_parallel │
   │ .token_limit   │  │ _compaction│   │ ._disabled  │
   │ v3_micro_      │  │ _strategy  │   │ v3_max_     │
   │ compact.*      │  │ async_     │   │ concurrent  │
   └─────────────────┘  │ compact    │   │ ._tasks     │
                        └────────────┘   └─────────────┘
```

---

## 4. 子代理系统

### 4.1 子代理架构

```
┌──────────────────────────────────────────────────────────────────┐
│                     Agent V3 子代理系统                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  主 Agent (master_agent prompt)                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  职责: 接收用户请求，拆解任务，调度子代理                      ││
│  │  特性: 支持 Plan/Execute 分离, 并行执行                       ││
│  └─────────────────────────────────────────────────────────────┘│
│                     │                                              │
│        ┌────────────┼────────────┬────────────┐                   │
│        ▼            ▼            ▼            ▼                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ 搜索子   │ │ 代码子   │ │ 文档子   │ │ 项目准   │             │
│  │ Agent    │ │ Agent    │ │ Agent    │ │ 备子Agent│             │
│  │search_   │ │custom_   │ │document_ │ │project_  │             │
│  │agent     │ │sub_agent │ │agent     │ │prepara…  │             │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘             │
│       │            │            │            │                    │
│       ▼            ▼            ▼            ▼                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │               context_asset/subagents/ 模块                  │  │
│  │  提供: 独立的 Agent 上下文、工具集、模型配置                   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 子代理事件

```rust
struct SubAgentCreateEvent {
    // 6 要素 - 子代理创建事件
}

// Agent 空闲事件
struct AgentIdleEvent {
    // 6 要素 - Agent 空闲时触发
    // 用于: 等待工具结果、等待用户输入等
}

// Agent 恢复事件
struct AgentResumeEvent {
    // 6 要素 - Agent 恢复时触发
    // 用于: 工具结果到达、用户确认后等
}
```

### 4.3 子代理协调流程

```
1. 主 Agent 分析用户请求
   ├── 识别子任务
   └── 为每个子任务选择子 Agent 类型

2. 创建子 Agent
   ├── SubAgentCreateEvent (6 要素)
   ├── 分配 prompt_key (search_agent / custom_sub_agent 等)
   ├── 分配模型配置 (v3_sub_agent_model_config_names)
   └── 分配工具集

3. 并行执行
   ├── v3_max_concurrent_tasks 控制并行度
   ├── 每个子 Agent 独立进行完整 Chat 生命周期
   ├── 子 Agent 可以有自己的 Plan/Execute
   └── 超时控制: v3_concurrent_task_timeout

4. 结果收集
   ├── 子 Agent 完成 → 返回结果给主 Agent
   ├── 子 Agent 错误 → v3_sub_agent_summary_return_after_error
   └── 主 Agent 综合所有子结果

5. 路由决策
   ├── v3_sub_agent_route_enable 控制是否启用子代理路由
   └── 路由策略: 基于任务类型动态选择子 Agent
```

---

## 5. Team Agent 团队代理

### 5.1 Team Agent 概念

Team Agent 是 Trae 的多 Agent 协作系统，支持后端管理的 Agent 团队。

```
┌──────────────────────────────────────────────────────────────────┐
│                     Team Agent 系统                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  API 端点:                                                       │
│  ├── POST /api/ide/v1/agent/team_agent/create  → 创建团队 Agent │
│  ├── POST /api/ide/v1/agent/team_agent/update  → 更新团队 Agent │
│  ├── DELETE /api/ide/v1/agent/team_agent/remove → 删除团队 Agent │
│  ├── GET  /api/ide/v1/agent/team_agent/list    → 列出团队 Agent │
│  ├── GET  /api/ide/v1/agent/team_agent/details → 获取团队详情   │
│  └── POST /api/ide/v1/agent/team_agent/change_status → 状态变更 │
│                                                                  │
│  数据结构:                                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ TeamAgentListItem (agent_env, last_updated_at, avatar_url…)  │ │
│  │ TeamAgentDetailsItem                                        │ │
│  │ TeamAgentDetailsResponse                                    │ │
│  │ BackendTeamAgentSubAgent           ← 后端管理的子 Agent      │ │
│  │ BackendTeamAgentCreateRequest                                │ │
│  │ TeamAgentSubTeamAgentRemoveRequest                           │ │
│  │ TeamAgentListRequest(search/sort)                            │ │
│  │ TeamAgentListResponse                                        │ │
│  │ TeamAgentDetailsRequest                                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Team Agent vs Sub-Agent

| 特性 | Team Agent | Sub-Agent (V3) |
|------|-----------|----------------|
| 管理方 | 后端 (API) | 本地 (主 Agent 动态创建) |
| 生命周期 | 持久化 (创建/更新/删除) | 临时的 (每次会话创建) |
| 团队结构 | 后端配置的子 Agent 列表 | 主 Agent 动态调度 |
| 共享能力 | 可跨会话共享 | 仅当前会话 |
| API 端点 | 6 个 REST 端点 | 无独立端点 |

---

## 6. Agent 终止与生命周期

### 6.1 完整 Agent 生命周期

```
CREATED
  │
  ├─ PLANNING (rs_14_get_history_plan → rs_15_before_generate_plan)
  │   ├─ 分析用户请求
  │   ├─ 拆解为子任务
  │   └─ 生成执行计划
  │
  ├─ EXECUTING
  │   ├─ Tool Calls (浏览器/文件/搜索/代码)
  │   │   ├─ tool_use → ToolResult
  │   │   └─ AgentIdleEvent (等待工具结果)
  │   ├─ Sub-Agent Spawn
  │   │   ├─ SubAgentCreateEvent
  │   │   └─ SubAgentResult
  │   └─ AgentResumeEvent (结果到达)
  │
  ├─ REVIEWING
  │   ├─ 验证执行结果
  │   └─ 是否需要额外操作?
  │       ├─ 是 → 回到 EXECUTING
  │       └─ 否 → COMPLETED
  │
  ├─ COMPLETED
  │   ├─ DoneEvent (1 要素)
  │   └─ 结果返回给用户
  │
  └─ TERMINATED (异常终止)
      ├─ ErrorEvent (4 要素)
      ├─ icube_ai_agent_pre_termination ← 预终止事件
      ├─ 超时: v3_concurrent_task_timeout
      ├─ 用户取消: stop_chat_session
      └─ 资源限制: 速率限制 / Token 限制
```

### 6.2 终止原因分类

| 原因 | 触发条件 | 处理 |
|------|---------|------|
| 正常完成 | 所有任务执行完毕 | DoneEvent |
| 用户取消 | `stop_chat_session` API | sse.cancel |
| 超时 | `v3_concurrent_task_timeout` | ErrorEvent |
| 速率限制 | Rate Limiter | HTTP 429 + retry_after |
| Token 超限 | Token 计数超限 | 触发压缩 (compaction) |
| 预终止 | `pre_termination` 标记 | 触发 handoff 或清理 |
| 系统错误 | 内部异常 | ErrorEvent(4) |

### 6.3 PreTerminationInfo

```rust
struct PreTerminationInfo {
    // 预终止信息 — 在 CreateChatSessionResponse 中包含
    // 用于: Lite VM 超时前通知、会话到期前迁移
}
```

---

## 7. Hook 事件系统

### 7.1 Hook 架构

```rust
struct RawEventHookGroup {
    // 3 要素 - 事件钩子组
}

struct RawHookItem {
    // 3 要素 - 单个钩子项
}

struct RawHookOutput {
    // 5 要素 - 钩子输出
}

struct RawHookSpecificOutput {
    // 5 要素 - 特定钩子输出
}
```

### 7.2 Event Types with Hooks

| 事件类型 | 编码 | 说明 |
|---------|------|------|
| `HistoryEvent` | 6 | 历史事件 |
| `SubAgentCreateEvent` | 6 | 子代理创建 |
| `AgentIdleEvent` | 6 | Agent 空闲 |
| `ErrorEvent` | 4 | 错误事件 |
| `DoneEvent` | 1 | 完成事件 |
| `QueueBeginEvent` | 4 | 队列开始 |
| `QueueEndEvent` | 3 | 队列结束 |
| `QueueContinueEvent` | 1 | 队列继续 |

### 7.3 Hub Hook 触发器

```rust
apps/icube_server_rs/modules/ai-agent/src/domain/hub/hook/trigger.rs:26

Hub Hook 用于:
- 事件通知回溯
- 跨 Hub 事件同步
- Agent 状态变更广播
```

---

## 8. 工具调用与 MCP 完整链

### 8.1 工具调用完整流程

```
┌──────────────────────────────────────────────────────────────────┐
│                 工具调用完整流程                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  阶段 1: LLM 生成 tool_use                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ content_block_start: type="tool_use"                        │ │
│  │ ├── id: "toolu_abc123"                                      │ │
│  │ ├── name: "browser_navigate"                                │ │
│  │ └── input: { "url": "https://..." }                         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  阶段 2: 解析与路由                                              │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ LLMClientToolCall (5 要素)                                   │ │
│  │ ├── id: String (工具调用 ID)                                 │ │
│  │ ├── type: "function"                                         │ │
│  │ ├── function.name: String                                    │ │
│  │ ├── function.arguments: String (JSON)                        │ │
│  │ ├── index: Option<u32> (流式索引)                            │ │
│  │ └── delta: Option<bool> (增量标志)                           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                    │                                              │
│                    ▼                                              │
│  阶段 3: 工具执行                                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 1. 路由到工具                                                     │ │
│  │    ├── 内置工具 → domain/toolcall/tools/                      │ │
│  │    ├── MCP 工具 → mcp_name_resolver → MCP Server            │ │
│  │    └── 自定义工具 → v3_custom_tool_list                     │ │
│  │ 2. 安全检查                                                   │ │
│  │    ├── Content Security 检查                                   │ │
│  │    ├── MCP Whitelist 检查                                     │ │
│  │    └── Sandbox 隔离 (如果需要)                                │ │
│  │ 3. 执行                                                       │ │
│  │    ├── AgentIdleEvent (等待结果)                                │ │
│  │    └── toolConfirmTimeoutSecs: 30s (超时)                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                    │                                              │
│                    ▼                                              │
│  阶段 4: 结果回传                                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ ToolResult                                                   │ │
│  │ ├── tool_use_id: "toolu_abc123" (匹配原始调用)              │ │
│  │ ├── content: [{ type: "text", text: "结果..." }]             │ │
│  │ └── is_error: bool (是否错误)                                │ │
│  │                                                              │ │
│  │ → 封装为 tool_result content_block                            │ │
│  │ → 添加到消息列表                                              │ │
│  │ → AgentResumeEvent (恢复 Agent)                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                    │                                              │
│                    ▼                                              │
│  阶段 5: 继续生成                                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ LLM 收到 tool_result                                        │ │
│  │ ├── 继续生成回复或调用更多工具                                 │ │
│  │ └── 直到 message_stop                                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 MCP 工具调用链

```
LLM tool_use
  │
  ├─ 路由到 mcp_name_resolver
  │   ├── 查找 mcp_server_agent_relation 数据库表
  │   ├── 匹配 MCP server + tool 名称
  │   └── 检查 MCPWhitelist
  │
  ├─ 建立 MCP 连接 (如需)
  │   ├── 通过 WebSocket 或 stdio 连接 MCP Server
  │   └── 认证握手
  │
  ├─ 调用 MCP tool
  │   ├── icube_ai_mcp_call_tool 事件
  │   ├── 发送 JSON-RPC 请求
  │   └── 等待响应
  │
  ├─ 处理结果
  │   ├── icube_ai_mcp_call_success / icube_ai_mcp_call_failed
  │   ├── 格式化为 ToolResult
  │   └── Content Security 检查
  │
  └─ 返回 LLM
```

### 8.3 工具缓存系统

```rust
struct ToolCacheDataEvent {
    group_name: String,
    // + 1 字段
}

struct ToolCacheGroup {
    // 3 要素 - 工具缓存组
}

struct ToolCacheItem {
    // 3 要素 - 工具缓存项
}

// 来源:
source: domain/plan/simple_service_v2/tool_cache.rs:66
```

### 8.4 工具结果存

```javascript
// 配置
{
    save_toolcall_result_config: any,     // 保存工具调用结果配置
    enable_tool_result_trimming: boolean,  // 工具结果裁剪
    v3_max_toolcall_chars: number,         // 工具调用最大字符数
}
```

---

## 9. Core Memory 核心记忆系统

### 9.1 概述

Trae 实现持久化的核心记忆模块，使 Agent 在多轮对话间保持上下文连贯性。

```rust
domain/memory/core_memory/service.rs
```

### 9.2 记忆淘汰策略

| 策略 | 说明 |
|------|------|
| `w_tinylfu` | 加权 TinyLFU 缓存淘汰 |
| `hybrid_half_life` | 混合半衰期衰减策略 |

### 9.3 配置

```javascript
{
    core_memory_disabled: boolean,              // 禁用核心记忆
    core_memory_block_rough_max_token: number,  // 记忆块最大 Token
    shallow_memento_disabled: boolean,          // 禁用浅层记忆
}
```

### 9.4 记忆工作流

```
1. 每轮对话结束 → 提取关键信息
2. 存储到 core_memory (持久化)
3. 下一轮对话开始 → 加载相关记忆
4. 注入到 AgentContext
5. 淘汰策略控制存储容量
```

---

## 10. Agent API 端点索引

### 10.1 Agent 相关 API

| 方法 | 端点 | 用途 |
|------|------|------|
| POST | `/api/ide/v1/agents/runs` | 运行 Agent 任务 |
| POST | `/api/ide/v1/agent/cancel_queue_task` | 取消队列任务 |
| POST | `/api/ide/v1/agent/jump_queue_task` | 跳转队列任务 |
| GET | `/api/ide/v1/agent/get` | 获取 Agent 信息 |
| POST | `/api/ide/v1/agent/team_agent/create` | 创建团队 Agent |
| POST | `/api/ide/v1/agent/team_agent/update` | 更新团队 Agent |
| DELETE | `/api/ide/v1/agent/team_agent/remove` | 删除团队 Agent |
| GET | `/api/ide/v1/agent/team_agent/list` | 列出团队 Agent |
| GET | `/api/ide/v1/agent/team_agent/details` | 获取团队详情 |
| POST | `/api/ide/v1/agent/team_agent/change_status` | 变更团队状态 |
| POST | `/api/ide/v1/agents/workflows/workflow_id/start` | 启动工作流 |
| POST | `/api/agent/v3/workflow/start` | V3 工作流启动 |
| POST | `/api/agent/v3/interrupt` | V3 工作流中断 |

### 10.2 Agent 相关事件

```
icube_ai_agent_v3_hil_wait_for_tool_confirmation  — HIL 等待工具确认
icube_ai_agent_v3_call_tool_node                  — 工具节点调用
icube_ai_agent_pre_termination                    — 预终止事件
icube_ai_agent_generate_image                     — 图像生成
icube_ai_agent_image_process                      — 图像处理
icube_ai_agent_lite_vm_startup                    — Lite VM 启动
icube_ai_agent_context_usage_send                 — 上下文用量上报
icube_ai_agent_vsock_request                      — Vsock 通信
icube_ai_agent_lite_vm_stream_error               — VM 流错误
icube_ai_agent_schedule_execution                 — 定时任务执行
icube_ai_agent_schedule_config                    — 任务配置
icube_ai_agent_schedule_disabled                  — 任务禁用
```

---

> 本报告基于 ai-agent 二进制分析 + 协议分析文档 + 配置提取。
> 所有结构体字段数和配置项以二进制分析及文档提取为准。