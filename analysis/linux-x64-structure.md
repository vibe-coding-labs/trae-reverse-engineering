# Trae IDE v2.3.30128 - ai-agent Binary Analysis (Linux x64)

**Binary:** `libai_agent.so` (127 MB ELF shared library)
**Strings file:** `data/ide/linux-x64/ai-agent-strings.txt` (~958,188 lines)
**Symbols file:** `data/ide/linux-x64/ai-agent-symbols.txt` (366 dynamic symbols)
**Analysis date:** 2026-05-27

---

## 1. Executive Summary

The ai-agent binary (`libai_agent.so`) is the Rust-based AI backend for Trae IDE, internally known as `icube_server_rs`. It has evolved significantly from v1.98.2, with major new features including:

- **SOLO Agent mode** (renamed from "solo_coder"), a fully autonomous coding agent
- **MCP (Model Context Protocol)** support with per-agent MCP server configuration
- **Browser automation tools** (30+ browser_use_* tools for web interaction)
- **Multi-agent architecture** (sub-agents, agent orchestration, agent_v3)
- **DeepWiki** integration for repository documentation
- **Scheduled tasks** (cron-like autonomous task scheduling)
- **Cloud/Remote agent** with handoff protocol (local-to-cloud session migration)
- **Supabase and Stripe** tool integrations
- **Scheduled tasks** with persistent execution tracking
- **Core memory** system for persistent agent context
- **Skill recommendation** system with trial skill installation
- **Enterprise agent** support with tenant isolation

---

## 2. AI Model References

### 2.1 LLM Providers (Struct Definitions in Binary)

| Provider | Source File | Struct Names |
|----------|-----------|--------------|
| **Anthropic** | `crates/llm-client/src/provider/anthropic.rs` | `AnthropicModel`, `AnthropicModelListResponse` |
| **OpenAI** | `crates/llm-client/src/provider/openai.rs` | `OpenAIModelListResponse` |
| **DeepSeek** | `crates/llm-client/src/provider/deepseek.rs` | `DeepseekModel` |
| **OpenRouter** | `crates/llm-client/src/provider/openrouter.rs` | `OpenrouterModel`, `OpenrouterModelListResponse` |
| **Google Gemini** | `crates/llm-client/src/provider/gemini.rs` | `GeminiModel`, `GeminiModelListResponse` |
| **AWS Bedrock** | `crates/llm-client/src/provider/aws.rs` | `AWSModelSummary`, `AWSModelListResponse`, `AWSModelLifecycle` |
| **Volcengine (ByteDance)** | `crates/llm-client/src/provider/volcengine.rs` | `VolcengineContextCreateResponse`, `VolcengineError` |

### 2.2 Specific Model References

- **Claude series**: `claude-3`, `claude-4` (gateway-style `anthropic/claude-3`), extended thinking support (`thinking_delta`, `signature_delta`, `thinking` blocks, `cache_creation_input_tokens`, `cache_read_input_tokens`)
- **GPT series**: `gpt-4`, `gpt-5` (gateway-style `openai/gpt-5`), config flag `is_gpt5`
- **DeepSeek**: `deepseek-chat`, `deepseek-V3` (for commit message generation)
- **Qwen**: `qwen2.5`, `qwen32` (for commit message generation: `git_qwen32_generate_commit_message`)
- **Doubao (ByteDance internal)**: `doubao-for-auto` (codename: `penelope`), `Doubao-Seed-2.0-Code` (codename: `penelope`)
- **Google Gemini**: `google/gemini-reasoning` (referenced with `.encrypted` suffix, suggesting encrypted prompt templates)
- **OpenRouter**: uses `/medium` path, acts as routing proxy to other models

### 2.3 New Models Since v1.98.2

- **Claude 4** (implied by `anthropic/claude-3` gateway format supporting newer versions)
- **GPT-5** (explicitly referenced in gateway identifiers and `is_gpt5` config flag)
- **Google Gemini** (new provider: `gemini.rs`, `GeminiModel` struct)
- **Google Gemini Reasoning** (`google/gemini-reasoning.encrypted`)
- **Doubao-Seed-2.0-Code** (ByteDance internal, codename "penelope")
- **AWS Bedrock models** (full AWS Bedrock Runtime SDK integration with ConverseStream API)

### 2.4 LLM Client Architecture

The `llm-client` crate supports:
- **Streaming responses** with SSE/event-stream parsing
- **Extended thinking** (Claude): `thinking_delta`, `signature_delta`, thinking block verification
- **Reasoning**: `LLMClientReasoningRaw`, `LLMClientReasoningDetailsRaw` with effort levels
- **Cache control**: `cache_creation_input_tokens`, `cache_read_input_tokens`, `CacheControl`
- **Image understanding**: `LLMClient Request Image` with format validation
- **Tool calls**: `LLMClientToolCall`, `LLMClientFunctionCallRaw`, `LLMClientToolCallExtraContent`
- **Encryption**: `crates/llm-client/src/crypto/crypto.rs` (AES-256-GCM via alkali library)
- **Model parameter encryption**: `encrypted_model_params` field in history config

---

## 3. Tool Names (Complete Inventory)

### 3.1 File Operation Tools

