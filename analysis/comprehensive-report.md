# Trae IDE v2.3.30128 — Comprehensive Reverse Engineering Report

## Executive Summary

Trae IDE v2.3.30128 is a VSCode/Electron-based IDE by ByteDance, built on Electron 39.2.7 (via @aha-kit/electron). The AI backend (`ai-agent`) is a Rust-compiled shared library (127MB on Linux) with significant new capabilities compared to the previously analyzed v1.98.2.

**Key new findings in v2.3.30128:**
- **New AI models**: GPT-5, GPT-5.2, GPT-5.2-codex, GPT-5.3-codex, GPT-5.4, Gemini 3 Pro, Gemini 3.1 Pro, Gemini 3 Flash SOLO, DeepSeek V3.1
- **AWS Bedrock integration** via aws_sdk_bedrockruntime
- **Full browser automation** tools (click, type, screenshot, navigate, etc.)
- **MCP (Model Context Protocol)** with safety checks
- **Sub-agent system** for multi-agent workflows
- **SOLO mode** as a separate product/installer
- **Cloud agent** and **handoff** capabilities for remote sessions
- **Chat memory, skill recommendation, visual editor** features
- **CKG (Code Knowledge Graph)** server (44MB shared library)
- **Trae Sandbox** binary (18MB)

---

## 1. Version Evolution: v1.98.2 → v2.3.30128

| Aspect | v1.98.2 (old) | v2.3.30128 (new) |
|--------|---------------|-------------------|
| Electron | v34.2.0 | v39.2.7 (@aha-kit/electron) |
| VSCode base | 1.107.1 | 1.107.1 (same distro) |
| ai-agent format | Standalone Mach-O binary | Shared library (.so/.dll/.dylib) |
| ai-agent size | ~26.7MB | ~127MB (Linux), much larger |
| AI models | Claude 3.5, DeepSeek V3, Qwen 2.5 | + GPT-5/5.2/5.3/5.4, Gemini 3/3.1, DeepSeek V3.1 |
| Browser tools | None | Full browser automation suite |
| MCP | Referenced | Full implementation with safety checks |
| Sub-agents | None | Multi-agent system with sub-agent invocation |
| Data folder | .icube | .trae (changed!) |
| Build platform | macOS only analyzed | macOS, Windows, Linux, Android, iOS |

---

## 2. Architecture Overview

```
Trae IDE v2.3.30128
├── Electron 39.2.7 (@aha-kit/electron fork)
│   ├── Chromium (renderer process)
│   └── Node.js (main process)
├── VSCode Core (1.107.1 distro)
│   ├── out/main.js (2.4MB - main process + tslib)
│   ├── out/cli.js (225KB - CLI module)
│   └── out/vs/workbench/ (16MB - UI code)
├── ByteDance Custom Modules
│   ├── @byted-icube/ai-modules-chat (13MB - AI chat UI)
│   ├── @byted-icube/desktop-modules (12MB - desktop features)
│   ├── @byted-icube/solo-lite (SOLO mode)
│   ├── @byted-icube/manager-sdk (RPC client)
│   ├── @byted-icube/webcomponents (UI components)
│   ├── @byted/modelcontextprotocol-client (MCP)
│   ├── @byted/modelcontextprotocol-sdk (MCP types)
│   └── @byted-icube/trae-network-client (network)
├── ai-agent (Rust shared library, 127MB)
│   ├── libai_agent.so (Linux)
│   ├── ai-agent (macOS, Mach-O)
│   └── ai-agent.dll (Windows)
├── ckg_server (Code Knowledge Graph, 36MB binary)
│   └── libckg.so (44MB shared library)
├── trae-sandbox (18MB binary)
└── Built-in Extensions
    ├── ai-completion (AI code completion with server.js)
    ├── byted-icube.python-enhance
    ├── byted-icube.java-helper
    ├── byted-icube.go-enhance
    ├── byted-icube.integrations-extended (with Skia canvas)
    ├── cloudide.icube-remote-ssh
    ├── cloudide.icube-devtool-ports
    ├── cloudide.icube-im-bridge (Feishu integration)
    ├── terminal-suggest
    └── ... (20+ more)
```

