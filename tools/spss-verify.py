#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SPSS MCP 通道四步自检（换机 / 重装后跑这一条即可判断通道是否可用）。

步骤：
  1) 引擎连通     SPSS 自带 python + spsscli.py 跑 SHOW VERSION.
  2) CSV → .sav   校验文件类工具链路
  3) 统计过程     DESCRIPTIVES + T-TEST，回读结果表
  4) 无界面出图   OMS IMAGES=YES + GRAPH/GGRAPH → HTML → 300dpi PNG

用法：
  "E:\\venvs\\spss-mcp\\Scripts\\python.exe" spss-verify.py [--out-dir E:\\tmp\\spss-verify]
环境变量（可选）：SPSS_PY / SPSS_CLI，默认值见下方常量。
退出码：0 = 全通过；非 0 = 失败步骤数。
"""

import argparse
import base64
import io
import os
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

SPSS_PY = os.environ.get("SPSS_PY", r"E:\大三·\Python3\python.exe")
SPSS_CLI = os.environ.get("SPSS_CLI", r"E:\SPSS-MCP\spsscli.py")
EMBEDDED = re.compile(r"data:image/(\w+);base64,([A-Za-z0-9+/=\s]+)")

CSV_DATA = "x,y,grp,sex\n" + "".join(
    "%d,%.0f,%s,%d\n" % (i, 2 * i + (i % 3) - 1, "A" if i % 2 else "B",
                         1 if i % 2 else 2)
    for i in range(1, 31)
)

CHART_SPS = """GET FILE='{sav}'.
OMS /TAG='IMG1' /SELECT CHARTS /DESTINATION FORMAT=HTML IMAGES=YES IMAGEFORMAT=PNG OUTFILE='{html}'.
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
  GUIDE: text.title(label("verify"))
  ELEMENT: point(position(xx*yy))
END GPL.
OMSEND TAG='IMG1'.
"""

STAT_SPS = """GET FILE='{sav}'.
DESCRIPTIVES VARIABLES=x y.
* 分组变量故意用数值型 sex(1 2)：字符串分组变量若宽度 > 8（长字符串）
* 会被 T-TEST 判为 [errLevel 3]，需先用 ALTER TYPE 收窄（见 docs 雷区清单）。
T-TEST GROUPS=sex(1 2) /VARIABLES=y.
"""


def cli(args, timeout=300):
    """调用 spsscli.py（自动用 SPSS 自带 python）。"""
    return subprocess.run([SPSS_PY, SPSS_CLI] + args, capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=timeout)


def step(name, ok, detail=""):
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name,
                         ("  -> " + detail) if detail else ""))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=r"E:\tmp\spss-verify",
                    help="产物目录（默认 E:\\tmp\\spss-verify）")
    args = ap.parse_args()

    out = os.path.abspath(args.out_dir)
    os.makedirs(out, exist_ok=True)
    sav = os.path.join(out, "demo.sav")
    html = os.path.join(out, "chart.html")
    csv = os.path.join(out, "demo.csv")
    failed = 0
    t0 = time.time()

    print("SPSS_PY  = %s" % SPSS_PY)
    print("SPSS_CLI = %s" % SPSS_CLI)
    print("OUT_DIR  = %s\n" % out)

    # 1) 引擎连通
    try:
        r = cli(["syntax", "--arg", "SHOW VERSION."])
        ok = '"ok": true' in r.stdout and "STATS.EXE" in r.stdout
        ver = re.search(r"STATS\.EXE\s*\|\s*([\d.]+)", r.stdout)
        failed += step("1/4 引擎连通（SHOW VERSION）", ok,
                       ("STATS.EXE " + ver.group(1)) if ver else r.stdout[:120])
    except Exception as e:
        failed += step("1/4 引擎连通（SHOW VERSION）", False, repr(e))

    # 2) CSV -> SAV
    with io.open(csv, "w", encoding="utf-8-sig", newline="") as f:
        f.write(CSV_DATA)
    try:
        r = cli(["csv2sav", csv, sav])
        failed += step("2/4 CSV → .sav", '"ok": true' in r.stdout, sav)
    except Exception as e:
        failed += step("2/4 CSV → .sav", False, repr(e))

    # 3) 统计过程
    sps = os.path.join(out, "stat.sps")
    with io.open(sps, "w", encoding="utf-8") as f:
        f.write(STAT_SPS.format(sav=sav))
    try:
        r = cli(["syntax", "--file", sps])
        ok = "Descriptive Statistics" in r.stdout and '"ok": true' in r.stdout
        failed += step("3/4 统计过程（DESCRIPTIVES + T-TEST）", ok,
                       "结果表已回读" if ok else r.stdout[:160])
    except Exception as e:
        failed += step("3/4 统计过程（DESCRIPTIVES + T-TEST）", False, repr(e))

    # 4) 无界面出图
    sps2 = os.path.join(out, "chart.sps")
    with io.open(sps2, "w", encoding="utf-8") as f:
        f.write(CHART_SPS.format(sav=sav, html=html))
    try:
        cli(["syntax", "--file", sps2])
        if not os.path.isfile(html):
            raise RuntimeError("HTML 未落盘：检查 OUTFILE 路径与 OMSEND 是否换行")
        text = io.open(html, encoding="utf-8", errors="replace").read()
        found = EMBEDDED.findall(text)
        if not found:
            raise RuntimeError("HTML 无内嵌图：OMS 漏了 IMAGES=YES")
        from PIL import Image
        sizes = []
        for i, (fmt, b64) in enumerate(found, start=1):
            img = Image.open(io.BytesIO(base64.b64decode(re.sub(r"\s+", "", b64))))
            big = img.convert("RGB").resize((1950, 1500), Image.LANCZOS)
            p = os.path.join(out, "chart_300dpi_%03d.png" % i)
            big.save(p, format="PNG", dpi=(300, 300))
            sizes.append("%s %s" % (fmt, img.size))
        failed += step("4/4 无界面出图 + 300dpi 提取", True,
                       "%d 张（%s）→ %s" % (len(found), ", ".join(sizes), out))
    except Exception as e:
        failed += step("4/4 无界面出图 + 300dpi 提取", False, repr(e))

    print("\n%s  用时 %.1fs  产物目录 %s"
          % ("全部通过 ✅" if failed == 0 else "%d 项失败 ❌" % failed,
             time.time() - t0, out))
    if failed:
        print("排查：见仓库 docs/spss-mcp-integration.md 第 6 节「雷区清单」")
    return failed


if __name__ == "__main__":
    sys.exit(main())
