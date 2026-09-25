#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 SPSS 的 OMS HTML（IMAGES=YES）里提取内嵌图表，输出原始图 + 可投稿的 300dpi PNG。

用法：
    python extract_chart.py <chart.html> [--out-dir DIR] [--prefix P]
                            [--dpi 300] [--width 1950] [--height 1500]

要点（实测）：
    * SPSS 内嵌的其实是 JPEG，会忽略 OMS 里的 IMAGEFORMAT=PNG → 按实际格式解码。
    * 原始尺寸固定 801x501，且没有 DPI 元数据 → 放大 + 重写 DPI 才能满足期刊要求。
    * 若 HTML 里一张图都没有：99% 是 OMS 漏了 IMAGES=YES。

技术出处：OMS IMAGES=YES 无界面出图思路参考
ZHENGHAOYa/workbuddy-spss-headless-chart；本脚本为自行实现。
"""

import argparse
import base64
import io
import os
import re
import sys

EMBEDDED = re.compile(r"data:image/(\w+);base64,([A-Za-z0-9+/=\s]+)")


def parse_args(argv):
    ap = argparse.ArgumentParser(description="提取 SPSS OMS HTML 里的图表")
    ap.add_argument("html", help="chart.html 路径")
    ap.add_argument("--out-dir", default=None, help="输出目录（默认与 html 同目录）")
    ap.add_argument("--prefix", default=None, help="输出文件名前缀（默认取 html 名）")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--width", type=int, default=1950)
    ap.add_argument("--height", type=int, default=1500)
    ap.add_argument("--keep-raw", action="store_true", help="保留未放大的原图")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    html_path = os.path.abspath(args.html)
    if not os.path.isfile(html_path):
        print("找不到 HTML 文件: %s" % html_path)
        return 1

    out_dir = os.path.abspath(args.out_dir) if args.out_dir else os.path.dirname(html_path)
    os.makedirs(out_dir, exist_ok=True)
    prefix = args.prefix or os.path.splitext(os.path.basename(html_path))[0]

    try:
        from PIL import Image
    except ImportError:
        print("缺少 Pillow，请先: pip install Pillow")
        return 1

    with io.open(html_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    found = EMBEDDED.findall(text)
    if not found:
        print("=" * 62)
        print("HTML 里没有找到任何图片。")
        print("99% 的原因是 OMS 命令漏了 IMAGES=YES。正确写法：")
        print("  OMS /TAG='IMG1' /SELECT CHARTS /DESTINATION FORMAT=HTML")
        print("    IMAGES=YES IMAGEFORMAT=PNG OUTFILE='<这个HTML路径>'.")
        print("  <图表语法>")
        print("  OMSEND TAG='IMG1'.")
        print("同时确认 OMSEND 已配对关闭、且 HTML/图片路径所在目录存在。")
        print("=" * 62)
        return 2

    print("找到 %d 张图 → %s" % (len(found), out_dir))
    written = []
    for i, (fmt, b64) in enumerate(found, start=1):
        blob = base64.b64decode(re.sub(r"\s+", "", b64))
        img = Image.open(io.BytesIO(blob))
        print("  图%d: 实际格式=%s 原始尺寸=%s 字节=%d" % (i, fmt, img.size, len(blob)))

        if args.keep_raw:
            raw = os.path.join(out_dir, "%s_raw_%03d.%s" % (prefix, i, fmt))
            img.save(raw)
            written.append(raw)
            print("    原图 ->", raw)

        big = img.convert("RGB").resize((args.width, args.height), Image.LANCZOS)
        out = os.path.join(out_dir, "%s_%ddpi_%03d.png" % (prefix, args.dpi, i))
        big.save(out, format="PNG", dpi=(args.dpi, args.dpi))
        written.append(out)
        print("    %ddpi -> %s (%dx%d)" % (args.dpi, out, args.width, args.height))

    print("完成，共 %d 个文件。" % len(written))
    print("提示：放大是 Lanczos 插值；严格矢量请走 EMF 路线（OMS FORMAT=DOC → word/media/imageN.emf）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
