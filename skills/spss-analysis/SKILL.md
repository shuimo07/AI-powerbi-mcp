---
name: spss-analysis
description: 在对话里直接驱动本机 IBM SPSS Statistics 跑统计、出论文级图表（全程不开 SPSS 界面）。当任务涉及"用 SPSS 做描述统计/频数/交叉表/t 检验/方差分析/相关/回归/卡方/信度"、"打开 .sav 看变量和数据"、"CSV 转 .sav"、"SPSS 出图（直方图/散点/箱线/条形/折线）、导出 300dpi PNG 投稿图"、"SPSS 无界面 / headless / OMS / GGRAPH"时使用。参考机为 SPSS 27（装在 E:\大三·）且实测通过。
agent_created: true
---

# 对话驱动 SPSS（MCP 通道 + 无界面出图）

> 本文件是仓库版（路径已脱敏，把 `<user>` 换成本机用户名、`E:\大三·` 换成实际 SPSS 安装目录）。
> 本机安装位置：`%USERPROFILE%\.workbuddy\skills\spss-analysis\`。

## 一、通道现状（参考机已装好并验证）

| 部件 | 位置 / 值 |
|---|---|
| MCP 服务名 | `spss`（注册在 `%USERPROFILE%\.workbuddy\mcp.json`，片段见仓库 `configs/mcp.spss.json`） |
| 上游实现 | `meteor0620/spss-mcp`(MIT)，本地副本 **`E:\SPSS-MCP`**（含 .git，可 `git pull` 更新） |
| 服务端解释器 | **`E:\venvs\spss-mcp\Scripts\python.exe`**（pyreadstat + pandas + Pillow） |
| SPSS 本体 | **IBM SPSS Statistics 27.0.1**，装在 **`E:\大三·\`**（非默认路径） |
| 引擎解释器 | **`E:\大三·\Python3\python.exe`**（Python 3.8.2，`spss` 模块已内置） |

- 引擎由 MCP 常驻维护：**冷启动只有第一次调用**，之后毫秒级；`DATASET NAME` 建的数据集**跨调用保留**。
- **如果工具列表里没有 `spss_*`**：让用户去「连接器管理 → 右上角自定义连接器」对 `spss` 点**信任**并重启应用。
- 想先自检通道（不经 MCP）：
  ```bash
  cd /e/SPSS-MCP && "/e/大三·/Python3/python.exe" spsscli.py syntax --arg "SHOW VERSION."
  ```
  返回 `STATS.EXE 27.00.01.00` 即正常。完整四步自检：`tools/spss-verify.py`。

## 二、可用工具（7 个）

| 工具 | 用途 | 要引擎 |
|---|---|---|
| `spss_run_syntax` | **主力**：跑 SPSS 语法，返回过程输出表格 | 是 |
| `spss_run_python` | 在 SPSS Python 集成里跑代码（`spss` 模块已导入，返回变量 `result`） | 是 |
| `spss_reset_engine` | 重启引擎、清空内存状态（引擎假死时自救） | 是 |
| `spss_dict` | 变量字典：名称/标签/格式/值标签/测量层级/行数 | 否 |
| `spss_read` | 读数据行（可限行数/列，返回 CSV 文本） | 否 |
| `spss_sav2csv` | `.sav` → CSV | 否 |
| `spss_csv2sav` | CSV → `.sav`（数值列自动识别） | 否 |

## 三、标准流程

1. **先看数据**：`spss_dict` / `spss_read` 摸清变量名——**后续语法里的变量名必须与之一致**（拼错会连锁 `errLevel 3`）。
2. **CSV 必须先转 `.sav`**：无界面后端直接 `GET DATA` 读 CSV 会报 `errLevel 3`。用 `spss_csv2sav`。
3. **跑分析**：`spss_run_syntax`。语法要求：**每条命令独立成行、以 `.` 结尾**；失败时会标出 `ROOT CAUSE` 命令与修正提示。
4. **出图**：用 `spss_run_syntax` 跑 `OMS` 包裹的图表语法（见第四节），图会被内嵌进 HTML。
5. **提图**：`python <本skill>/scripts/extract_chart.py <chart.html> --out-dir <E盘目录>` → 300dpi PNG。

## 四、无界面出图（核心：`IMAGES=YES`）

> **唯一关键点：`OMS` 必须带 `IMAGES=YES`，否则 SPSS 不会把图渲染进 HTML，提取时什么都拿不到。**

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

**OMS 四件套，少一个都失败**：`/TAG='IMG1'`（命名）、`/SELECT CHARTS`（只抓图）、**`IMAGES=YES`**（渲染图）、`OMSEND TAG='IMG1'.`（配对关闭）。
`OUTFILE` **不会自动补扩展名**，必须自己写全 `xxx.html`。

### 其它常用图（一行版）
```spss
GRAPH /SCATTERPLOT(BIVAR)=x WITH y /MISSING=LISTWISE.
GRAPH /BOXPLOT(VARIABLES)=y BY grp.
GRAPH /LINE(SIMPLE)=MEAN(y) BY x.
GRAPH /PIE=COUNT BY grp.          /* 饼图别用 GPL 的 shape.pie（未定义） */
```

## 五、雷区清单（真机踩过的）

| 症状 | 原因 | 解法 |
|---|---|---|
| HTML 有内容但提不到图 | **漏 `IMAGES=YES`** | 补上 |
| `Unknown keyword: IMAGE` | 用了废弃写法 `FORMAT=IMAGE` | 改 HTML 路线 |
| `[errLevel 3] Serious error`（连锁一片） | 变量名拼错 / CLI 直读 CSV | 先 `spss_dict` 核对；CSV 先转 `.sav` |
| `T-TEST` 等过程报 `errLevel 3`，但变量名数据都对 | 分组变量是**长字符串**（CSV 导入后自动 `A9`，SPSS 这类过程只吃 **≤8** 的字符串） | `ALTER TYPE grp (A1).` 收窄，或改用数值型分组变量（实测 `A8` ✅ / `A9` ❌） |
| `END GPL.` 后同行的 `OMSEND` 不生效 | 命令没换行 | `END GPL.` 后**必须换行** |
| GPL 报 repeated keyword | 写成 `VARIABLES=x VARIABLES=y` | 写 `VARIABLES=x y` |
| GPL error on 聚合 | 在 `position()` 里内联 `summary.mean(v)` | 在 `/GRAPHDATASET` 预计算 `MEAN(v)[name="MEAN_v"]` |
| `line` 元素颜色不生效 | 用了 `color.exterior` | 用 `color.interior` |
| 出图后连 `GET DATA` 都崩 | 引擎被污染 | `spss_reset_engine`，必要时任务管理器杀 `stats.exe` 重启应用 |
| 导出的"PNG"其实是 JPEG | SPSS 忽略 `IMAGEFORMAT=PNG` | 提取脚本按实际格式解码，别硬编码扩展名 |
| 图只有 800×500、无 DPI | SPSS 导出按像素不给 DPI | 提取脚本 LANCZOS 放大 + 重写 DPI（脚本已处理） |

## 六、产物落盘约定

- **一律落 E 盘**（用户硬要求，禁止占 C 盘）：让用户给个目录，或默认 `<工程目录>/spss_result/`。
- 建议命名：`NN_<分析类型>.png` / `.spv`；图表与结果表分别归档，别把调试图混进交付目录。
- 严格矢量图需求走 EMF 路线：`OMS ... FORMAT=DOC OUTFILE='x.docx'` → 解压取 `word/media/imageN.emf`。

## 七、换电脑 / 重装（回滚用）

1. `git clone https://github.com/meteor0620/spss-mcp.git E:\SPSS-MCP`（钉住 `807f8f6`）
2. 建 venv：`"C:\Users\<user>\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m venv E:\venvs\spss-mcp`
   - 装依赖：`E:\venvs\spss-mcp\Scripts\python.exe -m pip install pyreadstat pandas Pillow -i https://pypi.org/simple`
   - ⚠ **清华镜像上没有 pyreadstat**（报 `No matching distribution found`），必须用官方源。
3. 把 `config/mcp.spss.json` 的 `spss` 段合并进 `%USERPROFILE%\.workbuddy\mcp.json`，按新机器改 `SPSS_PY`。
4. 连接器管理 → 右上角自定义连接器 → 信任 `spss` → 重启应用。
5. 跑 `tools/spss-verify.py` 四步自检。

## 八、出处与致谢

- MCP 服务端：`meteor0620/spss-mcp`（MIT）——常驻引擎 + pyreadstat 文件 I/O + 失败根因诊断。
- **`OMS IMAGES=YES` 无界面出图技巧**参考 `ZHENGHAOYa/workbuddy-spss-headless-chart`（本 skill 的提取脚本为自行实现，非直接复制）。
- 备选上游：`Exekiel179/SPSS-MCP`（36 个现成统计工具）。
- 部分踩坑（`errLevel 3` 连锁、`END GPL.` 换行、GPL 雷区）来自上述两项目的实践总结，已在参考机复现确认。
