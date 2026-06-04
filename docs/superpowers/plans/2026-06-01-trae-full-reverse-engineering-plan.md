# Trae IDE 全面逆向分析 — 持续调研与执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`
> Steps use checkbox (`- [ ]`) syntax.

**Goal:** 每 5 分钟一轮，逐步全面逆向分析 Trae IDE 的所有通信协议、架构组件、流程机制、认证系统、工具系统、Agent 系统、MCP 协议等，输出完整的 Markdown 分析报告。每轮增量分析，逐步收敛到 100% 覆盖率。

**Architecture:**
- **数据流:** 每轮分析从 todo.md 读取当前进度 → 选择待分析领域 → 深入逆向该领域 → 输出增量报告 → 更新 todo.md → 设定 Cron 下一轮
- **关键组件:**
  - `todo.md` — 进度跟踪和上下文记录
  - `analysis/` — 增量分析报告输出目录
  - `scripts/` — 逆向脚本（已有 7 个 Python 脚本）
  - 目标文件: main.js, cli.js, ai-agent shared library, installers
- **设计理由:** 5 分钟一轮的短周期适合聚焦单个子领域，渐进式深入而非一次性大而全；每轮独立可验证

**Tech Stack:** Python 3.8+, Rust (ai-agent), Go (CLI), TypeScript/JavaScript (main.js), Electron 39.2.7, ZeroMQ, JSON-RPC 2.0, WebSocket, SQLCipher

**Scope:** Large — 9 大领域，每个领域 2-8 个子项
**Risk:** Low — 纯分析任务，无代码修改风险
**Risks:**
- 二进制分析工具缺失（strings/objdump/readelf）→ 缓解：先用 Python 基本分析
- 5 分钟时间窗口可能不足 → 缓解：拆分极小粒度子任务，完成多少算多少
- 网络端点可能不可达 → 缓解：先分析已有数据和代码，再尝试网络验证

**Autonomy Level:** Full — AI 自行完成所有分析轮次，每轮输出增量报告后自动安排下一轮

---

## 领域分解与轮次规划

### 总览：9 大领域，预计 20-30 轮完成

| 领域 | 子任务数 | 优先级 | 预计轮次 | 当前进度 |
|------|---------|--------|---------|---------|
| 1. main.js 架构 | 6 | P0 | 3-4 | 0% |
| 2. ai-agent 二进制 | 5 | P0 | 3-4 | 30% |
| 3. 认证系统 | 6 | P1 | 2-3 | 70% |
| 4. AI 通信协议 | 5 | P0 | 2-3 | 60% |
| 5. Frontier Hub Bridge | 5 | P1 | 2-3 | 20% |
| 6. Agent 系统 | 5 | P0 | 3-4 | 10% |
| 7. MCP 与工具系统 | 5 | P1 | 2-3 | 50% |
| 8. Custom Model Proxy | 5 | P2 | 2-3 | 30% |
| 9. CLI 分析 | 4 | P2 | 2-3 | 40% |

---

## 每轮执行模板

### 统一入口流程（每次 Cron 触发自动执行）

```
1. 读取 todo.md — 获取当前进度和上下文
2. 检查当前轮次是否有未完成子任务
   ├── 有 → 继续该子任务
   └── 无 → 选择下一个待分析领域（按优先级）
3. 执行分析（具体内容见各领域 Step）
4. 输出增量报告到 analysis/live/<domain>-<subtopic>.md
5. 更新 todo.md 进度
6. 创建 Cron 下一轮（5 分钟后）
7. 输出进度摘要
```

### 输出格式

每轮输出到 `analysis/live/` 目录，命名格式：`<轮次编号>-<领域>-<子主题>.md`

```markdown
# Trae 逆向分析 — 轮次 L{N}

**时间:** {datetime}
**领域:** {domain_name}
**子主题:** {subtopic}

---

## 关键发现

{具体发现}

## 代码/数据证据

{代码片段、二进制字符串、网络请求示例}

## 技术细节

{深入的技术分析}

## 待验证点

{下一步需要验证的内容}

## 本轮总结

{总结和下一步方向}
```

