# Trae AI Communication Protocol Reverse Engineering Plan

**Goal:** Reverse engineer Trae's AI communication protocol and authentication system to enable proxying Trae's AI capabilities for use with Codex.

**Architecture:** Analyze extracted Trae IDE binaries → Map IPC/RPC protocol → Document API endpoints → Extract authentication flow → Build protocol specification for proxy implementation.

**Tech Stack:** Binary analysis (strings, nm, objdump), JavaScript deobfuscation, Protocol analysis (JSON-RPC, WebSocket, SSE), Network traffic analysis

**Scope:** Large
**Risk:** Medium (read-only analysis, but involves reverse engineering proprietary protocols)

**Risks:**
- Protocol obfuscation may hide critical details → use multiple analysis techniques
- Authentication tokens may be encrypted → focus on protocol structure first
- WebSocket/SSE protocols may use custom framing → analyze packet structure
- API endpoints may change between versions → document version-specific details

**Autonomy Level:** Full

---

## Type Detection

**Plan Type:** Research
**Scope:** Large
**Risk:** Medium
**Detection Reason:** User requested continuous reverse engineering analysis of AI communication protocols, which is a research/investigation task focused on understanding existing systems.

→ Routing to Phase 1 (Research) branch...

---

## Phase 1: PRE-PLANNING (Research Branch)

### Research调研清单

1. **定义调研问题** — 明确要回答什么问题:
   - Trae IDE如何与ai-agent通信？
   - AI模型调用的完整协议栈是什么？
   - 用户认证和token管理机制是什么？
   - 如何代理这些AI能力给Codex使用？

2. **搜索现有方案** — 已有分析结果:
   - 已有comprehensive-report.md包含架构概览
   - 已有ai-agent-win32-strings.txt包含关键字符串
   - 已有product.json包含API端点配置
   - 已有IPC/RPC代码分析

3. **评估技术选型** — 分析方法:
   - 字符串分析：提取API端点、方法名、数据结构
   - 代码分析：理解协议实现逻辑
   - 网络分析：抓包验证实际通信
   - 协议逆向：重建完整通信流程

4. **检查项目约束** — 已有资源:
   - 已提取的IDE文件在data/ide/linux-arm64/extracted/
   - 已有ai-agent二进制字符串分析
   - 已有product.json配置分析
   - 已有IPC/RPC代码分析

5. **记录信息源** — 每个结论必须有出处:
   - 字符串分析结果：analysis/ai-agent-win32-strings.txt
   - 配置文件：data/ide/linux-arm64/extracted/resources/app/product.json
   - 代码分析：node_modules/@aha-kit/rpc/dist/index.js
   - 已有报告：analysis/comprehensive-report.md

6. **识别知识缺口** — 还需要验证什么:
   - 实际网络通信抓包验证
   - 认证token格式和加密方式
   - 完整的API调用流程
   - 错误处理和重试机制

---

## Phase 2: CREATE PLAN (Research Template)

### Research Plan Header

# Trae AI Protocol Reverse Engineering Research Plan

**Question:** What is the complete AI communication protocol and authentication system used by Trae IDE, and how can it be proxied for Codex integration?

**Context:** Trae IDE v2.3.30128 uses a complex AI system with multiple providers (OpenAI, Anthropic, Google, DeepSeek, AWS Bedrock, Volcengine). Understanding this protocol is essential for building a proxy that allows Codex to use Trae's AI capabilities.

**Deliverable:** Comprehensive protocol specification document with:
- Complete communication flow diagrams
- API endpoint specifications
- Authentication token formats
- Data structure definitions
- Error handling procedures
- Proxy implementation guidelines

**Time Box:** Continuous analysis (5-minute intervals)

---

## Phase 2: CREATE PLAN (Research Steps)

### Task 1: IPC/RPC Protocol Analysis

**Depends on:** None
**Files:**
- Analyze: `data/ide/linux-arm64/extracted/resources/app/node_modules/@aha-kit/rpc/dist/index.js`
- Analyze: `data/ide/linux-arm64/extracted/resources/app/node_modules/@aha-kit/ipc-linux-arm64/dist/client.js`
- Analyze: `analysis/ai-agent-win32-strings.txt`