| Tool | Internal ID | Description |
|------|------------|-------------|
| `view_file` | `toolcall_view_file` | View file contents |
| `view_files` | `toolcall_view_files` | View multiple files (batch) |
| `view_folder` | `toolcall_view_folder` | List directory contents |
| `read` | `toolcall_read` | Read file (with dedup, truncation, image/video support) |
| `create_file` | `toolcall_create_file` | Create new file |
| `edit_file` | `toolcall_edit_file` | Edit existing file (search/replace) |
| `edit_file_update` | `toolcall_edit_file_update` | Update file with block-level editing |
| `edit_file_fast_apply` | `toolcall_edit_file_fast_apply` | Fast apply edit (FastApply system) |
| `edit_file_rewrite` | `toolcall_edit_file_rewrite` | Rewrite entire file |
| `edit_file_rename` | `toolcall_edit_file_rename` | Rename file |
| `delete_file` | `toolcall_delete_file` | Delete file |
| `write` | `toolcall_write` | Write content to file |
| `write_to_file` | `toolcall_write_to_file` | Write to specific file (with continue_write support) |
| `write_to_document` | `toolcall_write_to_document` | Write to document (UI builder) |
| `edit_document_update` | `toolcall_edit_document_update` | Edit document update |
| `edit_document_fast_apply` | `toolcall_edit_document_fast_apply` | Fast apply document edit |
| `multi_edit` | `toolcall_multi_edit` | Edit multiple locations in one call |
| `apply_patch` | `toolcall_apply_patch` | Apply diff/patch |
| `edit` | `toolcall_edit` | Generic edit operation |
| `file_exists` | `toolcall_file_exists` | Check file existence |
| `file_search` | `toolcall_file_search` | Search for files by name |
| `ls` | `toolcall_ls` | List directory |

### 3.2 Search Tools

| Tool | Internal ID | Description |
|------|------------|-------------|
| `search_by_keyword` | `toolcall_search_by_keyword` | Full-text keyword search |
| `search_by_definition` | `toolcall_search_by_definition` | Search by symbol definition |
| `search_by_reference` | `toolcall_search_by_reference` | Search by symbol reference |
| `search_by_regex` | `toolcall_search_by_regex` | Regex search |
| `search_codebase` | `toolcall_search_codebase` | Semantic code search |
| `search_directory` | (inline) | Directory search |
| `grep` | `toolcall_grep` | Grep (ripgrep-based, with `v3_grep_*` config) |
| `glob` | `toolcall_glob` | Glob pattern matching (ripgrep-based with `v3_glob_*` config) |

### 3.3 Execution Tools

| Tool | Internal ID | Description |
|------|------------|-------------|
| `run_command` | `toolcall_run_command` | Execute shell command |
| `shell` | `toolcall_shell` | Shell execution |
| `send_to_command` | `toolcall_send_to_command` | Send input to running command |
| `stop_command` | `toolcall_stop_command` | Stop running command |
| `check_command_status` | `toolcall_check_command_status` | Check command execution status |
| `check_command_status_v3` | `toolcall_check_command_status_v3` | V3 status check |

### 3.4 Browser Automation Tools (NEW - 30+ tools)

| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to URL |
| `browser_navigate_back` | Go back |
| `browser_navigate_forward` | Go forward |
| `browser_click` | Click element |
| `browser_type` | Type text into element |
| `browser_fill` | Fill form field |
| `browser_fill_form` | Fill entire form |
| `browser_press_key` | Press keyboard key |
| `browser_scroll` | Scroll page |
| `browser_snapshot` | Take accessibility snapshot |
| `browser_take_screenshot` | Take screenshot (with OCR auto-read) |
| `browser_hover` | Hover over element |
| `browser_drag` | Drag element |
| `browser_select_option` | Select dropdown option |
| `browser_evaluate` | Execute JavaScript |
| `browser_get_attribute` | Get element attribute |
| `browser_get_bounding_box` | Get element bounding box |
| `browser_get_input_value` | Get input element value |
| `browser_handle_dialog` | Handle browser dialogs |
| `browser_highlight` | Highlight element |
| `browser_is_checked` | Check checkbox state |
| `browser_is_enabled` | Check element enabled state |
| `browser_is_visible` | Check element visibility |
| `browser_lock` / `browser_unlock` | Lock/unlock browser state |
| `browser_network_requests` | Monitor network requests |
| `browser_console_messages` | Read console messages |
| `browser_upload_file` | Upload file to browser |
| `browser_wait_for` | Wait for condition |
| `browser_waiting_for_user_interaction` | Wait for user interaction |
| `browser_tabs` | List/manage browser tabs |
| `browser_reload` | Reload page |
| `browser_resize` | Resize browser window |
| `browser_search` | Search within page |

### 3.5 Agent/Workflow Tools

| Tool | Description |
|------|-------------|
| `agent_finish` | Signal agent completion |
| `run_agent` | Run a sub-agent |
| `complete` | Complete current task |
| `task` | Create/manage tasks |
| `schedule` | Schedule periodic tasks |
| `create_requirement` | Create project requirement |
| `deploy_to_remote` | Deploy to remote environment |
| `open_preview` | Open preview in IDE |
| `open_preview_and_wait_for_error` | Preview with error capture |
| `get_preview_console_logs` | Get preview console logs |
| `init_env` | Initialize environment |

### 3.6 UI/Interaction Tools

| Tool | Description |
|------|-------------|
| `show_widget` | Display UI widget |
| `pure_show_widget` | Display widget (pure) |
| `show_widget_read_me` | Widget with readme |
| `show_diff` | Show diff view |
| `ask_user_question` | Ask user a question with options |
| `notify_user` | Notify user with message |
| `response_to_user` | Send text response to user |
| `finish` | Finish conversation |

### 3.7 Memory/Knowledge Tools

| Tool | Description |
|------|-------------|
| `manage_core_memory` | Manage persistent core memory blocks |
| `update_shallow_memento` | Update shallow memento |
| `condense_shallow_memento` | Condense shallow memento |
| `todo_write` | Write/update todo list |
| `web_search` | Web search |
| `web_fetch` | Fetch URL content |
| `get_diagnostics` | Get IDE diagnostics/lint errors |
| `get_llm_config` | Get LLM configuration |
| `generate_image` | Generate image via API (`/api/ide/v1/text_to_image`) |