---

## 领域 1：main.js 架构全面分析 [P0]

### 调研清单
1. 模块加载机制 — main.js 的模块系统、Webpack 打包、懒加载
2. Handler 注册 — 所有 AI 相关 handler (chat/agent/model) 的注册方式和参数
3. IPC 通信桥 — main.js ↔ ai-agent 的 ZMQ/JSON-RPC 全流程
4. UI → Handler → IPC → Agent 的完整调用链
5. Electron 主进程事件循环
6. @byted-icube 模块依赖树

### 信息源
- `main.js/main.js` — 2.4MB Electron 主进程代码
- `main.js/split/` — 已拆分的代码模块
- `analysis/linux-x64-structure.md` — Linux 安装目录结构
- `data/ide/` — IDE 安装包

### 分析方法
```bash
# 分析 main.js 的 handler 注册模式
grep -c 'ipcMain.handle\|handler_\|Handler' main.js/main.js

# 列出所有导出的模块
grep -oP 'exports\.\w+' main.js/main.js | sort -u | head -50

# 查找 ZMQ/JSON-RPC 相关调用
grep -n 'zmq\|zeromq\|jsonrpc\|rpc\.stream' main.js/main.js | head -30
```

---

## 领域 2：ai-agent 二进制深入分析 [P0]

### 调研清单
1. DDD 模块架构 — Rust 领域驱动设计分层（handler/service/repository/infrastructure）
2. Handler 注册表 — 所有 RPC method 的注册点
3. 模型路由 — 模型选择器如何根据类型选择 provider
4. Prompt 模板系统 — KV 模板存储和渲染流程
5. AHA IPC JSON-RPC 全协议映射

### 信息源
- `ai-agent/ai-agent` — macOS ARM64 Mach-O 二进制
- `ai-agent/ai-agent分析报告.md` — 已有分析
- `data/download-manifest.json` — 安装清单
- `analysis/ai-agent-win32-strings.txt` — 1.4MB Windows 字符串提取

### 分析方法
```bash
# 从字符串文件中提取 RPC 方法
grep -E '^[a-z_]+::[a-z_]+$' analysis/ai-agent-win32-strings.txt | sort -u | head -100

# 提取所有 handler 注册
grep -oP 'handler_\w+|Handler\w+' analysis/ai-agent-win32-strings.txt | sort -u

# 查找 DDD 模块名
grep -E 'domain|infrastructure|adapter|repository' analysis/ai-agent-win32-strings.txt | sort -u
```

---

## 领域 3：认证系统完整解析 [P1]

### 调研清单
1. Supabase OAuth — 完整的 Supabase 认证流
2. 多 Scope 认证 — marscode/marscode_cn/bytedance/saas 的区别
3. BootConfig 交互 — 启动配置获取和处理
4. Token 层级和生命周期 — 完整的 token 链
5. SQLCipher 数据库完整结构
6. AWS SSO/OIDC 完整流程

### 信息源
- `scripts/auth_oauth2_pkce.py` — PKCE 认证
- `scripts/auth_bootconfig_jwt.py` — BootConfig JWT
- `scripts/auth_token_refresh.py` — Token 刷新
- `scripts/auth_frontier_ws.py` — Frontier WS
- `scripts/auth_aws_sso.py` — AWS SSO
- `analysis/oauth2-credentials.md` — OAuth2 凭证
- `analysis/product-json-analysis.md` — product.json 分析

### 分析方法
```bash
# 提取 OAuth 相关端点
grep -oP 'https?://[^"'\''<> ]+' scripts/auth_*.py | sort -u

# 分析 token 结构
python3 scripts/trae_token_extractor.py --help

# 验证 BootConfig 响应
curl -sk https://icube-boot.trae.ai | python3 -m json.tool 2>/dev/null || echo "BootConfig unreachable"
```

---

## 领域 4：AI 通信协议完整映射 [P0]

### 调研清单
1. 全消息类型枚举 — 所有可能的 sse.* / rpc.* 消息
2. 错误码映射 — 所有错误码含义（20324, 20101 等）
3. 重连/容错机制 — 完整的状态机和超时逻辑
4. 工具调用链 — MCP tool 调用和结果回传的全过程
5. SSE 事件格式完整规范