---

## 3. ai-agent Deep Analysis

### 3.1 Binary Format

| Platform | Format | Size | Architecture |
|----------|--------|------|--------------|
| Linux x64 | ELF shared library (.so) | 127MB | x86_64 |
| Linux arm64 | ELF shared library (.so) | ~127MB | aarch64 |
| macOS ARM64 | Mach-O dylib | ~130MB | arm64 |
| Windows x64 | PE32+ DLL (ai_agent.dll) | 144MB | x86_64 |

**Key change from v1.98.2**: ai-agent is now a **shared library** (loaded via `dlopen`/`LoadLibrary`) instead of a standalone binary. This allows the Electron main process to load it directly.

### 3.2 AI Model Support

| Model | Version Reference | Notes |
|-------|-------------------|-------|
| Claude 3.5 | `claude35_multi_content`, `claude-3-5-` | Primary model |
| GPT-5 | `gpt-5` | New |
| GPT-5.2 | `gpt-5.2` | New |
| GPT-5.2 Codex | `gpt-5.2-codex` | New - coding specialized |
| GPT-5.3 Codex | `gpt-5.3-codex` | New - coding specialized |
| GPT-5.4 | `gpt-5.4` | New |
| GPT-4.1 | `gpt-4.1` | New |
| Gemini 3 Pro | `gemini-3-pro` | New |
| Gemini 3.1 Pro | `gemini-3.1-pro` | New |
| Gemini 3 Flash SOLO | `gemini-3-flash-solo` | New - SOLO-specific |
| Gemini 2.0 | `gemini-2.0` | New |
| Gemini 1.5 | `gemini-1.5` | New |
| DeepSeek V3 | `deepseek-v3` | Existing |
| DeepSeek V3.1 | `deepseek-v3.1__max` | New |
| Doubao for Auto | `doubao-for-auto` | New - ByteDance Doubao for autonomous mode |
| Doubao-Seed-2.0-Code | Codename "penelope" | ByteDance internal coding model |
| Qwen 2.5 | `qwen2.5` | Existing (commit messages) |
| Qwen 32 | `qwen32_generate_commit_message` | Existing (commit messages) |
| OpenRouter | `provider/openrouter.rs` | Multi-model proxy gateway |

### 3.3 LLM Provider Architecture

The `llm-client` crate implements direct API clients for 7 providers:
- **Anthropic** (`provider/anthropic.rs`) — Full Claude API with cache control, streaming
- **OpenAI** (`provider/openai.rs`) — GPT series API
- **Google Gemini** (`provider/gemini.rs`) — Gemini API
- **DeepSeek** (`provider/deepseek.rs`) — DeepSeek API
- **AWS Bedrock** (`provider/aws.rs`) — Bedrock Runtime SDK
- **Volcengine** (`provider/volcengine.rs`) — ByteDance cloud AI (Doubao models)
- **OpenRouter** (`provider/openrouter.rs`) — Multi-model proxy gateway

### 3.4 AWS Bedrock Integration

The ai-agent binary includes the full **AWS SDK for Rust** (`aws_sdk_bedrockruntime`), enabling direct calls to Amazon Bedrock for LLM inference. Key components:
- `ConverseStream` API support
- `ConverseStreamEndpointParams`
- `ConverseStreamResponseDeserializer`
- `AmazonBedrockFrontendService`
- AWS credential chain (env vars, profile, IAM, SSO, web identity)

### 3.4 AWS Bedrock Integration