### 3.8 External Service Tools (NEW)

| Tool | Description |
|------|-------------|
| `supabase_apply_migration` | Apply Supabase database migration |
| `supabase_get_project` | Get Supabase project info |
| `supabase_get_tables` | Get Supabase table list |
| `stripe_get_config` | Get Stripe configuration |
| `diffs` | View diffs |
| `diffview` | Diff view |
| `commit` | Git commit |
| `exit_plan_mode` | Exit plan mode |

### 3.9 MCP (Model Context Protocol) Tools

| Tool | Description |
|------|-------------|
| `run_mcp` | Execute MCP server tool |

MCP integration details:
- `mcp_server_list` - available MCP servers
- `mcp_server_name_list` - names of MCP servers
- `mcp_server_agent_relation_table` - database table linking agents to MCP servers
- `mcp_server_ids` - list of MCP server IDs per agent
- `Failed to parse MCP server relation` - error handling
- `Tool definition tag is not MCP type` - validation
- `run_mcp_result_max_char_count` - output truncation config
- `run_custom_tool_output_max_char_count` - custom tool output limit

### 3.10 Dynamic Tool Configuration Flags

The binary contains numerous feature flags controlling tool availability:

| Flag | Purpose |
|------|---------|
| `enable_browser_tools` | Enable browser automation |
| `enable_browser_screenshot_auto_read` | Auto-read screenshots with OCR |
| `enable_read_tool_image_to_text` | Image-to-text in read tool |
| `enable_read_tool_video_to_text` | Video-to-text in read tool |
| `v3_enable_web_fetch_tool` | Enable web fetch |
| `v3_enable_skill_tool` | Enable skill tools |
| `v3_enable_knowledge_tool` | Enable knowledge tools |
| `v3_enable_file_diff_resolver` / `v2` | File diff resolver versions |
| `dynamic_tool_loading_search` | Dynamic tool loading for search |
| `dynamic_tool_loading_filesystem` | Dynamic tool loading for filesystem |
| `replace_edit_tools_by_apply_patch` | Replace edit with apply_patch |
| `v3_replace_edit_tools_by_edit_file_update` | Replace edit with update |
| `v3_use_edit_file_update_replace_blocks` | Use update for blocks |
| `v3_enable_multi_edit_tool` | Multi-edit tool |
| `v3_use_view_files_tool` | View files batch tool |
| `v3_custom_tool_list` | Custom tool list |
| `enable_edit_tool_fuzzy_match` | Fuzzy matching in edit tool |
| `enable_nfc_prefill_agent_name` | NFC agent name prefill |
| `v3_sub_agent_route_enable` | Sub-agent routing |
| `v3_parallel_agents_disabled` | Disable parallel agents |

---

## 4. MCP (Model Context Protocol) References

MCP is a major new addition in v2.3.30128, not present in v1.98.2.

### 4.1 MCP Architecture

- **Database table**: `mcp_server_agent_relation` (created migration `m20250328_000002`, modified `m20250825_000001`, `m20251109_000001`)
- **Per-agent MCP**: Each agent can have its own set of MCP servers (`mcp_server_ids`, `mcp_server_list`)
- **MCP tool execution**: `run_mcp` tool with `run_mcp_result_max_char_count` truncation
- **MCP type validation**: `Tool definition tag is not MCP type` - distinguishes MCP tools from builtin
- **MCP in builders**: `builder_with_mcp_v3` - SOLO Builder agents can use MCP tools
- **Custom tools**: `run_custom_tool_output_max_char_count` for non-MCP custom tools

### 4.2 MCP Configuration Flow

1. Agent is created/selected with associated MCP server list
2. `mcp_server_name_list` populated from configuration
3. MCP tools loaded dynamically per agent
4. `run_mcp` executes MCP server tool calls
5. Results truncated to `run_mcp_result_max_char_count`

---

## 5. Security Mechanisms

### 5.1 Encryption

- **AES-256-GCM**: Implemented via alkali library (`crypto_aead_aes256gcm_encrypt`)
  - Source: `crates/llm-client/src/crypto/crypto.rs`
  - Used for model parameter encryption (`encrypted_model_params`)
  - Error: "An unexpected error occurred in `crypto_aead_aes256gcm_encrypt`"
- **TLS**: rustls library with full TLS 1.3 support (X25519, secp256r1/384r1/521r1, FFDHE)
- **SQLCipher**: Encrypted SQLite database at `$HOME/.icube/ai-agent/database.db`

### 5.2 Code Obfuscation

- **VBVirtualize/VMProtect**: NOT found in this Linux x64 build (was present in older Windows builds)
- No Themida, OLLVM, or other obfuscation markers detected
- The binary uses standard Rust compilation without virtualization protection

### 5.3 Sandbox

- **Linux namespace sandbox**: `crates/sandbox/src/linux/` with kernel, namespace, profile, and semver modules
- Sandbox features: `sandbox_mode_enabled`, `sandbox_filesystem_config`, `sandbox_network_config`
- Command execution in sandbox: `toolcall_run_command_in_sandbox_ai_config`
- Sandbox awareness: `sandbox_awareness_enabled`
- **VSOCK**: Virtual socket communication (`crates/net-bridge/src/http/client/vsock.rs`)
- **Lite VM**: `icube_ai_agent_lite_vm_startup`, `icube_ai_agent_lite_vm_stream_error`

### 5.4 Content Security

