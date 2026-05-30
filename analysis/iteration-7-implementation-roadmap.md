# Trae AI Proxy - Implementation Roadmap - Iteration 7

**Date**: 2026-05-30
**Focus**: Implementation Roadmap and Remaining Analysis

---

## Executive Summary

本文档提供完整的实现路线图，基于前 6 次迭代的分析成果。所有核心协议和接口已分析完成，可以开始实现。

---

## 1. 实现路线图

### 1.1 Phase 1: 基础架构 (1-2 天)

```
trae-proxy/
├── src/
│   ├── auth/
│   │   ├── oauth.ts          # OAuth2 PKCE 认证
│   │   ├── token.ts          # Token 管理
│   │   └── discovery.ts      # OAuth 发现
│   ├── config/
│   │   ├── config.ts         # 配置管理
│   │   └── boot.ts           # Boot 配置
│   └── utils/
│       ├── logger.ts         # 日志
│       └── retry.ts          # 重试逻辑
├── package.json
└── tsconfig.json
```

**任务**:
- [ ] 初始化项目结构
- [ ] 实现 OAuth2 PKCE 认证流程
- [ ] 实现 Token 存储和刷新
- [ ] 实现 Boot 配置获取

### 1.2 Phase 2: 核心代理 (2-3 天)

```
src/
├── api/
│   ├── chat.ts               # 聊天 API
│   ├── model.ts              # 模型 API
│   └── session.ts            # 会话 API
├── stream/
│   ├── sse.ts                # SSE 流处理
│   └── websocket.ts          # WebSocket 处理
└── proxy/
    ├── translator.ts         # 协议转换
    └── handler.ts            # 请求处理
```

**任务**:
- [ ] 实现会话管理 (create, send, stop)
- [ ] 实现 SSE 流式处理
- [ ] 实现 WebSocket 连接
- [ ] 实现协议转换 (OpenAI ↔ Trae)

### 1.3 Phase 3: 工具集成 (1-2 天)

```
src/
├── tools/
│   ├── builtin.ts            # 内置工具
│   ├── mcp.ts                # MCP 工具
│   └── registry.ts           # 工具注册
└── agent/
    ├── workflow.ts            # Agent 工作流
    └── events.ts              # 事件处理
```

**任务**:
- [ ] 实现内置工具调用
- [ ] 实现 MCP 工具发现和调用
- [ ] 实现 Agent 事件监听
- [ ] 实现工具结果处理

### 1.4 Phase 4: 优化和测试 (1-2 天)

```
src/
├── middleware/
│   ├── rateLimit.ts          # 速率限制
│   ├── error.ts              # 错误处理
│   └── auth.ts               # 认证中间件
└── __tests__/
    ├── auth.test.ts
    ├── chat.test.ts
    └── tools.test.ts
```

**任务**:
- [ ] 实现速率限制处理
- [ ] 实现错误恢复机制
- [ ] 编写单元测试
- [ ] 性能优化

---

## 2. 关键实现细节

### 2.1 OAuth2 PKCE 认证

```typescript
// src/auth/oauth.ts
import crypto from 'crypto';

export class OAuthClient {
    private clientId = '6eefa01c-1036-4c7e-9ca5-d891f63bfcd8';
    private tokenHost: string;

    async discoverEndpoints() {
        const response = await fetch(
            `${this.tokenHost}/.well-known/oauth-authorization-server`
        );
        return response.json();
    }

    generatePKCE() {
        const codeVerifier = crypto.randomBytes(32).toString('base64url');
        const codeChallenge = crypto.createHash('sha256')
            .update(codeVerifier)
            .digest('base64url');
        return { codeVerifier, codeChallenge };
    }

    async exchangeToken(refreshToken: string) {
        const response = await fetch(
            `${this.tokenHost}/cloudide/api/v3/trae/oauth/ExchangeToken`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ClientID: this.clientId,
                    RefreshToken: refreshToken,
                    ClientSecret: '-',
                    UserID: ''
                })
            }
        );
        return response.json();
    }
}
```

### 2.2 会话管理

```typescript
// src/api/session.ts
export class SessionManager {
    private sessions: Map<string, Session> = new Map();

    async create(): Promise<Session> {
        const response = await fetch(
            'https://icube-normal.trae.ai/data/data/chat_session_id',
            {
                method: 'POST',
                headers: auth.getHeaders(),
                body: JSON.stringify({
                    cli_conversation_id: generateUUID()
                })
            }
        );
        const data = await response.json();
        const session = new Session(data.chat_session_id);
        this.sessions.set(session.id, session);
        return session;
    }

    async sendMessage(sessionId: string, message: string, model: string) {
        const session = this.sessions.get(sessionId);
        return session.sendMessage(message, model);
    }
}
```

### 2.3 SSE 流式处理

```typescript
// src/stream/sse.ts
export class SSEStream {
    private controller: ReadableStreamDefaultController;

    constructor(private res: Response) {
        const stream = new ReadableStream({
            start: (controller) => {
                this.controller = controller;
            }
        });

        res.headers.set('Content-Type', 'text/event-stream');
        res.headers.set('Cache-Control', 'no-cache');
        res.headers.set('Connection', 'keep-alive');
    }

    write(data: any) {
        const chunk = `data: ${JSON.stringify(data)}\n\n`;
        this.controller.enqueue(new TextEncoder().encode(chunk));
    }

    end() {
        this.controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'));
        this.controller.close();
    }
}
```

### 2.4 协议转换

