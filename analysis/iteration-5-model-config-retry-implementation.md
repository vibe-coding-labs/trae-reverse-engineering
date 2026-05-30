# Trae Model Config, Retry Logic & Implementation Guide - Iteration 5

**Date**: 2026-05-30
**Focus**: Model Configuration, Error Recovery, Complete Implementation Guide

---

## Executive Summary

本次分析完成了模型配置、错误恢复机制的研究，并提供了完整的 Codex 集成实现指南。

---

## 1. 模型配置

### 1.1 模型列表端点

```
GET /api/ide/v1/model_list
GET /api/ide/v1/get_model_list
GET /api/ide/v1/get_detail_param
```

### 1.2 模型配置结构

```json
{
    "model_config": {
        "model_name": "claude35_multi_content",
        "temperature": 0.7,
        "max_tokens": 4096,
        "top_p": 0.9,
        "top_k": 50
    }
}
```

### 1.3 模型配置缓存

```sql
CREATE TABLE model_config_cache (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    env TEXT NOT NULL,
    function TEXT NOT NULL,
    config_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 查询缓存
SELECT config_data FROM model_config_cache
WHERE user_id=? AND env=? AND function=?
```

### 1.4 支持的模型

| 模型 | 名称 | 用途 |
|------|------|------|
| Claude 3.5 | `claude35_multi_content` | 多模态 |
| GPT-5 | `gpt5` | 通用 |
| GPT-5.2 | `gpt52` | 轻量级 |
| DeepSeek V3 | `deepseek_v3` | 代码 |
| Gemini 3 | `gemini3` | 多模态 |

---

## 2. 错误处理和重试

### 2.1 错误码映射

| HTTP 状态码 | 含义 | 处理 |
|-------------|------|------|
| 401 | 未授权 | 刷新 token |
| 429 | 速率限制 | 等待 `X-RateLimit-Reset` |
| 502 | 网关错误 | 指数退避重试 |
| 503 | 服务不可用 | 指数退避重试 |
| 504 | 网关超时 | 指数退避重试 |

### 2.2 重试配置

```javascript
const RETRY_CONFIG = {
    retryCount: 3,
    retryTimeout: 1000,        // 1秒
    backoffMultiplier: 2,      // 指数退避
    retryCodes: [502, 503, 504],
    noEventTimeout: 30000      // 30秒无事件超时
};
```

### 2.3 指数退避算法

```javascript
async function retryWithBackoff(fn, config) {
    let lastError;

    for (let attempt = 0; attempt < config.retryCount; attempt++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error;

            if (!config.retryCodes.includes(error.status)) {
                throw error;
            }

            const delay = config.retryTimeout * Math.pow(config.backoffMultiplier, attempt);
            console.log(`Retry attempt ${attempt + 1} after ${delay}ms`);
            await sleep(delay);
        }
    }

    throw lastError;
}
```

### 2.4 重试错误类别

| 类别 | 描述 |
|------|------|
| Connection timeout | 连接超时 |
| Network IO error | 网络 IO 错误 |
| TLS connection error | TLS 连接错误 |
| Connection reset by peer | 连接被重置 |
| Connection refused | 连接被拒绝 |
| Write buffer full | 写缓冲区满 |

### 2.5 心跳超时检测

```
Stale heartbeat detected before processing ping: last ping was {time}
Heartbeat timeout detected (last ping: {time} ago)
Too many missed heartbeats
```

### 2.6 重连逻辑

**触发条件**:
- WebSocket 关闭
- 心跳超时
- 服务器请求关闭
- 连接错误

**重连行为**:
1. 尝试 WebSocket 重连
2. 失败后切换到 HTTP 回退
3. HTTP 空闲超时后结束隧道

---

## 3. 速率限制

### 3.1 速率限制头

```http
X-RateLimit-Remaining: 100
X-RateLimit-Reset: 1234567890
X-RateLimit-Limit: 1000
```

### 3.2 速率限制响应

```json
{
    "error": {
        "code": 429,
        "message": "Rate limit exceeded",
        "retry_after": 60
    }
}
```

