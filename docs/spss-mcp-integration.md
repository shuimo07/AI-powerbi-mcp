# SPSS × MCP 接入报告（对话里直接驱动 SPSS + 无界面出论文级图表）

> 目标：在对话里输入"要实现的 SPSS 操作"→ 立刻拿到结果表 / 图；**全程不开 SPSS 界面**；
> 产物一律落 **E 盘**。本文件记录环境事实、选型、安装清单、验收证据、雷区与回滚。
> 接入日期：2026-09-25（Windows 本机，IBM SPSS Statistics 27）。

## 0. TL;DR

| 问题 | 答案 |
|---|---|
| 客户端更新后能不能"直接调用 SPSS"？ | **不能**。`%USERPROFILE%\.workbuddy\mcp.json` 的 `mcpServers` 为空、技能市场搜 "SPSS" 0 命中、官方连接器市场无 SPSS 条目 —— 更新本身不产生任何 SPSS 通道，必须自建 MCP。 |
| 怎么解决？ | 抄开源上游 `meteor0620/spss-mcp`（MIT）当通道，**本机 SPSS 27 真机验证通过**：语法执行回读结果表、无界面出图 → 300dpi PNG。 |
| 动了几处 C 盘？ | **只有一处**：`%USERPROFILE%\.workbuddy\mcp.json`（几百字节的注册文件，live home 根目录无法 junction）。其余全部在 E 盘。 |

## 1. 环境事实核查（实测，非推测）

| 项 | 实测值 |
|---|---|
| SPSS 本体 | **IBM SPSS Statistics 27.0.1**（`Version=27.0.1.0`，`STATS.EXE 27.00.01.00`，2020-10-09） |
| 安装路径 | **`E:\大三·\`**（**非默认路径**，安装根下 707 个顶层条目） |
| 授权 | 安装根下存在 `lservrc`，已激活（`spssprod.inf` 的 `CustomerName` 非空） |
| 自带 Python | `E:\大三·\Python3\python.exe` = **Python 3.8.2**，`site-packages\spss` 模块内置 |
| 驱动方式 | 外部模式：`import spss; spss.Submit("<语法>")` → 返回文本结果表，**不弹 GUI** |
| 历史残留 | `spssprod.inf` 的 `CommonRoot=E:\八爪鱼\common`（该目录已不存在）——**不影响使用**，无需修复 |

自检命令（不经 MCP）：

```bash
cd /e/SPSS-MCP && "/e/大三·/Python3/python.exe" spsscli.py syntax --arg "SHOW VERSION."
# → 返回 STATS.EXE / SPSSWCTL.DLL … 27.00.01.00 版本表即正常
```

## 2. 选型

| 候选 | 取舍 |
|---|---|
| **`meteor0620/spss-mcp`（MIT）← 采用** | 明确面向 **SPSS 27**、假定安装目录下有 `Python3\python.exe`；通用 stdio MCP（不绑客户端）；`SPSS_PY` 环境变量可指向**非默认安装路径**；常驻引擎（冷启动只有第一次）；失败时给根因命令 |
| `Exekiel179/SPSS-MCP`（MIT，36 工具） | 工具更多（频数/交叉表/t 检验/回归…各自独立工具），但其 `configure-claude` 只写 Claude Code 配置，WorkBuddy 需手改；未采用 |

**钉住版本**：`meteor0620/spss-mcp@807f8f69ed6e8e3b37c752d5f0ee0961d2e4eabc`（2026-09-02）。

## 3. 安装清单

| 部件 | 路径 / 值 |
|---|---|
| 上游副本（含 `.git`，可 `git pull`） | **`E:\SPSS-MCP`** |
| 服务端 venv | **`E:\venvs\spss-mcp`**（Python 3.13.14 + pyreadstat 1.3.6 + pandas 3.0.6 + Pillow 12.3.0） |
| MCP 注册 | `%USERPROFILE%\.workbuddy\mcp.json` → `mcpServers.spss`（片段见 [`configs/mcp.spss.json`](../configs/mcp.spss.json)） |
| 引擎解释器 | `env.SPSS_PY = E:\大三·\Python3\python.exe` |
| 技能（agent SOP） | `skills/spss-analysis/`（本机安装位置 `%USERPROFILE%\.workbuddy\skills\spss-analysis\`，实体在 E 盘） |

```bash
"C:/Users/<you>/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m venv "E:\venvs\spss-mcp"
"E:\venvs\spss-mcp\Scripts\python.exe" -m pip install pyreadstat pandas Pillow -i https://pypi.org/simple
```

> ⚠ **`pyreadstat` 必须用官方源装**：清华镜像上直接报 `No matching distribution found`（不是缺 wheel，是镜像里没有这个包），换 `-i https://pypi.org/simple` 一次通过。
>
> ⚠ 改完 `mcp.json` 后要到「**连接器管理 → 右上角自定义连接器**」对新服务点 **信任** 并重启应用，工具才会以 `spss_*` 出现。

