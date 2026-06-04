# Trae 逆向分析 — 轮次 L01

**时间:** 2026-06-01
**领域:** main.js 架构
**子主题:** Manager 类 — AI Agent 管理器和 IPC 通信

---

## 关键发现

### 1. Manager 类完整架构

main.js 中的 Manager 类是 Trae AI 架构的核心组件，负责管理 ai-agent、ai-completion 等子进程的生命周期。以下是关键发现：

#### 1.1 模块注册表 (RD)

```javascript
RD = {
    completionServer: "ai-completion",   // 代码补全服务
    chatServer: "ai",                     // AI 聊天服务
    agentServer: "ai-agent"               // AI Agent 服务
}
```

三个核心 AI 服务通过此映射进行管理。

#### 1.2 端口发现机制

Manager 使用两阶段端口发现：

```
阶段 1: IPv6 检测
  - 同时尝试连接 ::1 (IPv6) 和 127.0.0.1 (IPv4)
  - 使用 Promise.any() 取最先响应的
  - 结果决定 ICUBE_USE_IPV6 环境变量

阶段 2: 端口分配
  - 起始端口: 51000 (port: 51e3)
  - 使用 getPortPromise() 分配随机端口
  - 将端口写入 {ModularData}/manager.port 文件
```

#### 1.3 WebSocket 连接 URL

```
ws://127.0.0.1:{port}/module/manager/1?session_id={sessionId}
ws://[::1]:{port}/module/manager/1?session_id={sessionId}  (IPv6 模式)
```

路径格式: `/module/{moduleName}/{moduleVersion}`

#### 1.4 IPC 消息格式

Manager 通过 WebSocket 接收以下格式的消息：

```json
{
    "msg_type": "execute_command",
    "payload": "...",
    "stream_id": "..."
}
```

已知命令：
| Command | 用途 |
|---------|------|
| `execute_command` | 执行管理命令 |
| `execute_command_result` | 命令执行结果 |
| `icube.event.aiSlardarReport` | Slardar 遥测报告 |
| `error` | 错误响应 |

#### 1.5 进程管理

```
Manager 子进程:
  - 二进制路径: {appRoot}/bin/manager (Linux/macOS) 或 manager.exe (Windows)
  - 库路径: {appRoot}/bin/lib
  - 日志路径: {userDataPath}/ModularData/manager_out.log
  - 错误日志: {userDataPath}/ModularData/manager_err.log
  - Panic 日志: {userDataPath}/ModularData/manager_panic.log
  - PID 文件: {pid}.manager.pid
```

#### 1.6 优雅关闭

```javascript
ICUBE_GRACE_PERIOD_SECONDS: "999999999"    // 非 Windows
ICUBE_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS: "999999999"  // 非 Windows
```

非 Windows 平台使用极长的优雅关闭超时，表明 Manager 进程应该长期运行。

### 2. 环境变量系统 (32 个 ICUBE_* 变量)

| 环境变量 | 用途 |
|---------|------|
| `ICUBE_PROXY_HOST` | IPC 代理主机 (127.0.0.1 或 ::1) |
| `ICUBE_PROXY_PORT` | IPC 代理端口 |
| `ICUBE_MODULAR_DATA_DIR` | 模块数据目录 |
| `ICUBE_MANAGER_PID_FILE` | Manager PID 文件路径 |
| `ICUBE_ELECTRON_PATH` | Electron 可执行路径 |
| `ICUBE_MACHINE_ID` | 机器唯一 ID |
| `ICUBE_BUILD_VERSION` | 构建版本号 |
| `ICUBE_QUALITY` | 发布质量 (stable/alpha) |
| `ICUBE_APP_VERSION` | 应用版本 |
| `ICUBE_VSCODE_VERSION` | VSCode 核心版本 |
| `ICUBE_PRODUCT_TYPE` | 产品类型 (desktop) |
| `ICUBE_USER_DATA_DIR` | 用户数据目录 |
| `ICUBE_GLOBAL_STORAGE_DIR` | 全局存储目录 |
| `ICUBE_FORCE_RANDOM_PORT` | 强制随机端口 |
| `ICUBE_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS` | 优雅关闭超时 |
| `ICUBE_MODULE_LOG_TO_FILE` | 模块日志到文件 |
| `ICUBE_MODULE_PID_DIR` | 模块 PID 目录 |
| `ICUBE_DISABLED_MODULES` | 禁用模块列表 |

