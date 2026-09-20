# PBIR 报表生成与校验实战笔记

用 `powerbi-designer` 的 PBIR（file-first）能力**纯手写生成**一个 6 页报表工程，全程离线（不开 Desktop）直到最终验收。这里记下踩到的坑与可复用的校验方法。

> 参考产物：`shuimo07/powerbi_work` → `projects/2026-09-18/可视化实战演练/`（6 页 / 12 个视觉对象 / PBIR 增强格式）

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
…（6 页 12 个视觉对象，凡带标题的全部中招）
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

## 2. 离线校验：两遍扫描，缺一不可

`powerbi-designer` 自带 validation engine（含 vendored PBIR schema），本仓库封装为
[`tools/validate-pbir.py`](../tools/validate-pbir.py)：

```bash
python tools/validate-pbir.py E:\PowerBI_Projects\对比类数据实战演练
```

输出：

```
ok=True
schema_issues=0
query_issues=0
total=0

[query] 扫描 visual.json=15 个，投影=44 条
```

### ⚠️ 只跑 Schema 那一遍是不够的（这是踩过的坑）

vendored schema 里 **`visualContainer/2.4.0` 根本没有 `queryState` 的定义**——
也就是说 `visual.query` **完全不校验**。

后果：`Aggregation/Function` 写成字符串 `"Sum"`（应为整数 `0`）这类错误，
Schema 那一遍照样报 `ok=True`，**但 Desktop 会拒载整份报表**。
第 3 节那一大批错误就是这么漏掉的。

所以校验必须**两遍**：

| 遍次 | 覆盖面 | 卡什么 |
|---|---|---|
| 1. Schema | `visualContainerObjects` / `objects` / 页面元数据 | 闭集校验类（多写未定义键） |
| 2. query 投影静态检查 | `visual.query.queryState.*.projections[*]` | 聚合枚举类型、`field` 单键、`queryRef` 缺失 |

> 第 1 节那 33 条错误由第 1 遍离线复现；第 3 节那批由第 2 遍复现。
> **约定：两遍都干净（`total=0`）才允许开 Desktop 验收。**

---

## 3. ⭐ 聚合函数必须是**整数枚举**（`Aggregation.Function` 不能写字符串）

### 现象

第二份作业（簇状柱形图 / 簇状条形图）生成后，Desktop 又弹一大批校验错误，
每条路径固定 **11 行**，全部指向同一个位置：

```
visuals/viz0101/visual.json 中的属性
  /visual/query/queryState/Y/projections/0/field/Aggregation/Function 未作为正确的类型提供。
visuals/viz0101/visual.json 中的
  /visual/query/queryState/Y/projections/0/field/Aggregation/Function 属性必须作为常量提供。
  ⋮（重复 9 次）
作为 visuals/viz0101/visual.json 的
  /visual/query/queryState/Y/projections/0/field/Aggregation/Function 属性提供的值无效。
```

`viz0101/…/viz0601` 六个图表全中招（`viz0501` / `viz0601` 有 4 条 Y 投影，故报错更多）。

> 数一下：1（类型）+ 9（const）+ 1（无效值）= 11 行/路径。
> **9 = 枚举的合法取值个数**，正好对应 0–8。

### 根因

`semanticQuery` 里 `Aggregation.Function` 的类型是**整数枚举**：

| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Sum | Average | Count | Min | Max | CountNonNull | Median | StandardDeviation | Variance |

写成 `"Function": "Sum"`（字符串）→ 类型不符 + 不匹配任何 const → **值无效 → 整份报表拒载**。

第一份作业（折线图 / 分区图）之所以没出问题，仅仅是因为当时手写的是整数 `0`。
**同一个生成器换个写法就复发，说明这是极易踩的坑。**

### 正确做法

生成器里维护名字↔整数双向映射，**入口接受名字、出口一律整数**：