- **Content filter**: `crates/content-filter/src/engine.rs`
- Rule-based filtering: `Content blocked by rule ''`, `Content desensitized by rule ''`
- Filter timeout handling: `Filter timeout for rule ''`
- `privacy_mode` domain for privacy controls

### 5.5 Authentication

- AWS SDK credential chain (env vars, ECS, EC2 metadata, profile, SSO, web identity)
- Volcengine authentication: `AuthenticationError`, `Volcengine Connection Test Passed`
- Custom model proxy: `crates/custom-model-proxy-client/` with WebSocket tunneling

---

## 6. Internal Module Structure

### 6.1 Project Code Name

- **icube_server_rs** (Rust monorepo)
- **marscode** (legacy name still referenced)

### 6.2 DDD Domain Modules (47 domains)

```
ai_agent::domain::agent
ai_agent::domain::agent_process_v3
ai_agent::domain::agent_v3
ai_agent::domain::apply
ai_agent::domain::chat
ai_agent::domain::chat_message
ai_agent::domain::chat_session
ai_agent::domain::chat_turn
ai_agent::domain::commercial
ai_agent::domain::content_security
ai_agent::domain::context_asset
ai_agent::domain::context_resolver
ai_agent::domain::deepwiki         (NEW)
ai_agent::domain::diagnostic
ai_agent::domain::docset           (NEW)
ai_agent::domain::environment_context
ai_agent::domain::fs
ai_agent::domain::general_chat
ai_agent::domain::git
ai_agent::domain::handoff          (NEW)
ai_agent::domain::history_v2
ai_agent::domain::hooks            (NEW)
ai_agent::domain::hub
ai_agent::domain::interaction_flow
ai_agent::domain::lite             (NEW)
ai_agent::domain::locale
ai_agent::domain::memory           (NEW)
ai_agent::domain::merge
ai_agent::domain::model
ai_agent::domain::multimodal       (NEW)
ai_agent::domain::multi_root_path  (NEW)
ai_agent::domain::plan
ai_agent::domain::privacy_mode     (NEW)
ai_agent::domain::project
ai_agent::domain::prompt
ai_agent::domain::ralph_loop       (NEW)
ai_agent::domain::remote_agent     (NEW)
ai_agent::domain::rule             (NEW)
ai_agent::domain::schedule         (NEW)
ai_agent::domain::skill            (NEW)
ai_agent::domain::snapshot
ai_agent::domain::summary
ai_agent::domain::system_diagnosis
ai_agent::domain::todo_list        (NEW)
ai_agent::domain::toolcall
ai_agent::domain::understanding
ai_agent::domain::user_configuration
ai_agent::domain::web_search       (NEW)
ai_agent::domain::work_mode        (NEW)
ai_agent::domain::workspace
ai_agent::domain::worktree         (NEW)
```

### 6.3 Shared Crates (15 crates)

```
apps/icube_server_rs/crates/ai-config
apps/icube_server_rs/crates/code (code-*)
apps/icube_server_rs/crates/concurrent (concurrent-*)
apps/icube_server_rs/crates/content (content-filter)
apps/icube_server_rs/crates/custom (custom-model-proxy-client)
apps/icube_server_rs/crates/framework
apps/icube_server_rs/crates/hub-net
apps/icube_server_rs/crates/jr
apps/icube_server_rs/crates/llm (llm-client)
apps/icube_server_rs/crates/net (net-bridge)
apps/icube_server_rs/crates/proxy
apps/icube_server_rs/crates/sandbox
apps/icube_server_rs/crates/slardar
apps/icube_server_rs/crates/snapshot
apps/icube_server_rs/crates/util
```

### 6.4 Source File Paths

Key source files recovered from embedded debug strings:

```
apps/icube_server_rs/crates/ai-config/src/source/aha_ipc_source.rs
apps/icube_server_rs/crates/ai-config/src/source/async_builder.rs
apps/icube_server_rs/crates/content-filter/src/engine.rs
apps/icube_server_rs/crates/custom-model-proxy-client/src/aws_handler.rs
apps/icube_server_rs/crates/custom-model-proxy-client/src/default_handler.rs
apps/icube_server_rs/crates/custom-model-proxy-client/src/response_sender.rs
apps/icube_server_rs/crates/custom-model-proxy-client/src/retry.rs
apps/icube_server_rs/crates/custom-model-proxy-client/src/stream_manager.rs
apps/icube_server_rs/crates/custom-model-proxy-client/src/tunnel.rs
apps/icube_server_rs/crates/custom-model-proxy-client/src/utils.rs
apps/icube_server_rs/crates/custom-model-proxy-client/src/websocket.rs
apps/icube_server_rs/crates/framework/src/agent/context.rs
apps/icube_server_rs/crates/framework/src/agent/registry.rs
apps/icube_server_rs/crates/framework/src/core/artifact.rs
apps/icube_server_rs/crates/framework/src/core/task.rs
apps/icube_server_rs/crates/framework/src/core/tool.rs
apps/icube_server_rs/crates/framework/src/ioc/ioc.rs
apps/icube_server_rs/crates/framework/src/tool/tool_box.rs
apps/icube_server_rs/crates/hub-net/src/client/frontier/aha_ffi_frontier.rs
apps/icube_server_rs/crates/hub-net/src/client/http/aha_ffi_http.rs
apps/icube_server_rs/crates/jr/src/v2/context.rs
apps/icube_server_rs/crates/llm-client/src/crypto/crypto.rs
apps/icube_server_rs/crates/llm-client/src/llm_client.rs
apps/icube_server_rs/crates/llm-client/src/model/provider/aws.rs
apps/icube_server_rs/crates/llm-client/src/model/tools.rs
apps/icube_server_rs/crates/llm-client/src/parser.rs
apps/icube_server_rs/crates/llm-client/src/provider/anthropic.rs
apps/icube_server_rs/crates/llm-client/src/provider/aws.rs
apps/icube_server_rs/crates/llm-client/src/provider/deepseek.rs
apps/icube_server_rs/crates/llm-client/src/provider/gemini.rs
apps/icube_server_rs/crates/llm-client/src/provider/openai.rs
apps/icube_server_rs/crates/llm-client/src/provider/openrouter.rs
apps/icube_server_rs/crates/llm-client/src/provider/volcengine.rs
apps/icube_server_rs/crates/net-bridge/src/http/client/aha.rs
apps/icube_server_rs/crates/net-bridge/src/http/client/reqwest.rs
apps/icube_server_rs/crates/net-bridge/src/http/client/vsock.rs
apps/icube_server_rs/crates/net-bridge/src/websocket/client/aha.rs
apps/icube_server_rs/crates/proxy/src/noproxy.rs
apps/icube_server_rs/crates/proxy/src/proxy_schema.rs
apps/icube_server_rs/crates/sandbox/src/linux/kernel.rs
apps/icube_server_rs/crates/sandbox/src/linux/ns/mod.rs
apps/icube_server_rs/crates/sandbox/src/linux/ns/profile.rs
apps/icube_server_rs/crates/sandbox/src/linux/ns/sandbox.rs
apps/icube_server_rs/crates/sandbox/src/linux/semver.rs
apps/icube_server_rs/crates/sandbox/src/linux/utils.rs
apps/icube_server_rs/crates/slardar/src/log.rs
apps/icube_server_rs/crates/slardar/src/slog.rs
apps/icube_server_rs/crates/slardar/src/system_info.rs
apps/icube_server_rs/crates/slardar/src/utils.rs
```