### 3. 重试机制

```javascript
retryDelays = [1, 1, 2, 3, 5];  // 秒
maxRetries = 100;                // 最大重试次数
retryCounter = 0;                // 当前重试计数
errorThreshold = 100;            // 错误上限
```

- 使用循环指数退避 (固定数组而非指数公式)
- 达到 errorThreshold 后停止遥测报告（因为 Slardar/Tea 可能也挂了）
- 子进程退出后自动重启

### 4. 其他发现

- **IPC 通道**: 仅 `vscode:getManagerInfo` 通过 ipcMain.handle 暴露
- **Slardar 遥测**: `iCubeSlardarService` 和 `iCubeTeaService` 实现事件上报
- **进程监控**: `processDiagnosticsMainService` 监控进程内存/CPU
- **进程退出处理**: 监听 `quit` 事件和 `process.once('exit')`

---

## 代码/数据证据

来自 main.js Manager.js 模块的直接提取：

```javascript
// Manager.js 模块 (已解混淆)
// 端口: 51000 起始
const proxyPort = await getPortPromise({ port: 51000, host: ipv6 ? "::1" : "127.0.0.1" });

// 进程环境
process.env.ICUBE_USE_IPV6 = ipv6.toString();
process.env.ICUBE_PROXY_HOST = ipv6 ? "::1" : "127.0.0.1";
process.env.ICUBE_PROXY_PORT = proxyPort.toString();
process.env.ICUBE_ELECTRON_PATH = process.execPath;
process.env.ICUBE_CODEMAIN_SESSION = sessionId;

// PID 文件
const pidFile = `${process.pid}.manager.pid`;

// 端口持久化
writeFileSync(join(modularData, "manager.port"), String(proxyPort));

// WebSocket 连接
const wsUrl = `ws://${host}:${port}/module/manager/1?session_id=${sessionId}`;

// 重试
const retryDelays = [1, 1, 2, 3, 5];
const maxRetries = 100;

// 禁用模块配置
const disabledModules = (process.env.ICUBE_DISABLED_MODULES?.split(",") || []);
// 从 nativeAppConfig.dsc 中读取模块禁用状态
for (const key in nativeAppConfig) {
    if (RD[key] && nativeAppConfig[key] === true) disabledModules.push(RD[key]);
}
```

---

## 技术细节

### Manager 启动时序

```
1. 主进程启动
2. 创建 Manager 实例 (new Manager(...))
3. 端口探测 (IPv6 vs IPv4)
4. 分配随机端口 (51000+)
5. 设置 32 个 ICUBE_* 环境变量
6. 生成 WebSocket URL + session_id
7. 启动 Manager 子进程 (bin/manager)
8. Manager 子进程连接到 WebSocket
9. 通过 ipcMain.handle('vscode:getManagerInfo') 暴露端口
10. 子进程退出 → 重试 (最多 100 次，指数退避)
```

### AI 模块依赖树

```
vscode.main.js (Electron 主进程)
  └── Manager (进程管理器)
       ├── bin/manager (Manager 守护进程)
       │    ├── WebSocket IPC (/module/manager/1)
       │    ├── 子进程管理 (ai-agent, ai-completion)
       │    └── ZMQ Dealer-Router 通信
       ├── ai-agent (Rust 共享库 / AI 核心)
       │    ├── LLM Providers (7 个)
       │    ├── Agent Workflow
       │    └── Tool System
       └── ai-completion (代码补全)
```

---

## 待验证点

1. [ ] bin/manager 可执行文件的具体实现（Go/Rust？）
2. [ ] ai-agent 作为共享库的加载方式（dlopen/napi-rs?）
3. [ ] ZMQ Dealer-Router 在 ai-agent 内部的具体实现
4. [ ] Module 系统如何加载和通信（除了 manager/1 外还有哪些 module）
5. [ ] `module/manager/1` 的 1 代表协议版本，其他版本的差异
6. [ ] Slardar/Tea 遥测的具体数据格式

---

## 本轮总结

L01 深入分析了 main.js 中的 Manager 类，发现了完整的 AI 进程管理架构。Manager 使用 WebSocket 作为 IPC 通信方式，管理 ai-agent、ai-completion 等 AI 子进程。关键发现包括 32 个环境变量、端口发现机制、重试策略和消息格式。

**→ 下一轮 (L02):** 继续 main.js 分析，深入 @byted-icube 模块和 Handler 注册机制