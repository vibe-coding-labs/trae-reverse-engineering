# Trae IDE Windows (win32-x64) Build Analysis

**Analysis Date:** 2026-05-27
**Source:** Trae-Setup-x64.exe (246 MB Inno Setup installer)
**App Version:** 3.5.60
**Tron Build Version:** 2.3.30128
**Build Branch:** release_desktop_win32_i18n
**Package Type:** TRAE_I18N
**Provider:** Spring (SPRING (SG) PTE. LTD)

---

## 1. Directory Structure

The Inno Setup installer (v6.4.0.1) was extracted using `innoextract 1.10-dev` (built from source to support Inno Setup 6.4.x). The extraction yields two primary directories:

### Top-Level Layout

```
code$GetDestDir/          (934 MB, 4894 files - the main application)
app/                      (740 KB - installer helper tools)
  tools/
    inno_updater.exe      (623 KB - Inno Setup auto-updater)
    remove-env.ps1        (17 KB - PowerShell env cleanup script)
    set-env.ps1           (17 KB - PowerShell env setup script)
    vcruntime140.dll      (78 KB - MSVC runtime)
```

### Main Application Directory (`code$GetDestDir/`)

```
code$GetDestDir/
  Trae.exe                            204 MB   (Electron/Chromium main executable)
  aha_doctor/                         12 MB    (Telemetry/diagnostics subsystem)
    aha_doctor.exe
    config/
      certs/                          (SSL root certificates)
      3partyAppDetect.dat
      BrandDetect.dat
      BrowserPlugin.dat
    resources/
      lang/
      themes/
  aha_kit_wer.dll                     121 KB   (Windows Error Reporting kit)
  aha_net.dll                         1.8 MB   (ByteDance network SDK)
  bin/
    trae                              2 KB     (WSL/CLI shell script)
    trae.cmd                          178 B    (Windows CLI batch script)
  concrt140.dll                       309 KB   (MSVC Concurrency Runtime)
  d3dcompiler_47.dll                  4.5 MB   (DirectX shader compiler)
  doctor_sdk.dll                      587 KB   (Diagnostics SDK)
  dxcompiler.dll                      25 MB    (DXIL shader compiler)
  dxil.dll                           1.5 MB   (DX Intermediate Language)
  ffmpeg.dll                          3.0 MB   (Media codec library)
  icudtl.dat                          10 MB    (ICU internationalization data)
  innoplugin.dll                      218 KB   (Inno Setup plugin - 32-bit)
  libEGL.dll                         505 KB   (OpenGL EGL)
  libGLESv2.dll                       8.1 MB   (OpenGL ES 2.0)
  LICENSES.chromium.html              15 MB
  locales/                            (Chromium locale .pak files)
  logifier_retrieval.dll              2.9 MB   (Logging subsystem)
  manifest.json                       1.8 KB   (Boot configuration)
  msvcp140.dll                        537 KB   (MSVC++ Standard Library)
  node_modules/                       (Node.js type definitions)
  resources/
    app/                              (Electron app resources)
      product.json                    74 KB
      package.json                    12 KB
      out/
        cli.js                        221 KB
        main.js                       2.3 MB
      extensions/                     109 built-in extensions
      modules/
        ai-agent/                     153 MB   (AI agent module)
          ai_agent.dll                144 MB
          sscronet.dll                8.7 MB
          sscronet.lib                241 KB
          meta.json                   274 B
          start.bat                   1.2 KB
          start.sh                    1.7 KB
        ckg/                          40 MB    (Code knowledge graph)
          binary/
            libckg.dll                37 MB
            libgcc_s_seh-1.dll        162 KB
            libstdc++-6.dll           2.4 MB
            libwinpthread-1.dll       73 KB
        sandbox/                      4.7 MB   (Execution sandbox)
          trae-sandbox.exe            1.1 MB
          sbox_sdk.dll                1.9 MB
          api-ms-win-core-synch-l1-2-0.dll  16 KB
          x64/
            sbox_ipc.dll              559 KB
            trae_sbox.dll             675 KB
          x86/
            sbox_ipc.dll              416 KB
            trae_sbox.dll             508 KB
      resources/
        win32/                        (Icons for file type associations)
      node_modules/                   (NPM dependencies)
      licenses/                       (License files)
      bin/
        lib/                          (Helper scripts)
  resources.pak                       6.1 MB
  simplelog.dll                       335 KB   (Logging library)
  snapshot_blob.bin                   395 KB   (V8 snapshot)
  sscronet.dll                        8.7 MB   (Cronet network library - standalone)
  v8_context_snapshot.bin             760 KB   (V8 context snapshot)
  vcomp140.dll                        181 KB   (OpenMP runtime)
  vcruntime140.dll                    114 KB   (MSVC runtime)
  vcruntime140_1.dll                   41 KB   (MSVC runtime extension)
  vk_swiftshader.dll                  5.4 MB   (Vulkan software renderer)
  vk_swiftshader_icd.json             106 B
  vulkan-1.dll                        934 KB   (Vulkan loader)
```