```python
AGG = {"Sum": 0, "Average": 1, "Count": 2, "Min": 3, "Max": 4,
       "CountNonNull": 5, "Median": 6, "StandardDeviation": 7, "Variance": 8}
AGG_NAME = {v: k for k, v in AGG.items()}

def col_field(entity, prop, agg=None):
    """agg 可传枚举名（"Sum"）或整数（0），内部一律产出整数。"""
    base = {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}
    if agg is None:
        return {"field": base, "queryRef": "%s.%s" % (entity, prop), "nativeQueryRef": prop}
    if isinstance(agg, str):
        if agg not in AGG:
            raise ValueError("未知聚合 %r，可选：%s" % (agg, sorted(AGG)))
        fn = AGG[agg]
    else:
        fn = int(agg)
        if fn not in AGG_NAME:
            raise ValueError("非法聚合枚举 %r，合法值 0-8" % (agg,))
    return {"field": {"Aggregation": {"Expression": {"Column": {
        "Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}, "Function": fn}},
        "queryRef": "%s(%s.%s)" % (AGG_NAME[fn], entity, prop),
        "nativeQueryRef": "总和 %s" % prop}
```

注意 `queryRef` 是**给人看的字符串**，反而应该用名字：`"Sum(流量结构.成交订单数)"`；
只有 `Function` 是机器枚举，必须整数。**两者容易混为一谈，正是出错的认知根源。**

### 教训

- **同一类坑会以不同面目复发。** 上次是"多写了键"，这次是"值的类型错了"，
  本质都是"PBIR 只接受 schema 里定义的样子，otherwise 整份报表无效"。
- **`ok=True` 不等于能开。** 校验器没覆盖到的字段，照样炸。校验盲区要靠自建检查补。
- 落地到生成器：**能抛异常的地方就抛异常**（`raise ValueError`），别把错误推迟到 Desktop 弹窗。

---

## 4. 分类轴显示 `(空白)`：M 文本列不可靠 → 改用 DAX 计算列

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

## 5. TMDL：计算列 vs 导入列 的写法差异

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

## 5. 视觉类型名要用内部名（如 分区图 = `areaChart`）

`visualType` 不能写中文，也不能照抄语言资源文件里的键名。中文名 → 内部名的可靠反查方式：

在 Desktop 安装目录搜语言资源文件（以简体中文为例）：

```
E:\PowerBI_Tools\bin\zh-HANS\Strings.resjson
```

搜 `分区图` → 命中资源键 `AreaChart`。**注意大小写**：资源键是 PascalCase，
但 `visual.json` 里持久化的 `visualType` 是**小驼峰** `areaChart`。写 `AreaChart` 会被判为未知视觉类型。

> 最稳的做法：拿一个 Desktop 亲手做好的同类视觉对象，看它 `visual.json` 里的 `visualType` 到底写什么，
> 别只信资源文件。

同理：

| 中文 | visualType |
|---|---|
| 折线图 | `lineChart` |
| 分区图（面积图） | `areaChart` |
| 表格 | `tableEx` |
| 卡片图 | `card` |
| 条形图 | `barChart` |
| 簇状柱形图 | `clusteredColumnChart` |
| 簇状条形图 | `clusteredBarChart` |

---

## 6. 终态验收

| 项 | 结果 |
|---|---|
| `validate_pbir.py` | `ok=True`，0 error |
| Desktop 打开 | 无校验弹窗 |
| 逐页数据 | 6 页全部正常渲染，X 轴为 `MM-dd` |
| 截图 | 6 张，已归档 |

---

## 8. 可复用清单

生成 PBIR 工程时的最小自查项：

1. `visualContainerObjects.title[0].properties` **只写合法键**——不写副标题，副标题拼进 `text`
2. **`Aggregation.Function` 必须是整数**（`0`=Sum … `8`=Variance），**不是** `"Sum"`
3. 生成后**先跑两遍离线校验**（schema + query），`total=0` 再开 Desktop
4. 分类轴要用 **DAX 计算列 + `sortByColumn`**，不要用 M 文本列
5. 计算列的 TMDL 块放在 **partition 之后**，且不写 `sourceColumn`
6. `visualType` 一律用内部名
7. 数据需要**手动刷新**才加载；刷新进度框会挡住后续界面点击，翻页/截图前先关掉
8. 生成器里对枚举/固定取值做**显式校验并抛异常**——把错误挡在 Desktop 之前
