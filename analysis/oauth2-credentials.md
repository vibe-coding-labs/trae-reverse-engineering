# OAuth2 凭证参考

> 从 main.js 和 ai-agent 二进制文件中提取

## Client IDs

| 环境 | Client ID |
|------|-----------|
| Trae IDE (通用) | `6eefa01c-1036-4c7e-9ca5-d891f63bfcd8` |
| 未知/备用 | `850edec7-b9d0-48aa-99b5-67c888e282cd` |

## OAuth2 Scopes

| Scope | 描述 | 使用场景 |
|-------|------|---------|
| `marscode` | 通用国际版 Trae/MarsCode 访问权限 | 国际用户默认 |
| `marscode_cn` | 中国区 MarsCode 访问权限 | 中国区用户 |
| `marscode_com` | MarsCode 国际站访问权限 | MarsCode 国际站 |
| `bytedance` | ByteDance 内部系统访问权限 | 内部员工 |
| `saas` | SaaS 企业版访问权限 | 企业客户 |

## OAuth2 端点

| 系统 | 授权端点 | 令牌端点 |
|------|---------|---------|
| Trae 自有 | `{tokenHost}/oauth/authorize` | `{tokenHost}/oauth/token` |
| Google | Google OAuth2 | Google Token API |
| GitHub | GitHub OAuth2 | GitHub Token API |
| GitLab | GitLab OAuth2 | GitLab Token API |
| Supabase | `https://api.supabase.com/v1/oauth/authorize` | `https://api.supabase.com/v1/oauth/token` |

## Trae API 认证端点

| 端点 | 用途 |
|------|------|
| `POST /cloudide/api/v3/trae/ExchangeToken` | 刷新 access+refresh token |
| `POST /cloudide/api/v3/trae/CheckLogin` | 检查登录状态 |
| `POST /cloudide/api/v3/trae/GetUserInfo` | 获取用户信息 |
| `POST /cloudide/api/v3/trae/GetThirdPartyToken` | 获取第三方服务 token |

## 认证头

| Header | 用途 | 来源 |
|--------|------|------|
| `Authorization: Bearer {token}` | 标准 Bearer token | JWT access token |
| `x-cloudide-token: {token}` | Trae IDE token | CloudIDE 认证 |
| `x-ide-token: {token}` | IDE 级 token | IDE 内部认证 |
| `x-frontier-id: {id}` | Frontier 连接标识 | WebSocket 握手后获得 |
