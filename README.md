# dsh-powerbi-mcp

让 DeepSeek Harness (DSH) 像 Codex + MCP 方案一样 **vibe 操控 Power BI**：语义建模、PBIP/PBIR 报表设计、PBIX 分析与云操作。

本仓库提供：一份**最终版提示词**（`PROMPT.md`），粘贴给 DSH（建议模型：DeepSeek-V4-Pro）即可执行接入流程；以及一份**已验收的接入产物**（配置块、接入报告、自检脚本），供复用与复核。

## 内容

按**用途**分五类：

| 分类 | 路径 | 说明 |
|---|---|---|
| 📄 **提示词** | `PROMPT.md` | 完整任务提示词：环境核查 → E 盘目录/运行时准备 → 核实三个 MCP 服务器 → 配置 DSH → 端到端验收。粘贴给 DSH（建议 DeepSeek-V4-Pro）即可执行接入 |
| ⚙️ **可执行配置** | `cordis-powerbi.patch.yml` | 追加到活动 profile `cordis.patch.yml` 末尾的三实例块（含参考机备注与偏差说明） |
| 📚 **文档** | `docs/` | `接入报告.md`（环境事实 / 安装清单 / 工具数与验收证据 / C 盘写入点 / 回滚方案）、`powerbi-desktop-integration.md`（Desktop 接入记录）、`codex-powerbi-modeling-integration.md`（Codex 接入记录）、`pbir-report-build-notes.md`（**PBIR 生成与校验实战笔记**：闭集校验、分类轴、TMDL 计算列）、`desktop-userdata-to-e-drive.md`（**Desktop 用户数据搬 E 盘的 junction 方案**，修正"不可重定向"结论） |
| 🧩 **上游补丁** | `patches/` | `powerbi-mcp-desktop-discovery.patch` —— 给 AjvoGod/powerbi-mcp 的补丁：修复 Desktop 实例发现与语义模型提取（端口文件位置/编码、ADOMD 加载、DMV 列集） |
| 🔧 **脚本** | `tools/` | `mcp-inspect.cjs`（握手 + 工具清单）、`mcp-call.cjs`（只读工具冒烟）、`mcp-e2e-desktop.cjs`（Desktop 端到端）、`verify-modeling.cjs`（官方 modeling 服务自检）、`validate-pbir.py`（**离线校验 PBIP 工程，不开 Desktop 就能卡住结构错误**）、`migrate_pbi_userdata_to_e.py`（**Desktop 用户数据迁 E 盘 + 建 junction**）、`runtime/`（自检脚本的独立依赖） |
| 🛠️ **配置样例** | `configs/` | 三个服务的启动配置、参数样例（列实例 / 列连接 / 连文件夹）、Codex 配置改动前备份（已脱敏） |
| 📦 **实测产物** | `artifacts/` | `modeling-tools.json`（21 个工具的完整 schema 快照）+ `CodexConnectionCheck/`（端到端连通性验证 PBIP 工程） |

```
AI-powerbi-mcp/
├── PROMPT.md                       # 接入提示词（粘给 DSH 即用）
├── cordis-powerbi.patch.yml        # DSH profile 追加块
├── docs/                           # 接入报告 / Desktop 记录 / Codex 记录 / PBIR 实战笔记 / 用户数据迁移
├── patches/                        # 上游 powerbi-mcp 的 Desktop 发现补丁
├── tools/                          # 自检与验收脚本 + 离线校验 + 数据迁移（+ runtime/ 独立依赖）
├── configs/                        # 服务启动配置 + 调用样例 + Codex 改动前备份
└── artifacts/                      # 工具清单快照 + 连通性验证工程
```

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

## 使用侧实测（接入之后）

接入只是起点。以下是**真正拿 designer 的 PBIR 能力做报表**时踩到的坑，已沉淀成文档与脚本：

| 发现 | 结论 | 落点 |
|---|---|---|
| **PBIR 的 `title` 是闭集校验** | 多写一个未定义键（如 `showSubtitle`）不是被忽略，而是**整份报表判为无效**——表现成"所有视觉对象空白"，极易误判为"数据没加载" | [`docs/pbir-report-build-notes.md`](docs/pbir-report-build-notes.md) §1 |
| **离线校验可提前卡住** | designer 自带 validation engine（含 vendored PBIR schema），可在**不开 Desktop** 的情况下 100% 复现并定位这类错误 | [`tools/validate-pbir.py`](tools/validate-pbir.py) |
| **M 文本列当分类轴会显示 `(空白)`** | 改用 **DAX 计算列 + `sortByColumn`** 才可靠；计算列的 TMDL 块必须放在 partition **之后**且不写 `sourceColumn` | 同上 §3 / §4 |
| **`visualType` 必须用内部名** | 中文名不可用（分区图 = `areaChart`）；可在 `bin\zh-HANS\Strings.resjson` 里反查 | 同上 §5 |
| **Desktop 用户数据其实可以搬走** | 早前写的"不可重定向"**不准确**：junction 可整体搬 E 盘且路径不变，MCP 侧零改动 | [`docs/desktop-userdata-to-e-drive.md`](docs/desktop-userdata-to-e-drive.md) |

> 端到端验证产出一个 6 页 / 12 视觉对象的 PBIR 工程（`validate` `ok=True`），归档在
> [shuimo07/powerbi_work · `projects/2026-09-18/`](https://github.com/shuimo07/powerbi_work/tree/main/projects/2026-09-18)。

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