```typescript
// src/proxy/translator.ts
export class ProtocolTranslator {
    translateRequest(openaiRequest: any) {
        return {
            method: 'send_message',
            params: {
                message: {
                    content: openaiRequest.messages[0].content
                },
                model_config: {
                    model_name: this.mapModel(openaiRequest.model),
                    temperature: openaiRequest.temperature || 0.7,
                    max_tokens: openaiRequest.max_tokens || 4096
                }
            }
        };
    }

    translateResponse(traeResponse: any) {
        return {
            id: traeResponse.id,
            object: 'chat.completion.chunk',
            choices: [{
                index: 0,
                delta: {
                    content: traeResponse.content
                }
            }]
        };
    }

    private mapModel(model: string): string {
        const modelMap: Record<string, string> = {
            'gpt-4o': 'gpt5',
            'gpt-4o-mini': 'gpt52',
            'claude-3.5-sonnet': 'claude35_multi_content',
            'deepseek-coder': 'deepseek_v3',
            'gemini-pro': 'gemini3'
        };
        return modelMap[model] || model;
    }
}
```

---

## 3. 错误处理

### 3.1 重试逻辑

```typescript
// src/utils/retry.ts
export async function retryWithBackoff<T>(
    fn: () => Promise<T>,
    options: {
        maxRetries: number;
        baseDelay: number;
        maxDelay: number;
        retryableErrors: number[];
    }
): Promise<T> {
    let lastError: Error;

    for (let attempt = 0; attempt <= options.maxRetries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error;

            if (!options.retryableErrors.includes(error.status)) {
                throw error;
            }

            if (attempt < options.maxRetries) {
                const delay = Math.min(
                    options.baseDelay * Math.pow(2, attempt),
                    options.maxDelay
                );
                console.log(`Retry attempt ${attempt + 1} after ${delay}ms`);
                await new Promise(r => setTimeout(r, delay));
            }
        }
    }

    throw lastError;
}
```

### 3.2 错误中间件

```typescript
// src/middleware/error.ts
export function errorHandler(err: Error, req: Request, res: Response) {
    console.error('Error:', err);

    if (err.status === 401) {
        // Token 过期，刷新
        return refreshTokenAndRetry(req, res);
    }

    if (err.status === 429) {
        // 速率限制
        const retryAfter = err.headers?.['x-ratelimit-reset'];
        return res.status(429).json({
            error: {
                message: 'Rate limit exceeded',
                retry_after: retryAfter
            }
        });
    }

    res.status(500).json({
        error: {
            message: err.message || 'Internal server error'
        }
    });
}
```

---

## 4. 配置管理

### 4.1 配置文件

```typescript
// src/config/config.ts
export interface Config {
    // 服务器配置
    port: number;
    host: string;

    // Trae 配置
    trae: {
        bootUrl: string;
        chatUrl: string;
        modelUrl: string;
        hubUrl: string;
    };

    // OAuth 配置
    oauth: {
        clientId: string;
        tokenHost: string;
        redirectUri: string;
    };

    // 重试配置
    retry: {
        maxRetries: number;
        baseDelay: number;
        maxDelay: number;
        retryableErrors: number[];
    };
}

export const defaultConfig: Config = {
    port: 8080,
    host: 'localhost',
    trae: {
        bootUrl: 'https://icube-boot.trae.ai',
        chatUrl: 'https://icube-normal.trae.ai',
        modelUrl: 'https://mcs-boot.trae.ai',
        hubUrl: 'wss://hub.trae.ai/ws'
    },
    oauth: {
        clientId: '6eefa01c-1036-4c7e-9ca5-d891f63bfcd8',
        tokenHost: 'https://icube-boot.trae.ai',
        redirectUri: 'http://localhost:8080/callback'
    },
    retry: {
        maxRetries: 3,
        baseDelay: 1000,
        maxDelay: 10000,
        retryableErrors: [502, 503, 504]
    }
};
```

---

## 5. 使用示例

### 5.1 启动代理

```bash
# 安装依赖
npm install

# 配置环境变量
export TRAE_ACCESS_TOKEN="your_access_token"
export TRAE_REFRESH_TOKEN="your_refresh_token"

# 启动代理
npm start
```

### 5.2 使用 Codex

```bash
# 设置 OpenAI API 基础 URL
export OPENAI_API_BASE="http://localhost:8080/v1"

# 使用 Codex
codex "Write a hello world program in Python"
```

### 5.3 API 调用

```bash
# 聊天
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'

# 模型列表
curl http://localhost:8080/v1/models
```

---

## 6. 待完成任务

### 6.1 高优先级

1. [ ] 实现 OAuth2 PKCE 完整流程
2. [ ] 实现 WebSocket 重连逻辑
3. [ ] 实现工具调用处理
4. [ ] 编写单元测试

### 6.2 中优先级

1. [ ] 实现 MCP 工具发现
2. [ ] 实现 Agent 事件监听
3. [ ] 实现性能监控
4. [ ] 优化错误处理

### 6.3 低优先级

1. [ ] 实现语音识别 (ASR) 集成
2. [ ] 实现图片生成
3. [ ] 实现文档 RAG
4. [ ] 实现 Wiki 功能

---

## 7. 总结

经过 7 次迭代分析，我们已经：

1. ✅ 完整逆向了 Trae 的 AI 通信协议
2. ✅ 分析了认证系统 (OAuth2 PKCE)
3. ✅ 研究了 IPC/RPC 机制 (ZeroMQ + JSON-RPC 2.0)
4. ✅ 分析了 91 个 iCubeAI 事件
5. ✅ 逆向了工具调用系统 (18+ 内置 + MCP)
6. ✅ 研究了模型配置和错误恢复
7. ✅ 提供了完整的实现路线图

**下一步**: 按照路线图开始实现代理服务器。