---

## 7. Developer Information Leakage

### 7.1 Build Environment Paths

- **Linux build**: `/root/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/`
- **macOS build (old)**: `/Users/tron_mac_03/.cargo/registry/` (from v1.98.2, not in current build)
- **Git checkout paths**: `/root/.cargo/git/checkouts/`

### 7.2 Cargo Dependencies Identified

| Dependency | Version/Checkout | Source |
|-----------|-----------------|--------|
| `aws-runtime` | 1.5.12 | `index.crates.io-1949cf8c6b5b557f` |
| `aws-sdk-bedrockruntime` | (latest) | crates.io |
| `jsonrpsee` | git checkout `397edabd1a050472/239fde3` | GitHub |
| `aha-ipc` | git checkout `0152e3c7ae4208d9/821c6e5` | Internal Git |

### 7.3 Embedded Data

The binary contains significant embedded skill/template data:
- Prompt templates for web design (CSS, layout, color systems)
- React/Next.js/Svelte/Vue best practices
- Markdown documentation for skills
- PPTX generation scripts
- SVG/chart generation templates

---

## 8. API Endpoints and URLs

### 8.1 Internal API Routes

| Route | Purpose |
|-------|---------|
| `/ws/api/v1/:service/:method` | WebSocket JSON-RPC endpoint |
| `/api/ide/v1/text_to_image` | Image generation endpoint |
| `/context/create` | Volcengine context creation |

### 8.2 LLM Provider Endpoints

| Provider | Endpoint Pattern |
|----------|-----------------|
| **Anthropic** | (via `anthropic-version: 2023-06-01` header) |
| **AWS Bedrock** | `https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke-with-response-stream` |
| **OpenAI** | `/chat/completions` |
| **DeepSeek** | `deepseek-chat` model via `/chat/completions` |
| **Gemini** | `/chat/completions/foundation-models/openai/v1/chat/completions` |
| **OpenRouter** | `openrouter//medium` path |
| **Volcengine** | `/context/create` for session; chat completion endpoint |

### 8.3 Hub Network (AHA FFI)

- `HubNetService` with `upload_artifacts_batch` (PUT operations)
- `aha_ffi_frontier.rs` and `aha_ffi_http.rs` for FFI-based network access
- Frontier URL: `frontierUrl` configuration parameter

---

## 9. New Features Since v1.98.2

### 9.1 SOLO Agent (Major Feature)

Previously called "solo_coder", renamed to "solo_agent":

- **Database migration**: `m20260128_000001_copy_solo_coder_relations_to_solo_agent`, `m20260414_000001_migrate_solo_coder_to_solo_agent`
- **Agent types**: `solo_coding`, `solo_agent`, `solo_agent_remote`
- **SOLO Builder**: UI builder agent with MCP support (`builder_with_mcp_v3`)
- **SOLO Project Preparation**: `solo_project_preparation` / `agent_ui_builder_project_preparation`
- **Configuration flags**: `solo_enabled`, `v3_solo_coder_*` series
- **Cloud agent mode**: `cloud_agent` with snippet/category content limits

### 9.2 Agent V3 / Multi-Agent Architecture

- `agent_v3` domain with `tool_call_accumulator`, `git_ai_checkpoint`
- Sub-agent routing: `v3_sub_agent_route_enable`
- Parallel agents: `v3_max_concurrent_tasks`, `v3_concurrent_task_timeout`
- Agent registry: `crates/framework/src/agent/registry.rs`
- Agent types: `solo_coding`, `code_reviewer`, `refactor_finder`, `solo_agent`, `ProjectPreparationTask`, `DocumentTask`, `SOLO Builder`

### 9.3 Handoff Protocol (Local-to-Cloud Migration)

The `handoff` domain supports migrating sessions between local and cloud:

