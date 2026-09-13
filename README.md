# dsh-powerbi-mcp

让 DeepSeek Harness (DSH) 像 Codex + MCP 方案一样 **vibe 操控 Power BI**：语义建模、PBIP/PBIR 报表设计、PBIX 分析与云操作。

本仓库提供：一份**最终版提示词**（`PROMPT.md`），粘贴给 DSH（建议模型：DeepSeek-V4-Pro）即可执行接入流程；以及一份**已验收的接入产物**（配置块、接入报告、自检脚本），供复用与复核。

## 内容

| 文件 | 说明 |
|---|---|
| `PROMPT.md` | 完整任务提示词：环境核查 → E 盘目录/运行时准备 → 核实三个 MCP 服务器 → 配置 DSH → 端到端验收 |
| `cordis-powerbi.patch.yml` | **可执行配置**：追加到活动 profile `cordis.patch.yml` 末尾的三实例块（含参考机备注与偏差说明） |
| `docs/接入报告.md` | 参考机接入报告：环境事实、安装清单、工具数与验收证据、C 盘写入点清单、回滚方案 |
| `docs/powerbi-desktop-integration.md` | **Power BI Desktop 接入记录**：三个 server 的 Desktop 能力、上游缺陷与修复、配置片段、验证方式 |
| `docs/codex-powerbi-modeling-integration.md` | **Codex 接入记录**：微软官方 Modeling MCP 的 E 盘缓存、注册状态、使用边界与回滚方式 |
| `patches/powerbi-mcp-desktop-discovery.patch` | 给 AjvoGod/powerbi-mcp 的补丁：修复 Desktop 实例发现与语义模型提取（端口文件位置/编码、ADOMD 加载、DMV 列集） |
| `tools/` | 自检脚本：`mcp-inspect.cjs`（握手+工具清单）、`mcp-call.cjs`（只读工具冒烟）、`mcp-e2e-desktop.cjs`（Desktop 端到端） |

## 状态与验收（2026-09-03 接入 / 2026-09-11 补 Desktop）

参考机已完成接入并通过本地端到端验收（详见 `docs/接入报告.md`）：

| serverName | 启动方式（实测） | 工具数 | 验收证据 |
|---|---|---|---|
| `powerbi-modeling` | `npx -y @microsoft/powerbi-modeling-mcp --start` | 21 | 本地 TMDL 连接：11 表/61 度量/11 关系全链路只读 ✅；Power BI Desktop 直连（发现→连接→列库→读模型）✅ |
| `powerbi-designer` | E 盘 venv：`python -m powerbi_mcp.server` | 92 | PBIP 项目摘要/页清单经 DSH 桥直调 ✅；Desktop 定位 doctor `[OK]` ✅ |
| `powerbi` | 本地构建：`node dist\index.js` | 12 | server_info + 11 个 PBIX 本地工具 ✅；Desktop 发现/提取经补丁修复后可用 ✅ |

接入后在新会话可见工具前缀 `mcp__powerbi-modeling__*` / `mcp__powerbi-designer__*` / `mcp__powerbi__*`；配置热重载即时生效（watchUserPatches + HMR），回滚=删除追加块即可。

> 实测偏差：designer 用 venv 而非 uvx（商店版 Python 的 EFS 复制错误）；powerbi 用本地构建而非 `npx github:`（参考机 git TLS 证书链异常）；modeling 需官方 `--start` 参数；powerbi 的 Desktop 工具需应用 `patches/` 下的补丁。细节见 `docs/接入报告.md` 第 4/8 节与 `docs/powerbi-desktop-integration.md`。
>
> Desktop 相关提醒：程序本体可放非系统盘，但用户数据仍在 `%LOCALAPPDATA%\Microsoft\Power BI Desktop`；把程序移出 C 盘会使 HKLM 的 MSI 记录失效；Desktop 未打开报表时本地 AS 的 DMV 返回 0 行（属正常）。

## 方案架构（三个 MCP 服务器）

| server | 来源 | 能力 |
|---|---|---|
| `powerbi-modeling` | [@microsoft/powerbi-modeling-mcp](https://www.npmjs.com/package/@microsoft/powerbi-modeling-mcp)（微软官方） | 语义模型：表/度量/关系/DAX（通常需 Power BI 服务工作区与认证） |
| `powerbi-designer` | [dbru540/powerbi-mcp-designer](https://github.com/dbru540/powerbi-mcp-designer) | 报表视觉与布局设计（file-first PBIP/PBIR） |
| `powerbi` | [AjvoGod/powerbi-mcp](https://github.com/AjvoGod/powerbi-mcp) | PBIX 分析、语义模型提取、报表导出、云操作 |

DSH 侧无需安装额外插件：`@deepseek-ai/dsh-mcp-client` 是 DSH 内置插件，按 `cordis.patch.yml` 的 `- insert:` 语法追加三个实例即可，工具以 `mcp__<serverName>__<工具名>` 形式暴露给模型。

## Codex 接入

除 DSH 方案外，本仓库也记录了 Microsoft 官方 `powerbi-modeling-mcp` 在 Codex 中的独立接入方式。该方案通过本地 stdio MCP 将 Codex 连接到 Power BI 语义模型，并将 npm 缓存保留在 E 盘；它不覆盖本仓库既有 DSH 配置，也不负责报表视觉层编辑。详见 [Codex × Power BI Modeling MCP 接入记录](./docs/codex-powerbi-modeling-integration.md)。

## 参考文档

- [什么是 Power BI MCP 服务器（Microsoft Learn）](https://learn.microsoft.com/zh-cn/power-bi/developer/mcp/mcp-servers-overview)
- [Power BI 语义模型创作技能（Microsoft Learn）](https://learn.microsoft.com/zh-cn/power-bi/developer/agentic/semantic-model-authoring-skill-overview)

## 注意

- 提示词按 **Windows 本机（DSH_HOME=E:\\.dsh，profile=web）** 定制：存储优先 E 盘、不迁移既有 Node/Python、不修改 DSH 核心文件。
- 执行前请让 DSH 先跑"阶段 0 事实核查"，以实测为准调整路径与包名。
- Power BI Desktop 安装与账号登录为人工步骤（非管理员、零售版安装器不支持自定义目录）。