---

## 2. Key Files Found

### Configuration Files

| File | Size | Description |
|------|------|-------------|
| `resources/app/product.json` | 74 KB | Main product configuration with AI features, auth, extensions gallery |
| `resources/app/package.json` | 12 KB | NPM package manifest (name: Trae, version: 1.107.1) |
| `manifest.json` | 1.8 KB | Boot config with API domains, aha-net config, access policies |
| `resources/app/modules/ai-agent/meta.json` | 274 B | AI agent module descriptor |

### Startup Scripts

| File | Size | Description |
|------|------|-------------|
| `bin/trae` | 2 KB | WSL-aware CLI launcher shell script |
| `bin/trae.cmd` | 178 B | Windows CLI batch launcher |
| `resources/app/modules/ai-agent/start.bat` | 1.2 KB | AI agent Windows startup script |
| `resources/app/modules/ai-agent/start.sh` | 1.7 KB | AI agent Unix startup script |

### Key JavaScript Bundles

| File | Size | Description |
|------|------|-------------|
| `resources/app/out/main.js` | 2.3 MB | Electron main process entry |
| `resources/app/out/cli.js` | 221 KB | CLI entry point |

---

## 3. Binary Types (PE32+ Format Details)

### Trae.exe (Electron Main Executable)

- **Format:** PE32+ (64-bit x86-64)
- **Original Name:** electron.exe
- **Physical Size:** 213,776,176 bytes (204 MB)
- **Image Size:** 217,784,320 bytes (208 MB)
- **Sections:** 14
- **Subsystem:** Windows GUI
- **Linker Version:** 14.0
- **OS Version:** 10.0
- **DLL Characteristics:** Relocated, NX-Compatible, TerminalServerAware (0x4020)
- **Image Base:** 0x140010000 (5,368,709,120)
- **Code Size:** 174,646,784 bytes
- **Initialized Data:** 39,106,048 bytes
- **Stack Reserve:** 8,388,608 / Commit: 4,096
- **Heap Reserve:** 1,048,576 / Commit: 4,096
- **File Version:** 2.3.30128.0 (Electron version)
- **Product Version:** 3.5.60.0 (Trae version)
- **Digital Signature:** Signed by SPRING (SG) PTE. LTD with DigiCert/GlobalSign certificates
- **PKCS7 Authenticode:** Present

### ai_agent.dll (AI Agent Core)

- **Format:** PE32+ (64-bit x86-64 DLL)
- **Physical Size:** 150,703,408 bytes (144 MB)
- **Image Size:** 150,740,992 bytes (144 MB)
- **Sections:** 5
- **Subsystem:** Windows GUI
- **Linker Version:** 14.29 (MSVC)
- **OS Version:** 6.0
- **DLL Characteristics:** Relocated, NX-Compatible (0x20)
- **Code Size:** 93,112,320 bytes
- **Initialized Data:** 57,614,848 bytes
- **Build Timestamp:** 2026-05-21 14:14:25
- **Language:** Rust (compiled from `apps/icube_server_rs/`)
- **No ASLR high-entropy flag** (unlike Trae.exe)

### innoplugin.dll (Inno Setup Plugin)

- **Format:** PE32 (32-bit i386 DLL) -- notably the only 32-bit binary
- **Physical Size:** 222,512 bytes (218 KB)
- **Image Size:** 225,280 bytes
- **Subsystem:** Windows GUI
- **DLL Characteristics:** Relocated, NX-Compatible
- **Linker Version:** 14.44
- **Created:** 2025-06-24

### aha_net.dll (Network SDK)

