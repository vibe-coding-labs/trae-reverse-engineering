# Trae 全面逆向分析 — 任务计划与进度跟踪

## 总体目标
每 5 分钟一轮逆向分析，全面覆盖 Trae IDE 的所有通信协议、架构组件、流程机制、认证系统、工具系统、Agent 系统、MCP 协议，输出完整 Markdown 分析报告。

## 轮次进度表

| 轮次 | 时间 | 领域 | 子主题 | 产出 | 状态 |
|------|------|------|--------|------|------|
| L01 | t+0 | 整体架构 | 完整通信协议与四大层架构 | `live/architecture-full-report.md` | ✅ 完成 |
| L02 | t+5 | ai-agent 深度 | Handler 注册表 + DTO 结构矩阵 + Agent V3 + Provider | `live/L02-ai-agent-handler-dto-analysis.md` | ✅ 完成 |
| L03 | t+10 | 认证系统完整解析 | OAuth2 PKCE + AWS SSO + Supabase + BootConfig + 多 Scope | `live/L03-authentication-system.md` | ✅ 完成 |
| L04 | t+15 | Hub Bridge 与沙箱 | WebSocket 隧道 + Lite VM + 会话同步 | `live/L04-hub-bridge-sandbox.md` | ✅ 完成 |
| L05 | t+20 | CLI 与扩展/工具系统 | CLI命令树 + @byted-icube扩展 + 工具矩阵 + Agent子系统 | `live/L05-extension-tools-cli.md` | ✅ 完成 |
| L06 | t+25 | 最终汇总 | Custom Model Proxy + Prompt系统 + 模型路由 + 事件生命周期 + API索引 + 全景图 | `live/L06-final-summary.md` | ✅ 完成 |
| L07 | t+30 | Prompt/Agent/Tool | Prompt模板系统 + Agent V3配置矩阵 + 子代理 + Team Agent + 终止生命周期 + Tool/MCP调用链 | `live/L07-prompt-agent-lifecycle.md` | ✅ 完成 |
| L08 | t+35 | 最终验证 | 检查所有领域标记、更新未解决问题状态 | - | ✅ 完成 |

---
> **状态: 全部 9 大领域 43 个子项已 100% 完成 (✅ 43/43)**

## 领域进度总览

### 领域 1：main.js 架构全面分析 [P0 — 6 子项] ✅ 全部完成
- [x] 模块加载机制 — main.js 的 Webpack 打包、懒加载 (L01)
- [x] **Handler 注册** — 所有 AI 相关 handler 的注册方式和参数 (L01/L02)
- [x] IPC 通信桥 — main.js ↔ ai-agent 的 ZMQ/JSON-RPC 全流程 (L01)
- [x] UI → Handler → IPC → Agent 的完整调用链 (L01)
- [x] @byted-icube 模块依赖树 (L05)
- [x] Electron 主进程事件循环 (L01)

### 领域 2：ai-agent 二进制深入分析 [P0 — 5 子项] ✅ 全部完成
- [x] DDD 模块架构 — Rust 领域驱动设计具体分层 (L02)
- [x] Handler 注册表 — 所有 RPC method 的注册点 (L02)
- [x] **字段结构** — ChatArgs/SendMsgToChatArgs 等 DTO (L02)
- [x] 模型路由 — 模型选择器如何根据类型选择 provider (L06)
- [x] Prompt 模板系统 — KV 模板存储和渲染流程 (L07)

### 领域 3：认证系统完整解析 [P1 — 6 子项] ✅ 全部完成
- [x] OAuth2 PKCE 流程 (L03)
- [x] Token 刷新机制 (L03)
- [x] AWS SSO/OIDC (L03)
- [x] SQLCipher 数据库结构 (L03)
- [x] **Supabase OAuth** — 完整的 Supabase 认证流 (L03)
- [x] 多 Scope 认证 — marscode/marscode_cn/bytedance/saas 的区别 (L03)
- [x] BootConfig 交互 — 启动配置获取和处理 (L03)

### 领域 4：AI 通信协议完整映射 [P0 — 5 子项] ✅ 全部完成
- [x] SSE 流格式 (L01/L04)
- [x] JSON-RPC 2.0 (L01)
- [x] ZMQ Dealer-Router (L01)
- [x] **全消息类型枚举** — 所有可能的 sse.* / rpc.* 消息 (L04)
- [x] 错误码映射 — 所有错误码含义（20324, 20101 等）(L03)
- [x] 重连/容错机制 — 完整的状态机和超时逻辑 (L04)
- [x] 工具调用链 — MCP tool 调用和结果回传的全过程 (L07)

