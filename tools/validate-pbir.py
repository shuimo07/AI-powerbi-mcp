# -*- coding: utf-8 -*-
r"""离线检查 PBIR 工程（不开 Power BI Desktop），分两遍：

  第 1 遍  Schema 校验（powerbi_mcp.validation.engine）
           能卡住**闭集校验类**错误 —— 例如 visualContainerObjects/title/properties
           里多写一个未定义键（showSubtitle 之类）。这类错误不会"被忽略"，
           而是整份报表拒载（现象是视觉对象全空，极易误判为数据没加载）。

  第 2 遍  query 投影静态检查（本项目自建）
           ⚠️ vendored schema 里 visualContainer 2.4.0 **根本没有 queryState 的定义**，
           `visual.query` 完全不校验 —— 所以 Aggregation.Function 写错类型
           （字符串 "Sum" 而不是整数 0）时引擎报 ok=True，但 Power BI 会拒载。
           这一遍专门补这个洞。

用法:
    "<designer-venv>\Scripts\python.exe" validate-pbir.py [工程根] [-o 输出txt]
"""
import json, os, sys, glob, dataclasses

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else os.path.dirname(HERE)
OUT = None
if "-o" in sys.argv:
    OUT = sys.argv[sys.argv.index("-o") + 1]

from powerbi_mcp.validation.engine import validate_project

# Aggregation.Function 的合法整数枚举（semanticQuery 1.3.0）
AGG_NAME = {0: "Sum", 1: "Average", 2: "Count", 3: "Min", 4: "Max",
            5: "CountNonNull", 6: "Median", 7: "StandardDeviation", 8: "Variance"}


def dump(o):
    if dataclasses.is_dataclass(o):
        return {f.name: dump(getattr(o, f.name)) for f in dataclasses.fields(o)}
    if isinstance(o, list):
        return [dump(x) for x in o]
    if isinstance(o, dict):
        return {k: dump(v) for k, v in o.items()}
    return o


data = dump(validate_project(PROJ))

lines = []


def walk(d):
    if isinstance(d, dict):
        if d.get("severity") is not None or d.get("code") is not None:
            lines.append("[%s] %s | %s | path=%s | ptr=%s"
                         % (d.get("severity"), d.get("code"), d.get("message"),
                            d.get("path"), d.get("pointer")))
        else:
            for v in d.values():
                walk(v)
    elif isinstance(d, list):
        for v in d:
            walk(v)


walk(data)
schema_issues = len(lines)


# ------------------------------------------------------------------ 第 2 遍
def check_queries():
    """扫所有 visual.json 的 queryState 投影，补引擎的盲区。"""
    bad = []
    report_dirs = [d for d in glob.glob(os.path.join(PROJ, "*.Report")) if os.path.isdir(d)]
    if not report_dirs:
        bad.append("找不到 *.Report 目录，跳过 query 检查")
        return bad
    n_files = n_proj = 0
    pat = os.path.join(report_dirs[0], "definition", "pages", "*", "visuals", "*", "visual.json")
    for vf in sorted(glob.glob(pat)):
        rel = os.path.relpath(vf, PROJ).replace("\\", "/")
        n_files += 1
        try:
            v = json.load(open(vf, encoding="utf-8"))
        except Exception as e:
            bad.append("%s | JSON 解析失败: %r" % (rel, e))
            continue
        qs = (((v.get("visual") or {}).get("query") or {}).get("queryState")) or {}
        if not qs:
            bad.append("%s | 没有 query.queryState（图表类视觉对象应当有）" % rel)
        for role, blob in qs.items():
            for i, pj in enumerate((blob or {}).get("projections") or []):
                n_proj += 1
                where = "%s | %s/projections/%d" % (rel, role, i)
                field = pj.get("field")
                if not isinstance(field, dict) or len(field) != 1:
                    bad.append("%s | field 必须是单键对象，实为 %r" % (where, field))
                    continue
                kind = next(iter(field))
                if kind == "Aggregation":
                    agg = field["Aggregation"]
                    if "Expression" not in agg:
                        bad.append("%s | Aggregation 缺 Expression" % where)
                    if "Function" not in agg:
                        bad.append("%s | Aggregation 缺 Function" % where)
                    else:
                        fn = agg["Function"]
                        if isinstance(fn, bool) or not isinstance(fn, int):
                            bad.append("%s | Aggregation/Function 必须是**整数枚举**，"
                                       "现在收到 %s（%r）—— 写字符串会整份报表拒载"
                                       % (where, type(fn).__name__, fn))
                        elif fn not in AGG_NAME:
                            bad.append("%s | Aggregation/Function=%r 非法，合法值 0-8" % (where, fn))
                elif kind != "Column" and kind != "Measure":
                    bad.append("%s | field 的键 %r 不是已知的字段类型" % (where, kind))
                if not pj.get("queryRef"):
                    bad.append("%s | 缺 queryRef" % where)
                if not pj.get("nativeQueryRef"):
                    bad.append("%s | 缺 nativeQueryRef" % where)
        # 视觉对象类型必须用内部名
        vt = (v.get("visual") or {}).get("visualType")
        if not vt:
            bad.append("%s | 缺 visualType" % rel)
        # title 闭集校验的常见来源：确认没混进 showSubtitle 之类
        for k in ("visualContainerObjects", "objects"):
            blob = (v.get("visual") or {}).get(k) or {}
            for obj_name, arrs in blob.items():
                for arr in arrs or []:
                    for prop in (arr.get("properties") or {}):
                        if prop in ("showSubtitle", "subtitle", "subtitleFontSize"):
                            bad.append("%s | %s/%s/properties 含未定义键 %r（闭集校验会拒载）"
                                       % (rel, k, obj_name, prop))
    bad.insert(0, "扫描 visual.json=%d 个，投影=%d 条" % (n_files, n_proj))
    return bad


bad = check_queries()
bad_lines = [b for b in bad if "扫描 visual.json" not in b]
tot = schema_issues + len(bad_lines)

report = "ok=%s\nschema_issues=%d\nquery_issues=%d\ntotal=%d\n%s\n%s" % (
    data.get("ok") and not bad_lines, schema_issues, len(bad_lines), tot,
    "\n".join(lines), "\n".join("[query] " + b for b in bad))

if OUT:
    open(OUT, "w", encoding="utf-8").write(report)
print(report)
