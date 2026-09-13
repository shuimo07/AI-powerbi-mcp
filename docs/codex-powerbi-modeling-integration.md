# Codex × Power BI Modeling MCP 接入记录

- 日期：2026-09-13
- 目标：让本机 Codex 通过微软官方 MCP 服务器访问 Power BI 语义模型。
- 服务器：`@microsoft/powerbi-modeling-mcp` `0.5.0-beta.13`
- 存储：`E:\PowerBI-MCP\.npm-cache`

## 本机状态

Power BI Desktop、Node.js、Git 与 Codex CLI 均已可用。官方 MCP 已注册为全局 Codex 服务器 `powerbi-modeling`：

```text
command: npx
args: -y @microsoft/powerbi-modeling-mcp@latest --start
env:  npm_config_cache=E:\PowerBI-MCP\.npm-cache
```

首次启动时，`npx` 会把官方包缓存到 E 盘；不会将项目依赖安装到仓库内，也不会写入 Power BI 模型。

## 使用方式

1. 重启 Codex Desktop，或打开一个新 Codex 会话。
2. 在 Power BI Desktop 中打开目标 `.pbix` 或 PBIP 项目；也可连接有相应权限的 Fabric 语义模型。
3. 在 Codex 输入 `/mcp`，确认 `powerbi-modeling` 已连接。
4. 先用只读请求验证，例如：`列出当前 Power BI Desktop 模型中的表和度量值。`
5. 涉及创建、删除或修改模型对象的请求，应先审阅 Codex 展示的操作，再批准执行；执行前保留 `.pbix`/PBIP 备份。

## 边界与安全

- 该官方服务器负责语义建模、DAX 查询及模型对象操作；不编辑报表页面、视觉对象或布局。
- Power BI/Fabric 权限不会被 MCP 绕过；服务端仅能使用当前账号已有的访问权限。
- 返回给 MCP 的模型架构、元数据或查询结果可能成为模型上下文的一部分。处理敏感数据前应遵从组织的数据处理政策。
- 服务仍属预览版；更新前请在副本或分支上验证。

## 运维

查看注册状态：

```powershell
codex mcp get powerbi-modeling
```

移除注册（不删除 E 盘缓存）：

```powershell
codex mcp remove powerbi-modeling
```

Codex 的 Desktop、CLI 与 IDE 扩展共享 MCP 配置。详细配置语义见 [OpenAI 官方 MCP 文档](https://learn.chatgpt.com/docs/extend/mcp)。Power BI 模型能力与限制见 [微软项目](https://github.com/microsoft/powerbi-modeling-mcp)。