## 4. 工具一览（7 个）

| 工具 | 用途 | 需要引擎 |
|---|---|---|
| `spss_run_syntax` | **主力**：执行 SPSS 语法并回读过程输出表格；引擎常驻，`DATASET NAME` 建的数据集**跨调用保留** | 是 |
| `spss_run_python` | 在 SPSS Python 集成里跑代码（`spss` 模块已导入） | 是 |
| `spss_reset_engine` | 重启引擎清状态（引擎假死自救） | 是 |
| `spss_dict` | 变量字典（名称/标签/格式/值标签/测量层级/行数） | 否 |
| `spss_read` | 读数据行（返回 CSV 文本） | 否 |
| `spss_sav2csv` / `spss_csv2sav` | `.sav` ↔ CSV 互转 | 否 |

文件类工具走 `pyreadstat` 进程内直调（秒级、不占引擎）；统计过程才进引擎。

## 5. 验收证据（2026-09-25 真机）

| 验证项 | 结果 |
|---|---|
| 引擎连通 | `SHOW VERSION.` → `STATS.EXE 27.00.01.00` 版本表 ✅ |
| MCP 握手 | `initialize` → `spss-mcp 1.1.0`；`tools/list` → 7 个工具 ✅ |
| 统计过程 | `DESCRIPTIVES` / `T-TEST` 返回完整结果表（含 Levene 检验、95% CI）✅ |
| CSV→SAV | `spss_csv2sav` 生成 `.sav`，变量名自动清洗（`F8.2`/`A9`）✅ |
| **无界面出图** | `OMS IMAGES=YES` + `GRAPH`/`GGRAPH` 一次跑出 **3 张图**（直方图 / 分组条形图 / 散点+拟合线），提取为 **1950×1500 @300dpi PNG** ✅ |

证据文件：[`artifacts/spss-headless-charts/`](../artifacts/spss-headless-charts/)（3 张 300dpi PNG）。

## 6. 无界面出图（核心：`IMAGES=YES`）

> **唯一关键点：`OMS` 必须带 `IMAGES=YES`**。漏了 → SPSS 不把图渲染进 HTML → 提取阶段一无所获，
> 极易被误判成"headless 环境不支持图表渲染"（曾有开源作者因此误建议升级到 SPSS 32 / 装虚拟显示器，真因只是少个关键字）。

```spss
GET FILE='E:\...\data.sav'.
OMS /TAG='IMG1' /SELECT CHARTS /DESTINATION FORMAT=HTML IMAGES=YES IMAGEFORMAT=PNG OUTFILE='E:\...\chart.html'.
GRAPH /HISTOGRAM(NORMAL)=y.
GRAPH /BAR(SIMPLE)=MEAN(y) BY grp.
GGRAPH
  /GRAPHDATASET NAME="graphdataset" VARIABLES=x y
  /GRAPHSPEC SOURCE=INLINE.
BEGIN GPL
  SOURCE: s = userSource(id("graphdataset"))
  DATA: xx = col(source(s), name("x"))
  DATA: yy = col(source(s), name("y"))
  GUIDE: axis(dim(1), label("X"))
  GUIDE: axis(dim(2), label("Y"))
  GUIDE: text.title(label("图标题"))
  GUIDE: text.footnote(label("脚注：r = .83, p < .001, N = 30"))
  ELEMENT: point(position(xx*yy))
  ELEMENT: line(position(smooth.linear(xx*yy)), color.interior(color.red))
END GPL.
OMSEND TAG='IMG1'.
```