### 信息源
- `analysis/ai-protocol-analysis.md` — 271KB AI 协议深度分析
- `analysis/iteration-2-ipc-rpc-protocol-analysis.md` — IPC/RPC
- `analysis/iteration-3-ai-service-events-analysis.md` — 事件系统
- `analysis/iteration-4-tool-call-mcp-analysis.md` — MCP + Tool Call
- `analysis/trae-ai-proxy-deep-analysis.md` — 5.3KB 深度分析

### 分析方法
```bash
# 从 AI 协议分析中提取所有事件类型
grep -oP 'sse\.\w+|rpc\.\w+' analysis/ai-protocol-analysis.md | sort -u

# 提取所有错误码
grep -oP '\b[0-9]{4,5}\b' analysis/ai-protocol-analysis.md | sort -u

# 统计消息类型
grep -c 'sse\.' analysis/ai-protocol-analysis.md
```

---

## 领域 5：Frontier Hub Bridge 协议 [P1]

### 调研清单
1. 完整会话创建流程 — create_project → create_chat_session → send_message → subscribe
2. Lite Mode（沙箱） — VM 初始化和状态管理
3. Domain Handoff — 本地 ↔ 云端的会话迁移
4. CLI 注册/心跳 — cli 生命周期管理
5. WebSocket 隧道协议完整映射

### 信息源
- `scripts/auth_frontier_ws.py` — Frontier WS 客户端
- `scripts/trae_chat_client.py` — Chat 客户端
- `scripts/trae_chat_final.py` — Chat 最终版
- `ai-agent/API文档.md` — API 文档
- `data/cli/` — trae-cli 二进制

### 分析方法
```bash
# 提取 Frontier 消息类型
grep -oP 'WsProto\w+' scripts/auth_frontier_ws.py | sort -u

# 提取 Hub 端点
grep -oP 'hub\.[^"'\'' ]+' scripts/*.py | sort -u

# 分析 CLI 二进制命令
tar -tzf data/cli/trae-cli_0.120.35_linux_amd64.tar.gz | head -30
```

---

## 领域 6：Agent 系统与子代理 [P0]

### 调研清单
1. 子代理协调 — 多 Agent 任务分发和结果汇总
2. Termination 检测 — Agent 终止条件和生命周期
3. Plan/Execute 模式 — Agent 规划-执行分离的实现
4. 沙箱隔离 — trae-sandbox 与 Agent 的交互
5. Agent v3 架构 — tool call accumulator 实现

### 信息源
- `ai-agent/ai-agent分析报告.md` — 已有分析
- `analysis/iteration-4-tool-call-mcp-analysis.md` — 工具调用
- `analysis/comprehensive-report.md` — 综合报告
- `analysis/ai-agent-win32-strings.txt` — Windows 字符串

### 分析方法
```bash
# 提取 Agent 相关模块
grep -i 'agent_v\|ralph_loop\|sub_agent' analysis/ai-agent-win32-strings.txt | sort -u

# 查找 Agent session 端点
grep -oP '/api/ide/v1/agents/[^"'\'' ]+' analysis/*.md | sort -u
```

---

## 领域 7：MCP 与工具系统 [P1]

### 调研清单
1. 工具注册表 — 所有内置工具的注册和声明
2. 浏览器自动化 — 30+ browser 工具的触发和编排
3. 文件/Shell 工具 — 文件操作和命令执行的权限控制
4. Content Security — 输出安全过滤和手动确认机制
5. MCP 工具限制 — 40 tools max, 8000 tokens max

### 信息源
- `analysis/iteration-4-tool-call-mcp-analysis.md` — MCP
- `analysis/comprehensive-report.md` — 综合报告
- `analysis/ai-agent-win32-strings.txt` — 字符串
- `ai-agent/API文档.md` — API 文档

### 分析方法
```bash
# 提取所有工具名
grep -oP 'browser_\w+|toolcall_\w+' analysis/ai-agent-win32-strings.txt | sort -u

# 查找 MCP 相关
grep -i 'mcp_server\|mcp_tool\|mcp_safety' analysis/ai-agent-win32-strings.txt | sort -u
```

