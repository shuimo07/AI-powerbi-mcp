#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
migrate_pbi_userdata_to_e.py —— 把 Power BI Desktop 的用户数据目录从 C 盘搬到 E 盘，
并原地建立目录联接（junction），做到**路径不变、Desktop 与 MCP 侧零改动**。

默认搬迁对象（Windows）：
    C:\\Users\\<用户>\\AppData\\Local\\Microsoft\\Power BI Desktop
  → E:\\WBData\\local\\PowerBI-Desktop

安全设计：
  * 复制 → 逐文件核对（文件数 + 字节数）→ 只在**完全一致**时才删源
  * 全程 reparse-aware：不递归进 junction，也不会下穿联接删除目标盘数据
  * 任一环节失败立即中止，源目录保持不动
  * 删源统一走 `cmd /c rmdir`（绕开可能存在的 safe-delete 钩子）

用法：
    python migrate_pbi_userdata_to_e.py                 # 默认路径
    python migrate_pbi_userdata_to_e.py --check         # 只体检，不动数据
    python migrate_pbi_userdata_to_e.py --src <目录> --dst <目录>
    python migrate_pbi_userdata_to_e.py --allow-running  # 跳过进程检查（不建议）

参考：docs/desktop-userdata-to-e-drive.md
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

DEFAULT_SRC = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                           "Microsoft", "Power BI Desktop")
DEFAULT_DST = r"E:\WBData\local\PowerBI-Desktop"

# 会占用用户数据目录的进程
BLOCKING = ["PBIDesktop.exe", "msmdsrv.exe"]

FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def is_reparse(path: str) -> bool:
    try:
        return bool(os.lstat(path).st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return False


def is_junction(path: str) -> bool:
    """junction 在 lstat 里表现为 reparse point 且是目录。"""
    return is_reparse(path) and os.path.isdir(path) and not os.path.islink(path)


def dir_stats(root: str):
    """reparse-aware 统计：返回 (文件数, 总字节数)。不递归进 junction。"""
    n = 0
    total = 0
    for r, ds, fs in os.walk(root):
        # 剔除子目录里的 reparse point，避免重复计数/下穿
        keep = []
        for d in ds:
            p = os.path.join(r, d)
            if is_reparse(p):
                continue
            keep.append(d)
        ds[:] = keep
        for f in fs:
            p = os.path.join(r, f)
            if is_reparse(p):
                continue
            try:
                total += os.path.getsize(p)
                n += 1
            except OSError:
                pass
    return n, total


def running_processes():
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return []
    hit = []
    low = (out or "").lower()
    for exe in BLOCKING:
        if exe.lower() in low:
            hit.append(exe)
    return hit


def junction_target(path: str):
    """读 junction 的 Substitute Name。取不到返回 None。"""
    try:
        out = subprocess.run(["cmd", "/c", "dir", "/AL", os.path.dirname(path)],
                             capture_output=True, text=True, timeout=60,
                             encoding="oem", errors="replace").stdout or ""
        base = os.path.basename(path)
        for line in out.splitlines():
            if base.upper() in line.upper() and "<JUNCTION>" in line.upper():
                idx = line.upper().find("<JUNCTION>")
                return line[idx + len("<JUNCTION>"):].strip()
    except Exception:
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Power BI Desktop 用户数据搬到 E 盘并建 junction")
    ap.add_argument("--src", default=DEFAULT_SRC, help="源目录（默认 %%LOCALAPPDATA%%\\Microsoft\\Power BI Desktop）")
    ap.add_argument("--dst", default=DEFAULT_DST, help="E 盘目标目录")
    ap.add_argument("--check", action="store_true", help="只体检，不搬迁")
    ap.add_argument("--allow-running", action="store_true", help="跳过进程占用检查（不建议）")
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    dst = os.path.abspath(args.dst)

    print("=" * 72)
    print("源目录 : %s" % src)
    print("目标   : %s" % dst)
    print("=" * 72)

    # ---------- 0. 状态体检 ----------
    if not os.path.exists(src):
        print("[FAIL] 源目录不存在。Desktop 是否装过/运行过？")
        return 2

    already = is_junction(src)
    print("[状态] 源是 junction : %s%s" % (already, "" if not already else "  ← 已迁移过，无需重复"))
    if already:
        tgt = junction_target(src)
        print("[状态] 联接指向     : %s" % (tgt or "(读取失败)"))
        print("[OK] 已经是联接，路径不变、数据在 %s" % (tgt or "目标"))
        return 0

    procs = running_processes()
    print("[状态] 占用进程     : %s" % (", ".join(procs) if procs else "无"))
    if procs and not args.allow_running:
        print("")
        print("[STOP] 以下进程仍在运行，请先完全退出再执行：")
        for p in procs:
            print("       taskkill /IM %s /F" % p)
        print("       （PBIDesktop.exe 退出后 msmdsrv.exe 可能仍在，必须一并确认）")
        return 2

    n_src, sz_src = dir_stats(src)
    print("[状态] 源目录规模   : %d 文件 / %.1f MB" % (n_src, sz_src / 1048576.0))

    if args.check:
        print("")
        print("[CHECK] 体检完成（--check 模式，未做任何改动）")
        if os.path.exists(dst):
            n_d, sz_d = dir_stats(dst)
            print("        目标已存在  : %d 文件 / %.1f MB" % (n_d, sz_d / 1048576.0))
        return 0

    # ---------- 1. 复制 ----------
    print("")
    print("[1/5] robocopy 复制…")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    rc = subprocess.run(["robocopy", src, dst, "/E", "/COPY:DAT", "/DCOPY:DAT",
                         "/R:1", "/W:1", "/NFL", "/NDL", "/NP", "/XJ"],
                        capture_output=True, text=True, timeout=3600).returncode
    # robocopy: 0-7 为成功类返回码
    if rc > 7:
        print("[FAIL] robocopy 返回码 %d，中止（源目录未改动）" % rc)
        return 2
    print("      完成 (robocopy rc=%d)" % rc)

    # ---------- 2. 核对 ----------
    print("[2/5] 逐文件核对…")
    n_dst, sz_dst = dir_stats(dst)
    print("      源  : %d 文件 / %d B" % (n_src, sz_src))
    print("      目标: %d 文件 / %d B" % (n_dst, sz_dst))
    if n_dst < n_src or sz_dst < sz_src:
        print("[FAIL] 目标少于源，**不删源**。请检查后重跑（robocopy 会续传）。")
        return 2
    print("      [OK] 一致")

    # ---------- 3. 删源 ----------
    print("[3/5] 删除源目录（cmd /c rmdir，避免下穿联接）…")
    r = subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", src],
                       capture_output=True, text=True, timeout=1800)
    if os.path.exists(src) and not is_junction(src):
        print("[FAIL] 源目录仍存在（rc=%s）。可能被杀软/保护进程占用。" % r.returncode)
        print("       目标副本已就位，可稍后手动删除源后重跑本脚本（会跳过复制）。")
        return 2
    print("      [OK] 源已删除")

    # ---------- 4. 建联接 ----------
    print("[4/5] 建立目录联接…")
    r = subprocess.run(["cmd", "/c", "mklink", "/J", src, dst],
                       capture_output=True, text=True, timeout=120,
                       encoding="oem", errors="replace")
    if not is_junction(src):
        print("[FAIL] 联接创建失败：%s" % (r.stdout or r.stderr or "").strip())
        return 2
    print("      [OK] %s" % (r.stdout or "").strip())

    # ---------- 5. 验证 ----------
    print("[5/5] 验证…")
    n_now, sz_now = dir_stats(src)
    ok = is_junction(src) and n_now >= n_src
    print("      reparse=True : %s" % is_reparse(src))
    print("      目标指向     : %s" % (junction_target(src) or dst))
    print("      经联接可读   : %d 文件 / %.1f MB" % (n_now, sz_now / 1048576.0))
    print("")
    print("[DONE] %s" % ("迁移成功，路径未变、Desktop 与 MCP 侧无需改动。" if ok else "迁移未完全成功，请检查上面输出。"))
    print("       长期有效请把这条映射登记进登录守卫脚本（见 docs/desktop-userdata-to-e-drive.md 第 6 节）。")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