### 3.5 Tool System
- `view_file` / `read_file` — File reading
- `create_file` / `write_file` — File creation
- `edit_file` / `apply_patch` — File editing (with search-replace and multi-edit)
- `delete_file` — File deletion
- `search_by_keyword` / `search_by_regex` — Code search
- `search_by_reference` / `search_by_definition` — Symbol search
- `run_command` — Shell command execution
- `web_search` — Web search
- `web_fetch` — Web page fetching
- `fast_apply` — Fast code application
- `list_dir` — Directory listing
- `terminal` — Terminal access
- `todo_write` — Task management

#### Core Tools
- `browser_navigate` / `browser_navigate_back` / `browser_navigate_forward`
- `browser_click` / `browser_type` / `browser_press_key`
- `browser_screenshot` / `browser_take_screenshot`
- `browser_snapshot` — Page state snapshot
- `browser_evaluate` — JavaScript execution
- `browser_select_option` / `browser_fill` / `browser_fill_form`
- `browser_hover` / `browser_drag` / `browser_scroll`
- `browser_upload_file` / `browser_download`
- `browser_wait_for` / `browser_handle_dialog`
- `browser_get_attribute` / `browser_get_bounding_box` / `browser_get_input_value`
- `browser_is_visible` / `browser_is_enabled` / `browser_is_checked`
- `browser_lock` / `browser_unlock` — Browser session locking
- `browser_hand_over` — Transfer control to user

#### Browser Automation Tools (NEW)
- `toolcall_agent_finish` — Complete agent execution
- `toolcall_ask_user_question` — Interactive user questions
- `toolcall_notify_user` — User notifications
- `toolcall_apply_patch` — Apply code patches
#### Agent Tools (NEW)

- Sub-agent invocation system

### 3.6 AI Agent Internal Architecture (from strings analysis)

**Domain Layer** (`modules/ai-agent/src/domain/`):
- `apply/` — Code apply/edit operations
- `model/` — Model management, config caching, LLM streaming, token counting
- `prompt/` — Prompt engineering (includes `count_claude.rs` for Claude token counting)
- `ralph_loop/` — Agent loop execution
- `skill/` — Skill system with trial store
- `agent_v3/` — Agent v3 with tool call accumulator
- `understanding/ckg/` — Code knowledge graph integration
- `plan/` — Planning system (simple_service_v2 with tool cache)

**Infrastructure Layer** (`modules/ai-agent/src/infrastructure/`):
- `adapter/` — IDE command adapters, custom model proxy, AB test config
- `ahavm/` — AHA virtual machine integration
- `dal/` — Data access layer with SQLite (30+ tables)
- `vm/manager/` — VM/runtime environment management
- `toolhost/` — Tool hosting system

**Chat Event System** (SSE):
- Events: ChatDone, Heartbeat, UserMessage, SessionTitle, AgentCall, AgentWakeup, Notification, ModelConfig, WorktreeCheck, WorktreeCreated, NeedSandboxUpgrade, ContextUsage

**Database Tables** (from 60+ migrations, 2025-03 to 2026-03):
- agent, agent_run, chat_message, chat_session, chat_turn, checkpoint, core_memory, history_v2, mcp_server_agent_relation, plan_item, project, rules_attachment, scheduled_tasks, session_project, task, todo_list, user_configuration, worktree, model_config_cache

**IPC Port**: 40005 (defined in `meta.json`)

### 3.7 MCP (Model Context Protocol)

Full MCP implementation with:
- `mcp_server` — Server management
- `mcp_tool` — Tool registration and invocation
- `mcp_safety` — Safety checks for MCP tools
- Dynamic tool loading (`dynamic_tool_loading_search`, `dynamic_tool_loading_filesystem`)
- Custom tool support (`v3_custom_tool_list`)

### 3.8 Internal Architecture (from symbol analysis)