- **Format:** PE32+ (64-bit x86-64 DLL)
- **Size:** 1,818,928 bytes (1.8 MB)
- **Linker Version:** 14.44
- **DLL Characteristics:** Relocated, NX-Compatible
- **Created:** 2026-03-20

---

## 4. ai-agent Binary Analysis

### Architecture and Language

The `ai_agent.dll` is a 144 MB Rust-compiled shared library. The binary contains extensive debug path references revealing the internal monorepo structure at `apps/icube_server_rs/`. The build was done inside a Windows container (`C:\Users\ContainerAdministrator/`) using the Cargo package manager with dependencies from `crates.io`.

### Internal Rust Crate Structure

The ai-agent binary is composed of the following internal crates:

| Crate | Purpose |
|-------|---------|
| `ai-config` | AI model configuration management |
| `code` | Code analysis/processing |
| `concurrent-executor` | Parallel task execution |
| `content-filter` | Content safety/filtering |
| `custom-model-proxy-client` | Custom model proxy (WebSocket/tunnel) |
| `framework` | Agent framework (context, registry, tools, IoC) |
| `hub_net` | ByteDance network hub (HTTP transport, FFI) |
| `jr` | Job routing (v2 context) |
| `llm-client` | LLM provider clients (Anthropic, OpenAI, Gemini, DeepSeek, AWS, Volcengine, OpenRouter) |
| `net-bridge` | Network bridge |
| `proxy` | Proxy support |
| `sandbox` | Windows sandbox implementation |
| `slardar` | ByteDance monitoring/crash reporting |
| `snapshot` | State snapshots |
| `util` | Utilities |

### LLM Provider Support

The `llm-client` crate implements direct API client support for the following providers:

| Provider | Source File | Notes |
|----------|------------|-------|
| **Anthropic** | `provider/anthropic.rs` | Full Claude API support with cache control, streaming |
| **OpenAI** | `provider/openai.rs` | GPT series API support |
| **DeepSeek** | `provider/deepseek.rs` | DeepSeek API support |
| **Google Gemini** | `provider/gemini.rs` | Gemini API support |
| **AWS Bedrock** | `provider/aws.rs` + `model/provider/aws.rs` | AWS Bedrock Runtime SDK integration |
| **Volcengine** | `provider/volcengine.rs` | ByteDance cloud AI (Doubao models) |
| **OpenRouter** | `provider/openrouter.rs` | Multi-model proxy gateway |

### AI Model References

Extracted from string analysis of `ai_agent.dll`:

| Model Identifier | Notes |
|-----------------|-------|
| `claude-3` | Claude 3 family (via Anthropic provider) |
| `claude35_multi_content` | Claude 3.5 multi-modal content handling |
| `gpt-5` | OpenAI GPT-5 |
| `gpt-5.2` | GPT-5.2 variant |
| `gpt-5.2-codex` | GPT-5.2 Codex (code-focused) |
| `gpt-5.3-codex` | GPT-5.3 Codex |
| `gpt-5.4` | GPT-5.4 |
| `deepseek-chat` | DeepSeek chat model |
| `deepseek-v3.1__max` | DeepSeek V3.1 with max token config |
| `doubao-for-auto` | ByteDance Doubao for auto mode |
| `gemini-3-pro` | Google Gemini 3 Pro |
| `gemini-3.1-pro` | Gemini 3.1 Pro |
| `gemini-3-flash-solo` | Gemini 3 Flash Solo |
| `gemini-reasoning` | Gemini reasoning model (encrypted reference) |
| `qwen2.5` | Alibaba Qwen 2.5 |

Additional model references found in feature flag/config strings:
- `deepseek_v3_generate_commit_message` - DeepSeek V3 used for commit message generation
- `qwen32_generate_commit_message` - Qwen 32B also used for commit messages
- `bytedancevpcprivate_volcprivate_localmarscodedeepseek` - Volcengine/BYtedance private deployments

### Security Mechanisms

#### Encryption and Crypto
- **AES-256-GCM encryption** implemented in `llm-client/src/crypto/crypto.rs` using the `alkali` Rust crate (libsodium wrapper)
- **OpenSSL** statically linked (full crypto library with ASN1, EVP, SSL/TLS support)
- **AWS SigV4a signing** for Bedrock API authentication
- **Custom model proxy** uses WebSocket tunneling with encrypted connections

