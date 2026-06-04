# Trae AI API 账号 & 配额问题解决方案报告

> 生成时间: 2026-06-03
> 背景: 当前 Trae 账号配额已耗尽 (code 5003 "agent running quota limit exceeded")

---

## 一、问题本质

```
当前状态:
  refresh_token → ExchangeToken → JWT ✅ (认证完全通畅)
  agents/runs → code 5003 "quota exceeded" 🔴 (配额阻塞)
  25 个供应商中 2 个支持 client_connect 绕过配额 🔑

核心问题: 不是"不知道怎么调 API"，而是"这个账号的免费配额用完了"
```

---

## 二、3 种可行方案

### 方案 A: 🟢 DeepSeek 免费 API Key（推荐 — 最快捷）

**成本:** $0（DeepSeek 注册送免费额度）
**耗时:** 5 分钟
**方式:** `client_connect` 模式，直接用个人 API Key 调 DeepSeek，完全不经过 Trae 配额

**操作步骤:**

```
1. 浏览器打开 https://platform.deepseek.com
2. 点击 "Sign Up" → 支持邮箱注册（中国大陆/国际手机号均可）
3. 注册后进入 API Keys 页面 → 创建新的 API Key
4. 复制 key（格式: sk-xxx...）
5. 在终端设置:
   export DEEPSEEK_API_KEY='sk-你的key'
6. 测试:
   python3 scripts/trae_e2e.py --action client-chat --provider deepseek --message "你好"
```

**优点:** 免费、立即可用、不需要 Trae 账号
**缺点:** 只能用 DeepSeek 模型（但 deepseek-v4-flash 已经很强了）

### 方案 B: 🟢 Anthropic API Key

**成本:** Anthropic 有免费试用额度（新账号 $5 赠送）
**耗时:** 5 分钟
**方式:** `client_connect` 模式，直接调 Claude

**操作步骤:**

```
1. 浏览器打开 https://console.anthropic.com
2. 注册账号 → 获取 API Key (格式: sk-ant-xxx)
3. 设置:
   export ANTHROPIC_API_KEY='sk-ant-你的key'
4. 测试:
   python3 scripts/trae_e2e.py --action client-chat --provider anthropic --message "你好"
```

**优点:** 能用 Claude Sonnet 4.6，质量最好
**缺点:** Key 不是无限的（新账号有小额赠送）

### 方案 C: 🟡 注册新 Trae 账号

**成本:** $0（Trae 有 Free 套餐）
**耗时:** 5 分钟注册 + 提取 refresh_token
**方式:** 用新账号的免费配额

**操作步骤:**

```
1. 浏览器打开 https://www.trae.ai
2. 点击 "Sign Up" 或 "Download"
3. 支持 Google OAuth / GitHub OAuth / 邮箱注册
4. 注册完成后登录 Trae IDE
5. 从 IDE 本地数据库提取 refresh_token:
   cat ~/.config/Trae/User/globalStorage/storage.json | grep refresh
   或运行:
   python3 scripts/trae_token_extractor.py --action extract
6. 设置新 token:
   export TRAE_REFRESH_TOKEN='新token'
7. 验证:
   python3 scripts/trae_e2e.py --action full-diagnose
```

**注意事项:**
- Free 套餐的配额也是 "Limited usage" — 可能很快用完
- 批量注册账号 → Trae 可能有风控（设备指纹、IP 限制）
- 方案 C 适合偶尔用，不适合大量调用

---

## 三、方案对比

| 维度 | A: DeepSeek Key | B: Anthropic Key | C: 新 Trae 账号 |
|------|----------------|-----------------|----------------|
| **费用** | $0 (免费额度) | $0-$5 (新账号赠送) | $0 (Free 套餐) |
| **耗时** | 5 分钟 | 5 分钟 | 10 分钟 |
| **可持续性** | 高（可充值） | 高（可充值） | 低（配额有限） |
| **模型质量** | DeepSeek V4 (很棒) | Claude Sonnet 4.6 (最佳) | 取决于配额 |
| **可批量** | 多人共享 Key | 多人共享 Key | 需多账号 |
| **成功率** | 极高 | 高 | 中（配额限制） |

---

## 四、推荐行动路径

### 立即（今天就能跑的）：

```bash
# 方案 A — 最快
1. 去 https://platform.deepseek.com 注册拿 API Key
2. export DEEPSEEK_API_KEY='sk-your-key'
3. python3 scripts/trae_e2e.py --action client-chat --provider deepseek --message "用中文介绍自己"
```

### 同时做（准备备用方案）：

```bash
# 方案 B — 做 Anthropic Key 备用
1. 去 https://console.anthropic.com 注册拿 API Key
2. export ANTHROPIC_API_KEY='sk-ant-your-key'
3. python3 scripts/trae_e2e.py --action client-chat --provider anthropic --message "Hello"
```

---

## 五、关于"批量注册"的问题

批量注册 Trae 账号获取 refresh_token 从技术上说**可行**（注册流程走 OAuth，只需要邮箱），但：

| 风险 | 说明 |
|------|------|
| **风控封号** | Trae 可能有设备指纹/IP 限制，同一设备批量注册会被关联 |
| **容量有限** | Free 套餐的 "Limited usage" 可能每个账号只能跑几十次 agents/runs |
| **配额共享** | 同一个 TenantID 下多个账号配额可能共享 |
| **维护成本** | 需要维护 N 个 refresh_token，定期检查有没有过期 |

**结论：方案 C（批量注册）不值得花时间。** 直接弄一个 DeepSeek API Key 就能解决问题——花 5 分钟注册，用 client_connect 绕配额，比注册 10 个 Trae 账号有效率得多。
