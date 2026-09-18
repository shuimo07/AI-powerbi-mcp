# PBIR 报表生成与校验实战笔记

用 `powerbi-designer` 的 PBIR（file-first）能力**纯手写生成**一个 6 页报表工程，全程离线（不开 Desktop）直到最终验收。这里记下踩到的坑与可复用的校验方法。

> 参考产物：`shuimo07/powerbi_work` → `projects/2026-09-18/可视化实战演练/`（6 页 / 13 个视觉对象 / PBIR 增强格式）

---

## 1. ⭐ 闭集校验：多一个属性键 = 整份报表拒载

### 现象

工程生成完毕、JSON 语法完全合法，但用 Desktop 打开后**所有视觉对象一片空白**，同时弹出 33 条校验错误：

```
visuals/viz0101/visual.json 的 /visual/visualContainerObjects/title/0/properties
属性中包含一个额外的属性 "showSubtitle"。
visuals/viz0101/visual.json 的 /visual/visualContainerObjects/title/0/properties
属性中包含一个额外的属性 "subtitle"。
visuals/viz0101/visual.json 的 /visual/visualContainerObjects/title/0/properties
属性中包含一个额外的属性 "subtitleFontSize"。
…（6 页 13 个视觉对象，凡带标题的全部中招）
```

### 根因

`visualContainerObjects.title[0].properties` 是**闭集（closed set）**校验：

> **不是"多余键被忽略"，而是"存在任何未定义键 → 整份报表判为无效"。**

当时凭直觉写了 `showSubtitle` / `subtitle` / `subtitleFontSize` 三个"标题 + 副标题"语义的键——这三者在 PBIR `visualContainer/2.4.0` 的 `title` 对象里**根本不存在**。

### 正确做法

`title` 的合法键只有：

```
show  text  fontSize  fontColor  fontFamily  alignment
bold  italic  underline  titleWrap  background  showTitleBackground …
```

**PBIR 的 title 没有"副标题"概念。** 想要"标题 + 副标题"，只能拼进同一个 `text`：

```python
def chart_container(title, subtitle=None):
    txt = title if not subtitle else (title + " ｜ " + subtitle)
    return {
        "title": [{"properties": {
            "show": lit(True), "text": lit(txt), "fontSize": lit(15),
            "fontColor": solid("#1F3864"), "alignment": lit("left")}}],
        "background": [{"properties": {"show": lit(True), "color": solid("#FFFFFF"), "transparency": lit(0)}}],
        "border":     [{"properties": {"show": lit(True), "color": solid("#D0D7E5"), "radius": lit(6)}}],
        "dropShadow": [{"properties": {"show": lit(True)}}],
    }
```

### 教训

- **错误表现极具误导性**。"视觉全空"极易被误判成"数据没加载 / 没刷新"，于是去折腾 Power Query、点刷新按钮、重连数据源——**全都无效**，浪费时间。
- **务必先离线校验，再开界面。** 这类结构性错误在 schema 层面就能 100% 卡住。
- 唯一可靠的排查依据是**官方 JSON schema**；不要靠"我记得这个属性好像叫…"去写 PBIR。

---

## 2. 离线校验：不开 Desktop 就能卡住错误

`powerbi-designer` 自带 validation engine（含 vendored PBIR schema），可直接在命令行调用。

本仓库提供 [`tools/validate-pbir.py`](../tools/validate-pbir.py)：

```bash
python tools/validate-pbir.py E:\PowerBI_Projects\可视化实战演练
```

输出：

```
项目: E:\PowerBI_Projects\可视化实战演练
ok = True
errors = 0   warnings = 0
```

> 退出码非 0 即代表有 error。**约定：`ok=True` 才允许开 Desktop 验收。**

第 1 节那 33 条错误，正是这个脚本离线复现出来并定位到 `title/properties` 的。

---

## 3. 分类轴显示 `(空白)`：M 文本列不可靠 → 改用 DAX 计算列

### 现象

折线图 / 分区图的 X 轴**整条显示 `(空白)`**，但同一列在数据表预览里完全正常。

### 原因

用 M 生成的文本列：

```m
#"改类型" = Table.TransformColumnTypes(源, {{"日期", type datetime}}),
#"日期文本" = Table.AddColumn(#"改类型", "日期文本", each Date.ToText([日期], "MM-dd"), type text)
```

这个 `日期文本` 列作为**分类轴投影**时不能正确建立分组。

### 解法

删除 M 文本列，改为 **TMDL 计算列（DAX）**：

```tmdl
	column '日期标签' = FORMAT('访客数据'[日期], "MM-dd")
		dataType: string
		lineageTag: 3c1f…
		summarizeBy: none
		sortByColumn: 日期
```

要点：

- `FORMAT()` 返回文本 → `dataType: string`
- **必须配 `sortByColumn` 指向真实日期列**，否则按字符串排序（`01-09` 会排到 `12-27` 前面）
- 改完重新生成 + 刷新，轴标签即正常显示 `MM-dd`

---

## 4. TMDL：计算列 vs 导入列 的写法差异

| | 导入列（来自 M partition） | 计算列（DAX） |
|---|---|---|
| 首行 | `column 'X'` | `column 'X' = <DAX 表达式>` |
| `sourceColumn` | **必须有** `sourceColumn: X` | **必须没有** |
| `lineageTag` | 有 | 有 |
| 数值列 | `summarizeBy: sum` | 视情况（指标用 sum） |
| 文本 / 标签列 | `summarizeBy: none` | `summarizeBy: none` |
| 位置 | partition 之前 | **partition 之后** |
| 排序 | 可选 `sortByColumn` | 常用 `sortByColumn` |

漏掉"计算列必须在 partition 之后"会直接导致 TMDL 解析失败。

---

## 5. 视觉类型名要用内部名（如 分区图 = `AreaChart`）

`visualType` 不能写中文。中文名 → 内部名的可靠反查方式：

在 Desktop 安装目录搜语言资源文件（以简体中文为例）：

```
E:\PowerBI_Tools\bin\zh-HANS\Strings.resjson
```

搜 `分区图` → 命中 `AreaChart`。同理：

| 中文 | visualType |
|---|---|
| 折线图 | `lineChart` |
| 分区图（面积图） | `areaChart` |
| 表格 | `tableEx` |
| 卡片图 | `card` |
| 条形图 | `barChart` |
| 簇状柱形图 | `clusteredColumnChart` |

---

## 6. 终态验收

| 项 | 结果 |
|---|---|
| `validate_pbir.py` | `ok=True`，0 error |
| Desktop 打开 | 无校验弹窗 |
| 逐页数据 | 6 页全部正常渲染，X 轴为 `MM-dd` |
| 截图 | 6 张，已归档 |

---

## 7. 可复用清单

生成 PBIR 工程时的最小自查项：

1. `visualContainerObjects.title[0].properties` **只写合法键**——不写副标题，副标题拼进 `text`
2. 生成后**先跑离线校验**，`ok=True` 再开 Desktop
3. 分类轴要用 **DAX 计算列 + `sortByColumn`**，不要用 M 文本列
4. 计算列的 TMDL 块放在 **partition 之后**，且不写 `sourceColumn`
5. `visualType` 一律用内部名
6. 数据需要**手动刷新**才加载；刷新进度框会挡住后续界面点击，翻页/截图前先关掉