#### Sandbox System
- **Windows sandbox**: `trae-sandbox.exe` (1.1 MB) with `sbox_sdk.dll` (1.9 MB), `trae_sbox.dll`, and `sbox_ipc.dll` (IPC bridge)
- Both x64 and x86 sandbox DLLs provided (for cross-architecture process sandboxing)
- Sandbox error handling includes: `init failed`, `create_sandbox_failed`, `sdk_crash`, `process_launch_failed`, `process_crashed`, `hit_restricted`
- File and network access controls: `Not allow operate files`, `Not allow tcp network access`, `Not allow udp network access`
- Dynamic auto-run configuration with `command_red_list`, `sandbox_rw_list`, `sandbox_ro_list`, `disable_sandbox_win_net`

#### Command Safety
- `is_safe_command.rs` implements command validation/filtering
- Red list system prevents execution of dangerous commands

#### Content Filtering
- `content-filter` crate with `engine.rs` for content safety checks
- Risk checking pipeline: `pre_security_check` -> `post_security_check`

#### Process Monitoring
- Memory monitoring with configurable thresholds (8 GB report, 1.5 GB notification)
- Single process monitors for: icube-manager, ckg_server, ai-agent, ai-completion/ai-server
- Memory limits: 2048 MB per monitored process
- CPU limits: 100% per process

### AI Agent Internal Architecture

#### Domain Layer (`modules/ai-agent/src/domain/`)
- `apply/` - Code apply/edit operations
- `model/` - Model management, config caching, LLM streaming, token counting
- `prompt/` - Prompt engineering (includes `count_claude.rs` for Claude token counting)
- `project/` - Project context management
- `ralph_loop/` - Agent loop execution
- `rule/` - Rule management repository
- `skill/` - Skill system with trial store
- `task/` - Task management (v2 service)
- `todo_list/` - Todo tracking
- `understanding/ckg/` - Code knowledge graph integration
- `plan/` - Planning system (simple_service_v2 with tool cache)
- `toolcall/` - Tool call execution with command safety
- `agent_v3/` - Agent v3 with tool call accumulator
- `history_v2/` - Chat history management

#### Infrastructure Layer (`modules/ai-agent/src/infrastructure/`)
- `adapter/` - IDE command adapters, custom model proxy client, AB test config
- `ahavm/` - AHA virtual machine integration
- `dal/` - Data access layer with SQLite models (30+ tables)
- `ide_model/` - IDE document model
- `skill_recommend_client/` - Skill recommendation service
- `toolhost/` - Tool hosting system
- `towel/ipc/` - Inter-process communication
- `typing/` - Context variable typing
- `util/` - AIGC metadata utilities
- `vm/manager/` - VM/runtime environment management (1904 lines)

#### Chat Event System
- Server-Sent Events (SSE) with event types: ChatDone, Heartbeat, UserMessage, SessionTitle, SessionIcon, ProjectName, AgentCall, AgentWakeup, Notification, ModelConfig, WorktreeCheck, WorktreeCreated, NeedSandboxUpgrade, ContextUsage
- Token usage tracking by display type
- Context batching with chunk index/total tracking

#### Database Schema (Migration Files)
- 30+ database tables including: agent, agent_run, chat_message, chat_session, chat_turn, checkpoint, core_memory, history_v2, mcp_server_agent_relation, plan_item, project, rules_attachment, scheduled_tasks, session_project, task, todo_list, user_configuration, worktree, model_config_cache
- Active development: migrations from 2025-03 through 2026-03

### ByteDance API Endpoints

| URL | Purpose |
|-----|---------|
| `https://aipa-api.bytedance.net/api/get-dep-info` | Dependency info API |
| `https://aipa.bytedance.net/api/file-upload` | File upload API |
| `https://aipa-pai-webview.gf.bytedance.net` | PAI webview |
| `https://promptpilot.volcengine.com/aipa` | Prompt Pilot (Volcengine) |
| `https://trae.mobile.volcapp.com/preview` | Trae mobile preview |
| `https://pai.mobile.volcapp.com` | PAI mobile |
| `https://mcs.zijieapi.com` | Monitoring/analytics |
| `https://cdn-tos-cn.bytedance.net/obj/aipa-tos/` | CDN assets |

