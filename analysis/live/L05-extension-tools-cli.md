# L05: CLI 工具链、扩展体系与 Agent/工具系统

> 生成时间: 2026-06-01 ~12:14 GMT+8  
> 分析版本: Trae IDE v2.3.30128

---

## 目录

1. [CLI 命令树](#1-cli-命令树)
2. [扩展体系总览](#2-扩展体系总览)
3. [Trae 特有扩展详细分析](#3-trae-特有扩展详细分析)
4. [工具系统完整映射](#4-工具系统完整映射)
5. [Agent V3 子代理系统](#5-agent-v3-子代理系统)
6. [Content Security 安全系统](#6-content-security-安全系统)
7. [特征配置矩阵](#7-特征配置矩阵)
8. [@byted-icube 模块依赖树](#8-byteed-icube-模块依赖树)
9. [知识图谱 (CKG)](#9-知识-cgkg)
10. [Scheduled Tasks 定时任务](#10-scheduled-tasks-定时任务)

---

## 1. CLI 命令树

### 1.1 CLI 概述

CLI 基于 VSCode CLI 架构，通过 `cli.js` (17,233 行) 实现。支持完整的 Electron 命令行参数。

### 1.2 完整命令树

```
code/trae
├── <file|folder|workspace>     # 打开文件/文件夹/工作区
│
├── tunnel                       # 安全隧道（远程访问）
│   ├── user
│   │   └── login                # 隧道用户登录
│   │       └── --provider       # 认证提供商
│   │       └── --access-token   # 访问令牌
│   ├── --cli-data-dir           # CLI 数据目录
│   ├── --disable-telemetry      # 禁用遥测
│   └── --telemetry-level        # 遥测级别
│
├── serve-web                    # 启动 Web 版编辑器
│   ├── --cli-data-dir           # CLI 数据目录
│   ├── --disable-telemetry      # 禁用遥测
│   └── --telemetry-level        # 遥测级别
│
├── 编辑选项 (-o):
│   ├── -d, --diff <file> <file>        # 比较文件差异
│   ├── -m, --merge <path1 path2 base result> # 合并文件
│   ├── -a, --add <folder>              # 添加文件夹到工作区
│   ├── --remove <folder>               # 从工作区移除文件夹
│   ├── -g, --goto <file:line:char>     # 跳转到文件位置
│   ├── -n, --new-window                # 新窗口打开
│   ├── -r, --reuse-window              # 复用窗口打开
│   ├── -w, --wait                      # 等待文件关闭
│   ├── --locale <locale>               # 界面语言
│   ├── --user-data-dir <dir>           # 用户数据目录
│   ├── --profile <profileName>         # 使用指定配置
│   └── -h, --help                      # 帮助信息
│
├── 扩展选项 (-e):
│   ├── --extensions-dir <dir>          # 扩展安装目录
│   ├── --extensions-download-dir       # 扩展下载目录
│   ├── --list-extensions               # 列出已安装扩展
│   ├── --show-versions                 # 显示扩展版本
│   ├── --category <category>           # 按分类筛选
│   ├── --install-extension <ext-id>    # 安装扩展
│   ├── --pre-release                   # 安装预发布版
│   ├── --uninstall-extension <ext-id>  # 卸载扩展
│   └── --update-extensions             # 更新扩展
│
├── 调试/追踪 (-t):
│   ├── -v, --version                   # 显示版本号
│   ├── --verbose                       # 详细输出
│   ├── --log <level>                   # 日志级别
│   ├── -s, --status                    # 进程状态
│   ├── --prof-startup                  # 启动性能分析
│   └── --prof-append-timers            # 附加计时器分析
│
└── 其他选项:
    ├── --enable-proposed-api <ext-id>  # 启用提案 API
    ├── --disable-gpu                   # 禁用 GPU 加速
    └── --max-memory <memory>           # 最大内存限制
```

### 1.3 命令分类

```javascript
// argv.js 中的分类定义
categories = {
    o: "edit",           // 编辑相关 (-d diff, -m merge, -a add, -g goto, -n new-window, etc.)
    e: "extensions",     // 扩展管理 (install/list/uninstall/update)
    t: "troubleshooting" // 调试 (-v verbose, --log, --status, --prof-startup)
}
```

### 1.4 CLI 数据目录

```
Linux:   ~/.config/trae/
macOS:   ~/.config/Trae/
Windows: %APPDATA%\Trae\
```

数据目录包含：
- `User/globalStorage/storage.json` — 全局存储
- `User/settings.json` — 用户设置
- `logs/` — 日志目录
- `ModularData/` — 模块数据（含 ai-agent database.db）

### 1.5 CLI 认证（trae-cli v0.120.35）

```javascript
CLI Auth 结构:
{
    DeviceID: String,       // 设备 ID
    Host: String,           // API 主机
    LoginBaseURL: String,   // 登录基 URL
    Scope: String,          // 认证 Scope
    OauthToken: OAuthTokenStore  // Token 存储
}

Token 存储优先级:
1. KeyringStore (系统密钥链)
2. OAuthTokenStore (文件存储)
3. MemoryStore (内存, 临时)

授权头:
  Authorization: Bearer {token}
  (注意: CLI 不使用 x-cloudide-token)
```

---

## 2. 扩展体系总览

### 2.1 扩展分类

Trae IDE 使用 100+ 个扩展，分为三类：

```
├── VSCode 标准扩展 (90+)
│   ├── git / git-base / github / github-authentication
│   ├── html / css / json / markdown / typescript / javascript
│   ├── python / java / go / rust / cpp / csharp
│   ├── debug-auto-launch / merge-conflict / npm
│   └── themes: default / dark+ / light+ / monokai / etc.
│
├── Trae 特有扩展 (16)
│   ├── ai-completion          — AI 代码补全
│   ├── git-ai.git-ai-vscode   — Git AI 代码追踪
│   ├── trae.flux-helper       — Flux 功能辅助
│   ├── tunnel-forwarding      — 隧道转发
│   └── byted-icube.*          — Trae 核心功能扩展 (11个)
│       ├── go-enhance         — Go 语言增强
│       ├── java-helper        — Java 辅助
│       ├── node-helper        — Node.js 辅助
│       ├── python-enhance     — Python 环境管理
│       ├── integrations-extended — 集成扩展 (Supabase 等)
│       ├── icube-jetbrains-experience-helper — JB 体验增强
│       └── cloudide.*         — CloudIDE 基础设施
│           ├── icube-agent-shell-exec  — Agent Shell 执行
│           ├── icube-devtool-ports      — DevTool 端口
│           ├── icube-im-bridge          — IM 桥接
│           └── icube-remote-ssh         — 远程 SSH
│
└── 主题 (3)
    ├── theme-icube          — Trae 主题
    └── theme-defaults       — 默认主题
```

### 2.2 @byted-icube 模块依赖树

```
node_modules/@byted-icube/
├── ai-modules-chat          ← AI 聊天模块 (从 ../../modules/ai-chat/cdn)
├── bundled-deps             ← 捆绑依赖 (portfinder, jsdom, etc.)
├── desktop-modules          ← 桌面端模块 (从 ../../modules/desktop/cdn)
├── lite-modules             ← Lite 模式模块 (从 ../../modules/lite/cdn)
├── manager-sdk              ← Manager SDK (0.0.0-alpha.20250402)
├── env                      ← 环境检测
├── trae-network-client      ← 网络客户端 (HTTP/Undici)
├── uploader                 ← 文件上传
├── tea                      ← 事件追踪 (GTM)
├── slardar                  ← 监控上报
├── webcomponents            ← Web Components
└── dynamic-config-sdk       ← 动态配置 SDK

第三方依赖:
├── @aha-kit/ipc             ← AHA IPC 层
├── @aha-kit/ipc-linux-x64   ← AHA IPC Linux 平台
├── @aha-kit/rpc             ← AHA RPC (JSON-RPC 2.0)
└── @aha-kit/zmq             ← Rust ZMQ 实现
```

---

## 3. Trae 特有扩展详细分析

### 3.1 ai-completion

```json
{
    "name": "ai-code-completion",
    "publisher": "trae",
    "versionCode": 20260212,        // 版本构建日期 2026-02-12
    "categories": ["Machine Learning", "Programming Languages", "Snippets"]
}
```

负责 AI 代码补全功能，包括内联补全和代码片段建议。

### 3.2 git-ai.git-ai-vscode

```json
{
    "name": "git-ai-vscode",
    "version": "0.1.17",
    "publisher": "git-ai",
    "activationEvents": [
        "onTraeGitAiTracking",
        "onCommand:icube.ai.reportGitAiCodeContribution",
        "onCommand:git-ai.checkpointCueInlineCompletion",
        "onCommand:git-ai.checkpointTrae",
        "onCommand:git-ai.toggleAICode",
        "onCommand:git-ai.showRepoHealth",
        "onCommand:git-ai.showStatsOverview"
    ]
}
```

**功能：**
- AI 代码变更追踪（追踪哪些代码由 AI 生成）
- AI 代码贡献报告（`icube.ai.reportGitAiCodeContribution`）
- Checkpoint 管理（AI 生成的代码段）
- 仓库健康度检查
- 统计概览

**配置项：**
- `gitai.enableCheckpointLogging` — AI 编辑检测通知
- `gitai.experiments.aiTabTracking` — AI Tab 补全追踪（实验性）
- `gitai.blameMode` — AI 责任归属显示模式（auto/off/line/all）
- `gitai.enableInTrae` — 在 Trae 中启用

### 3.3 trae.flux-helper

```json
{
    "name": "flux-helper",
    "publisher": "trae",
    "activationEvents": ["onStartupFinished"],
    "contributes": {}
}
```

Flux 功能辅助 — 提供 Flux 相关集成能力。

### 3.4 Integrations Extended

```json
{
    "commands": [
        {
            "command": "_icube.extended.integrations.supabase.listProjects",
            "title": "Integrations: Supabase List Projects"
        }
    ]
}
```

提供第三方服务集成，包括 Supabase 项目管理。

### 3.5 icube-agent-shell-exec

Shell 命令执行扩展 — 用于在 IDE 中执行 Agent Shell 命令。

### 3.6 icube-im-bridge

即时通讯桥接扩展 — 连接 IM 系统（如飞书/钉钉）。

### 3.7 icube-remote-ssh

基于 SSH 的远程开发扩展。

### 3.8 icube-devtool-ports

开发者工具端口管理。

### 3.9 icube-jetbrains-experience-helper

JetBrains 用户迁移到 Trae 的体验增强插件：Search Everywhere、Implementation Jump 等。

---

## 4. 工具系统完整映射

### 4.1 工具分类

```
┌──────────────────────────────────────────────────────────────────┐
│                      Trae 工具系统完整分类                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 浏览器自动化 (30+ tools)                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ browser_navigate          browser_click                    │  │
│  │ browser_type              browser_snapshot                 │  │
│  │ browser_take_screenshot   browser_scroll                   │  │
│  │ browser_hover             browser_drag                     │  │
│  │ browser_press_key         browser_select_option            │  │
│  │ browser_upload_file       browser_evaluate_script          │  │
│  │ browser_get_attribute     browser_go_back                  │  │
│  │ browser_tabs              browser_handle_dialog            │  │
│  │ browser_lock/unlock       browser_code_variable            │  │
│  │ browser_download_files    browser_custom_commands          │  │
│  │ browser_navigate_back/forward                              │  │
│  │ browser_screenshot        (别名)                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  2. 文件操作 (8 tools)                                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ view_file       — 查看文件内容                              │  │
│  │ view_files      — 批量查看文件                              │  │
│  │ view_folder     — 查看目录结构                              │  │
│  │ create_file     — 创建文件                                  │  │
│  │ delete_file     — 删除文件                                  │  │
│  │ edit_file_rewrite  — 重写编辑文件                           │  │
│  │ edit_file_rename   — 重命名文件                             │  │
│  │ edit_file_fast_apply — 快速应用编辑                          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  3. 代码搜索 (3 tools)                                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ search_by_reference — 引用搜索 (查找引用)                    │  │
│  │ search_by_regex     — 正则搜索                              │  │
│  │ search_by_definition — 定义搜索 (跳转到定义)                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  4. 命令执行 (3 tools)                                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ run_command        — 运行命令 (在终端/Sandbox 中)           │  │
│  │ check_command_status — 检查命令状态                        │  │
│  │ stop_command       — 停止命令                              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  5. 网络工具 (3 tools)                                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ web_search         — 网络搜索                               │  │
│  │ web_fetch          — 网页抓取                               │  │
│  │ open_preview       — 打开预览                               │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  6. LLM 配置 (2 tools)                                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ get_llm_config     — 获取 LLM 配置                          │  │
│  │ finetune_check     — 微调检查                               │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  7. 应用/完成 (3 tools)                                           │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ finish             — 完成/结束                              │  │
│  │ apply_diff         — 应用差异                               │  │
│  │ write_refactor_output — 重构输出写入                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  8. Supabase 工具 (2 tools, 集成扩展)                             │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ supabase_get_tables      — 获取 Supabase 表列表             │  │
│  │ supabase_apply_migration — 应用 Supabase 迁移               │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  9. MCP 工具 (动态)                                               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ mcpToolLimit: 40      — 最大 MCP 工具数                     │  │
│  │ mcpTokenLimit: 8000   — MCP Token 限制                      │  │
│  │ mcpToolHardCap        — 硬限制                              │  │
│  │ mcp_server_agent_relation  — 数据库表关联 Agent↔MCP         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  10. HTTP API 端点工具 (间接)                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ api/ide/v1/fast_apply         — 快速应用                    │  │
│  │ api/ide/v1/web_search         — 网络搜索 API                │  │
│  │ api/ide/v1/web_fetch          — 网页抓取 API                │  │
│  │ api/ide/v1/intent_detect      — 意图检测                    │  │
│  │ api/ide/v1/query_rewrite      — 查询重写                    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 工具调用链

```
LLM 生成 tool_use Block
  │
  ├─ ContentBlock: type="tool_use"
  │   ├─ id: "toolu_xxxx"
  │   ├─ name: "browser_navigate"
  │   └─ input: { url: "https://..." }
  │
  ├─ LLMClientToolCall 解析
  │   ├─ id: String
  │   ├─ type: "function"
  │   ├─ function.name: String
  │   └─ function.arguments: String (JSON)
  │
  ├─ domain/toolcall 工具执行
  │   ├─ 查找工具注册表
  │   ├─ 验证参数
  │   ├─ 安全检查 (ContentSecurity)
  │   ├─ 执行工具逻辑
  │   │   ├─ browser → Playwright-like API
  │   │   ├─ file → fs operations
  │   │   ├─ search → ripgrep / tree-sitter
  │   │   └─ web → HTTP fetch
  │   └─ 返回 ToolResult
  │
  ├─ ToolResult 格式化
  │   ├─ tool_use_id: "toolu_xxxx"
  │   └─ content: [{ type: "text", text: "..." }]
  │
  └─ 发送回 LLM 继续生成
```

### 4.3 工具注册表

```rust
// 伪代码：工具注册表结构
struct ToolRegistry {
    tools: HashMap<String, Box<dyn Tool>>,
    mcp_tools: HashMap<String, MCPTool>,
    limits: ToolLimits,
}

trait Tool {
    fn name(&self) -> &str;
    fn description(&self) -> &str;
    fn parameters(&self) -> JSONSchema;
    fn execute(&self, args: Value) -> Result<ToolResult>;
}

// 每个工具声明
struct ToolDeclaration {
    name: String,
    description: String,
    input_schema: JSONSchema,   // JSON Schema 格式
    output_schema: Option<JSONSchema>,
}
```

工具通过 JSON Schema 描述输入输出参数。LLM 被提供工具的 `name` + `description` + `input_schema` 来理解何时调用。

---

## 5. Agent V3 子代理系统

### 5.1 Agent 架构

```
domain/
├── agent_v3/              // Agent V3 (最新版本)
│   ├── service/
│   │   ├── git_ai_checkpoint.rs  — Git AI 检查点 (115 行)
│   │   └── ...
│   └── tools/
│       ├── web_fetch.rs          — 网络抓取工具
│       └── write_refactor_output.rs — 重构输出写入 (82 行)
│
├── agent_process_v3/      // Agent 流程 V3
│   └── solo/
│       ├── voice_summary/       — 语音总结 Agent
│       │   └── roles/voice_summary_agent.rs
│       └── voice_transcription/ — 语音转录 Agent
│           └── roles/voice_transcription_agent.rs
│
├── context_asset/
│   └── subagents/         // 子代理模块
│
└── agent/                 // Agent (旧版)
```

### 5.2 Agent V3 核心概念

**Agent 类型：**
- `plan` — 规划 Agent（拆解任务为步骤）
- `execute` — 执行 Agent（执行具体操作）
- `researcher` — 研究 Agent（搜索和信息收集）
- `writer` — 写作 Agent（生成内容）
- `coder` — 编码 Agent（代码编写）
- `reviewer` — 审查 Agent（代码审查）

**Agent 生命周期：**
```
CREATED → PLANNING → EXECUTING → REVIEWING → COMPLETED
                      ↓                         ↓
                  WAITING_FOR_TOOL           FAILED
                      ↓
                  TOOL_EXECUTING
```

**Agent 事件：**
```
AgentIdleEvent    — Agent 空闲（6 字段）
AgentResumeEvent  — Agent 恢复（6 字段）
AgentStatus       — Agent 状态（2 字段）
AgentStatusItem   — 状态项（3 字段）
```

### 5.3 子代理协调

```
                                ┌──────────────────┐
                                │  主 Agent (规划)  │
                                │  domain/agent_v3  │
                                └────────┬─────────┘
                                         │
                         ┌───────────────┼───────────────┐
                         │               │               │
                         ▼               ▼               ▼
                 ┌────────────┐  ┌────────────┐  ┌────────────┐
                 │ 研究子代理  │  │ 编码子代理  │  │ 审查子代理  │
                 │ subagents/ │  │ subagents/ │  │ subagents/ │
                 └────────────┘  └────────────┘  └────────────┘
                         │               │               │
                         ▼               ▼               ▼
                  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
                  │ context_asset│ │ tools/       │ │ content_secu │
                  │ (20+ 来源)  │ │ (50+ tools)  │ │ rity check  │
                  └──────────────┘ └──────────────┘ └──────────────┘
```

**协调流程：**
```
1. 主 Agent 接收用户请求
2. 分析并分解为子任务
3. 为每个子任务创建/调度子代理
4. 子代理并行执行 (使用 context_asset 收集上下文)
5. 子代理调用工具 (toolcall)
6. 安全检查 (content_security)
7. 收集子代理结果
8. 主 Agent 综合结果
9. 返回最终响应
```

### 5.4 Agent Context (43 字段)

```rust
struct AgentContext {
    // 43 个元素 — 完整的 IDE 状态快照
    // 分类:
    //   编辑器状态: 当前编辑器、选区、可见范围
    //   终端: 活跃终端、输出缓存、Shell 类型
    //   问题: 林特错误、构建错误、警告
    //   规则: 活跃规则文件、自定义指令
    //   文档: 打开的文档页
    //   网络: 浏览器元素、网络搜索结果
    //   工作区: 项目结构、文件列表
    //   用户交互: 对话历史、偏好
}
```

---

## 6. Content Security 安全系统

### 6.1 安全架构

```rust
domain/content_security/
└── service.rs            // 内容安全服务
```

### 6.2 安全特性

```
┌────────────────────────────────────────────────────┐
│               Content Security 系统                  │
├────────────────────────────────────────────────────┤
│                                                    │
│  1. 输出安全过滤                                     │
│     ├── content_security_blocked — 阻止的输出内容    │
│     ├── need_manual_confirm    — 需要手动确认        │
│     └── enterprise_command_blacklist — 企业命令黑名单│
│                                                    │
│  2. 命令执行控制                                     │
│     ├── Sandbox 执行 (trae-sandbox)                 │
│     ├── Command red list (禁止命令列表)              │
│     └── sandbox_rw_list / sandbox_ro_list           │
│                                                    │
│  3. MCP 工具安全                                    │
│     ├── MCPWhitelist (11 字段)                      │
│     │   ├── server_name: String                     │
│     │   └── allowed_tools: Vec<String>              │
│     └── MCPWhitelistConfigInfo (2 字段)             │
│         ├── enabled: bool                           │
│         └── ...                                     │
│                                                    │
│  4. Token 安全                                      │
│     ├── SQLCipher 数据库加密                        │
│     ├── alkali AES-256-GCM 参数加密                 │
│     └── 内存安全处理 (mlock)                        │
│                                                    │
│  5. 工具超时                                       │
│     └── toolConfirmTimeoutSecs: 30                  │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 6.3 安全事件

```
ICubeAIChatGlobalError   — 聊天全局错误
content_security_blocked — 内容安全阻止
need_manual_confirm      — 需要用户手动确认
```

---

## 7. 特征配置矩阵

### 7.1 AI 功能开关

```javascript
// 动态配置中的 AI 功能开关
{
    // MCP
    mcpToolLimit: 40,                    // MCP 工具数限制
    mcpTokenLimit: 8000,                 // MCP Token 限制
    mcpToolHardCap,                      // MCP 硬限制

    // 工具
    toolConfirmTimeoutSecs: 30,          // 工具确认超时
    maxConcurrentTools,                  // 最大并发工具数

    // 会话
    maxSessionDurationMs,               // 最大会话持续时间
    maxMessagesPerSession,               // 每会话最大消息数
    compactionThresholdRatio,           // 压缩阈值

    // 安全
    enable_ai_sandbox_awareness: boolean, // AI 沙箱感知
    encrypted_content_token_limit: number,

    // 多 Agent
    v2_multi_agent_read_enable: boolean,
    v2_multi_agent_read_model_config_name: string,
    v2_multi_agent_read_support_tools: string[],
    v2_multi_agent_read_agent_blacklist: string[],
    v2_multi_agent_read_handoff_tools_blacklist: string[],
    v2_multi_agent_read_history_skip_tools: string[],

    // Function Calling
    native_function_call: boolean,
    nfc_force_use_edit_file_update: boolean,
    parallel_tool_calling: boolean,
    nfc_use_original_tool_call_id: boolean,

    // Max Mode
    v2_max_mode_enabled: boolean,

    // 压缩
    v2_post_compress_enabled: boolean,
    v2_post_compress_compare_percent: number,

    // 截断
    v2_max_mention_file_context_truncation_type: string,
    v2_max_mention_file_context_truncation_size: number,

    // 历史版本
    v2_kept_history_message_count_limit: number,
    v2_multimodal_per_message_token_limit: number,
    v2_summary_message_token_limit: number,

    // 用户消息简化
    v2_user_message_simplify: boolean,

    // 模型
    v3_llm_message_use_separate_toolcall: boolean,

    // 技能
    builtin_skill_mapping: BuiltinSkillMapping,
    skill_as_agent: SkillAsAgentConfig,

    // 聊天记忆
    chat_memory_with_history: ChatMemoryWithHistoryConfig,
    memory_config: MemoryConfig,

    // 虚拟路径
    virtual_path: VirtualPathConfig,

    // SQLite
    sqlite_optimization: SqliteOptimizationPlatformConfig,
}
```

### 7.2 动态配置来源

```
dynamic-config-sdk (@byted-icube/dynamic-config-sdk)
  └── 从远端获取特征配置
  └── 缓存在本地 database.db
  └── 通过 api/ide/v1/ 同步
```

---

## 8. @byted-icube 模块依赖树

```
@byted-icube/ai-modules-chat
  ├── 文件: ../../modules/ai-chat/cdn
  ├── 功能: AI 聊天 UI / 会话管理 / 流式渲染
  └── 依赖: @aha-kit/rpc → @aha-kit/ipc

@byted-icube/desktop-modules
  ├── 文件: ../../modules/desktop/cdn
  ├── 功能: 桌面端特有功能 (窗口管理、菜单、通知)
  └── 子模块: worker/layout-engine.worker.js

@byted-icube/lite-modules
  ├── 文件: ../../modules/lite/cdn
  ├── 功能: Lite 模式 (VM 沙箱)
  └── 作用: 轻量级云端执行环境

@byted-icube/manager-sdk (0.0.0-alpha.20250402)
  ├── web/rpcclient.js (649KB) — Web RPC 客户端
  ├── node/rpcclient.js (649KB) — Node RPC 客户端
  ├── 功能:
  │   ├── RpcWebSocketClient — WebSocket RPC 客户端
  │   ├── ReconnectingWebSocketClient — 自动重连 WS 客户端
  │   ├── ExchangeConnector — Hub Bridge 连接器
  │   ├── PseudoWebSocket — EventStream → WebSocket 适配
  │   └── makeWebSocketRpcClient — 一站式 RPC 客户端创建
  └── 协议: msgpack 编码 + JSON-RPC

@byted-icube/trae-network-client
  ├── index.js — 网络客户端入口
  ├── fetch.js — HTTP Fetch 包装
  └── undici-dispatcher.js — Undici 调度器

@byted-icube/slardar
  ├── 功能: 事件监控和上报 (ICubeSlardarService)
  ├── events: icube_rust_error, icube_rust_warn
  └── 使用: Slardar.sendEvent({ name, categories })

@byted-icube/tea
  ├── 功能: 事件追踪 (GTM/TEA 集成)
  └── 文件: gtm-CO5U54xR.js, constant-BvzpCtnC.js

@byted-icube/env
  ├── 功能: 环境检测 (platform, language, locale)
  └── 文件: dist/index.js, dist/esm/index.js

@byted-icube/dynamic-config-sdk
  ├── 功能: 动态配置拉取和缓存
  └── 文件: dist/esm/node.js, dist/esm/index.js
```

---

## 9. 知识图谱 (CKG)

### 9.1 CKG 概述

```javascript
CKG = Code Knowledge Graph (代码知识图谱)
二进制: ckg_server 44MB
域模块: domain/understanding/ckg/
```

### 9.2 配置

```javascript
// BootConfig 中的配置
ckg: CKGConfig;

// 事件
icube_ai_start_ckg_server — CKG 服务器启动
```

### 9.3 功能

- 代码结构理解
- 符号索引
- 代码关系图
- 上下文感知

---

## 10. Scheduled Tasks 定时任务

Trae 支持类 Cron 的自主任务调度：

```
Scheduled Tasks 特性:
  ├── 基于时间触发的 AI 任务
  ├── 自动代码审查
  ├── 依赖检查更新
  ├── 知识图谱索引更新
  └── 缓存清理和维护
```

---

## 附录 A: 源码路径索引

```
# Electron 主进程
main.js (2.4MB) / split/default.js (61K 行)
├── out-build/vs/platform/environment/node/argv.js — CLI 参数解析
├── out-build/vs/code/electron-main/iCubeRustManager.js — Manager
└── out-build/vs/base/common/ — 通用基础库

# 扩展 (extensions/)
├── ai-completion/              — AI 代码补全
├── git-ai.git-ai-vscode/       — Git AI 代码追踪
├── trae.flux-helper/           — Flux 辅助
├── tunnel-forwarding/          — 隧道转发
├── theme-icube/                — Trae 主题
├── cloudide.icube-agent-shell-exec/ — Agent Shell
├── cloudide.icube-im-bridge/         — IM 桥接
├── cloudide.icube-remote-ssh/        — 远程 SSH
├── byted-icube.integrations-extended/— 集成扩展
├── byted-icube.java-helper/         — Java 辅助
├── byted-icube.python-enhance/      — Python 环境
├── byted-icube.go-enhance/          — Go 增强
└── byted-icube.node-helper/         — Node.js 辅助

# @byted-icube 模块 (node_modules/)
├── manager-sdk/web/rpcclient.js   — Manager SDK
├── slardar/                        — 监控
├── tea/                            — 事件追踪
├── trae-network-client/           — 网络客户端
├── dynamic-config-sdk/            — 动态配置
└── env/                            — 环境检测

# AHA 框架 (node_modules/)
├── @aha-kit/ipc/dist/             — IPC 层
├── @aha-kit/ipc-linux-x64/dist/   — IPC Linux 实现
├── @aha-kit/rpc/dist/index.js     — RPC 层
└── @aha-kit/zmq/                  — Rust ZMQ
```

---

## 附录 B: API 端点完整索引 (60+)

```
# Chat API
POST /api/ide/v1/agents/runs
POST /api/ide/v1/chat
POST /api/ide/v1/chat_prompt
POST /api/ide/v1/llm_raw_chat (v1/v2)
POST /api/ide/v1/llm_raw_chat_prompt
POST /api/ide/v1/connect

# Model API
POST /api/ide/v1/model_list
POST /api/ide/v1/model_list_by_function
POST /api/ide/v1/models
POST /api/ide/v1/add_custom_model
POST /api/ide/v1/update_custom_model
POST /api/ide/v1/get_custom_model_type_config
POST /api/ide/v1/providers

# Tool API
POST /api/ide/v1/web_search
POST /api/ide/v1/web_fetch
POST /api/ide/v1/fast_apply
POST /api/ide/v1/tools
POST /api/ide/v1/intent_detect
POST /api/ide/v1/query_rewrite
POST /api/ide/v1/context_select
POST /api/ide/v1/check_content

# Agent API
POST /api/ide/v1/agent/cancel_queue_task
POST /api/ide/v1/agent/jump_queue_task
POST /api/ide/v1/agent/get

# Image API
POST /api/ide/v1/text_to_image
POST /api/ide/v1/tool_text_to_image
POST /api/ide/v1/tool_text_to_image_stream

# Document RAG
POST /api/ide/v1/documentrag/retrieve
POST /api/ide/v1/wiki/get_wiki_content

# Misc
POST /api/ide/v1/feedback
POST /api/ide/v1/practice
POST /api/ide/v1/skill_recommend
POST /api/ide/v1/ping
POST /api/ide/v1/privacy
POST /api/ide/v1/report
POST /api/ide/v1/skill_recommend
POST /api/ide/v1/tenant
POST /api/ide/v1/user
```

---

> 本报告基于 main.js CLI 代码 + 扩展 package.json + ai-agent 反编译分析。
> 工具数量和配置参数以实际版本为准。