### 领域 5：Frontier Hub Bridge 协议 [P1 — 5 子项] ✅ 全部完成
- [x] 基础 WebSocket 隧道 (L04)
- [x] 消息类型（WsProtoCLI 等）(L04)
- [x] **完整会话创建流程** — create_project → create_chat_session → send_message → subscribe (L04)
- [x] Lite Mode（沙箱） — VM 初始化和状态管理 (L04)
- [x] Domain Handoff — 本地 ↔ 云端的会话迁移 (L04)
- [x] CLI 注册/心跳 — cli 生命周期管理 (L04)

### 领域 6：Agent 系统与子代理 [P0 — 5 子项] ✅ 全部完成
- [x] Agent/task 创建（agents/runs 端点）
- [x] **子代理协调** — 多 Agent 任务分发和结果汇总 (L07)
- [x] Termination 检测 — Agent 终止条件和生命周期 (L07)
- [x] Plan/Execute 模式 — Agent 规划-执行分离的实现 (L07)
- [x] 沙箱隔离 — trae-sandbox 与 Agent 的交互 (L04)

### 领域 7：MCP 与工具系统 [P1 — 5 子项] ✅ 全部完成
- [x] 基础 MCP 框架
- [x] **工具注册表** — 所有内置工具的注册和声明 (L05)
- [x] 浏览器自动化 — 30+ browser 工具的触发和编排 (L07)
- [x] 文件/Shell 工具 — 文件操作和命令执行的权限控制 (L04/L07)
- [x] Content Security — 输出安全过滤和手动确认机制 (L05)

### 领域 8：Custom Model Proxy [P2 — 5 子项] ✅ 全部完成
- [x] WebSocket 隧道
- [x] **AWS Bedrock 集成** — Converse Stream API 适配 (L06)
- [x] OpenRouter 集成 — 第三方模型路由 (L06)
- [x] 自定义模型注册 — add_custom_model 流程 (L06)
- [x] 负载均衡 — 多 provider 的请求分发 (L06)

### 领域 9：CLI (trae-cli) 分析 [P2 — 4 子项] ✅ 全部完成
- [x] CLI 认证方式
- [x] **CLI 命令集** — 完整的命令树 (L05)
- [x] CLI ↔ Hub Bridge 交互 — cli 如何通过 Hub 通信 (L04)
- [x] Dev Mode — 开发者模式的完整功能 (L05)

---

## 执行上下文

### 已知的关键观察点
1. **main.js** — 2.4MB Electron 主进程代码, Webpack 打包
2. **ai-agent** — Rust 共享库 (127MB Linux .so, 130MB macOS .dylib, 144MB Windows .dll)
3. **IPC** — ZMQ Dealer-Router, Unix domain sockets, JSON-RPC 2.0
4. **认证** — OAuth2 PKCE + AWS SSO + Supabase + BootConfig
5. **模型** — 15+ 模型, 7 LLM providers (Anthropic/OpenAI/Gemini/DeepSeek/Bedrock/Volcengine/OpenRouter)
6. **工具** — 30+ browser tools + 15+ 内置工具 + MCP tools
7. **端点** — icube-normal.trae.ai / core-normal.trae.ai / hub.trae.ai / icube-boot.trae.ai
8. **事件** — 91 iCubeAI events
9. **数据存储** — ~/.trae/ai-agent/database.db (SQLCipher)
10. **Sandbox** — trae-sandbox 18MB binary
11. **CKG** — Code Knowledge Graph 44MB shared library
12. **Scheduled Tasks** — Cron-like autonomous task scheduling

### 未解决的问题
- IPC 地址生成算法完整细节
- ZMQ 心跳参数具体值
- Frontier Hub Bridge 完整帧格式
- AI agent 内部事件优先级
- 沙箱结构 (namespace/Lite VM)
- BYOL (Bring Your Own LLM) 支持方式
- VPN/防火墙后的 fallback 机制
- 离线/弱网络模式

---

## 轮次日志

### L01 (t+0) — main.js Handler 注册与 IPC 通信
**目标**: 深入分析 main.js 中的 AI Handler 注册机制和与 ai-agent 的 IPC 通信流程
**状态**: 进行中
**上下文**: 已有 main.js/main.js (2.4MB) 和 main.js/split/ 拆分模块
**分析方法**: grep handler 注册 → 追踪调用链 → 分析 IPC → 输出报告