### AI Agent Environment Configuration

The `start.bat` reveals the following environment variable handling:

```
AI_NATIVE_ENV:       desktop | plugin_remote | desktop_ssh
TRAE_RESOLVE_TYPE:   remote | ssh
PLUGIN_IDE_TYPE:     (optional, adds --ideType parameter)
DB_PATH:             %ICUBE_MODULAR_DATA_DIR%\ai-agent\database.db
FILE_BASE_DIR:       %ICUBE_MODULAR_DATA_DIR%\ai-agent\snapshot
```

The AI agent listens on **port 40005** for IPC communication (defined in `meta.json`).

---

## 5. Differences from Linux Build

### Binary Format Comparison

| Component | Windows | Linux |
|-----------|---------|-------|
| Main IDE binary | `Trae.exe` (PE32+, 204 MB) | `trae` (ELF x86-64, 193 MB) |
| AI agent core | `ai_agent.dll` (PE32+ DLL, 144 MB) | `libai_agent.so` (ELF SO, 127 MB) |
| Network lib | `sscronet.dll` (8.7 MB) | `libsscronet.so` (10 MB) |
| CKG binary | `libckg.dll` (37 MB) + GCC runtime | `libckg.so` (44 MB) + full Linux runtime |
| aha_net | `aha_net.dll` (1.8 MB) | `libaha_net.so` (2.4 MB) |
| innoplugin | `innoplugin.dll` (218 KB, **32-bit**) | Not present |
| doctor_sdk | `doctor_sdk.dll` (587 KB) | Not present |
| aha_kit_wer | `aha_kit_wer.dll` (121 KB) | Not present |
| WER handler | Not present | Not present |
| Chrome sandbox | Not present | `chrome-sandbox` (15 KB, setuid) |
| Crash handler | Not present | `chrome_crashpad_handler` (3.5 MB) |

### Size Comparison

| Component | Windows | Linux | Difference |
|-----------|---------|-------|------------|
| Main IDE binary | 204 MB | 193 MB | +5.6% |
| ai-agent core | 144 MB | 127 MB | +13.7% |
| ai-agent network lib | 8.7 MB | 10 MB | -13.3% |
| ckg binary | 37 MB | 44 MB | -16.7% |
| aha_net | 1.8 MB | 2.4 MB | -27.6% |
| logifier_retrieval | 2.8 MB | 4.5 MB | -37.1% |
| simplelog | 335 KB | 615 KB | -45.7% |
| cli.js | 221 KB | 221 KB | ~0% |
| main.js | 2.3 MB | 2.3 MB | ~0% |

Windows PE binaries are generally larger due to:
- PE format overhead vs ELF
- Static linking of MSVC runtime components (msvcp140, vcruntime140, concrt140, vcomp140)
- Inclusion of DX compiler components (dxcompiler.dll 25 MB, dxil.dll 1.5 MB) which are DirectX-specific
- Debug symbols embedded differently between PE and ELF

### Sandbox Architecture Differences

| Aspect | Windows | Linux |
|--------|---------|-------|
| Sandbox binary | `trae-sandbox.exe` (1.1 MB) + `sbox_sdk.dll` (1.9 MB) | `trae-sandbox` (18 MB) |
| IPC library | `sbox_ipc.dll` (x64 + x86 variants) | Built-in |
| Sandbox wrapper | `trae_sbox.dll` (x64 + x86 variants) | N/A |
| Isolation mechanism | Windows Job Objects + restricted tokens | `bwrap` (bubblewrap, 176 KB) |
| Total sandbox size | ~4.7 MB | ~18.2 MB |

The Windows sandbox is significantly more lightweight, leveraging OS-native isolation primitives (Job Objects, restricted tokens) rather than the Linux approach using bubblewrap namespace isolation.

### Windows-Specific Components

1. **aha_doctor** (12 MB) - Complete telemetry/diagnostics subsystem not present in Linux build. Includes its own executable, SSL certificates, and language/theme resources.

2. **innoplugin.dll** - 32-bit Inno Setup plugin for installer integration.

3. **doctor_sdk.dll** - Diagnostics SDK for Windows.

4. **aha_kit_wer.dll** - Windows Error Reporting integration kit.

5. **DirectX components** - `d3dcompiler_47.dll`, `dxcompiler.dll`, `dxil.dll` for GPU-accelerated rendering on Windows.