---

## 领域 8：Custom Model Proxy [P2]

### 调研清单
1. AWS Bedrock 集成 — Converse Stream API 适配
2. OpenRouter 集成 — 第三方模型路由
3. 自定义模型注册 — add_custom_model 流程
4. 负载均衡 — 多 provider 的请求分发
5. Volcengine Ark 集成

### 信息源
- `analysis/iteration-2-ipc-rpc-protocol-analysis.md` — 隧道协议
- `analysis/comprehensive-report.md` — Bedrock 集成
- `analysis/ai-protocol-analysis.md` — AI 协议
- `scripts/trae_chat_client.py` — 支持自定义模型

### 分析方法
```bash
# 提取 Bedrock/OpenRouter 引用
grep -i 'bedrock\|openrouter\|volcengine' analysis/ai-agent-win32-strings.txt | sort -u

# 查找 Tunnel 协议
grep -i 'tunnel\|custom_model' analysis/ai-agent-win32-strings.txt | sort -u
```

---

## 领域 9：CLI (trae-cli) 分析 [P2]

### 调研清单
1. CLI 命令集 — 完整的命令树
2. CLI ↔ Hub Bridge 交互 — cli 如何通过 Hub 通信
3. Dev Mode — 开发者模式的完整功能
4. CLI 安装和更新机制

### 信息源
- `data/cli/` — trae-cli v0.120.35 二进制
- `analysis/iteration-1-cli-llm-proxy-analysis.md` — CLI 代理
- `cli.js/cli.js` — IDE CLI 模块
- `cli.js/split-modules.js` — CLI 拆分模块

### 分析方法
```bash
# 提取 CLI 命令
strings data/cli/trae-cli_0.120.35_linux_amd64/trae-cli 2>/dev/null | grep -E '^[a-z-]+$' | sort -u | head -50
```

---

## 每轮执行协议

### Step 1: 加载上下文
Read `todo.md` → Read 上一轮输出 → 确定本轮分析子任务

### Step 2: 执行分析
```
根据子任务类型选择分析方法：
- 代码分析 → grep/strings/read 目标文件
- 网络验证 → curl/wscat 测试端点
- 协议分析 → 对比已知模式推断
- 脚本执行 → python3 scripts/xxx.py --test
```

### Step 3: 记录发现
Write `analysis/live/L<轮次编号>-<领域>.md`

### Step 4: 更新进度
Append to todo.md:
- 标记完成的子项
- 记录新发现的待分析点
- 更新轮次计数

### Step 5: 安排下一轮
```bash
# 通过 Cron 系统设置 5 分钟后下一轮
# 使用 prompt 重新进入此计划
```

### Step 6: 输出轮次摘要
```markdown
## 轮次 L{N} 摘要

**完成:** {子任务名}
**时长:** ~5 分钟
**产出:** `analysis/live/L{N}-{domain}.md`
**关键发现:** {1-3 个最重要的发现}
**未完成:** {记录没做完的原因和剩余工作}
**下一轮:** 领域 {X} — {子任务}
```

---

## 验证方法

每轮完成后的验证标准：

| 维度 | 标准 |
|------|------|
| **分析深度** | 每轮至少发现 3 个新的技术细节 |
| **证据要求** | 每个发现必须有代码/字符串/网络请求证据 |
| **文档质量** | 输出文件必须有结构化 Markdown 格式 |
| **进度更新** | todo.md 更新及时，无遗漏 |
| **可复现性** | 所有分析方法必须有具体命令或脚本 |

---

## 输出目录约定

```
analysis/live/          # 每轮增量输出
analysis/               # 已有综合报告
scripts/                # 逆向脚本
todo.md                 # 进度追踪（每轮更新）
docs/superpowers/plans/ # 计划文件
```

> **重要:** analysis/live/ 目录存放每轮的增量分析，analysis/ 目录存放综合汇总。
> 每 5 轮将 analysis/live/ 的内容合并到 analysis/ 的综合报告。
