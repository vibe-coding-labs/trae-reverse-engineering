# Trae IDE product.json and Extension System Analysis

**Build analyzed:** Linux x64, extracted 2026-05-21
**Source path:** `data/ide/linux-x64/extracted/resources/app/`

---

## 1. product.json Structure

The product.json is 2212 lines and serves as the central configuration for the Trae IDE. It is a fork of the VS Code product.json with extensive ByteDance/iCube customizations.

### 1.1 Version Information

| Field | Value |
|---|---|
| `tronBuildVersion` | `2.3.30128` |
| `appVersion` | `3.5.60` |
| `vscodeVersion` (underlying) | `1.107.1` |
| `version` (code version) | `1.107.1` |
| `buildPlatform` | `linux` |
| `buildArch` | `x64` |
| `traeVersionCode` | `20250325` |
| `buildBranch` | `release_desktop_linux_i18n` |
| `buildId` | `1155311451650` |
| `commit` | `78f9592999aa7de189380ea552dd24807440dbb6` |
| `date` | `2026-05-21T04:53:01.131Z` |

### 1.2 Branding and Identity

| Field | Value |
|---|---|
| `nameShort` | `Trae` |
| `nameLong` | `Trae` |
| `applicationName` | `trae` |
| `dataFolderName` | `.trae` |
| `brandName` | `Trae` |
| `provider` | `Spring` |
| `providerCode` | `i18n` |
| `packageType` | `TRAE_I18N` |
| `deeplinkHost` | `trae.ai-ide` |
| `win32AppUserModelId` | `ByteDance.Trae` |
| `darwinBundleIdentifier` | `com.trae.app` |
| `urlProtocol` | `trae` |
| `licenseName` | `MIT` |
| `marketPackage` | `false` |

### 1.3 Extension Gallery Configuration

The `extensionsGallery` section configures the primary extension marketplace:

```json
{
  "serviceUrl": "https://open-vsx.org/vscode/gallery",
  "controlUrl": "",
  "resourceUrlTemplate": "https://open-vsx.org/vscode/asset/{publisher}/{name}/{version}/Microsoft.VisualStudio.Code.WebResources/{path}",
  "searchUrl": "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
  "extensionUrlTemplate": "https://open-vsx.org/vscode/gallery/{publisher}/{name}/latest",
  "nlsBaseUrl": "",
  "publisherUrl": "",
  "mcpUrl": ""
}
```

**Key observations:**
- Primary gallery: **Open VSX** (not Microsoft Marketplace)
- Search falls back to **Microsoft Marketplace API** for queries
- The `mcpUrl` field is empty in the primary gallery config, indicating MCP extensions are served through a different mechanism

### 1.4 Trae-Specific Extension Gallery (bootConfig.extensionGallery)

Inside `bootConfig.extensionGallery`, Trae defines its own hosted marketplace with domain routing by region:

**Trae marketplace:**
| Region | Domain |
|---|---|
| CN | `api.trae.com.cn` |
| SG/US/USTTP | `icube-normal.trae.ai` |

**Bytedance internal marketplace:**
| Region | Domain |
|---|---|
| CN | `ide-market.bytedance.net` |
| SG/US/USTTP | `ide-market-us.tiktok-row.net` |
| Remote CN | `ide.byted.org` |
| Remote SG/US/USTTP | `ide-us.byted.org` |

**Custom extension gallery domains** (for querying external marketplaces):
1. `marketplace.visualstudio.com` - Microsoft Marketplace (type: "other")
2. `open-vsx.org` - Open VSX (type: "original")
3. `open-vsx.gitpod.io` - Gitpod mirror (type: "mirror")
4. `open-vsx.trae.ai` - **Trae's own Open VSX mirror** (type: "mirror")

### 1.5 Server URLs (bootConfig)

The `bootConfig` section contains comprehensive API endpoint configuration, region-routed across `normal`, `SG`, `US`, and `USTTP` zones:

