# Trae CLI LLM Proxy & Auth Protocol - Iteration 1 Analysis

**Date**: 2026-05-30
**Focus**: Trae CLI (v0.120.35) LLM Proxy Endpoint & Authentication Protocol

---

## Executive Summary

本次分析深入逆向了 Trae CLI 的 LLM 代理端点和认证协议，发现了 Codex 集成的关键路径。CLI 使用 Go 语言编写，基于 ByteDance 内部的 `coco` 框架，通过 `/trae-cli/api/v1/llm/proxy` 端点提供 OpenAI 兼容的 LLM 代理服务。

---

## 1. LLM Proxy 端点 (关键发现)

### 1.1 核心端点

```
POST /trae-cli/api/v1/llm/proxy
```

这是 Codex 集成的**最关键端点**。CLI 通过此端点代理所有 LLM 请求到 Trae 后端。

### 1.2 流式处理

从 CLI 二进制中发现的关键函数：

```go
// OpenAI SSE 流式解析
parse openai sse chunk: %w

// 流式消息发送
code.byted.org/nextcode/coco/cli/tui/repl.sendToStream
sendToStream: channel full, dropped message

// Volcengine Ark Runtime 流式调用
github.com/volcengine/volcengine-go-sdk/service/arkruntime.(*Client).BotChatCompletionRequestStreamDo
github.com/volcengine/volcengine-go-sdk/service/arkruntime.(*Client).ChatCompletionRequestStreamDo
```

### 1.3 支持的模型格式

```go
// OpenAI 兼容格式
openai.ChatCompletionRequest
openai.ChatCompletionResponse
openai.ChatCompletionStreamResponse
openai.ChatCompletionStreamChoice
openai.ChatCompletionTokenLogprob

// DeepSeek 格式
deepseek.ChatCompletionRequest
deepseek.StreamChatCompletionRequest
deepseek.FIMStreamCompletionRequest  // Fill-in-Middle 补全

// Volcengine Ark 格式
model.BotChatCompletionRequest
model.BotChatCompletionResponse
model.ChatCompletionStreamResponse
```

### 1.4 流式响应结构

```go
// 流式响应读取器
utils.BotChatCompletionStreamReader
utils.ChatCompletionStreamReader

// 响应结构
model.ChatCompletionStreamChoice  // 流式选择
model.BotChatCompletionStreamResponse  // Bot 流式响应
```

---

## 2. 认证协议详解

### 2.1 Auth 数据结构

```go
// CLI 认证结构体
struct {
    DeviceID     string    `json:"DeviceId"`
    Host         string    `json:"Host"`
    LoginBaseURL string    `json:"LoginBaseURL,omitempty"`
    Scope        string    `json:"Scope"`
    OauthToken   *OauthToken `json:"OauthToken"`
}
```

### 2.2 Token 存储机制

CLI 实现了三层 token 存储：

```go
// 1. KeyringStore - 系统密钥环 (最安全)
code.byted.org/nextcode/coco/cli/util/tokenstore.(*KeyringStore).Get
code.byted.org/nextcode/coco/cli/util/tokenstore.(*KeyringStore).Set
code.byted.org/nextcode/coco/cli/util/tokenstore.(*KeyringStore).Delete

// 2. MemoryStore - 内存存储 (临时)
code.byted.org/nextcode/coco/cli/util/tokenstore.(*MemoryStore).Get
code.byted.org/nextcode/coco/cli/util/tokenstore.(*MemoryStore).Set
code.byted.org/nextcode/coco/cli/util/tokenstore.(*MemoryStore).Delete

// 3. OAuthTokenStore - OAuth 专用存储
code.byted.org/nextcode/coco/cli/util/oauth.NewOAuthTokenStore
code.byted.org/nextcode/coco/cli/util/oauth.(*OAuthTokenStore).GetToken
code.byted.org/nextcode/coco/cli/util/oauth.(*OAuthTokenStore).SaveToken
code.byted.org/nextcode/coco/cli/util/oauth.(*OAuthTokenStore).GetClientInfo
code.byted.org/nextcode/coco/cli/util/oauth.(*OAuthTokenStore).SaveClientInfo
code.byted.org/nextcode/coco/cli/util/oauth.(*OAuthTokenStore).Clear
```

### 2.3 登录方法

CLI 支持三种登录方式：

