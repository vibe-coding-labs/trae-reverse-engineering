# Trae AI Proxy Implementation Guide

## Overview

This guide provides detailed instructions for implementing a proxy server that allows Codex to use Trae's AI capabilities. The proxy translates between Codex's API format and Trae's internal protocol.

---

## 1. Architecture

### 1.1 System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Codex CLI     │ ──→ │  Trae AI Proxy  │ ──→ │  Trae Backend   │
│                 │     │                 │     │                 │
│  - OpenAI API   │     │  - Protocol     │     │  - ai-agent     │
│  - Streaming    │     │    Translation  │     │  - LLM Client   │
│  - Tool Calls   │     │  - Auth Mgmt    │     │  - Model Mgmt   │
└─────────────────┘     │  - Stream Proc  │     └─────────────────┘
                        └─────────────────┘
```

### 1.2 Component Overview

1. **Protocol Translator** - Converts Codex API requests to Trae protocol
2. **Authentication Manager** - Handles token lifecycle
3. **Stream Processor** - Manages SSE streaming
4. **Error Handler** - Maps error codes and handles retries
5. **Cache Manager** - Caches model configs and responses

---

## 2. Authentication Implementation

### 2.1 OAuth2 Flow

```typescript
// auth/oauth.ts
import { OAuth2Client } from 'google-auth-library';

interface TraeAuthConfig {
    clientId: string;
    redirectUri: string;
    authEndpoint: string;
    tokenEndpoint: string;
}

class TraeAuthManager {
    private config: TraeAuthConfig;
    private accessToken: string | null = null;
    private refreshToken: string | null = null;
    private tokenExpiry: number = 0;

    constructor(config: TraeAuthConfig) {
        this.config = config;
    }

    /**
     * Initialize authentication
     * Fetches boot config and initializes tokens
     */
    async initialize(): Promise<void> {
        // Fetch boot configuration
        const bootConfig = await this.fetchBootConfig();

        // Extract token host
        const tokenHost = bootConfig.tokenHost || bootConfig.token_host;

        // Initialize tokens from boot config
        if (bootConfig.userInfo) {
            this.initializeFromBootConfig(bootConfig);
        }
    }