- [ ] **Step 1: 分析JSON-RPC消息结构**

从ai-agent字符串中提取JSON-RPC消息格式：
```
JsonRpcMessagestruct JsonRpcMessageJsonRpcResponseJsonRpcErrorstruct HttpRequeststruct SseOpenParamsstruct SseOpenPayloadstruct SseCancelParamsstruct RpcCloseParamsSseDeltaParamsseqSseEndParamslast_seqSseErrorParamsSseErrorData
```

关键发现：
- 使用JSON-RPC 2.0协议
- 支持SSE (Server-Sent Events)流式响应
- 有SseOpen/SseDelta/SseEnd/SseError事件类型
- 支持RpcClose/RpcPing控制消息

- [ ] **Step 2: 分析WebSocket通信协议**

从字符串中提取WebSocket协议细节：
```
[CustomModelProxy] WebSocket connect failed: , falling back to HTTP mode
WebSocketConnectionConfig is required
[AI Agent Server] start unified transport server (HTTP + WebSocket)
[UnifiedTransport] WebSocket connection established
[UnifiedTransport] WebSocket connection closed
```

关键发现：
- 支持HTTP和WebSocket双传输模式
- WebSocket用于实时通信，HTTP作为回退
- 有连接管理和重连机制
- 支持二进制和文本消息

- [ ] **Step 3: 分析Hub Bridge服务通信**

从字符串中提取Hub Bridge通信协议：
```
[HubNetService] HTTP flush, messages from=
[HubNetService] WS connect failed (attempt
[HubNetService] WS connected, replaying  remaining messages
[HubNetService] WS closed by remote
[HubNetService] WS recv, down_seq=, proto=
```

关键发现：
- Hub Bridge是主要的远程通信服务
- 支持HTTP轮询和WebSocket推送
- 有消息序列号和确认机制
- 支持消息重放和重连

- [ ] **Step 4: 验证IPC通信机制**

分析@aha-kit/ipc模块：
```javascript
// 从client.js分析
class AhaIpcConnectionImpl extends EventEmitter {
    #serverName = '';
    #serverId = ''; // set by server
    #routingId = crypto.randomUUID();
    #socket = null;
    #ipcAddress = '';
    // ...
}
```

关键发现：
- 使用ZeroMQ (ZMQ)进行进程间通信
- 支持Dealer-Router模式
- 有心跳检测和活性管理
- 使用UUID作为路由标识

- [ ] **Step 5: 文档化IPC/RPC协议规范**

创建协议规范文档，包含：
- 消息格式定义
- 传输层协议
- 连接管理
- 错误处理

---

### Task 2: AI API端点分析

**Depends on:** Task 1
**Files:**
- Analyze: `data/ide/linux-arm64/extracted/resources/app/product.json`
- Analyze: `analysis/ai-agent-win32-strings.txt`

- [ ] **Step 1: 提取API端点配置**

从product.json提取API端点：
```json
{
  "icube-normal.trae.ai": "AI backend API",
  "core-normal.trae.ai": "Core API",
  "coresg-normal.trae.ai": "Singapore region API",
  "api-us-east.trae.ai": "US East region API",
  "icube-boot.trae.ai": "Boot API",
  "mcs-boot.trae.ai": "MCS Boot API"
}
```

关键发现：
- 多区域部署（新加坡、美国、中国）
- 有专门的boot API用于初始化
- 有MCS (Model Config Service)服务
- 有CDN和静态资源服务

- [ ] **Step 2: 分析AI模型调用API**

从字符串中提取AI模型调用方法：
```
model_list_by_function
update_custom_model
add_custom_model
get_model_selection_mode
prefetch_for_auto
```

关键发现：
- 支持按功能获取模型列表
- 支持自定义模型配置
- 有模型预取机制
- 支持自动模型选择

- [ ] **Step 3: 分析聊天会话API**

从字符串中提取聊天会话管理API：
```
create_chat_session
send_message
stop_chat_session
commit_chat_session
delete_chat_session
get_chat_session
list_chat_sessions
```