- **Handoff Down**: Local-to-cloud session migration
  - `Failed to prepare the remote session for handoff`
  - `Failed to restore the remote session after handoff`
  - `Failed to load remote session data`
  - `Failed to download remote history data`
- **Handoff Up**: Cloud-to-local session migration
  - `Handoff Up request is invalid`
  - `Remote session not found`
  - `The remote session already exists`
- Session sync: `do_message_sync`, `message conflict, skipping`
- Requires Git repository association

### 9.4 DeepWiki Integration

Repository documentation/knowledge system:

```
ai_agent::domain::deepwiki::clear_wiki
ai_agent::domain::deepwiki::diff_cache
ai_agent::domain::deepwiki::diff
ai_agent::domain::deepwiki::repo_meta
ai_agent::domain::deepwiki::update_wiki_progress_status
ai_agent::domain::deepwiki::wiki_content
ai_agent::domain::deepwiki::wiki_file_writer
ai_agent::domain::deepwiki::wiki_meta
ai_agent::domain::deepwiki::wiki_repo_info
ai_agent::domain::deepwiki::wiki_status
```

Key entities: `WikiContentItem`, `WikiRepoInfo`, `WikiCatalog`, `WikiStatus`, `MetaCatalogEntry`, `MetaVersionEntry`

### 9.5 Scheduled Tasks (Cron-like)

Database table `scheduled_tasks` with fields:
- `scheduled_task_id`, `trigger_type`, `trigger_config`
- `prompt_template`, `model_name`, `user_context`
- `max_execution_count`, `execution_count`, `next_run_at`, `last_run_at`
- `disabled_reason`

Migration: `m20260407_000001_create_scheduled_tasks`

### 9.6 Core Memory System

Persistent memory blocks for agent context:
- `manage_core_memory` tool
- `core_memory_block_rough_max_token` config
- `core_memory_enable_type` config
- Database table `core_memory` (migration `m20251023_000001_create_core_memory_table`)
- Operations: `get_core_memories`, `get_core_memory`, `forget_core_memory`, `reference`

### 9.7 Skill Recommendation System

- `[SkillRecommend]` prefixed log messages
- Trial skill installation: `trial_skills recommended skill(s), installed as trial for this turn`
- Skills detected: `skill-creator`, `digital-avatar-creator`, `TRAE-dynamic-ui`
- Skill paths: `work/default/skills/`, `.agentsskills`
- Skill files: `SKILL.md`

### 9.8 Ralph Loop

- `ai_agent::domain::ralph_loop` domain
- Loop continuation: `[TodoList] ralph loop continuation: restricting lookup to current msg_id only`
- `[ChatMessageRevert]` and `[ChatMessageMigration]` events

### 9.9 Worktree Support

- `worktree` database table (migration `m20251202_000001_create_worktree_table`)
- `review_status` and `base` fields (migration `m20260415_000001_modify_worktree_add_review_status_and_base`)
- `update_worktree_id_by_session_id`

### 9.10 Commercial/Enterprise Features

- `ai_agent::domain::commercial`
- Enterprise agent fields: `enterprise_tenant_id`, `enterprise_creator_user_id`, `enterprise_agent_version`
- Migration: `m20260120_000001_modify_agent_table_enterprise`
- Model hot info: `ModelHotInfo`, `ModelCommercialInfo`
- Model selection mode: `ModelSelectionModeConfig` with `is_unimodal`

---

## 10. WebSocket / IPC Protocol Details

### 10.1 AHA IPC (Primary Communication)

The binary exposes 4 C-ABI functions for IPC:

```
ai_agent_ipc_init
ai_agent_ipc_connect
ai_agent_ipc_disconnect
ai_agent_ipc_recv
```

And 3 C-ABI bootstrap functions:

```
BP_Initialize
BP_GetInterface
BP_Shutdown
```

### 10.2 JSON-RPC Protocol

Uses `jsonrpsee` library (custom fork: `jsonrpsee-397edabd1a050472/239fde3`):

- **IPC mode**: `[aha_ipc] spawning RPC server for new connection`
- **Methods**: `request_lite`, `request_stream`, `stream_request`, `stream_request_lite`
- **WebSocket mode**: `[UnifiedTransport] server listening on:`, `/ws/api/v1/:service/:method`
- **Streaming**: RPC streaming with `chunkIndex`, `totalChunks`, `StreamParams`
- **Subscriptions**: Full subscription support (subscribe/unsubscribe)
- **MuxRpc**: Multiplexed RPC with `read_loop`, Pong/latency tracking

### 10.3 Transport Configuration

```
serviceId
frontierUrl
maxWsReconnectAttempts
wsReconnectDelaySecs
defaultEmptyFlushCount
pollIntervalMs
flushIntervalMs
flushCountThreshold
wsMsgSizeThreshold
pushConversationSize
pushMessageSize
syncSessionChunkSize
maxSentMessageCache
```

### 10.4 Message Types

The IPC handles various message categories:
- Chat messages (general, task, toolcall)
- Agent lifecycle (init, run, finish)
- History synchronization
- Snapshot operations
- Session management (handoff up/down)
- CKG operations
- Streaming LLM responses

---

## 11. Environment Variables and Configuration

### 11.1 Environment Variables