    /**
     * Fetch boot configuration from Trae
     */
    private async fetchBootConfig(): Promise<any> {
        const response = await fetch('https://icube-boot.trae.ai/boot/config', {
            headers: {
                'User-Agent': 'Trae-IDE/2.3.30128',
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch boot config: ${response.status}`);
        }

        return response.json();
    }

    /**
     * Initialize tokens from boot config
     */
    private initializeFromBootConfig(bootConfig: any): void {
        const userInfo = bootConfig.userInfo;

        // Set token expiry
        this.tokenExpiry = userInfo.expiredAt * 1000; // Convert to milliseconds

        // Note: Actual tokens are stored in encrypted database
        // This is a simplified example
    }

    /**
     * Get valid access token
     * Refreshes if expired
     */
    async getAccessToken(): Promise<string> {
        // Check if token is expired
        if (this.isTokenExpired()) {
            await this.refreshAccessToken();
        }

        return this.accessToken!;
    }

    /**
     * Check if token is expired
     */
    private isTokenExpired(): boolean {
        return Date.now() >= this.tokenExpiry - 60000; // 1 minute buffer
    }

    /**
     * Refresh access token
     */
    private async refreshAccessToken(): Promise<void> {
        if (!this.refreshToken) {
            throw new Error('No refresh token available');
        }

        const response = await fetch(`${this.config.tokenEndpoint}/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.refreshToken}`
            },
            body: JSON.stringify({
                grant_type: 'refresh_token',
                refresh_token: this.refreshToken
            })
        });

        if (!response.ok) {
            throw new Error(`Token refresh failed: ${response.status}`);
        }

        const data = await response.json();
        this.accessToken = data.access_token;
        this.refreshToken = data.refresh_token;
        this.tokenExpiry = Date.now() + (data.expires_in * 1000);
    }

    /**
     * Get authorization headers
     */
    async getAuthHeaders(): Promise<Record<string, string>> {
        const token = await this.getAccessToken();

        return {
            'Authorization': `Bearer ${token}`,
            'User-Agent': 'Trae-IDE/2.3.30128',
            'X-Trae-Version': '2.3.30128'
        };
    }
}
```

### 2.2 Token Storage

```typescript
// auth/token-store.ts
import { open } from 'sqlite';
import sqlite3 from 'sqlite3';
import crypto from 'crypto';

interface TokenStoreConfig {
    dbPath: string;
    encryptionKey: string;
}

class TokenStore {
    private db: any;
    private encryptionKey: string;

    constructor(config: TokenStoreConfig) {
        this.encryptionKey = config.encryptionKey;
    }

    /**
     * Initialize token store
     */
    async initialize(dbPath: string): Promise<void> {
        this.db = await open({
            filename: dbPath,
            driver: sqlite3.Database
        });

        // Create tokens table if not exists
        await this.db.exec(`
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                token_type TEXT NOT NULL,
                token_value TEXT NOT NULL,
                expires_at INTEGER,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                UNIQUE(user_id, token_type)
            )
        `);
    }

    /**
     * Store token
     */
    async storeToken(userId: string, tokenType: string, tokenValue: string, expiresAt?: number): Promise<void> {
        const encryptedValue = this.encrypt(tokenValue);

        await this.db.run(`
            INSERT OR REPLACE INTO tokens (user_id, token_type, token_value, expires_at)
            VALUES (?, ?, ?, ?)
        `, [userId, tokenType, encryptedValue, expiresAt]);
    }

    /**
     * Get token
     */
    async getToken(userId: string, tokenType: string): Promise<string | null> {
        const row = await this.db.get(`
            SELECT token_value FROM tokens
            WHERE user_id = ? AND token_type = ?
        `, [userId, tokenType]);

        if (!row) {
            return null;
        }

        return this.decrypt(row.token_value);
    }

    /**
     * Encrypt token value
     */
    private encrypt(value: string): string {
        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipheriv('aes-256-gcm', Buffer.from(this.encryptionKey, 'hex'), iv);

        let encrypted = cipher.update(value, 'utf8', 'hex');
        encrypted += cipher.final('hex');

        const authTag = cipher.getAuthTag();

        return `${iv.toString('hex')}:${authTag.toString('hex')}:${encrypted}`;
    }

    /**
     * Decrypt token value
     */
    private decrypt(encryptedValue: string): string {
        const [ivHex, authTagHex, encrypted] = encryptedValue.split(':');

        const iv = Buffer.from(ivHex, 'hex');
        const authTag = Buffer.from(authTagHex, 'hex');
        const decipher = crypto.createDecipheriv('aes-256-gcm', Buffer.from(this.encryptionKey, 'hex'), iv);

        decipher.setAuthTag(authTag);

        let decrypted = decipher.update(encrypted, 'hex', 'utf8');
        decrypted += decipher.final('utf8');

        return decrypted;
    }

    /**
     * Delete token
     */
    async deleteToken(userId: string, tokenType: string): Promise<void> {
        await this.db.run(`
            DELETE FROM tokens
            WHERE user_id = ? AND token_type = ?
        `, [userId, tokenType]);
    }
}
```

---

## 3. Protocol Translation

### 3.1 Request Translation

```typescript
// protocol/request-translator.ts

interface CodexRequest {
    model: string;
    messages: Array<{
        role: 'system' | 'user' | 'assistant';
        content: string;
    }>;
    stream?: boolean;
    temperature?: number;
    max_tokens?: number;
    tools?: Array<{
        type: 'function';
        function: {
            name: string;
            description: string;
            parameters: any;
        };
    }>;
}

interface TraeRequest {
    method: string;
    params: {
        session_id: string;
        message: {
            content: string;
            type: 'text';
        };
        model_config: {
            model_name: string;
            temperature?: number;
            max_tokens?: number;
        };
        tools?: Array<{
            name: string;
            description: string;
            parameters: any;
        }>;
    };
}

class RequestTranslator {
    /**
     * Translate Codex request to Trae format
     */
    translate(codexRequest: CodexRequest): TraeRequest {
        // Extract system message
        const systemMessage = codexRequest.messages.find(m => m.role === 'system');

        // Extract user messages
        const userMessages = codexRequest.messages.filter(m => m.role === 'user');

        // Combine user messages
        const combinedContent = userMessages.map(m => m.content).join('\n');

        // Translate tools
        const translatedTools = codexRequest.tools?.map(tool => ({
            name: tool.function.name,
            description: tool.function.description,
            parameters: tool.function.parameters
        }));

        return {
            method: 'send_message',
            params: {
                session_id: this.generateSessionId(),
                message: {
                    content: combinedContent,
                    type: 'text'
                },
                model_config: {
                    model_name: this.translateModelName(codexRequest.model),
                    temperature: codexRequest.temperature,
                    max_tokens: codexRequest.max_tokens
                },
                tools: translatedTools
            }
        };
    }

    /**
     * Translate model name from Codex to Trae format
     */
    private translateModelName(codexModel: string): string {
        const modelMap: Record<string, string> = {
            'gpt-4': 'gpt-4',
            'gpt-4-turbo': 'gpt-4-turbo',
            'gpt-4o': 'gpt-4o',
            'gpt-4o-mini': 'gpt-4o-mini',
            'claude-3-opus': 'claude35_multi_content',
            'claude-3-sonnet': 'claude35_multi_content',
            'claude-3-haiku': 'claude35_multi_content',
            'deepseek-v3': 'deepseek-v3',
            'gemini-pro': 'gemini-3-pro'
        };

        return modelMap[codexModel] || codexModel;
    }

    /**
     * Generate session ID
     */
    private generateSessionId(): string {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}
```

### 3.2 Response Translation

```typescript
// protocol/response-translator.ts

interface TraeResponse {
    type: 'message_start' | 'content_block_start' | 'content_block_delta' | 'content_block_stop' | 'message_stop';
    message?: {
        id: string;
        role: string;
    };
    index?: number;
    content_block?: {
        type: string;
        text?: string;
    };
    delta?: {
        type: string;
        text?: string;
    };
}

interface CodexResponse {
    id: string;
    object: string;
    created: number;
    model: string;
    choices: Array<{
        index: number;
        message?: {
            role: string;
            content: string;
            tool_calls?: Array<{
                id: string;
                type: 'function';
                function: {
                    name: string;
                    arguments: string;
                };
            }>;
        };
        delta?: {
            role?: string;
            content?: string;
            tool_calls?: Array<{
                id: string;
                type: 'function';
                function: {
                    name: string;
                    arguments: string;
                };
            }>;
        };
        finish_reason: string | null;
    }>;
    usage?: {
        prompt_tokens: number;
        completion_tokens: number;
        total_tokens: number;
    };
}

class ResponseTranslator {
    private currentMessage: any = null;
    private currentContent: string = '';

    /**
     * Translate Trae response to Codex format
     */
    translate(traeResponse: TraeResponse): CodexResponse | null {
        switch (traeResponse.type) {
            case 'message_start':
                return this.handleMessageStart(traeResponse);
            case 'content_block_delta':
                return this.handleContentDelta(traeResponse);
            case 'message_stop':
                return this.handleMessageStop(traeResponse);
            default:
                return null;
        }
    }

    /**
     * Handle message start
     */
    private handleMessageStart(traeResponse: TraeResponse): CodexResponse {
        this.currentMessage = {
            id: traeResponse.message?.id || `msg_${Date.now()}`,
            role: 'assistant',
            content: ''
        };

        return {
            id: this.currentMessage.id,
            object: 'chat.completion.chunk',
            created: Math.floor(Date.now() / 1000),
            model: 'trae-proxy',
            choices: [{
                index: 0,
                delta: {
                    role: 'assistant'
                },
                finish_reason: null
            }]
        };
    }

    /**
     * Handle content delta
     */
    private handleContentDelta(traeResponse: TraeResponse): CodexResponse {
        const text = traeResponse.delta?.text || '';
        this.currentContent += text;

        return {
            id: this.currentMessage?.id || `msg_${Date.now()}`,
            object: 'chat.completion.chunk',
            created: Math.floor(Date.now() / 1000),
            model: 'trae-proxy',
            choices: [{
                index: 0,
                delta: {
                    content: text
                },
                finish_reason: null
            }]
        };
    }

    /**
     * Handle message stop
     */
    private handleMessageStop(traeResponse: TraeResponse): CodexResponse {
        const response: CodexResponse = {
            id: this.currentMessage?.id || `msg_${Date.now()}`,
            object: 'chat.completion.chunk',
            created: Math.floor(Date.now() / 1000),
            model: 'trae-proxy',
            choices: [{
                index: 0,
                delta: {},
                finish_reason: 'stop'
            }]
        };

        // Reset state
        this.currentMessage = null;
        this.currentContent = '';

        return response;
    }

    /**
     * Reset translator state
     */
    reset(): void {
        this.currentMessage = null;
        this.currentContent = '';
    }
}
```

---

## 4. Stream Processing

### 4.1 SSE Stream Handler

```typescript
// stream/sse-handler.ts

interface SSEEvent {
    event?: string;
    data: string;
    id?: string;
    retry?: number;
}

class SSEStreamHandler {
    private buffer: string = '';
    private eventBuffer: SSEEvent[] = [];

    /**
     * Process SSE data chunk
     */
    processChunk(chunk: string): SSEEvent[] {
        this.buffer += chunk;

        const events: SSEEvent[] = [];
        const lines = this.buffer.split('\n');

        let currentEvent: Partial<SSEEvent> = {};

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];

            // Empty line indicates end of event
            if (line === '') {
                if (currentEvent.data) {
                    events.push(currentEvent as SSEEvent);
                    currentEvent = {};
                }
                continue;
            }

            // Parse line
            if (line.startsWith('event:')) {
                currentEvent.event = line.substring(6).trim();
            } else if (line.startsWith('data:')) {
                currentEvent.data = line.substring(5).trim();
            } else if (line.startsWith('id:')) {
                currentEvent.id = line.substring(3).trim();
            } else if (line.startsWith('retry:')) {
                currentEvent.retry = parseInt(line.substring(6).trim(), 10);
            }
        }

        // Keep incomplete event in buffer
        this.buffer = lines[lines.length - 1];

        return events;
    }

    /**
     * Parse SSE event data
     */
    parseEventData(event: SSEEvent): any {
        try {
            return JSON.parse(event.data);
        } catch (error) {
            console.error('Failed to parse SSE event data:', error);
            return null;
        }
    }

    /**
     * Reset handler state
     */
    reset(): void {
        this.buffer = '';
        this.eventBuffer = [];
    }
}
```

### 4.2 Stream Processor

```typescript
// stream/stream-processor.ts

import { SSEStreamHandler } from './sse-handler';
import { ResponseTranslator } from '../protocol/response-translator';

interface StreamProcessorConfig {
    onChunk: (chunk: any) => void;
    onComplete: (response: any) => void;
    onError: (error: Error) => void;
}

class StreamProcessor {
    private sseHandler: SSEStreamHandler;
    private responseTranslator: ResponseTranslator;
    private config: StreamProcessorConfig;

    constructor(config: StreamProcessorConfig) {
        this.sseHandler = new SSEStreamHandler();
        this.responseTranslator = new ResponseTranslator();
        this.config = config;
    }

    /**
     * Process stream data
     */
    async processStream(response: Response): Promise<void> {
        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error('No response body');
        }

        const decoder = new TextDecoder();

        try {
            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    break;
                }

                // Decode chunk
                const chunk = decoder.decode(value, { stream: true });

                // Process SSE events
                const events = this.sseHandler.processChunk(chunk);

                // Process each event
                for (const event of events) {
                    const eventData = this.sseHandler.parseEventData(event);

                    if (eventData) {
                        // Translate to Codex format
                        const codexResponse = this.responseTranslator.translate(eventData);

                        if (codexResponse) {
                            this.config.onChunk(codexResponse);
                        }
                    }
                }
            }

            // Stream complete
            this.config.onComplete({
                object: 'chat.completion',
                status: 'complete'
            });

        } catch (error) {
            this.config.onError(error as Error);
        } finally {
            reader.releaseLock();
        }
    }

    /**
     * Reset processor state
     */
    reset(): void {
        this.sseHandler.reset();
        this.responseTranslator.reset();
    }
}
```

---

## 5. Main Proxy Server

### 5.1 Express Server

```typescript
// server.ts

import express from 'express';
import cors from 'cors';
import { TraeAuthManager } from './auth/oauth';
import { TokenStore } from './auth/token-store';
import { RequestTranslator } from './protocol/request-translator';
import { ResponseTranslator } from './protocol/response-translator';
import { StreamProcessor } from './stream/stream-processor';

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize components
const authManager = new TraeAuthManager({
    clientId: process.env.TRAE_CLIENT_ID || '',
    redirectUri: process.env.TRAE_REDIRECT_URI || 'http://localhost:3000/callback',
    authEndpoint: 'https://www.trae.ai/oauth/authorize',
    tokenEndpoint: 'https://www.trae.ai/oauth/token'
});

const tokenStore = new TokenStore({
    dbPath: process.env.TOKEN_DB_PATH || './tokens.db',
    encryptionKey: process.env.ENCRYPTION_KEY || crypto.randomBytes(32).toString('hex')
});

const requestTranslator = new RequestTranslator();

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'ok', version: '1.0.0' });
});

// Chat completion endpoint
app.post('/v1/chat/completions', async (req, res) => {
    try {
        // Get authentication headers
        const authHeaders = await authManager.getAuthHeaders();

        // Translate request
        const traeRequest = requestTranslator.translate(req.body);

        // Make request to Trae backend
        const response = await fetch('https://icube-normal.trae.ai/chat', {
            method: 'POST',
            headers: {
                ...authHeaders,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(traeRequest)
        });

        if (!response.ok) {
            throw new Error(`Trae API error: ${response.status}`);
        }

        // Handle streaming
        if (req.body.stream) {
            res.setHeader('Content-Type', 'text/event-stream');
            res.setHeader('Cache-Control', 'no-cache');
            res.setHeader('Connection', 'keep-alive');

            const streamProcessor = new StreamProcessor({
                onChunk: (chunk) => {
                    res.write(`data: ${JSON.stringify(chunk)}\n\n`);
                },
                onComplete: () => {
                    res.write('data: [DONE]\n\n');
                    res.end();
                },
                onError: (error) => {
                    console.error('Stream error:', error);
                    res.end();
                }
            });

            await streamProcessor.processStream(response);
        } else {
            // Non-streaming response
            const data = await response.json();
            res.json(data);
        }

    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({
            error: {
                message: 'Internal server error',
                type: 'server_error',
                code: 'internal_error'
            }
        });
    }
});

// OAuth callback endpoint
app.get('/callback', async (req, res) => {
    const { code } = req.query;

    if (!code) {
        return res.status(400).json({ error: 'Missing authorization code' });
    }

    try {
        // Exchange code for tokens
        // This is a simplified example
        res.json({ success: true });
    } catch (error) {
        console.error('OAuth callback error:', error);
        res.status(500).json({ error: 'Failed to exchange authorization code' });
    }
});

// Start server
app.listen(port, () => {
    console.log(`Trae AI Proxy listening on port ${port}`);
});
```

---

## 6. Configuration

### 6.1 Environment Variables

```bash
# .env

# Server Configuration
PORT=3000
NODE_ENV=development

# Trae OAuth Configuration
TRAE_CLIENT_ID=your_client_id
TRAE_CLIENT_SECRET=your_client_secret
TRAE_REDIRECT_URI=http://localhost:3000/callback

# Token Storage
TOKEN_DB_PATH=./tokens.db
ENCRYPTION_KEY=your_encryption_key_here

# Trae API Endpoints
TRAE_BOOT_ENDPOINT=https://icube-boot.trae.ai
TRAE_CHAT_ENDPOINT=https://icube-normal.trae.ai
TRAE_MODEL_ENDPOINT=https://mcs-boot.trae.ai

# Logging
LOG_LEVEL=debug
```

### 6.2 Docker Configuration

```dockerfile
# Dockerfile

FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build TypeScript
RUN npm run build

# Expose port
EXPOSE 3000

# Start server
CMD ["node", "dist/server.js"]
```

```yaml
# docker-compose.yml

version: '3.8'

services:
  trae-proxy:
    build: .
    ports:
      - "3000:3000"
    environment:
      - PORT=3000
      - NODE_ENV=production
      - TRAE_CLIENT_ID=${TRAE_CLIENT_ID}
      - TRAE_CLIENT_SECRET=${TRAE_CLIENT_SECRET}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    volumes:
      - ./tokens.db:/app/tokens.db
    restart: unless-stopped
```

---

## 7. Testing

### 7.1 Unit Tests

```typescript
// tests/request-translator.test.ts

import { RequestTranslator } from '../protocol/request-translator';

describe('RequestTranslator', () => {
    let translator: RequestTranslator;

    beforeEach(() => {
        translator = new RequestTranslator();
    });

    test('should translate basic request', () => {
        const codexRequest = {
            model: 'gpt-4',
            messages: [
                { role: 'user', content: 'Hello' }
            ]
        };

        const result = translator.translate(codexRequest);

        expect(result.method).toBe('send_message');
        expect(result.params.message.content).toBe('Hello');
        expect(result.params.model_config.model_name).toBe('gpt-4');
    });

    test('should translate model names', () => {
        const codexRequest = {
            model: 'claude-3-opus',
            messages: [
                { role: 'user', content: 'Hello' }
            ]
        };

        const result = translator.translate(codexRequest);

        expect(result.params.model_config.model_name).toBe('claude35_multi_content');
    });

    test('should handle tools', () => {
        const codexRequest = {
            model: 'gpt-4',
            messages: [
                { role: 'user', content: 'Hello' }
            ],
            tools: [
                {
                    type: 'function' as const,
                    function: {
                        name: 'get_weather',
                        description: 'Get weather information',
                        parameters: {
                            type: 'object',
                            properties: {
                                location: { type: 'string' }
                            }
                        }
                    }
                }
            ]
        };

        const result = translator.translate(codexRequest);

        expect(result.params.tools).toHaveLength(1);
        expect(result.params.tools![0].name).toBe('get_weather');
    });
});
```

### 7.2 Integration Tests

```typescript
// tests/integration.test.ts

import request from 'supertest';
import { app } from '../server';

describe('Integration Tests', () => {
    test('health check endpoint', async () => {
        const response = await request(app)
            .get('/health')
            .expect(200);

        expect(response.body.status).toBe('ok');
    });

    test('chat completion endpoint', async () => {
        const response = await request(app)
            .post('/v1/chat/completions')
            .send({
                model: 'gpt-4',
                messages: [
                    { role: 'user', content: 'Hello' }
                ]
            })
            .expect(200);

        expect(response.body.choices).toBeDefined();
    }, 30000); // 30 second timeout
});
```

---

## 8. Deployment

### 8.1 Production Deployment

```bash
# Build and deploy
npm run build
docker build -t trae-proxy .
docker run -d -p 3000:3000 --env-file .env trae-proxy
```

### 8.2 Monitoring

```typescript
// monitoring/metrics.ts

import { Counter, Histogram } from 'prom-client';

// Request counter
export const requestCounter = new Counter({
    name: 'trae_proxy_requests_total',
    help: 'Total number of requests',
    labelNames: ['method', 'status']
});

// Request duration histogram
export const requestDuration = new Histogram({
    name: 'trae_proxy_request_duration_seconds',
    help: 'Request duration in seconds',
    labelNames: ['method'],
    buckets: [0.1, 0.5, 1, 2, 5, 10]
});

// Error counter
export const errorCounter = new Counter({
    name: 'trae_proxy_errors_total',
    help: 'Total number of errors',
    labelNames: ['type']
});
```

---

## 9. Security Considerations

### 9.1 Token Security

- Store tokens in encrypted database
- Use environment variables for secrets
- Implement token rotation
- Set appropriate token expiry

### 9.2 API Security

- Validate all input
- Implement rate limiting
- Use HTTPS only
- Log all requests for audit

### 9.3 Network Security

- Use firewall rules
- Implement IP whitelisting
- Monitor for suspicious activity

---

## 10. Troubleshooting

### 10.1 Common Issues

1. **Authentication Failed**
   - Check token expiry
   - Verify OAuth configuration
   - Check network connectivity

2. **Stream Timeout**
   - Increase timeout configuration
   - Check network stability
   - Implement retry logic

3. **Model Not Found**
   - Verify model name mapping
   - Check available models
   - Update model configuration

### 10.2 Debug Logging

```typescript
// Enable debug logging
process.env.LOG_LEVEL = 'debug';

// Log all requests
app.use((req, res, next) => {
    console.log(`${req.method} ${req.url}`, {
        headers: req.headers,
        body: req.body
    });
    next();
});
```

---

## Appendix A: API Reference

### Chat Completions

```
POST /v1/chat/completions

Request:
{
    "model": "gpt-4",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    "stream": true,
    "temperature": 0.7,
    "max_tokens": 1000
}

Response (streaming):
data: {"id":"msg_xxx","object":"chat.completion.chunk","created":1234567890,"model":"trae-proxy","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"msg_xxx","object":"chat.completion.chunk","created":1234567890,"model":"trae-proxy","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"msg_xxx","object":"chat.completion.chunk","created":1234567890,"model":"trae-proxy","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

## Appendix B: Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| 401 | Unauthorized | Check authentication |
| 429 | Rate Limited | Implement backoff |
| 500 | Internal Error | Check logs |
| 502 | Bad Gateway | Check Trae backend |
| 503 | Service Unavailable | Retry later |