- **47 DDD domain modules**, 15 shared crates
- **JSON-RPC over AHA IPC** (Unix domain sockets) with `jsonrpsee` library
- **7 exported C-ABI functions**: `ai_agent_ipc_*`, `BP_*`
- **80+ dynamic feature flags** for A/B testing
- Internal Git dependency: `aha-ipc-0152e3c7ae4208d9`
- Codename: `icube_server_rs` with `marscode` legacy
- **AES-256-GCM** via `alkali` crate (libsodium wrapper) in `llm-client/src/crypto/crypto.rs`
- **OpenSSL** statically linked for TLS

### 3.9 Additional AI Model Providers

| Provider | Evidence | Notes |
|----------|----------|-------|
| **Volcengine** | ByteDance cloud AI | ByteDance's own cloud AI platform |
| **Doubao-Seed-2.0-Code** | Codename "penelope" | ByteDance internal coding model |
| **Doubao-for-Auto** | `doubao-for-auto` | ByteDance Doubao for autonomous mode |
| **GPT-5 detection** | `is_gpt5` flag | Explicit GPT-5 detection flag |
| **Gemini reasoning** | `gemini-reasoning.encrypted` | Encrypted reasoning parameters |
| **OpenRouter** | `provider/openrouter.rs` | Multi-model proxy gateway |

### 3.10 Security Mechanisms

- **AES-256-GCM** — Data encryption (via alkali library) for model parameters
- **SQLCipher** — Encrypted SQLite database
- **AWS Sigv4** — Request signing for Bedrock
- **Linux namespace sandbox** + Lite VM for code execution
- **Windows sandbox** — Job Objects + `trae-sandbox.exe` (1.1MB) with `sbox_sdk.dll` (1.9MB), both x64 and x86 DLLs; file/network access controls; command red list; sandbox_rw_list/sandbox_ro_list
- **Content filter engine** — Rule-based content filtering
- **VBVirtualize** — Code virtualization (NOT present in Linux x64 build, may be macOS-only)
- **Certificate validation** — TLS certificate checking
- **Memory zeroing** — Secure memory cleanup
- **Command blacklist** — `in_enterprise_command_blacklist`
- **Manual confirmation** — `need_manual_confirm` for dangerous operations
- **Workspace boundary** — `file_outside_workspace` checks

### 3.7 Developer Information Leakage

Multiple developer machine paths found in the binary:
- `/root/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/` (Linux build)
- `/Users/cmt12_v_hksab/.cargo` (macOS build)
- `/Users/cmt12_v_ijvu/.cargo`
- `/Users/d3fe33daf08d/.cargo`
- `/Users/iOSAndroid_ttp_1_4_v_bedab/.cargo`
- `/Users/iOSAndroid_ttp_1_4_v_ooxba/.cargo`
- `/Users/iOS_ttp_2_6_10_v_oqza/.cargo`
- `/Users/iOS_ttp_2_6_10_v_qhap/.cargo`
- `/Users/RmOu164_v_rfkz/.cargo`
- `/Users/runner/.cargo` (CI/CD runner)

The obfuscated usernames suggest ByteDance's internal CI/CD system generates random usernames.

---

## 4. CLI and Main Process Analysis

| File | Old Size (v1.98.2) | New Size (v2.3.30128) | Notes |
|------|---------------------|------------------------|-------|
| cli.js | 649KB | 225KB | Smaller - may be restructured |
| main.js | 1.27MB | 2.4MB | Much larger - now includes actual app code |
| workbench.desktop.main.js | N/A | 16MB | Main UI code |

**Key finding**: The old main.js was just tslib (TypeScript helpers). The new main.js at 2.4MB contains actual VSCode main process code, not just tslib.

---

## 5. Extension System

### 5.1 Custom Extension Gallery

Trae uses a **multi-source extension marketplace**:
- **Open VSX** as primary marketplace
- **Microsoft Marketplace** for search only
- **Trae's own mirror** at `open-vsx.trae.ai`
- **Internal ByteDance marketplace** for proprietary extensions
- **Pylance explicitly banned** (`BANNED_BY_MS`), replaced by **BasedPyright**

### 5.2 MCP Integration Details

