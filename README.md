# Trae 逆向工程分析

## 简介
本项目是对Trae编辑器的逆向工程分析。Trae是一个基于VSCode/Electron开发的编辑器，由字节跳动(ByteDance)开发。

## 分析版本

| 版本 | Electron | 分析日期 | 平台 |
|------|----------|----------|------|
| v1.98.2 | v34.2.0 | 初次分析 | macOS ARM64 |
| **v2.3.30128** | **v39.2.7** | **2026-05-27** | **全平台** |

## 技术架构

Trae基于以下技术构建:
- Electron v39.2.7 (via @aha-kit/electron fork)
- VSCode核心 (1.107.1 distro, branch: release_desktop_linux_i18n)
- 字节跳动自研模块 (@byted-icube系列包)
- Rust ai-agent (127MB共享库)
- AWS Bedrock SDK (LLM推理)

## 全平台支持

| 产品 | 版本 | macOS | Windows | Linux | Mobile |
|------|------|-------|---------|-------|--------|
| TRAE IDE | 2.3.30128 | ARM64, x64 | x64 | x64, arm64 (.deb/.rpm/.tar.gz) | - |
| TRAE SOLO | 2.3.30125 | ARM64, x64 | x64 | - | iOS, Android |

## 关键发现 (v2.3.30128)

### AI模型支持 (15+模型)
- Claude 3.5 (`claude35_multi_content`)
- **GPT-5, GPT-5.2, GPT-5.2-codex, GPT-5.3-codex, GPT-5.4** (新增)
- **Gemini 3 Pro, Gemini 3.1 Pro, Gemini 3 Flash SOLO** (新增)
- **GPT-4.1** (新增)
- DeepSeek V3 / V3.1
- Qwen 2.5 / Qwen 32 (commit messages)
- 通过AWS Bedrock SDK访问Amazon Bedrock

### 工具系统
- 文件操作: view_file, create_file, edit_file, delete_file
- 代码搜索: search_by_keyword, search_by_regex, search_by_reference, search_by_definition
- 执行: run_command, terminal
- **浏览器自动化** (新增): browser_click, browser_type, browser_navigate, browser_screenshot等20+工具
- **MCP (Model Context Protocol)** (新增): 安全检查, 动态工具加载
- **子Agent系统** (新增): multi-agent orchestration
- Web: web_search, web_fetch
- AI: fast_apply, apply_patch, ask_user_question

### 安全机制
- VBVirtualize (代码虚拟化保护)
- SQLCipher (加密SQLite数据库)
- AES-256-GCM (数据加密)
- AWS Sigv4 (Bedrock请求签名)
- 命令黑名单和企业模式
- 工作区边界检查

### 网络通信
- `icube-normal.trae.ai` / `icube-normal.traeapi.us` — AI后端API
- `core-normal.trae.ai` / `core-normal.traeapi.us` — 核心API
- `api-us-east.trae.ai` — 美东区域API
- `/icube/api/v1/native/version/trae/latest` — 版本/清单API
- CDN: `lf-cdn.trae.ai` (新加坡), `lf-cdn.trae.com.cn` (中国), `lf-static.traecdn.us` (美国)

### 数据存储
- `~/.trae/` (主数据目录，从.icube迁移)
- `~/.trae/ai-agent/database.db` (SQLite + SQLCipher)

### 开发者信息泄露
多个CI/CD构建机器路径暴露在二进制文件中:
- `/Users/cmt12_v_hksab/.cargo`
- `/Users/d3fe33daf08d/.cargo`
- `/Users/runner/.cargo`
- `/root/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/`

## 项目结构

```
trae-reverse-engineering/
├── ai-agent/              # v1.98.2 ai-agent分析 (macOS Mach-O)
├── cli.js/                # v1.98.2 cli.js分析
├── main.js/               # v1.98.2 main.js分析 (tslib)
├── data/                  # v2.3.30128 下载的安装包和提取数据
│   ├── download-manifest.json  # 下载API返回的完整清单
│   ├── ide/               # IDE安装包 (darwin-arm64/x64, win32-x64, linux-x64/arm64)
│   ├── solo/              # SOLO安装包
│   └── mobile/            # APK
├── analysis/              # v2.3.30128 分析报告
│   └── comprehensive-report.md  # 综合逆向工程报告
└── docs/
    └── superpowers/
        └── plans/         # 执行计划
```

## 详细报告

- [综合逆向工程报告](analysis/comprehensive-report.md) — v2.3.30128 全平台分析
- [下载清单](data/download-manifest.json) — API返回的完整下载URL

## Trae CLI 格式化工具

见项目根目录的package.json，用于格式化cli.js文件。

## 下载API

获取最新版本清单:
```bash
curl -sk "https://api-us-east.trae.ai/icube/api/v1/native/version/trae/latest"
```