关键发现：
- 完整的会话生命周期管理
- 支持消息发送和流式响应
- 有会话提交和冻结机制
- 支持会话列表和查询

- [ ] **Step 4: 分析工具调用API**

从字符串中提取工具调用相关API：
```
toolcall_agent_finish
toolcall_response_to_user
toolcall_ask_user_question
toolcall_notify_user
toolcall_run_command
toolcall_view_file
toolcall_edit_file
```

关键发现：
- 丰富的工具调用系统
- 支持文件操作、命令执行、用户交互
- 有工具结果持久化
- 支持自定义工具

- [ ] **Step 5: 文档化API规范**

创建API规范文档，包含：
- 端点URL列表
- 请求/响应格式
- 认证要求
- 错误码定义

---

### Task 3: 认证系统分析

**Depends on:** Task 2
**Files:**
- Analyze: `data/ide/linux-arm64/extracted/resources/app/product.json`
- Analyze: `analysis/ai-agent-win32-strings.txt`

- [ ] **Step 1: 分析认证配置**

从product.json提取认证配置：
```json
{
  "authProviderId": "icube.cloudide",
  "authProviderLabel": "Trae IDE",
  "authDomain": "www.trae.ai",
  "authFrom": "trae"
}
```

关键发现：
- 使用icube.cloudide作为认证提供者
- 认证域名为www.trae.ai
- 支持多种认证方式

- [ ] **Step 2: 分析JWT Token机制**

从字符串中提取JWT相关字符串：
```
ReturnToLocalJwtStrategy
jwt_strategy.jwt_token is required for external strategy
JWT sign
JWT access & refresh tokens
```

关键发现：
- 使用JWT (JSON Web Token)进行认证
- 支持access token和refresh token
- 有JWT签名验证
- 支持外部JWT策略

- [ ] **Step 3: 分析BootConfig认证流程**

从字符串中提取BootConfig认证流程：
```
struct BootUserInfo
expiredAt
refreshExpiredAt
userId
tokenReleaseAt
tokenHost
token_host
```

关键发现：
- BootConfig包含用户认证信息
- 有token过期时间管理
- 有专门的token host服务
- 支持token刷新机制

- [ ] **Step 4: 分析OAuth/SSO集成**

从字符串中提取OAuth/SSO相关：
```
OAuthController
/api/oauth/*
POST /api/oauth/authorize
OAuth2 authorization code flow
Supports Google, GitHub, GitLab providers
Enterprise SSO Integration
```

关键发现：
- 支持OAuth2授权码流程
- 支持Google、GitHub、GitLab第三方登录
- 有企业SSO集成
- 有JWT中间件验证

- [ ] **Step 5: 文档化认证流程**

创建认证流程文档，包含：
- 完整认证流程图
- Token格式和生命周期
- 刷新机制
- 错误处理

---

### Task 4: 数据结构分析

**Depends on:** Task 3
**Files:**
- Analyze: `analysis/ai-agent-win32-strings.txt`

- [ ] **Step 1: 分析聊天消息结构**

从字符串中提取聊天消息相关结构：
```
struct ChatMultiMedia with 2 elements
ChatDoneEventPayload
HeartbeatEventPayload
UserMessageEventPayload
SessionTitleEventPayload
ModelConfigEventPayload
```

关键发现：
- 支持多媒体消息
- 有丰富的事件类型
- 支持会话标题和图标
- 有模型配置事件

- [ ] **Step 2: 分析模型配置结构**

从字符串中提取模型配置结构：
```
struct ModelExtraConfig with 142 elements
ModelDetailConfig
Temperature
PromptMaxTokens
CkgPromptMaxTokens
TopP
TopK
MinNewTokens
RepetitionPenalty
EnabledModels
```

关键发现：
- 详细的模型配置参数
- 支持温度、top-p、top-k等参数
- 有专门的CKG提示配置
- 支持多模型启用配置

- [ ] **Step 3: 分析工具调用结构**

从字符串中提取工具调用结构：
```
struct ToolCallEvent with 11 elements
struct LLMClientToolcallItem with 4 elements
struct RawLLMResponseToolCall with 3 elements
struct OutputEventToolCall with 4 elements
```