- Forked Anthropic SDK: `@byted/modelcontextprotocol-client` v2.0.0-alpha.2.byted.5
- Dedicated MCP marketplace endpoints
- SOLO-mode builtin MCP extension
- MCP limits: **40 tools max**, **8000 tokens max**
- Per-agent MCP server configuration with `mcp_server_agent_relation` database table

### 5.2 Built-in Extensions

Key ByteDance extensions:
- **ai-completion** — AI code completion with embedded server (16MB server.js, obfuscated; includes tree-sitter parsers for 14+ languages, custom tokenizers codeds/codez, and "Cue" system for inline suggestions)
- **byted-icube.python-enhance** — Enhanced Python support
- **byted-icube.java-helper** — Java assistance
- **byted-icube.go-enhance** — Go assistance
- **byted-icube.integrations-extended** — Extended integrations with Skia canvas (30MB native)
- **byted-icube.node-helper** — Node.js assistance
- **cloudide.icube-remote-ssh** — Remote SSH development
- **cloudide.icube-devtool-ports** — DevTools port management
- **cloudide.icube-im-bridge** — Feishu (Lark) IM integration
- **mermaid-chat-features** — Mermaid diagram rendering in chat
- **terminal-suggest** — Terminal command suggestions

---

## 6. SOLO vs IDE

| Aspect | TRAE IDE | TRAE SOLO |
|--------|----------|-----------|
| Version | 2.3.30128 | 2.3.30125 |
| Description | "Your 10x AI Coding Engineer" | "Think Anytime, Ship Everywhere" |
| Platforms | macOS, Windows, Linux | macOS, Windows (+ Mobile) |
| Mobile | No | iOS, Android |
| Linux support | .deb, .rpm, .tar.gz | Not available |
| Badge | None | "BETA" |
| ai-agent | Likely same | Likely same |

---

## 7. Network Communication

### 7.1 API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `icube-normal.trae.ai` | AI backend API |
| `core-normal.trae.ai` | Core API |
| `coresg-normal.trae.ai` | Singapore region API |
| `api-us-east.trae.ai` | US East region API |
| `icube-normal.traeapi.us` | US region icube API |
| `core-normal.traeapi.us` | US region core API |
| `/icube/api/v1/native/version/trae/latest` | Version/manifest API |
| `/cloudide/api/v3/trae/*` | Cloud IDE APIs |
| `bytedance.net` / `byteintl.net` / `tiktok-row.net` | Internal ByteDance endpoints |
| `aipa-api.bytedance.net/api/get-dep-info` | Dependency info API |
| `aipa.bytedance.net/api/file-upload` | File upload API |
| `aipa-pai-webview.gf.bytedance.net` | PAI webview |
| `promptpilot.volcengine.com/aipa` | Prompt Pilot (Volcengine) |
| `trae.mobile.volcapp.com/preview` | Trae mobile preview |
| `mcs.zijieapi.com` | Monitoring/analytics |
| `cdn-tos-cn.bytedance.net/obj/aipa-tos/` | CDN assets |

### 7.5 IPC Configuration

The ai-agent listens on **port 40005** for IPC communication (defined in `meta.json`). Environment variables:
- `AI_NATIVE_ENV`: desktop | plugin_remote | desktop_ssh
- `TRAE_RESOLVE_TYPE`: remote | ssh
- `DB_PATH`: `%ICUBE_MODULAR_DATA_DIR%\ai-agent\database.db`
- `FILE_BASE_DIR`: `%ICUBE_MODULAR_DATA_DIR%\ai-agent\snapshot`

### 7.6 Process Monitoring

Memory monitoring with configurable thresholds:
- 8 GB report threshold, 1.5 GB notification threshold
- Single process monitors for: icube-manager, ckg_server, ai-agent, ai-completion/ai-server
- Memory limits: 2048 MB per monitored process
- CPU limits: 100% per process