| Variable | Purpose |
|----------|---------|
| `TRAE_ENV_FILE` | Trae environment file path |
| `CLAUDE_ENV_FILE` | Claude environment file path (compatibility) |
| `CLAUDE_PROJECT_DIR` | Claude project directory (compatibility) |
| `AHA_RUNTIME_DIR` | AHA IPC runtime directory |
| `AHA_IPC_SERVICE_NAME` | AHA IPC service name |
| `ICUBE_MODULAR_DATA_DIR` | Data directory for modular storage |
| `DISABLE_DB_MIGRATION_ROLLBACK` | Disable database rollback |
| `AWS_PROFILE` | AWS SDK profile selection |
| `AWS_RETRY_MODE` | AWS retry mode |
| `AWS_USE_DUALSTACK_ENDPOINT` | AWS dual-stack |
| `AWS_USE_FIPS_ENDPOINT` | AWS FIPS endpoint |
| `AWS_ACCOUNT_ID_ENDPOINT_MODE` | AWS account ID endpoint mode |
| `AWS_DISABLE_REQUEST_COMPRESSION` | Disable request compression |
| `AWS_IGNORE_CONFIGURED_ENDPOINT_URLS` | Ignore configured URLs |
| `AWS_REQUEST_MIN_COMPRESSION_SIZE_BYTES` | Min compression size |
| `AWS_SDK_UA_APP_ID` | SDK user agent app ID |

### 11.2 Configuration Parameters (Dynamic)

```
model_timeout_ms
v3_solo_coder_disable_plan_mode
v3_solo_coder_cumulative_compaction_strategy
v3_passive_compaction_user_perceptible
v3_solo_coder_compaction_restore_reading_nums
v3_ls_max_result_chars
v3_read_max_content_byte_size
v3_read_enable_truncation
v3_read_enable_start_end_line
v3_solo_coder_only_single_chat
v3_grep_max_result_chars
v3_grep_default_output_mode
v3_grep_enable_hidden
v3_grep_max_columns
v3_grep_post_sort
v3_ripgrep_partial_on_timeout
v3_snippet_content_max_char_count
v3_sub_agent_route_enable
v3_sub_agent_summary_return_after_error
v3_compaction_token_limit_ratio
v3_async_compaction_token_limit_ratio
v3_micro_compact_trigger_token_ratio
v3_micro_compact_kept_token
v3_micro_compact_min_token
v3_parallel_agents_disabled
v3_max_concurrent_tasks
v3_concurrent_task_timeout
shallow_memento_disabled
core_memory_block_rough_max_token
replace_edit_tools_by_apply_patch
enable_edit_tool_fuzzy_match
apply_patch_return_fuzzy_match_result
history_adapter_strategy
is_gpt5
disable_history_adapter
v3_glob_enable_ripgrep
v3_glob_enable_no_ignore
v3_disable_nfc_dummy_tool
cloud_agent_snippet_content_max_char_count
cloud_agent_category_content_max_char_count
enable_nfc_prefill_agent_name
run_mcp_result_max_char_count
run_custom_tool_output_max_char_count
enhanced_command_ast_check_2605
v3_user_input_prompt_min_tokens
v3_user_input_prompt_max_tokens_ratio
v3_custom_rules_max_chars
v3_stream_throttle_enabled
v3_padding_line_num_before_line_content
v3_enable_multi_edit_tool
v3_replace_edit_tools_by_edit_file_update
v3_use_edit_file_update_replace_blocks
v3_rename_custom_tool_apply_patch_name
v3_require_get_diagnostics_after_edit
v3_llm_message_use_separate_toolcall
v3_custom_tool_list
v3_enable_skill_tool
v3_enable_knowledge_tool
v3_enable_web_fetch_tool
v3_enable_file_diff_resolver / v2
dynamic_tool_loading_search
dynamic_tool_loading_filesystem
enable_browser_tools
enable_browser_screenshot_auto_read
enable_show_widget
todo_write_allow_partial_input
web_search_skip_crawler_when_snippet_exists
web_fetch_strategy
save_toolcall_result_config
v3_read_dedup_enabled
enable_command_exit_code_semantics
enable_read_enoent_path_suggestion
enable_tool_result_trimming
```

---

## 12. Telemetry (Slardar / ByteDance Monitoring)

Slardar is ByteDance's monitoring platform, deeply integrated:

### 12.1 Slardar Event Categories

```
CkgRetrieval (CKG retrieval events)
ChatMessageRevert
ChatMessageMigration
LLMStream (stream errors)
LLMFirstToken (latency tracking)
ModelSync (model configuration sync)
ModelDbCache (model config caching)
DupToolcall (duplicate tool call detection)
CustomModelRequest (custom model usage)
AgentToolCall (tool call telemetry)
AgentCreateSnapshot / UpdateSnapshot / ListSnapshot / RevertSnapshot
AutoModelSelection (model selection tracking)
RemoteHookExecution
SandboxSupportCheck
ReadDedup (read deduplication)
PreTermination
GenerateImage
ImageProcess
LiteVmStartup
ContextUsage
VsockRequest
ScheduleExecution / ScheduleConfig
CoreMemOp / CoreMemEvict / CoreMemHit / CoreMemForget
```

### 12.2 Slardar Configuration

- `SlardarCKGConfig`, `SlardarConfig`, `HubConfig`
- `tea_web` (Tea reporting channel)
- `image_xcdn_prefix` (CDN prefix)
- `store_region` (data region)
- `ug_api` (user growth API)
- `ppe_env` (production/pre-production environment)

---

## 13. Database Schema (SQLite)

### 13.1 Database Location

- **Path**: `$HOME/.icube/ai-agent/database.db`
- **Encryption**: SQLCipher
- **Backup**: `[Backup] Database size: report_size`

### 13.2 Key Tables (from migrations)