### 3.3 速率限制处理

```javascript
async function handleRateLimit(response) {
    if (response.status === 429) {
        const retryAfter = response.headers.get('X-RateLimit-Reset');
        const waitTime = (retryAfter * 1000) - Date.now();

        console.log(`Rate limited. Waiting ${waitTime}ms`);
        await sleep(waitTime);

        return true;  // 需要重试
    }
    return false;
}
```

---

## 4. 完整实现指南

### 4.1 项目结构

```
trae-proxy/
├── src/
│   ├── auth/
│   │   ├── oauth.ts          # OAuth2 认证
│   │   └── token.ts          # Token 管理
│   ├── api/
│   │   ├── chat.ts           # 聊天 API
│   │   ├── model.ts          # 模型 API
│   │   └── session.ts        # 会话 API
│   ├── stream/
│   │   ├── sse.ts            # SSE 流处理
│   │   └── websocket.ts      # WebSocket 处理
│   ├── proxy/
│   │   ├── translator.ts     # 协议转换
│   │   └── handler.ts        # 请求处理
│   └── utils/
│       ├── retry.ts          # 重试逻辑
│       └── logger.ts         # 日志
├── config/
│   └── config.ts             # 配置
└── index.ts                  # 入口
```

### 4.2 核心实现

#### OAuth2 认证

```typescript
class TraeAuth {
    private accessToken: string;
    private refreshToken: string;
    private tokenExpiry: number;

    async initialize() {
        // 获取 boot 配置
        const bootConfig = await fetch('https://icube-boot.trae.ai/boot/config', {
            headers: { 'User-Agent': 'Trae-IDE/2.3.30128' }
        }).then(r => r.json());

        this.tokenHost = bootConfig.tokenHost || bootConfig.token_host;

        // 检查 token 是否需要刷新
        if (Date.now() >= bootConfig.userInfo.expiredAt * 1000 - 60000) {
            await this.refreshToken();
        }
    }

    async refreshToken() {
        const response = await fetch(`${this.tokenHost}/cloudide/api/v3/trae/oauth/ExchangeToken`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ClientID: '6eefa01c-1036-4c7e-9ca5-d891f63bfcd8',
                RefreshToken: this.refreshToken,
                ClientSecret: '-',
                UserID: ''
            })
        });

        const data = await response.json();
        this.accessToken = data.Result.Token;
        this.refreshToken = data.Result.RefreshToken;
        this.tokenExpiry = Date.now() + (data.Result.TokenExpireAt * 1000);
    }

    getHeaders() {
        return {
            'x-cloudide-token': this.accessToken,
            'x-ide-token': this.accessToken,
            'Authorization': `Bearer ${this.accessToken}`,
            'User-Agent': 'Trae-IDE/2.3.30128',
            'X-Trae-Version': '2.3.30128',
            'Content-Type': 'application/json'
        };
    }
}
```

#### 会话管理

```typescript
class TraeSession {
    private conversationId: string;
    private sessionId: string;

    async create() {
        // 创建会话
        const response = await fetch('https://icube-normal.trae.ai/data/data/chat_session_id', {
            method: 'POST',
            headers: auth.getHeaders(),
            body: JSON.stringify({
                cli_conversation_id: generateUUID()
            })
        });

        const data = await response.json();
        this.sessionId = data.chat_session_id;
    }

    async sendMessage(message: string, model: string = 'claude35_multi_content') {
        const response = await fetch('https://icube-normal.trae.ai/data/data/message_id', {
            method: 'POST',
            headers: auth.getHeaders(),
            body: JSON.stringify({
                cli_conversation_id: this.conversationId,
                initial_message: { content: message },
                model_config: {
                    model_name: model,
                    temperature: 0.7,
                    max_tokens: 4096
                }
            })
        });

        return response.json();
    }
}
```

#### 流式处理