Four deployment zones with separate API endpoints:
- **normal** — Default/global
- **SG** — Singapore
- **US** — United States
- **USTTP** — US (TikTok Technical Platform?)

Each zone has separate endpoints for: iCube, agent, copilot, and marketplace services.

### 7.2 CDN Infrastructure

| CDN Domain | Region | Purpose |
|------------|--------|---------|
| `lf-cdn.trae.ai` | Singapore | Primary download CDN |
| `lf-cdn.trae.com.cn` | China | China download CDN |
| `lf-static.traecdn.us` | US | US download CDN |
| `lf16-web-neutral.traecdn.ai` | Singapore | Website static assets |

### 7.3 WebSocket

The ai-agent communicates over WebSocket (previously port 40005, may have changed in v2).

---

## 8. Data Storage

| Path | Purpose |
|------|---------|
| `~/.trae/` | Main data directory (changed from `.icube`) |
| `~/.trae/ai-agent/database.db` | SQLite + SQLCipher encrypted database |
| `~/.icube/` | Legacy data directory (still referenced) |

---

## 9. Android APK Analysis

- **Package**: `com.bytedance.trae.overseas`
- **Version**: 0.0.2 (early release)
- **Size**: 80MB
- **DEX files**: 7 classes (61MB total)
- **Key packages**:
  - `com.bytedance.trae.conversation` — Chat/conversation system
  - `com.bytedance.trae.conversation.brainstorm` — Brainstorm feature
  - `com.bytedance.trae.conversation.chat` — Chat UI with agent content blocks
  - `com.bytedance.trae.login` — Login service
  - `com.bytedance.trae.init` — Initialization tasks
  - `com.bytedance.trae.apm` — APM monitoring
  - `com.bytedance.trae.im` — IM (instant messaging) network
  - `com.bytedance.trae.push` — Push notifications
- **Firebase**: Analytics, annotations, datatransport, encoders
- **Lynx**: ByteDance's Lynx rendering framework
- **Fresco**: Image loading (Facebook's library)
- **SoLoader**: Native library loading (Facebook's library)

---

## 10. Key Discoveries Summary

1. **Massive AI model expansion**: From 3 models (Claude 3.5, DeepSeek V3, Qwen 2.5) to 15+ models including GPT-5 series and Gemini 3 series
2. **AWS Bedrock integration**: Direct access to Amazon's managed AI service
3. **Full browser automation**: Playwright-like browser control for AI agents
4. **MCP support**: Model Context Protocol for extensible tool system
5. **Sub-agent architecture**: Multi-agent orchestration system
6. **Data folder migration**: From `.icube` to `.trae` (branding alignment)
7. **ai-agent as shared library**: Changed from standalone binary to .so/.dll/.dylib
8. **CKG (Code Knowledge Graph)**: 44MB shared library for code understanding
9. **Sandbox system**: 18MB binary for code execution sandboxing
10. **Mobile apps**: iOS and Android SOLO apps with brainstorm and chat features
11. **Developer info leakage**: Multiple CI/CD runner paths and obfuscated usernames
12. **Feishu/Lark integration**: IM bridge for enterprise messaging
13. **Cloud IDE**: Remote development and session handoff capabilities
14. **Skia canvas**: 30MB native rendering for integrations
15. **ByteDance internal monitoring**: Slardar, AppLog, APM systems throughout
16. **Volcengine + Doubao-Seed-2.0-Code**: ByteDance's own AI models (codename "penelope")
17. **Pylance banned**: Microsoft's Pylance explicitly blocked, replaced by BasedPyright
18. **DeepWiki**: Repository documentation/knowledge system
19. **Scheduled tasks**: Cron-like autonomous task scheduling with persistent execution
20. **Core memory**: Persistent memory blocks for agent context across sessions
21. **Handoff protocol**: Local-to-cloud and cloud-to-local session migration
22. **80+ feature flags**: Extensive A/B testing infrastructure for AI features
23. **Content filter engine**: Rule-based content filtering for AI outputs
