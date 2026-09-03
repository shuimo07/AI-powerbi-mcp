# dsh-powerbi-mcp

让 DeepSeek Harness (DSH) 像 Codex + MCP 方案一样 **vibe 操控 Power BI**：语义建模、PBIP/PBIR 报表设计、PBIX 分析与云操作。

本仓库提供一份**最终版提示词**（`PROMPT.md`），粘贴给 DSH（建议模型：DeepSeek-V4-Pro）即可执行接入流程。

## 内容

| 文件 | 说明 |
|---|---|
| `PROMPT.md` | 完整任务提示词：环境核查 → E 盘目录/运行时准备 → 核实三个 MCP 服务器 → 配置 DSH → 端到端验收 |

## 方案架构（三个 MCP 服务器）

| server | 来源 | 能力 |
|---|---|---|
| `powerbi-modeling` | [@microsoft/powerbi-modeling-mcp](https://www.npmjs.com/package/@microsoft/powerbi-modeling-mcp)（微软官方） | 语义模型：表/度量/关系/DAX（通常需 Power BI 服务工作区与认证） |
| `powerbi-designer` | [dbru540/powerbi-mcp-designer](https://github.com/dbru540/powerbi-mcp-designer) | 报表视觉与布局设计（file-first PBIP/PBIR） |
| `powerbi` | [AjvoGod/powerbi-mcp](https://github.com/AjvoGod/powerbi-mcp) | PBIX 分析、语义模型提取、报表导出、云操作 |

DSH 侧无需安装额外插件：`@deepseek-ai/dsh-mcp-client` 是 DSH 内置插件，按 `cordis.patch.yml` 的 `- insert:` 语法追加三个实例即可，工具以 `mcp__<serverName>__<工具名>` 形式暴露给模型。

## 参考文档

- [什么是 Power BI MCP 服务器（Microsoft Learn）](https://learn.microsoft.com/zh-cn/power-bi/developer/mcp/mcp-servers-overview)
- [Power BI 语义模型创作技能（Microsoft Learn）](https://learn.microsoft.com/zh-cn/power-bi/developer/agentic/semantic-model-authoring-skill-overview)

## 注意

- 提示词按 **Windows 本机（DSH_HOME=E:\\.dsh，profile=web）** 定制：存储优先 E 盘、不迁移既有 Node/Python、不修改 DSH 核心文件。
- 执行前请让 DSH 先跑"阶段 0 事实核查"，以实测为准调整路径与包名。
- Power BI Desktop 安装与账号登录为人工步骤（非管理员、零售版安装器不支持自定义目录）。