```go
// 1. 邮箱登录
code.byted.org/nextcode/coco/tenant/trae/cli/repl/slashcmd.(*LoginCommand).handleLoginWithEmail

// 2. 企业自定义域名登录
code.byted.org/nextcode/coco/tenant/trae/cli/repl/slashcmd.(*LoginCommand).handleLoginWithEnterpriseCustomDomain

// 3. Token 登录 (自动)
no existing auth info found in secure store
completed auth, got the oauth token
```

### 2.4 OAuth2 Discovery

```go
// OAuth2 保护资源发现
/.well-known/oauth-protected-resource
failed to create metadata request: %w

// OAuth2 授权服务器发现
/.well-known/oauth-authorization-server
failed to get server metadata: %w

// OpenID 配置
/.well-known/openid-configuration
```

### 2.5 PKCE 支持

```go
// PKCE 参数
*authhandler.PKCEParams
*auth.PKCEOptions
PKCEEnabled
PKCEOpts

// OAuth2 PKCE 流程
golang.org/x/oauth2/authhandler.TokenSourceWithPKCE
code_challenge_method
code_verifier
```

### 2.6 认证端点

```
POST /cloudide/api/v3/trae/CheckLogin     # 检查登录状态
POST /cloudide/api/v3/trae/GetUserInfo     # 获取用户信息
POST /cloudide/api/v3/trae/oauth/ExchangeToken  # 刷新 token
```

### 2.7 ZTI (Zero Trust Identity) 认证

```go
// ZTI Agent Socket
/var/run/zti-agent/sockets/agent.sock

// SPIFFE Workload API
code.byted.org/security/go-spiffe-v2/workloadapi
code.byted.org/security/go-spiffe-v2/svid/jwtsvid

// ZTI JWT Helper
code.byted.org/security/zti-jwt-helper-golang/helper
```

---

## 3. Go 模块架构

### 3.1 核心模块

```
code.byted.org/nextcode/coco/cli/              # CLI 主模块
code.byted.org/nextcode/coco/agent/             # Agent 运行时
code.byted.org/nextcode/coco/tenant/trae/cli/   # Trae CLI 特定实现
```

### 3.2 认证相关模块

```
code.byted.org/nextcode/coco/tenant/trae/cli/auth        # 认证核心
code.byted.org/nextcode/coco/tenant/trae/cli/util        # 工具函数
code.byted.org/nextcode/coco/cli/util/tokenstore          # Token 存储
code.byted.org/nextcode/coco/cli/util/oauth               # OAuth 存储
```

### 3.3 聊天模型模块

```
code.byted.org/nextcode/coco/tenant/trae/cli/chatmodel   # 聊天模型
code.byted.org/nextcode/coco/agent/model/deepseek        # DeepSeek 模型
```

### 3.4 LLM 提供商 SDK

```go
// Volcengine Ark Runtime (字节跳动内部 LLM 服务)
github.com/volcengine/volcengine-go-sdk/service/arkruntime

// OpenAI Go SDK
openai.ChatCompletionRequest
openai.ChatCompletionStream

// DeepSeek Go SDK
github.com/cohesion-org/deepseek-go
```

---

## 4. API 端点清单

### 4.1 LLM 代理端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/trae-cli/api/v1/llm/proxy` | POST | **LLM 代理 (核心)** |

### 4.2 配置端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/ide/v1/cli/get_config_list` | GET | 获取配置列表 |
| `/api/ide/v1/tenant/get_tenant_user_config` | GET | 获取租户用户配置 |

### 4.3 模型端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/ide/v1/report_custom_model_token_usage` | POST | 报告自定义模型 token 使用 |
| `/api/ide/v1/check_custom_model_quota` | POST | 检查自定义模型配额 |

### 4.4 审计端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/ide/v1/tenant/report_audit_log` | POST | 报告审计日志 |

---

## 5. 流式响应协议

### 5.1 SSE 格式

CLI 使用 OpenAI 兼容的 SSE 格式：

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"gpt-5","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"gpt-5","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### 5.2 流式处理函数

```go
// 解析 OpenAI SSE 块
parse openai sse chunk

// 发送到流
sendToStream: channel full, dropped message

// 流式请求执行
ChatCompletionRequestStreamDo
BotChatCompletionRequestStreamDo
```

---

## 6. Codex 集成方案

### 6.1 最简集成路径

```
Codex CLI
    ↓ (OpenAI 兼容请求)
Trae Proxy Server
    ↓ (认证 + 转换)
/trae-cli/api/v1/llm/proxy
    ↓
Trae Backend (icube-normal.trae.ai)
    ↓
LLM Provider (OpenAI/Anthropic/DeepSeek/etc.)
```