| Table | Created/Modified |
|-------|-----------------|
| `chat_session` | Multiple modifications |
| `chat_turn` | Multiple modifications |
| `chat_message` | Multiple modifications, chat sub-table |
| `agent` | `m20250321`, enterprise fields added |
| `agent_run` | `m20250815` |
| `agent_member_relation` | `m20250902` |
| `mcp_server_agent_relation` | `m20250328`, multiple modifications |
| `history_v2` | `m20250409`, many modifications |
| `todo_list` | `m20250709`, modifications |
| `plan_item` | Modifications for toolcall fields |
| `toolcall` | `m20250818` |
| `configuration` | `m20250624` |
| `core_memory` | `m20251023` |
| `checkpoint` | `m20250915` |
| `server_history_info` | `m20250923` |
| `rules_attachment` | `m20251124` |
| `worktree` | `m20251202` |
| `model_config_cache` | `m20251217` |
| `project` | Modified with `transient_fallback_project_id` |
| `multi_root_path` | `m20260105` |
| `session_project` | `m20260106` |
| `scheduled_tasks` | `m20260407` |
| `snapshot` / `snapshot_file` | Multiple modifications |
| `fast_apply` | Tracks FastApply operations |

### 13.3 Migration Timeline (Selected)

- Earliest: `m20250103` (snapshot file table)
- Latest: `m20260506` (add pin fields to chat session)
- Total: ~60+ migrations, indicating active development from Jan 2025 to May 2026

---

## 14. Exported Symbols

The binary exports only 7 functions via its C ABI:

| Symbol | Type | Purpose |
|--------|------|---------|
| `ai_agent_ipc_init` | T (text) | Initialize IPC subsystem |
| `ai_agent_ipc_connect` | T | Accept IPC connection |
| `ai_agent_ipc_disconnect` | T | Disconnect IPC |
| `ai_agent_ipc_recv` | T | Receive IPC message |
| `BP_Initialize` | T | Bootstrap protocol init |
| `BP_GetInterface` | T | Get interface pointer |
| `BP_Shutdown` | T | Shutdown |
| `crc_fast_checksum` | T | Fast CRC checksum |
| `crc_fast_checksum_combine` | T | CRC combine |
| `crc_fast_checksum_file` | T | CRC file checksum |
| `crc_fast_digest_*` | T (6) | CRC digest operations |
| `bz_internal_error` | T | Bzip2 error handler |

All other symbols are undefined (U) imports from libc, OpenSSL, zlib, lzma, zstd.

---

## 15. Comparison: v1.98.2 vs v2.3.30128

| Feature | v1.98.2 | v2.3.30128 |
|---------|---------|------------|
| Codename | icube_server_rs / marscode | icube_server_rs (marscode legacy) |
| Build host | macOS (tron_mac_03) | Linux (/root/) |
| LLM Providers | Anthropic, OpenAI, DeepSeek, OpenRouter | + Gemini, AWS Bedrock, Volcengine |
| Claude models | Claude 3.5 | Claude 3/4 with extended thinking |
| GPT models | GPT-4 | + GPT-5 (is_gpt5 flag) |
| ByteDance models | (unknown) | Doubao-Seed-2.0-Code (penelope) |
| MCP | Not present | Full MCP support with per-agent config |
| Browser tools | Not present | 30+ browser_use_* tools |
| SOLO mode | Not present | Full SOLO Agent with Builder, Project Prep |
| Multi-agent | Not present | Agent V3 with sub-agents, parallel execution |
| Handoff | Not present | Local-to-cloud session migration |
| DeepWiki | Not present | Full wiki integration |
| Scheduled tasks | Not present | Cron-like task scheduling |
| Core memory | Not present | Persistent memory blocks |
| Skill system | Not present | Skill recommendation with trial install |
| Sandbox | Basic | Linux namespace sandbox + Lite VM |
| Supabase/Stripe | Not present | Tool integrations |
| Browser automation | Not present | Playwright-style browser tools |
| DB migrations | ~10 | 60+ (active development) |
| Content filter | Not present | Rule-based content filter engine |
| Hooks system | Not present | Hook groups with matchers |
| Snapshot | Basic | V2 with git-based snapshots |
| Worktree | Not present | Full worktree support |
| Commercial | Not present | Enterprise agents, model selection mode |
| Privacy mode | Not present | Privacy mode domain |
| Web search | Not present | Web search + web fetch tools |
| Todo list | Not present | Persistent todo list |
| CKG | Basic | Enhanced with retrieval, error tracking |
| VBVirtualize | Present (Windows) | NOT present (Linux x64) |

---

## 16. Key Architectural Observations

1. **DDD Architecture**: The Rust codebase follows strict Domain-Driven Design with 47+ domain modules, each containing entity, repository, and service layers.

2. **Agent Framework**: The `framework` crate provides a generic agent infrastructure with context management, tool registration, task handling, and IoC (Inversion of Control) container.

3. **Multi-Provider LLM Client**: Unified `llm-client` crate with provider-specific implementations for 7 providers, each handling streaming, tool calls, and provider-specific features (thinking blocks, reasoning, etc.).

4. **IPC Architecture**: The Electron main process communicates with the Rust backend via AHA IPC (JSON-RPC over Unix domain sockets), with the `BP_*` C-ABI serving as bootstrap entry points.

5. **Encryption Layer**: Model parameters are encrypted at rest using AES-256-GCM, with the key management tied to the application instance.

6. **Observability**: Slardar (ByteDance's monitoring) is deeply integrated with 30+ event categories, tracking everything from LLM token usage to sandbox operations.

7. **Cloud-Native Design**: The handoff protocol and cloud agent support indicate a hybrid local/cloud architecture where sessions can migrate between environments.

8. **Progressive Feature Flags**: 80+ dynamic configuration flags control feature availability, enabling A/B testing and gradual rollout.