关键发现：
- 详细的工具调用事件结构
- 支持工具调用结果追踪
- 有工具调用错误处理
- 支持工具调用持久化

- [ ] **Step 4: 分析渲染变量结构**

从字符串中提取渲染变量结构：
```
struct RenderVariables
enable_parallel_tool_calling
is_in_chat_mode
is_in_plan_v2
response_can_be_text
left_turns
text_to_image_url
enable_multi_agent_reader
sub_agents
user_auto_run_prompt
is_use_npm_mirror
language_settings
actived_environments
supported_environments
```

关键发现：
- 丰富的渲染变量控制
- 支持多代理阅读
- 支持并行工具调用
- 有环境配置管理

- [ ] **Step 5: 文档化数据结构**

创建数据结构文档，包含：
- 完整结构定义
- 字段说明
- 使用示例
- 版本兼容性

---

### Task 5: 代理实现方案设计

**Depends on:** Task 4
**Files:**
- Create: `docs/superpowers/plans/2026-05-28-trae-ai-proxy-implementation.md`

- [ ] **Step 1: 设计代理架构**

基于逆向分析结果，设计代理架构：
```
Codex Client → Trae AI Proxy → Trae AI Backend
     ↓              ↓              ↓
  AI请求      协议转换      原始AI服务
     ↓              ↓              ↓
  AI响应      响应转换      流式响应
```

关键组件：
- 协议转换层：将Codex请求转换为Trae协议
- 认证管理：处理token获取和刷新
- 流式处理：处理SSE流式响应
- 错误处理：处理各种错误情况

- [ ] **Step 2: 设计协议转换方案**

设计请求/响应转换方案：
- 请求格式转换
- 参数映射
- 流式响应处理
- 错误码映射

- [ ] **Step 3: 设计认证代理方案**

设计认证代理方案：
- Token获取流程
- Token刷新机制
- 多用户支持
- 安全存储

- [ ] **Step 4: 设计错误处理方案**

设计错误处理方案：
- 网络错误处理
- 认证错误处理
- 限流处理
- 重试机制

- [ ] **Step 5: 创建实现指南**

创建详细实现指南：
- 技术栈选择
- 代码结构设计
- 部署方案
- 测试策略

---

## Phase 3: SELF-REVIEW

### Research 专属检查清单（+6 项，共 12 项）

1. [ ] 调研问题定义清晰（要回答什么、不回答什么）？
2. [ ] 信息源 ≥2 个且出处明确（URL/文档名/版本）？
3. [ ] 结论有数据支撑（不是"感觉"）？
4. [ ] 包含明确的行动建议（"下一步做什么"）？
5. [ ] 如果方案不可行，有替代方案和原因说明？
6. [ ] 输出格式是结构化文档（不是松散的笔记）？

### 公共检查清单（所有类型，共 8 项）

1. [ ] Header 包含 Goal + Plan Type + Scope + Risk？
2. [ ] 每个 Task 标注了 Depends on？
3. [ ] 每个 Task 有 3-8 个 Step？
4. [ ] 无 TBD/TODO/模糊描述？
5. [ ] 跨 Task 的函数签名、类型名、属性名一致？（Research 类型跳过）
6. [ ] 文件保存位置正确（docs/superpowers/plans/）？
7. [ ] 每个 Task 包含质量门禁 Step（编译 + 测试 + 回归 + 整洁 + 集成）？（Research 类型跳过）
8. [ ] Plan 中的代码未命中交付反模式清单中的任何反模式？（Research 类型跳过）

---

## Phase 4: EXECUTION SELECTION

### 分析任务特征

```
分析要点：
1. 总共有多少个任务？5个主要任务
2. 任务间是否有顺序依赖？是，按顺序执行
3. 用户是否明确要求 inline 执行？否，要求每5分钟分析一次
```

### 自动选择执行方式

| Condition | Selection |
|-----------|-----------|
| 3+ tasks | **Subagent-Driven** |
| < 3 tasks + user said inline | **Inline** |
| < 3 tasks + no preference | **Subagent-Driven** |
| Uncertain | **Subagent-Driven** |