**OMS 四件套**（少一个都失败）：`/TAG='IMG1'` · `/SELECT CHARTS` · **`IMAGES=YES`** · `OMSEND TAG='IMG1'.`
`OUTFILE` **不会自动补扩展名**，必须写全 `xxx.html`。

### 雷区清单（真机踩过）

| 症状 | 原因 | 解法 |
|---|---|---|
| HTML 有内容但提不到图 | 漏 `IMAGES=YES` | 补上 |
| `Unknown keyword: IMAGE` | 用了废弃写法 `FORMAT=IMAGE` | 改 HTML 路线 |
| `[errLevel 3] Serious error`（连锁一片） | **变量名与数据不一致** / CLI 直读 CSV | 先 `spss_dict` 核对变量名；CSV 先转 `.sav` |
| `T-TEST` 等过程报 `errLevel 3`，但变量名、数据都对 | 分组变量是**长字符串**：CSV 导入后自动宽度 `A9`，SPSS 只允许 **≤8** 的字符串参与这类过程 | `ALTER TYPE grp (A1).` 收窄，或改用数值型分组变量。**实测对照：`A8` ✅ / `A9` ❌** |
| `END GPL.` 后 `OMSEND` 不生效 | 两条命令写在同一行 | `END GPL.` 后**必须换行** |
| GPL `repeated keyword` | 写成 `VARIABLES=x VARIABLES=y` | 写 `VARIABLES=x y` |
| GPL 报聚合错误 | 在 `position()` 里内联 `summary.mean(v)` | 在 `/GRAPHDATASET` 预计算 `MEAN(v)[name="MEAN_v"]` |
| `line` 颜色不生效 | 用了 `color.exterior` | 用 `color.interior` |
| 出图后连 `GET DATA` 都崩 | 引擎被污染 | `spss_reset_engine`，必要时杀 `stats.exe` 并重启应用 |
| 导出"PNG"其实是 JPEG | SPSS 忽略 `IMAGEFORMAT=PNG` | 提取脚本按实际格式解码，**别硬编码扩展名** |
| 图只有 800×500 且无 DPI | SPSS 导出按像素、不给 DPI | LANCZOS 放大 + 重写 DPI（提取脚本已处理） |

## 7. 自检 / 换机复现

```bash
"E:\venvs\spss-mcp\Scripts\python.exe" tools/spss-verify.py --out-dir E:\tmp\spss-verify
```

四步一条命令：引擎版本 → CSV→SAV → 统计过程 → `OMS` 出图 + 提取 300dpi PNG，逐项打印 PASS/FAIL。
可复现的完整流程另见技能文件 [`skills/spss-analysis/SKILL.md`](../skills/spss-analysis/SKILL.md)。

## 8. 存储与 C 盘写入点

| 类型 | 位置 |
|---|---|
| 唯一 C 盘写入 | `%USERPROFILE%\.workbuddy\mcp.json`（**几百字节**，live home 根目录无法 junction，属必须留 C 的配置文件） |
| 技能目录 | `%USERPROFILE%\.workbuddy\skills\` → 已做 **symlink 到 E 盘**，实际写在 E |
| 工程 / venv / 产物 | 全在 E 盘（`E:\SPSS-MCP`、`E:\venvs\spss-mcp`） |

## 9. 回滚

1. 删掉 `%USERPROFILE%\.workbuddy\mcp.json` 里的 `mcpServers.spss` 段（**只删这一段**，勿整文件覆盖）→ 重启应用。
2. 删目录 `E:\SPSS-MCP`、`E:\venvs\spss-mcp`。
3. 不再需要时移除技能目录 `spss-analysis`。

SPSS 本体与授权不受任何影响（本方案只读驱动，不改 SPSS 安装）。

## 10. 已知限制

- 引擎会话由 MCP 常驻进程持有；同一时刻一个会话，`DATASET` 状态在进程内延续。
- 图表是位图（JPEG 内嵌 → 放大到 300dpi），文字边缘略软；**严格矢量**需求走 EMF 路线：
  `OMS ... FORMAT=DOC OUTFILE='x.docx'` → 解压取 `word/media/imageN.emf`。
- SPSS 27 自带的 Python 是 3.8.2，服务端另用 3.13 venv；两边不要互相装包。