| Service | Purpose | Normal Endpoint |
|---|---|---|
| `iCube` | Core AI platform | `https://icube-normal.trae.ai` |
| `iCubeAgent` | Agent platform | `https://icube-normal.trae.ai` |
| `frontier` | WebSocket service | `wss://frontier-normal.trae.ai/ws/v2` |
| `asr` | Speech recognition | Via iCube endpoints |
| `account.trae` | User accounts | `https://grow-normal.trae.ai` |
| `account.bytedance` | Internal accounts | `https://ide-us.tiktok-row.net` |
| `agent.trae` | AI agent service | `https://core-normal.trae.ai` |
| `agent.bytedance` | Internal agent | `https://copilot-sg-og.byteintl.net` (SG) |
| `ckg` | Code knowledge graph | `https://core-normal.trae.ai` |
| `cue` | AI code completion | `https://core-normal.trae.ai` |
| `hub` | Chat/conversation hub | `https://core-normal.trae.ai` |
| `ws` | Custom model WebSocket | `wss://wss-normal.trae.ai/custom_model` |
| `starling` | Unknown service | `https://starling-normal.trae.ai` |
| `cdn` | Content delivery | Region-specific CDN URLs |

**Notable internal (Bytedance) endpoints:**
- `https://copilot-cn.bytedance.net` - China copilot
- `https://copilot-sg.byteintl.net` - Singapore copilot
- `https://copilot.byteintl.net` - US copilot
- `https://ide-market-us.tiktok-row.net` - Internal extension marketplace
- `https://icube-api.bytedance.net/trae/ping` - Internal health check

### 1.6 MCP (Model Context Protocol) Configuration

MCP is deeply integrated into the Trae platform. Key config fields:

**`bootConfig.mcpConfig`:**
```json
{
  "trae": {
    "domain": {
      "normal": "https://icube-normal.trae.ai",
      "USTTP": "https://icube-normal.traeapi.us"
    },
    "path": {
      "searchUrl": "/extensions/api/-/agent/search",
      "detailUrl": "/extensions/api/-/agent/detail",
      "batchGetUrl": "/extensions/api/-/agent/batch-get",
      "recordVisitUrl": "/extensions/api/-/agent/record-visit",
      "recordDownloadUrl": "/extensions/api/-/agent/record-download"
    }
  },
  "bytedance": {
    "domain": {
      "normal": "https://ide-market-us.tiktok-row.net"
    },
    "path": { /* same paths */ }
  }
}
```

**`iCubeApp.aiFeatures` (MCP limits):**
| Setting | Value |
|---|---|
| `mcpToolLimit` | 40 |
| `mcpTokenLimit` | 8000 |
| `mcpTokenLimitM8` | 3000 |
| `customPromptTokenLimit` | 10000 |
| `customPromptTokenLimitM8` | 3000 |

**Sandbox configuration for MCP:**
- Sandbox read-only list includes `$WORKSPACE_FOLDER/.trae/mcp.json`
- MCP manual URL: `https://docs.trae.ai/ide/model-context-protocol`
- Set MCP system env doc: `https://docs.trae.ai/ide/model-context-protocol#7de32f4c`

### 1.7 AI/LLM Configuration

**`iCubeApp.aiFeatures`:**
| Setting | Value |
|---|---|
| `disablePeAvlCmd` | true |
| `chatMessageQueryLimit` | 200 |
| `historyQueryLimit` | 300 |
| `serverHistoryCacheLimit` | 400 |

**`iCubeApp.aiModelConfig`:**
- Has `autoDefaultConfig` with `initial` and `repeat` settings for `forceAuto`
- `modelOfflineBehavior`: `"auto_mode"`
- Model tag/tip ordering: `solo_pick, provider, multimodal, reasoning, memory, cost, beta, max_mode_switch, context_windows, access, early_access`
- Detailed tag and tooltip configuration for different model tiers (free, pro, enterprise)
- Billing tiers: lite ($5), trial ($10), pro ($20), pro_plus ($90), ultra ($400)
- Pro plan includes: 600 premium model fast requests, unlimited slow/advanced/completion, SOLO mode

**`bootConfig.git` (AI commit messages):**
- Default AI model for git: `"deepseek-V3"` (normal), `"gemini-3-flash"` (USTTP)

### 1.8 SOLO Mode Configuration

SOLO is Trae's autonomous AI coding agent mode. Configuration spans multiple sections:

- `soloBuiltinExtensions` - Dedicated SOLO extensions including `byted-solo.builtin-mcp` and `byted-solo.integrations-extended`
- `soloUrl`: `https://solo.trae.ai`
- `soloGuide` with access levels: saas=forbidden, bytedance=access, trae=access
- `soloLite` package in node_modules - lightweight React-based SOLO application
- Entitlement modals with free trial periods and tiered access

### 1.9 Authentication Configuration

**`iCubeApp.authConfig`** contains Auth0-style client IDs per environment:

| Environment | TRAE | SOLO |
|---|---|---|
| stable | `ono9krqynydwx5` | `en1oxy7wnw8j9n` |
| beta | `2k472yneke6pw3` | `nn572p8wnw1vd7` |
| alpha | `pl2689e0l0xr1n` | `0r4x5yq0r07nwp` |
| dev | `8e4olyd5e5pn36` | `y6d1xnrk6k28o3` |
| local | `qjpvq9k8j8ryde` | `4v468ylkvkwn02` |

**Native app config:**
- `authProviderId`: `icube.cloudide`
- `authProviderLabel`: `Trae IDE`
- `authDomain`: `www.trae.ai`
- `agentShareLinkAuthority`: `trae.ai-ide`

### 1.10 Monitoring and Telemetry

| Service | Purpose | Config |
|---|---|---|
| `tea` | Event tracking | App IDs: TRAE=677332, SOLO=931506 |
| `slardar` | Error monitoring | Bid: `marscode_nativeide_us` (TRAE), `solo_pc` (SOLO) |
| `slardarPC` | PC monitoring | Aid: TRAE=682161, SOLO=931506 |

### 1.11 Extension Control

**`iCubeApp.icubeExtensionControl`** blocks Microsoft's Pylance:
```json
{
  "condition": { "id": "ms-python.vscode-pylance" },
  "actions": {
    "reason": "BANNED_BY_MS",
    "level": "warning",
    "alternative": [{ "id": "detachhead.basedpyright", "name": "BasedPyright" }]
  }
}
```
Pylance is blocked from being activated by Python, BasedPyright, and Pyright extensions.

### 1.12 Process Monitoring

`singleProcessMonitors` defines resource limits for AI-related processes:

| Process Pattern | Memory Limit | CPU Limit | Weight |
|---|---|---|---|
| `icube-manager` | 2048 MB | 100% | 10 |
| `ckg_server`/`ckg` | 2048 MB | 100% | 10 |
| `ai-agent` | 2048 MB | 100% | 10 |
| `ai-completion`/`ai-server` | 2048 MB | 100% | 10 |
| `ai` (generic) | 2048 MB | 100% | 9 |

### 1.13 Auto-Run / Sandbox Configuration

The `autoRunConfig` defines security for AI-driven command execution:
- **Mode**: whitelist-based for both IDE and SOLO commands
- **Denied commands**: rm, delete, unlink, shred, dd, truncate, kill, chmod, mkfs, git force operations, database destructive operations
- **Sandbox RW list**: Includes temp dirs, package managers (npm, pip, maven, cargo, etc.), and development tool directories
- **Sandbox RO list**: `.vscode` and `.trae/mcp.json`

### 1.14 Link Protection Trusted Domains

```
*.twitter.com, *.larkoffice.com, *.juejin.cn, *.trae.ai, *.trae.com.cn,
*.trae.cn, *.byted.org, *.bytedance.net, *.bytedance.com, *.tiktok-row.org,
*.bytednsdoc.com, *.byteimg.com, *.marscode.cn, *.marscode.com,
*.vercel.com, *.reddit.com, *.supabase.com, *.mcdemo.show
```

### 1.15 defaultChatAgent

The product.json retains a `defaultChatAgent` section pointing to GitHub Copilot, but with placeholder URLs (`https://example.com`). This suggests the Trae chat agent has replaced Copilot as the default, but the VS Code base still references the Copilot structure.

---

## 2. Built-in Extensions

### 2.1 Standard VS Code Built-in Extensions (builtInExtensions)

These are the three Microsoft-built extensions included from the VS Code upstream:

| Extension | Version | SHA256 | Repo |
|---|---|---|---|
| `ms-vscode.js-debug-companion` | 1.1.3 | `7380a89078...` | vscode-js-debug-companion |
| `ms-vscode.js-debug` | 1.105.0 | `856db93429...` | vscode-js-debug |
| `ms-vscode.vscode-js-profile-table` | 1.0.10 | `7361748ddf...` | vscode-js-profile-visualizer |

### 2.2 Trae Custom Built-in Extensions (traeBuiltinExtensions)

These 12 extensions are loaded specifically for the Trae IDE:

| ID | Workspace Path | Extension Kind | Skip NPM |
|---|---|---|---|
| `cloudide.icube-devtool-ports` | `extensions/icube-devtool-ports` | desktop, remote-server | yes |
| `byted-icube.go-enhance` | `extensions/icube-guide-go-helper` | desktop, remote-server | no |
| `byted-icube.python-enhance` | `extensions/icube-guide-python-helper` | desktop, remote-server | no |
| `byted-icube.java-helper` | `extensions/icube-guide-java-helper` | desktop, remote-server | no |
| `byted-icube.node-helper` | `extensions/icube-guide-node-helper` | desktop, remote-server | no |
| `byted-icube.integrations-extended` | `extensions/icube-extended-integrations` | desktop, remote-server | no |
| `cloudide.icube-remote-ssh` | `extensions/icube-remote-ssh` | desktop | yes |
| `cloudide.dsl-agent-logs` | `extensions/dsl-agent-logs` | desktop, remote-server | no |
| `byted-icube.icube-jetbrains-experience-helper` | `extensions/icube-jetbrains-experience-helper` | desktop, remote-server | no |
| `cloudide.icube-agent-shell-exec` | `extensions/icube-agent-shell-exec` | desktop, remote-server | no |
| `git-ai.git-ai-vscode` | `modules/trae-git-ai/extension` | desktop, remote-server | no |
| `cloudide.icube-im-bridge` | `extensions/icube-im-bridge` | desktop | no |

### 2.3 SOLO Built-in Extensions (soloBuiltinExtensions)

Three extensions specifically for SOLO mode:

| ID | Workspace Path | Extension Kind |
|---|---|---|
| `byted-solo.integrations-extended` | `extensions/icube-extended-integrations` | desktop |
| `byted-solo.builtin-mcp` | `extensions/icube-builtin-mcp` | desktop, remote-server |
| `cloudide.icube-agent-shell-exec` | `extensions/icube-agent-shell-exec` | desktop, remote-server |

### 2.4 Complete Built-in Extension List (from extensions/ directory)

109 extension directories total. Full listing with name, version, and description:

**ByteDance Custom Extensions (7):**
1. `ai-code-completion` v1.0.0 - AI Code Completion (Trae's inline completion engine)
2. `go-enhance` v0.4.26 - Help users configure the go environment
3. `icube-jetbrains-experience-helper` v0.1.8 - Enhance your JetBrains IDE experience in Trae
4. `integrations-extended` v0.0.4 - Integrations extended for TRAE
5. `java-helper` v0.4.21 - Java helper for Trae
6. `node-helper` v0.2.17 - Node helper for Trae
7. `python-enhance` v0.5.10 - Manage Python environment

**CloudIDE Extensions (5):**
8. `dsl-agent-logs` v0.0.1 - Real-time DSL Agent log viewer
9. `icube-agent-shell-exec` v0.0.1 - Shell execution service for iCube Agent
10. `icube-devtool-ports` v0.0.124 - Ports Extension
11. `icube-im-bridge` v0.0.1 - Feishu and WeChat bridge for iCube
12. `icube-remote-ssh` v0.0.16 - Remote SSH development

**Other Custom Extensions (3):**
13. `git-ai-vscode` v0.1.17 - Keep track of code generated by AI
14. `mermaid-chat-features` v1.0.0 - Mermaid chat features
15. `flux-helper` v0.1.0 - A VS Code extension for Flux functionalities

**Theme Extensions (13):**
16. `theme-abyss`, `theme-defaults`, `theme-icube` (icube themes), `theme-kimbie-dark`, `theme-monokai`, `theme-monokai-dimmed`, `theme-quietlight`, `theme-red`, `theme-seti`, `theme-solarized-dark`, `theme-solarized-light`, `theme-tomorrow-night-blue`

**Language/Syntax Extensions (~70):**
Standard VS Code language extensions: bat, clojure, coffeescript, cpp, csharp, css, dart, docker, dotenv, fsharp, go, groovy, handlebars, hlsl, html, ini, java, javascript, json, julia, latex, less, lua, make, markdown, objective-c, perl, php, powershell, pug, python, r, razor, restructuredtext, ruby, rust, scss, shellscript, sql, swift, typescript, vb, xml, yaml

**Feature Extensions (~15):**
configuration-editing, css-language-features, debug-auto-launch, debug-server-ready, diff, emmet, extension-editing, git, git-base, github, github-authentication, html-language-features, ipynb, json-language-features, markdown-language-features, markdown-math, media-preview, merge-conflict, microsoft-authentication, npm, php-language-features, prompt-basics, references-view, search-result, simple-browser, terminal-suggest, tunnel-forwarding, typescript-language-features

**Debug Extensions:**
js-debug v1.104.0, js-debug-companion v1.1.3, vscode-js-profile-table v1.0.10

---

## 3. ByteDance Custom Extensions - Detailed Analysis

### 3.1 byted-icube.go-enhance
- **Version:** 0.4.26
- **Publisher:** byted-icube
- **Main:** `./dist/goMain.js`
- **Activation:** Go workspace detection (go.mod, *.go)
- **Commands:** 7 (Go environment management)
- **Has configuration:** Yes

### 3.2 byted-icube.python-enhance
- **Version:** 0.5.10
- **Publisher:** byted-icube
- **Main:** `./out/client/extension`
- **Activation:** Python workspace detection (pyproject.toml, Pipfile, setup.py, requirements.txt)
- **Commands:** 1

### 3.3 byted-icube.java-helper
- **Version:** 0.4.21
- **Publisher:** byted-icube
- **Main:** `./dist/main.js`
- **Activation:** Java workspace detection (pom.xml, *.java)
- **Commands:** 1
- **Has configuration:** Yes

### 3.4 byted-icube.node-helper
- **Version:** 0.2.17
- **Publisher:** byted-icube
- **Main:** `./dist/main.js`
- **Activation:** Node workspace detection (package.json, *.js, *.ts)
- **Commands:** 2
- **Has configuration:** Yes

### 3.5 byted-icube.integrations-extended
- **Version:** 0.0.4
- **Publisher:** byted-icube
- **Main:** `./dist/extension.js`
- **Activation:** None (always active)
- **Commands:** 17 (extensive integration commands)
- **Dependencies:** `@supabase/mcp-utils ^0.2.1` (MCP integration via Supabase)

### 3.6 byted-icube.icube-jetbrains-experience-helper
- **Version:** 0.1.8
- **Publisher:** byted-icube
- **Main:** `./dist/extension.js`
- **Activation:** `.idea` workspace detection
- **Commands:** 3 (Search Everywhere, Implementation Jump)
- **Has configuration:** Yes

### 3.7 cloudide.icube-devtool-ports
- **Version:** 0.0.124
- **Publisher:** cloudide
- **Main:** `./dist/extension.js`
- **Activation:** `*` (always active)
- **Commands:** 2 (port forwarding)
- **Has configuration:** Yes

### 3.8 cloudide.icube-remote-ssh
- **Version:** 0.0.16
- **Publisher:** cloudide
- **Main:** `./out/extension.js`
- **Activation:** Command-based (remote SSH, WSL)
- **Commands:** 30 (full SSH remote management)
- **Has configuration:** Yes

### 3.9 cloudide.dsl-agent-logs
- **Version:** 0.0.1
- **Publisher:** cloudide
- **Main:** `./dist/extension.js`
- **Activation:** On command
- **Commands:** 12 (agent log viewing)

### 3.10 cloudide.icube-agent-shell-exec
- **Version:** 0.0.1
- **Publisher:** cloudide
- **Main:** `./dist/extension.js`
- **Activation:** `*` (always active)
- **Commands:** 18 (shell execution for AI agent)

### 3.11 cloudide.icube-im-bridge
- **Version:** 0.0.1
- **Publisher:** cloudide
- **Main:** `./dist/extension.js`
- **Activation:** Feishu/WeChat commands
- **Commands:** 22 (Feishu and WeChat integration bridge)

### 3.12 git-ai.git-ai-vscode
- **Version:** 0.1.17
- **Publisher:** git-ai
- **Main:** `./out/extension.js`
- **Activation:** AI git tracking commands
- **Commands:** 3 (track AI-generated code, checkpoint)
- **Has configuration:** Yes

### 3.13 trae.flux-helper
- **Version:** 0.1.0
- **Publisher:** trae
- **Main:** `./dist/extension.js`
- **Activation:** onStartupFinished

---

## 4. AI Completion Extension Analysis

### 4.1 Extension Metadata

- **Name:** ai-code-completion
- **Display Name:** Trae: AI Code Completion
- **Version:** 1.0.0
- **Version Code:** 20260212
- **Publisher:** trae
- **Categories:** Machine Learning, Programming Languages, Education, Snippets
- **License:** MIT
- **Engine:** `vscode ^1.84.0`

### 4.2 API Proposals

The extension uses two proposed APIs:
1. `inlineCompletionsAdditions` - Enhanced inline completion capabilities
2. `icube` - Custom iCube API (ByteDance-specific)

### 4.3 Activation Events

Activates on: python, go, java, javascript, typescript, cpp, and `*` (always active)

### 4.4 Commands

| Command | Description | Keybinding |
|---|---|---|
| `trae.internal.lab.testCompFusionDisplay` | Mock Comp-Fusion Recommend Display UI | - |
| `trae.internal.lab.testCompFusionDisplayCMD` | Mock Comp-Fusion Recommend Display UI CMD | - |
| `trae.internal.lab.testGetSimilarCode` | Test Get Similar Code | - |
| `trae.internal.lab.testGetGrepSearchTool` | Test Get Grep Search Tool | - |
| `trae.acceptAllEdits` | Accept All Edits | Tab |
| `trae.buildEditRequest` | Perform an Edit Request | Ctrl+Shift+Enter |
| `trae.clearRecommendedEdits` | Clear Recommended Edits | Escape |
| `trae.selectNextEditRecommend` | Cue-Pro Select Next | Ctrl+Down |
| `trae.selectPrevEditRecommend` | Cue-Pro Select Previous | Ctrl+Up |

### 4.5 Keybindings

The extension overrides several key VS Code keybindings:
- **Tab**: Accepts AI edits or inline suggestions (context-dependent)
- **Shift+Tab**: Accepts line edits or next line of inline suggestion
- **Ctrl+Right/Cmd+Right**: Accept word-level edits
- **Escape**: Clears AI recommendations
- **Ctrl+Shift+Enter**: Triggers edit request
- **Ctrl+Up/Down**: Navigate between AI edit recommendations

### 4.6 AI Server (aiserver)

The `resource/aiserver/` directory contains the core AI inference engine:

**Key files:**

| File | Purpose |
|---|---|
| `server.js` | Main AI server (314 lines, ~15.8 MB, heavily obfuscated) |
| `cueMain.js` | Cue system main entry (obfuscated) |
| `cue.js` | Cue system logic |
| `worker.js` | Web Worker for background processing |
| `analyzer-worker.js` | Code analysis worker |
| `promptWorker.js` | Prompt engineering worker |
| `profilerWorker.js` | Performance profiling worker |
| `cueMain.js` | Cue system entry |

**Obfuscation:** The server.js uses aggressive JavaScript obfuscation (variable name mangling with hex identifiers like `_0xfb0e30`, control flow flattening, string array rotation). This is the same pattern as seen in MarsCode/Doubao AI completion tools.

**Tree-sitter WASM modules** (for code parsing):

| Language | WASM Module |
|---|---|
| C | `tree-sitter-c.wasm` |
| C++ | `tree-sitter-cpp.wasm` |
| C# | `tree-sitter-c-sharp.wasm` |
| Dart | `tree-sitter-dart.wasm` |
| Go | `tree-sitter-go.wasm` |
| Java | `tree-sitter-java.wasm` |
| JavaScript | `tree-sitter-javascript.wasm` |
| Kotlin | `tree-sitter-kotlin.wasm` |
| PHP | `tree-sitter-php.wasm` |
| Python | `tree-sitter-python.wasm` |
| Ruby | `tree-sitter-ruby.wasm` |
| Rust | `tree-sitter-rust.wasm` |
| TypeScript | `tree-sitter-typescript.wasm` |
| TypeScript React | `tree-sitter-typescriptreact.wasm` |
| Canvas | `canvaskit.wasm` (rendering) |

**Tokenizer models:**
- `codeds` - CodeDS tokenizer (tokenizer.json, tokenizer_config.json)
- `codez` - CodeZ tokenizer (tokenizer.json, tokenizer_config.json)

**Other resources:**
- Font files: `DejaVuSansMono.ttf`, `HeiTi.ttf` (Chinese font)
- Cue lint error configuration: `lintErrorCategory.config.json`
- Shell scripts: `ps.sh`, `cpuUsage.sh` (system monitoring)
- MarsCode branding logo: `codelogo.png`

### 4.7 "Cue" System

The extension implements a "Cue" system (referenced in `cue.js`, `cueMain.js`, `cueInlineSuggestionVisible`, `cueSuggestFirst`, `cueflowData`, `hasCueflowView`, `hasCueIntent`). This appears to be an advanced inline suggestion/edit system that goes beyond standard VS Code inline completions:

- **Cue-Pro**: A higher-tier suggestion mode with navigation (Ctrl+Up/Down)
- **CueFlow**: A flow-based UI for multi-step AI suggestions
- **Tab Cue**: Feature gate `enableTabCue` (currently disabled by default)
- **Cue Auto Import/Rename**: Feature gate `disableCueAutoImportAndRename`

### 4.8 dist/ Directory

The `dist/` directory contains the extension's compiled code:
- `extension.js` - Main extension entry
- `105.extension.js`, `121.extension.js`, `620.extension.js` - Code-split chunks
- `worker.js` - Web Worker
- `tree-sitter.wasm` - Tree-sitter core WASM

---

## 5. MCP (Model Context Protocol) References

### 5.1 MCP in product.json

MCP is referenced extensively in the product configuration:

1. **`extensionsGallery.mcpUrl`**: Empty in default gallery; populated in Trae-specific galleries
2. **`soloBuiltinExtensions`**: Contains `byted-solo.builtin-mcp` extension
3. **`bootConfig.mcpConfig`**: Full MCP server configuration with search, detail, batch-get, visit, and download endpoints
4. **`bootConfig.doc.mcpManualUrl`**: `https://docs.trae.ai/ide/model-context-protocol`
5. **`bootConfig.doc.setMcpSysEnvDocUrl`**: Environment variable configuration docs
6. **`aiFeatures.mcpToolLimit`**: 40 tools max
7. **`aiFeatures.mcpTokenLimit`**: 8000 tokens
8. **`aiFeatures.mcpTokenLimitM8`**: 3000 tokens (M8 tier)
9. **`autoRunConfig.sandboxROList`**: `.trae/mcp.json` is sandbox read-only

### 5.2 @byted/modelcontextprotocol-client

- **Version:** 2.0.0-alpha.2.byted.5
- **Description:** Model Context Protocol implementation for TypeScript - Client package
- **Author:** Anthropic, PBC
- **License:** Apache-2.0 / MIT (transitioning)
- **Homepage:** https://modelcontextprotocol.io
- **Repository:** https://github.com/modelcontextprotocol/typescript-sdk
- **Keywords:** modelcontextprotocol, mcp, client
- **Type:** ES Module
- **Size:** ~320 KB
- **Exports:** `./dist/index.mjs` (import), `./dist/index.d.ts` (types)

This is a **ByteDance fork** of the official Anthropic MCP TypeScript SDK client, versioned as `2.0.0-alpha.2.byted.5` (the `.byted.5` suffix indicates ByteDance's 5th patch iteration).

### 5.3 @byted/modelcontextprotocol-sdk

- **Private:** true
- **Type:** ES Module
- **Size:** ~324 KB
- **Exports:** `./dist/index.mjs` (import), `./dist/index.d.ts` (types)

This appears to be a private aggregate SDK package that bundles MCP functionality.

### 5.4 MCP in Extension Code

MCP references found in these files:
1. `package.json` (root) - Dependency declarations
2. `extensions/ai-completion/resource/aiserver/server.js` - AI server MCP integration
3. `extensions/ai-completion/resource/aiserver/cueMain.js` - Cue system MCP usage
4. `extensions/ai-completion/resource/aiserver/promptWorker.js` - Prompt worker MCP usage
5. `extensions/byted-icube.integrations-extended/package.json` - Depends on `@supabase/mcp-utils ^0.2.1`

### 5.5 MCP Architecture Summary

Trae's MCP implementation follows this architecture:
1. **Client SDK** (`@byted/modelcontextprotocol-client`) - Forked from Anthropic's official SDK with ByteDance modifications
2. **Aggregate SDK** (`@byted/modelcontextprotocol-sdk`) - Private wrapper package
3. **Built-in MCP Extension** (`byted-solo.builtin-mcp`) - SOLO mode's default MCP server
4. **MCP Configuration** (`.trae/mcp.json`) - Per-workspace MCP server configuration
5. **MCP Marketplace** (bootConfig.mcpConfig) - Central registry for MCP servers with search/detail/download endpoints at `icube-normal.trae.ai`
6. **Supabase MCP** (`integrations-extended` depends on `@supabase/mcp-utils`) - Supabase-specific MCP integration

---

## 6. @byted-icube Packages in node_modules

### 6.1 @byted-icube/ai-modules-chat
- **Version:** 0.0.1
- **Description:** Next generation of AI UI Modules
- **Publisher:** trae
- **Main:** `./dist/index.js`
- **Module:** `./dist/index.mjs`
- **Types:** `./dist-types/modules/ai-chat/index.d.ts`
- **Size:** ~15 MB (dist/index.mjs)
- **Contents:** AI chat UI components (dist/index.mjs, dist/index.css)
- **License:** MIT

### 6.2 @byted-icube/desktop-modules
- **Size:** ~47 MB (dist/index.mjs is ~12.5 MB)
- **Contents:** Desktop IDE modules, layout engine worker, SVG icons, media assets
- **Worker:** `layout-engine.worker.js` - Layout rendering engine
- **No package.json** at root (non-standard packaging)

### 6.3 @byted-icube/solo-lite
- **Version:** 0.0.1
- **Description:** SOLO Lite - A lightweight React-based application
- **Publisher:** cloudide
- **Main:** `./dist/index.js`
- **Types:** `./dist-types/index.d.ts`
- **Size:** ~8 KB (package.json only, dist not included)
- **License:** MIT

### 6.4 @byted-icube/manager-sdk
- **Version:** 0.1.1
- **Name:** @byted-icube/manager-sdk
- **Main (Node):** `node/rpcclient.js`
- **Module (Node):** `node/rpcclient.mjs`
- **Browser:** `web/rpcclient.js`
- **Browser Module:** `web/rpcclient.mjs`
- **Types:** `rpcclient.d.ts`
- **Dependencies:** `eventemitter3 ^5.0.1`
- **Size:** ~2.6 MB

### 6.5 @byted-icube/trae-network-client
- **Version:** 0.5.0-dev.1351818
- **Description:** ZeroMQ client for Trae Network Service - Node.js bindings
- **Size:** Binary native addon

### 6.6 @byted-icube/trae-network-client-linux-x64-gnu
- **Version:** 0.5.0-dev.1351818
- **Description:** ZeroMQ client for Trae Network Service - Node.js bindings (Linux x64)

### 6.7 Other @byted-icube Packages

| Package | Version | Description |
|---|---|---|
| `@byted-icube/dynamic-config-sdk` | 0.1.4 | Dynamic Config SDK for iCube applications |
| `@byted-icube/bundled-deps` | 1.0.0 | Bundled dependencies |
| `@byted-icube/slardar` | 0.0.1 | Error monitoring |
| `@byted-icube/tea` | 0.0.1 | Event tracking |
| `@byted-icube/webcomponents` | 0.1.5 | Web components |
| `@byted-icube/env` | 0.0.1 | Environment utilities |
| `@byted-icube/uploader` | 2.1.6 | Upload component from ByteDance |
| `@byted-icube/adsv` | 0.0.1 | Unknown (advertising?) |

### 6.8 @byted-fe Packages

The `@byted-fe` scope contains system utilities:
- `fd-linux-musl-x64` - `fd` file finder (musl static)
- `fd-linux-x64` - `fd` file finder (glibc)
- `ripgrep-linux-musl-x64` - ripgrep (musl static)
- `ripgrep-linux-x64` - ripgrep (glibc)

---

## 7. Key Findings Summary

1. **Trae is built on VS Code 1.107.1** with the Trae build system version 2.3.30128 and application version 3.5.60.

2. **Dual marketplace strategy**: Primary extensions from Open VSX, search from Microsoft Marketplace, plus Trae's own mirrored Open VSX at `open-vsx.trae.ai` and internal ByteDance marketplace at `ide-market-us.tiktok-row.net`.

3. **MCP is first-class**: Model Context Protocol is deeply integrated with dedicated SDK packages (forked from Anthropic's official SDK with ByteDance patches), marketplace endpoints, configuration files, and SOLO mode extension.

4. **AI completion engine is heavily obfuscated**: The ~15.8 MB server.js contains the core AI inference engine, protected with aggressive JavaScript obfuscation. It uses tree-sitter for code parsing across 14+ languages and includes custom tokenizer models (codeds, codez).

5. **Three deployment tiers**: `normal` (default international), `SG` (Singapore), `US` (US East), and `USTTP` (US TikTok) -- each with separate API endpoints.

6. **Internal ByteDance infrastructure**: Full internal copilot service at `copilot-cn.bytedance.net` / `copilot-sg.byteintl.net` / `copilot.byteintl.net`, with health checks at `icube-api.bytedance.net/trae/ping`.

7. **SOLO mode**: An autonomous AI agent mode with its own extension set, including `byted-solo.builtin-mcp` for MCP integration.

8. **Pylance is banned**: Microsoft's Pylance is explicitly blocked with reason "BANNED_BY_MS", replaced by BasedPyright.

9. **Region-aware configuration**: The entire system is designed for multi-region deployment with distinct API endpoints for China, Singapore, US, and internal ByteDance networks.

10. **ZeroMQ networking**: The `@byted-icube/trae-network-client` provides native ZeroMQ bindings for inter-process communication, suggesting a microservice architecture for AI components.