## Execution Selection

**Tasks:** 5
**Dependencies:** yes
**User Preference:** continuous analysis (5-minute intervals)
**Decision:** Subagent-Driven
**Reasoning:** 5 tasks with dependencies, user requested continuous analysis

**Auto-invoking:** `superpowers:subagent-driven-development`

---

## 持续分析计划

### 每5分钟分析任务

1. **字符串分析** - 提取新的API端点和方法
2. **协议分析** - 理解通信流程和数据格式
3. **认证分析** - 追踪token生命周期
4. **工具分析** - 识别可用工具和调用方式
5. **文档更新** - 记录新发现和更新规范

### 分析优先级

1. **高优先级** - 认证流程和token管理
2. **中优先级** - AI模型调用协议
3. **低优先级** - 辅助功能和工具调用

### 预期输出

1. **协议规范文档** - 完整的通信协议说明
2. **API参考手册** - 所有端点和方法的详细说明
3. **认证流程图** - 可视化的认证流程
4. **实现指南** - 代理实现的详细步骤
5. **测试用例** - 验证协议正确性的测试

---

## Self-Check (superpowers-guard)

Phase 2 完成后，验证输出格式：

```bash
echo "$OUTPUT" | npx superpowers-guard check --format json
```

**如果 `valid: false`，根据 `reason_codes` 修正。自检不通过时必须重做。**

---

## Hard Rules（铁律）

1. **永不向用户提问** — 不确定就自己读代码库
2. **Complete content only** — 每步包含具体发现和出处
3. **Exact paths only** — 精确文件路径 + 行号，无占位符
4. **每 Task 3-8 Steps** — 太粗拆细，太细合并
5. **每 Step 一个原子操作** — 搜索/分析/综合/输出
6. **验证三要素** — 命令 + exit code + output pattern
7. **标注依赖** — 每个 Task 写明 Depends on
8. **No placeholders** — Plan 中出现 TBD = 不合格
9. **Invoke immediately** — Phase 4 结束后自动调用下一个 skill
10. **篇幅合理** — 整个 Plan 1500-6000 字，过短或过长都要调整
11. **类型匹配** — Phase 0 检测的类型必须与 Phase 2 使用的模板一致
12. **Research 有出处** — 每个结论至少有 2 个独立信息源
13. **自主持续性** — AI 必须持续工作直到 Plan 中所有 Task 完成，中间不因 Level 1-2 问题停下来
14. **自愈优先** — 遇到问题先自行修复（最多 3 次），不第一次失败就通知用户
15. **验收自检** — 每个 Task 完成后 AI 自行运行完整验证，确保交付质量
16. **迭代修复** — 分析失败不是终点，是重新分析的起点；分析 → 验证 → 再分析，最多 3 轮
17. **检查点非确认点** — Phase 3 自检是 AI 自行完成的检查点，不是等用户确认的确认点
18. **交付即验收** — 每个 Task 的提交意味着 AI 已自行验证过：分析完整、结论有据、文档清晰
19. **质量门禁不可跳过** — 每个 Task 必须通过全部门禁才能提交，不允许"先提交再验证"
20. **范围不蔓延** — 严格执行 Plan 中的 Task/Step，发现额外工作记录为新 Task，不混入当前 Task

---

## Plan 可读性格式规范

Plan 是写给执行者（AI 或人）看的，排版质量直接影响执行成功率。

### 空行规则

| 位置 | 要求 | 示例 |
|------|------|------|
| Task 之间 | 至少 1 个 `---` 分隔线 + 2 行空行 | 见 Task Structure 模板 |
| Step 之间 | 2 行空行 | 每个 Step 之间留 2 空行 |
| 代码块前后 | 各 1 行空行 | 代码块上方空 1 行，下方空 1 行 |
| 代码块内注释 | 不空行 | 代码块内部保持紧凑 |

### 缩进规则