6. **MSVC runtime** - `concrt140.dll`, `msvcp140.dll`, `vcomp140.dll`, `vcruntime140.dll`, `vcruntime140_1.dll` bundled for portability.

### Linux-Specific Components

1. **chrome-sandbox** (15 KB) - Chromium setuid sandbox helper.
2. **chrome_crashpad_handler** (3.5 MB) - Crash reporting handler.
3. **.asc signature files** - All native libraries have GPG detached signatures (833 bytes each), suggesting Linux packages are signed and verified at runtime. Windows build lacks these.

### product.json Differences

| Field | Windows | Linux |
|-------|---------|-------|
| `buildBranch` | `release_desktop_win32_i18n` | `release_desktop_linux_i18n` |
| `buildPlatform` | `win32` | `linux` |
| `target` | `user` | (not present) |
| `checksums` | Different (platform-specific) | Different (platform-specific) |

All other fields are identical, including:
- Same `appVersion`: 3.5.60
- Same `tronBuildVersion`: 2.3.30128
- Same `commit`: 78f9592999aa7de189380ea552dd24807440dbb6
- Same `iCubeApp` configuration
- Same `defaultChatAgent` configuration
- Same `extensionsGallery` (Open VSX)

### Code Knowledge Graph (CKG) Differences

Windows bundles a minimal set of runtime DLLs:
- `libckg.dll` (37 MB) + `libgcc_s_seh-1.dll` + `libstdc++-6.dll` + `libwinpthread-1.dll`

Linux bundles a more comprehensive runtime:
- `libckg.so` (44 MB) + `ckg_server_linux_x64` (36 MB) + `libcom_err`, `libgcc_s`, `libgssapi_krb5`, `libk5crypto`, `libkeyutils`, `libkrb5`, `libkrb5support`, `libnorm`, `libpgm`, `libresolv`, `libsodium`, `libstdc++`, `libzmq`

The Linux CKG includes Kerberos and ZeroMQ dependencies, suggesting the Linux build has richer network/authentication capabilities in the code knowledge graph service.

---

## 6. product.json Key Fields

### Identity

```json
{
  "nameShort": "Trae",
  "nameLong": "Trae",
  "applicationName": "trae",
  "brandName": "Trae",
  "provider": "Spring",
  "providerCode": "i18n",
  "quality": "stable",
  "dataFolderName": ".trae",
  "urlProtocol": "trae",
  "deeplinkHost": "trae.ai-ide"
}
```

### Version Information

```json
{
  "appVersion": "3.5.60",
  "version": "1.107.1",
  "vscodeVersion": "1.107.1",
  "tronBuildVersion": "2.3.30128",
  "traeVersionCode": "20250325",
  "buildId": "1155311451650",
  "commit": "78f9592999aa7de189380ea552dd24807440dbb6",
  "buildPlatform": "win32",
  "buildArch": "x64",
  "buildBranch": "release_desktop_win32_i18n",
  "packageType": "TRAE_I18N"
}
```

### Windows-Specific Identifiers

```json
{
  "win32DirName": "Trae",
  "win32NameVersion": "Trae",
  "win32RegValueName": "Trae",
  "win32MutexName": "trae",
  "win32AppUserModelId": "ByteDance.Trae",
  "win32ShellNameShort": "Trae",
  "win32TunnelServiceMutex": "trae-tunnelservice",
  "win32TunnelMutex": "trae-tunnel",
  "win32x64AppId": "{96347D30-5894-42C1-9F66-3E31E44BE18B}",
  "win32x64UserAppId": "{1082AAEF-E2C3-4ABD-8789-9861082B709F}",
  "win32arm64AppId": "{0AC5137A-890C-42E9-B78A-15E6C8958CD6}",
  "win32arm64UserAppId": "{4D8DF948-4662-4234-9173-915C517E7086}"
}
```

### Cross-Platform Identifiers

```json
{
  "darwinBundleIdentifier": "com.trae.app",
  "linuxIconName": "trae"
}
```

### Extensions Gallery

```json
{
  "serviceUrl": "https://open-vsx.org/vscode/gallery",
  "searchUrl": "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
  "resourceUrlTemplate": "https://open-vsx.org/vscode/asset/{publisher}/{name}/{version}/Microsoft.VisualStudio.Code.WebResources/{path}",
  "extensionUrlTemplate": "https://open-vsx.org/vscode/gallery/{publisher}/{name}/latest"
}
```