```typescript
class TraeStream {
    private ws: WebSocket;

    connect() {
        this.ws = new WebSocket('wss://hub.trae.ai/ws');

        this.ws.onopen = () => {
            this.ws.send(JSON.stringify({
                method: 'register_cli',
                params: {
                    cli_id: generateUUID(),
                    frontier_id: generateUUID(),
                    app_id: 'trae-proxy',
                    product_id: 'trae-ide',
                    process_id: process.pid.toString()
                }
            }));
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
    }

    private handleMessage(data: any) {
        switch (data.type) {
            case 'content_block_delta':
                this.onContent(data.delta.text);
                break;
            case 'message_stop':
                this.onComplete();
                break;
            case 'tool_call':
                this.onToolCall(data);
                break;
        }
    }
}
```

#### OpenAI 兼容代理

```typescript
const app = express();

app.post('/v1/chat/completions', async (req, res) => {
    try {
        // 翻译请求
        const traeRequest = translator.translateRequest(req.body);

        // 发送到 Trae
        const session = new TraeSession();
        await session.create();
        const response = await session.sendMessage(
            traeRequest.params.message.content,
            traeRequest.params.model_config.model_name
        );

        // 流式响应
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');

        const stream = new TraeStream();
        stream.connect();
        stream.subscribe(session.sessionId);

        stream.onContent = (content) => {
            res.write(`data: ${JSON.stringify({
                choices: [{ delta: { content } }]
            })}\n\n`);
        };

        stream.onComplete = () => {
            res.write('data: [DONE]\n\n');
            res.end();
        };

        stream.onToolCall = (toolCall) => {
            res.write(`data: ${JSON.stringify({
                choices: [{
                    delta: {
                        tool_calls: [{
                            id: toolCall.id,
                            type: 'function',
                            function: {
                                name: toolCall.name,
                                arguments: JSON.stringify(toolCall.arguments)
                            }
                        }]
                    }
                }]
            })}\n\n`);
        };

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 模型列表端点
app.get('/v1/models', async (req, res) => {
    const response = await fetch('https://icube-normal.trae.ai/api/ide/v1/model_list', {
        headers: auth.getHeaders()
    });

    const data = await response.json();
    res.json({
        data: data.models.map(m => ({
            id: m.id,
            object: 'model',
            created: Math.floor(Date.now() / 1000),
            owned_by: 'trae'
        }))
    });
});

app.listen(8080, () => {
    console.log('Trae AI Proxy running on port 8080');
});
```

---

## 5. 使用示例

### 5.1 启动代理

```bash
# 安装依赖
npm install express ws

# 配置环境变量
export TRAE_ACCESS_TOKEN="your_access_token"
export TRAE_REFRESH_TOKEN="your_refresh_token"

# 启动代理
npx ts-node src/index.ts
```

### 5.2 使用 Codex 调用

```bash
# 设置 OpenAI API 基础 URL
export OPENAI_API_BASE="http://localhost:8080/v1"

# 使用 Codex
codex "Write a hello world program"
```

### 5.3 直接 API 调用

```bash
# 聊天
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'

# 模型列表
curl http://localhost:8080/v1/models
```

---

## 6. 关键发现总结

### 6.1 模型配置

1. **模型列表**: `/api/ide/v1/model_list`
2. **配置缓存**: SQLite `model_config_cache` 表
3. **参数**: temperature, max_tokens, top_p, top_k

### 6.2 错误恢复

1. **重试**: 3 次，指数退避
2. **退避**: 1s, 2s, 4s
3. **重试码**: 502, 503, 504
4. **超时**: 30 秒无事件

### 6.3 速率限制

1. **算法**: Token bucket
2. **头**: X-RateLimit-Remaining/Reset/Limit
3. **响应**: HTTP 429 + retry_after

---

## 7. 下一步分析

### 7.1 待验证

1. [ ] 模型选择策略
2. [ ] 并发请求处理
3. [ ] 会话持久化
4. [ ] 错误恢复测试

### 7.2 待实现

1. [ ] 完整的 OAuth2 流程
2. [ ] WebSocket 重连逻辑
3. [ ] 工具调用处理
4. [ ] 性能监控