| 元素 | 缩进 | 说明 |
|------|------|------|
| Task 标题 | 0 | `### Task N:` 顶格 |
| Step 标题 | 0 | `- [ ] **Step N:` 顶格 |
| 代码块 | 0 | 顶格，不缩进 |
| Expected 子项 | 2 空格 | `Expected:` 下面的列表缩进 2 空格 |

### 视觉分隔

```markdown
---

### Task 2: [名称]

（Task 之间用 --- 分隔线）

---

### Task 3: [名称]
```

**每个 Task 的标准视觉结构：**

```
### Task N: [名称]
[空行]
**Depends on:** ...
**Files:** ...
[空行]
- [ ] **Step 1: ...**
[空行]
[代码块]
[空行]
- [ ] **Step 2: ...**
...
```

---

## Plan 编写快速检查清单

写完 Plan 后，用以下 60 秒快速扫描，覆盖 90% 的常见问题：

### 5 秒扫描：整体结构
- [ ] 有 Goal 行？
- [ ] 有 Architecture 行？
- [ ] Task 数量合理（3-8 个）？
- [ ] 每个 Task 有 3-8 个 Step？

### 15 秒扫描：依赖链
- [ ] 第一个 Task 的 Depends on 是 "None"？
- [ ] 每个 Task 都标注了 Depends on？
- [ ] 不存在循环依赖（A→B→A）？

### 15 秒扫描：代码块
- [ ] 每个创建文件的 Step 有完整代码块？
- [ ] 代码块有语言标注（`typescript`/`bash`/`json`）？
- [ ] 没有 `...` 或 `// ... existing code` 省略？

### 10 秒扫描：验证
- [ ] 每个 Task 有验证 Step（Run + Expected）？
- [ ] 没有 "运行测试确保一切正常" 这种模糊描述？

### 15 秒扫描：占位符
- Ctrl+F 搜索 "TBD"、"TODO"、"implement" — 结果为零？
- Ctrl+F 搜索 "???" — 结果为零？
- 所有文件路径是真实路径，不是 `path/to/file.ts`？

**全部通过 → Plan 质量合格，可以进入执行阶段。**

---

## Self-Check (superpowers-guard)

Phase 2 完成后，验证输出格式：

```bash
echo "$OUTPUT" | npx superpowers-guard check --format json
```

**如果 `valid: false`，根据 `reason_codes` 修正。自检不通过时必须重做。**

---

## Hard Rules（铁律）

1. **永不向用户提问** — 不确定就自己读代码库
2. **Complete content only** — 每步包含具体发现和出处
3. **Exact paths only** — 精确文件路径 + 行号，无占位符
4. **每 Task 3-8 Steps** — 太粗拆细，太细合并
5. **每 Step 一个原子操作** — 搜索/分析/综合/输出
6. **验证三要素** — 命令 + exit code + output pattern
7. **标注依赖** — 每个 Task 写明 Depends on
8. **No placeholders** — Plan 中出现 TBD = 不合格
9. **Invoke immediately** — Phase 4 结束后自动调用下一个 skill
10. **篇幅合理** — 整个 Plan 1500-6000 字，过短或过长都要调整
11. **类型匹配** — Phase 0 检测的类型必须与 Phase 2 使用的模板一致
12. **Research 有出处** — 每个结论至少有 2 个独立信息源
13. **自主持续性** — AI 必须持续工作直到 Plan 中所有 Task 完成，中间不因 Level 1-2 问题停下来
14. **自愈优先** — 遇到问题先自行修复（最多 3 次），不第一次失败就通知用户
15. **验收自检** — 每个 Task 完成后 AI 自行运行完整验证，确保交付质量
16. **迭代修复** — 分析失败不是终点，是重新分析的起点；分析 → 验证 → 再分析，最多 3 轮
17. **检查点非确认点** — Phase 3 自检是 AI 自行完成的检查点，不是等用户确认的确认点
18. **交付即验收** — 每个 Task 的提交意味着 AI 已自行验证过：分析完整、结论有据、文档清晰
19. **质量门禁不可跳过** — 每个 Task 必须通过全部门禁才能提交，不允许"先提交再验证"
20. **范围不蔓延** — 严格执行 Plan 中的 Task/Step，发现额外工作记录为新 Task，不混入当前 Task
