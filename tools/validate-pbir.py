#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
validate-pbir.py —— 离线校验 Power BI PBIP 工程（PBIR + TMDL + reachability）

用 powerbi-designer MCP 自带的校验引擎，在**不开 Power BI Desktop** 的情况下
把结构性错误全部卡住。约定：只有 ok=True（0 error）才开 Desktop 验收。

典型用途：
  * 手写/程序生成 PBIR 工程后，先验一遍再打开
  * 复现并定位 Desktop 弹出的「校验错误」对话框（如 title 属性闭集校验）
  * CI / 提交前把关

用法：
    python validate-pbir.py <项目目录或 .pbip 文件> [-v] [--json 输出.json]
    python validate-pbir.py E:\\PowerBI_Projects\\可视化实战演练

退出码：
    0 = ok=True 且无 error
    1 = 存在 error（或被校验判为不 ok）
    2 = 运行环境问题（引擎导入失败 / 路径不存在）

依赖：
    需要能 import powerbi_mcp（即 powerbi-designer 所在环境）。
    若在独立 venv 里跑，请先：
        <venv>\\Scripts\\python.exe -m pip install -e <powerbi-mcp-designer 源码目录>
    或直接使用该 MCP 服务所用解释器执行本脚本。

参考：docs/pbir-report-build-notes.md
"""
from __future__ import annotations

import argparse
import dataclasses
import io
import json
import os
import sys


def to_plain(obj):
    """把 dataclass / 嵌套结构转成纯 dict/list，便于序列化。"""
    if dataclasses.is_dataclass(obj):
        return {f.name: to_plain(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {k: to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_plain(x) for x in obj]
    return obj


def collect_issues(data):
    """从校验结果里递归收集带 severity/code 的条目。"""
    found = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("severity") is not None or node.get("code") is not None:
                found.append({
                    "severity": node.get("severity"),
                    "code": node.get("code"),
                    "message": node.get("message"),
                    "path": node.get("path"),
                    "pointer": node.get("pointer"),
                })
            else:
                for v in node.values():
                    walk(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v)

    walk(data)
    return found


def normalize_target(arg: str) -> str:
    """接受目录或 .pbip 文件，统一返回工程目录。"""
    p = os.path.abspath(arg)
    if os.path.isfile(p) and p.lower().endswith(".pbip"):
        return os.path.dirname(p)
    return p


def main() -> int:
    ap = argparse.ArgumentParser(
        description="离线校验 Power BI PBIP 工程（PBIR + TMDL）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", help="工程目录，或 .pbip 文件路径")
    ap.add_argument("-v", "--verbose", action="store_true", help="打印全部 problem 明细")
    ap.add_argument("--json", metavar="FILE", help="把完整校验结果写成 JSON")
    args = ap.parse_args()

    proj = normalize_target(args.project)
    if not os.path.isdir(proj):
        print("[FAIL] 目录不存在: %s" % proj)
        return 2

    try:
        from powerbi_mcp.validation.engine import validate_project
    except Exception as exc:  # noqa: BLE001
        print("[FAIL] 无法导入 powerbi_mcp.validation.engine: %r" % (exc,))
        print("       请用 powerbi-designer 所在环境的解释器运行本脚本，")
        print("       或先把 powerbi-mcp-designer 以 -e 安装进当前 venv。")
        return 2

    report = validate_project(proj)
    data = to_plain(report)
    issues = collect_issues(data)
    errors = [i for i in issues if str(i["severity"]).lower() in ("error", "1", "critical")]
    warnings = [i for i in issues if str(i["severity"]).lower() in ("warning", "2", "warn")]

    ok = bool(data.get("ok")) if isinstance(data, dict) else False

    print("项目: %s" % proj)
    print("ok = %s" % ok)
    print("errors = %d   warnings = %d   (problems 总数 %d)" % (len(errors), len(warnings), len(issues)))

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".", exist_ok=True)
        io.open(args.json, "w", encoding="utf-8").write(
            json.dumps({"project": proj, "ok": ok, "issues": issues, "raw": data},
                       ensure_ascii=False, indent=2, default=str))
        print("完整结果已写入: %s" % args.json)

    if issues and (args.verbose or errors):
        print("")
        print("---- 明细 ----")
        for i in (errors + warnings if not args.verbose else issues):
            print("[%s] %s | %s | path=%s | ptr=%s" % (
                i["severity"], i["code"], i["message"], i["path"], i["pointer"]))

    return 0 if (ok and not errors) else 1


if __name__ == "__main__":
    sys.exit(main())
