# Trae AI Model Testing Report - L08

**测试时间:** 2026-06-01 22:16 (UTC+8)
**测试类型:** 实际 API 调用验证（配额限制验证）
**Token 状态:** ✅ 有效（已刷新，有效期至 2026-06-02 ~16:00）

---

## 一、认证状态

| 项目 | 状态 | 详情 |
|------|------|------|
| Access Token | ✅ 有效 | 已通过 ExchangeToken 刷新 |
| User Info | ✅ 可获取 | UserID: `7464581135470298120` |
| Region | ✅ SG | Singapore-Central |
| TenantID | ✅ | `7o2d894p7dr0o4` |
| 计划 | — | BytePlus Coding Plan |

---

## 二、API 端点测试结果

### 2.1 主要聊天端点 `POST /api/ide/v1/agents/runs`

| 测试项 | 结果 | 状态 |
|--------|------|------|
| HTTP 状态 | 200 | ✅ |
| SSE 事件格式 | 2 events（错误 + 空） | ⚠️ |
| 实际 AI 响应 | ❌ 被配额限制 | 🔴 |
| 错误码 | **5003** — "agent running quota limit exceeded" | ❌ |

**测试模型（全部相同结果）:**

| 模型名 | 结果 |
|--------|------|
| auto（不指定） | ❌ 5003 |
| claude-3.5-sonnet | ❌ 5003 |
| deepseek-v3 / deepseek_v3 / deepseek-v3.1 | ❌ 5003 |
| gpt-5 | ❌ 5003 |
| qwen-2.5-32b | ❌ 5003 |
| gemini-3-flash | ❌ 5003 |

### 2.2 LLM Raw Chat 端点

| 端点 | HTTP 状态 | 结果 |
|------|----------|------|
| `POST /api/ide/v2/llm_raw_chat` | 400 ❌ | 空 body，无错误信息 |
| `POST /api/ide/v1/llm_raw_chat` | 400 ❌ | 空 body |
| v2 + stream=true | 400 ❌ | 空 body |
| v2 @ mcs-boot host | 404 ❌ | Endpoint not found |

### 2.3 Chat 原始端点

| 端点 | HTTP 状态 | 结果 |
|------|----------|------|
| SG `POST /api/ide/v1/chat` | 200 ⚠️ | code 4001 "param is invalid" |
| US `POST /api/ide/v1/chat` | 404 ❌ | Endpoint not found |

### 2.4 模型/供应商 API

| 端点 | HTTP 状态 | 结果 |
|------|----------|------|
| `GET /api/ide/v1/model_list` | 500 ❌ | Internal Server Error |
| `POST /api/ide/v1/model_list` | 500 ❌ | Internal Server Error |
| `GET /api/ide/v1/providers` | **200 ✅** | **25 个供应商列表** |
| `POST /api/ide/v1/providers` | **200 ✅** | **25 个供应商列表** |

### 2.5 Hub Bridge / CLI Proxy（备选）

| 端点 | HTTP 状态 | 结果 |
|------|----------|------|
| `/clis/register` | 404 ❌ | Not found on coresg-normal |
| `/trae-cli/api/v1/llm/proxy` | 404 ❌ | Not found |
| `/conversations/messages/batchInsertMulti` | 404 ❌ | Not found |
| api-sg /cloudide/api/v1/llm/proxy | 403 ❌ | code 10303 权限错误 |

### 2.6 US 区域端点对比

| 端点 | HTTP 状态 | 结果 |
|------|----------|------|
| US icube `agents/runs` | 404 ❌ | Not found |
| US core `agents/runs` | 200 ⚠️ | 同 5003 配额限制 |

---

## 三、可用供应商与模型

通过 `POST /api/ide/v1/providers` 成功获取到 **25 个供应商** 的最新模型列表：

| 供应商 | ID | 可用模型 |
|--------|----|---------|
| **Anthropic** | anthropic | claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5-20251001 |
| **DeepSeek** | deepseek | deepseek-v4-pro, deepseek-v4-flash |
| **BytePlus** | byteplus / byteplus-plan | seed-2-0-pro-260328, seed-2-0-lite-260228, deepseek-v3-2-251201 |
| **Alibaba Cloud** | aliyuncs | qwen3-coder-plus, qwen3-coder-flash |
| **Tencent Cloud** | tencent | deepseek-v3.2, deepseek-r1-0528 |
| **Volcengine** | volcengine | doubao-seed-2-0-code-preview-260215, kimi-k2.5 |
| **Bigmodel (Zhipu)** | bigmodel | glm-5, glm-5.1 |
| **Kimi** | Kimi-Global | kimi-k2.5 |
| **MiniMax** | MiniMax-global | MiniMax-M2.7 |
| **SiliconFlow** | siliconflow | Pro/MiniMaxAI/MiniMax-M2.5, Pro/zai-org/GLM-5, etc. |
| +14 个更多... | | |

---

## 四、结论

### 核心发现

1. **配额是当前唯一限制** — Token 有效、端点可达、格式正确，但 **BytePlus Coding Plan 的 agent running quota 已耗尽**（code 5003）
2. **model_list 端点是坏的** — 即使配额正常也无法用 model_list 查询
3. **providers 端点正常工作** — 返回 25 个供应商的最新型号（显示 Trae 不断在更新模型库）
4. **模型名已更新** — 最新是 Claude 4.6 系列、DeepSeek V4、Kimi K2.5 等，而非旧 version 名
5. **`/api/ide/v1/chat` 端点参数不兼容** — 需要查看 IDE 实际发送的格式

### 当前阻塞点

| 阻塞项 | 说明 | 解决方案 |
|--------|------|---------|
| 配额 5003 | agent running quota exceeded | 等待重置 / 购买额度 / 使用自有 API key |

### 下一步建议

1. **等待配额自然重置**（可能按天/周周期）
2. **使用自提供 API Key** — Trae 支持 Custom Model Proxy，可以用自有 API Key 绕过配额
3. **分析配额重置机制** — 通过代码分析确定重置周期
4. **研究 /api/ide/v1/chat 参数格式** — 需要逆向 IDE 实际发送的请求 payload