### iCubeApp Auth Configuration

```json
{
  "authConfig": {
    "TRAE": {
      "stable": "ono9krqynydwx5",
      "beta": "2k472yneke6pw3",
      "alpha": "pl2689e0l0xr1n",
      "dev": "8e4olyd5e5pn36",
      "local": "qjpvq9k8j8ryde"
    },
    "SOLO": {
      "stable": "en1oxy7wnw8j9n",
      "beta": "nn572p8wnw1vd7",
      "alpha": "0r4x5yq0r07nwp",
      "dev": "y6d1xnrk6k28o3",
      "local": "4v468ylkvkwn02"
    }
  }
}
```

### iCubeApp Native App Configuration

```json
{
  "nativeAppConfig": {
    "authProviderId": "icube.cloudide",
    "authProviderLabel": "Trae IDE",
    "authDomain": "www.trae.ai",
    "authFrom": "trae",
    "agentShareLinkAuthority": "trae.ai-ide",
    "enableEntitlement": true,
    "dsc": {
      "agent": false,
      "chatServer": true
    }
  }
}
```

### manifest.json Key Domains

```json
{
  "activeUrl": "https://did-boot.trae.ai/service/2/app_alert_check/",
  "logifierDomain": "icube-normal.trae.ai",
  "settingsDomain": "icube-normal.trae.ai",
  "slardarDomain": "pcmon-boot.trae.ai",
  "registryUrl": "https://did-boot.trae.ai/service/2/desktop/device_register/",
  "ahaNet": {
    "ttnet_params": {
      "domain_httpdns": "34.102.215.99",
      "domain_netlog": "ttnet-sg.byteoversea.com",
      "app_id": "677332",
      "tnc_host_first": "tnc-boot.trae.ai",
      "tnc_host_second": "tnc-normal.trae.ai",
      "app_name": "trae",
      "version_code": "3560"
    }
  }
}
```

Domain access policy whitelist includes: `*.trae.ai`, `*.traeapi.us`, `*.mchost.guru`, `*.bytedance.net`, `*.tiktok-row.net`, `*.byteintl.net`, `*.byted.org`, `*.trae.com.cn`, `*.trae.cn`

---

## 7. Build Environment Insights

The binary strings reveal the build was performed on a Windows container:

- **Build user:** `ContainerAdministrator`
- **Cargo registry:** `C:\Users\ContainerAdministrator/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f\`
- **Source tree:** `C:\88920\icube-mono\target\release\build\` (for OpenSSL build artifacts)
- **Rust crates used:** tokio 1.48.0, aws-sdk-bedrockruntime 1.92.0, time 0.3.37, zip 0.6.6, openssl-sys
- **AI agent source:** `apps/icube_server_rs/` within a monorepo named `icube-mono`

---

## 8. Summary

The Trae IDE Windows build is a comprehensive Electron-based IDE built on VS Code (version 1.107.1) with significant ByteDance-specific AI integration. The key architectural components are:

1. **Trae.exe** (204 MB) - Chromium/Electron shell providing the IDE GUI
2. **ai_agent.dll** (144 MB) - Rust-compiled AI agent with multi-provider LLM support (Anthropic Claude, OpenAI GPT-5, DeepSeek, Google Gemini, AWS Bedrock, ByteDance Volcengine/Doubao, OpenRouter)
3. **aha_doctor** (12 MB) - Windows-only telemetry/diagnostics subsystem
4. **sandbox** (4.7 MB) - Lightweight Windows sandbox using Job Objects for AI agent tool execution
5. **ckg** (40 MB) - Code knowledge graph for code understanding features

The Windows build differs from Linux primarily in:
- Binary format (PE32+ vs ELF) with 5-14% size overhead
- Windows-specific telemetry (aha_doctor) and error reporting (aha_kit_wer)
- DirectX rendering components instead of X11/Wayland
- Lighter sandbox implementation (4.7 MB vs 18 MB)
- No GPG signature verification (.asc files absent on Windows)
- Bundled MSVC runtime libraries
- Simpler CKG runtime (no Kerberos/ZeroMQ on Windows)