### 6.2 认证流程

```
1. 获取 OAuth2 授权 URL
   GET /.well-known/oauth-authorization-server

2. 用户授权 (浏览器)
   GET {authorization_url}?code_challenge={challenge}&code_challenge_method=S256

3. 获取 token
   POST /cloudide/api/v3/trae/oauth/ExchangeToken
   Body: {ClientID, RefreshToken, ClientSecret}

4. 保存 token
   KeyringStore (系统密钥环) 或 MemoryStore

5. 刷新 token
   POST /cloudide/api/v3/trae/oauth/ExchangeToken
   Body: {ClientID, RefreshToken}
```

### 6.3 请求格式

```http
POST /trae-cli/api/v1/llm/proxy
Content-Type: application/json
Authorization: Bearer {access_token}

{
  "model": "gpt-5",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "stream": true,
  "temperature": 0.7,
  "max_tokens": 4096
}
```

---

## 7. 关键发现总结

### 7.1 新发现

1. **LLM Proxy 端点**: `/trae-cli/api/v1/llm/proxy` - 这是 Codex 集成的核心
2. **OpenAI 兼容**: CLI 使用 OpenAI 兼容的请求/响应格式
3. **Volcengine Ark**: 使用字节跳动的 Volcengine Ark Runtime 作为 LLM 代理
4. **PKCE 支持**: 完整的 OAuth2 PKCE 流程支持
5. **ZTI 认证**: Zero Trust Identity 通过 SPIFFE Workload API
6. **三层存储**: KeyringStore > OAuthTokenStore > MemoryStore

### 7.2 认证关键点

1. **Client ID**: `6eefa01c-1036-4c7e-9ca5-d891f63bfcd8`
2. **Token 端点**: `/cloudide/api/v3/trae/oauth/ExchangeToken`
3. **Discovery**: `/.well-known/oauth-authorization-server`
4. **PKCE**: 支持 `code_challenge` + `code_verifier`

### 7.3 代理关键点

1. **端点**: `/trae-cli/api/v1/llm/proxy`
2. **格式**: OpenAI 兼容
3. **流式**: SSE 格式，`parse openai sse chunk`
4. **模型**: 支持 GPT-5、DeepSeek、Claude、Gemini 等

---

## 8. 下一步分析计划

### 8.1 需要验证

1. [ ] `/trae-cli/api/v1/llm/proxy` 的完整请求/响应格式
2. [ ] 认证 token 的具体格式和有效期
3. [ ] 流式响应的完整事件类型
4. [ ] 错误处理和重试机制

### 8.2 需要实现

1. [ ] OAuth2 PKCE 认证流程
2. [ ] Token 存储和刷新
3. [ ] LLM 代理服务器
4. [ ] OpenAI 兼容接口

---

## 9. 技术细节附录

### 9.1 Go 包路径

```go
// 认证
code.byted.org/nextcode/coco/tenant/trae/cli/auth
code.byted.org/nextcode/coco/tenant/trae/cli/auth.OauthToken

// Token 存储
code.byted.org/nextcode/coco/cli/util/tokenstore
code.byted.org/nextcode/coco/cli/util/oauth

// 聊天模型
code.byted.org/nextcode/coco/tenant/trae/cli/chatmodel
code.byted.org/nextcode/coco/agent/model/deepseek

// Agent 运行时
code.byted.org/nextcode/coco/agent/runtime/local
code.byted.org/nextcode/coco/agent/promptcommand
```

### 9.2 错误消息

```
failed to list trae models
basic info not initialized
no existing auth info found in secure store
completed auth, got the oauth token
login session has expired, please reauthenticate
failed to create refresh token request
failed to decode token response
failed to save token to keyring
```

### 9.3 配置相关

```
custom config does not contain trae model
skip quota check: failed to get auth info
skip quota report: missing model identity
```

---

## 10. 结论

Trae CLI 的 LLM 代理端点 `/trae-cli/api/v1/llm/proxy` 是 Codex 集成的**最佳切入点**。它提供：

1. **OpenAI 兼容接口** - 无需格式转换
2. **流式响应** - 支持实时输出
3. **多模型支持** - GPT-5、DeepSeek、Claude、Gemini
4. **完整认证** - OAuth2 + PKCE + ZTI

**推荐实现顺序**:
1. 实现 OAuth2 PKCE 认证
2. 调用 `/trae-cli/api/v1/llm/proxy` 端点
3. 处理 SSE 流式响应
4. 集成到 Codex CLI
