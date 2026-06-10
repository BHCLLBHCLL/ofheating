#!/usr/bin/env python3
"""topoSet 后检查各 cellZone 单元数; 同时核对 cellSet 文件以定位 setToCellZone 失败。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CASE = Path(__file__).resolve().parent.parent
ZONES = ["cpu", "vc", "motherboard", "fins", "chassis", "screen", "air"]
CELL_SETS = {
    "cpu": "cpuCells",
    "vc": "vcCells",
    "motherboard": "motherboardCells",
    "fins": "finsCells",
    "screen": "screenCells",
    "chassis": "chassisCells",
    "air": "airCells",
}
CELL_ZONES = CASE / "constant" / "polyMesh" / "cellZones"
SETS_DIR = CASE / "constant" / "polyMesh" / "sets"
LOG_TOPO = CASE / "log.topoSet"


def zone_cell_counts(text: str) -> dict[str, int]:
    """逐行扫描 zone 名与 cellLabels 数量 (不依赖块级 split)。"""
    counts = {z: 0 for z in ZONES}
    current: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in ZONES and not stripped.endswith(";"):
            current = stripped
            continue
        if stripped == "{":
            continue
        if stripped == "}":
            current = None
            continue
        if current and "cellLabels" in line and "List<label>" in line:
            m = re.search(r"List<label>\s+(\d+)", line)
            if m:
                counts[current] = int(m.group(1))
                current = None
    return counts


def cellset_count(name: str) -> int | None:
    """从 constant/polyMesh/sets/<name> 读取 cellSet 大小。"""
    path = SETS_DIR / name
    if not path.exists():
        return None
    text = path.read_text(errors="replace")
    m = re.search(r"^\s*(\d+)\s*\(", text, re.MULTILINE)
    return int(m.group(1)) if m else None


def topo_log_hint(zone: str) -> str | None:
    if not LOG_TOPO.exists():
        return None
    text = LOG_TOPO.read_text(errors="replace")
    for line in reversed(text.splitlines()):
        if zone in line and ("cellZone" in line or "Cell set" in line or "cells" in line):
            return line.strip()
    return None


def main() -> int:
    if not CELL_ZONES.exists():
        print(f"ERROR: missing {CELL_ZONES}", file=sys.stderr)
        return 1

    counts = zone_cell_counts(CELL_ZONES.read_text())
    failed = [z for z in ZONES if counts[z] == 0]

    print("cellZone audit:")
    for zone in ZONES:
        n = counts[zone]
        status = "ok" if n > 0 else "EMPTY"
        extra = ""
        if n == 0:
            cs = CELL_SETS.get(zone)
            if cs:
                sc = cellset_count(cs)
                if sc is not None and sc > 0:
                    extra = f"  [cellSet {cs}={sc}, setToCellZone 可能失败]"
                elif sc == 0:
                    extra = f"  [cellSet {cs}=0, 检查 box 包络]"
        print(f"  {zone:12s}  {n:6d} cells  [{status}]{extra}")

    if failed:
        print(f"ERROR: empty cellZones: {', '.join(failed)}", file=sys.stderr)
        for zone in failed:
            hint = topo_log_hint(zone)
            if hint:
                print(f"  log.topoSet: {hint}", file=sys.stderr)
        if "motherboard" in failed and counts.get("cpu", 0) > 0:
            print(
                "提示: v2412 若 motherboard 为首个 cellZone 会在后续写入时丢失;"
                " 请确认 topoSetDict 中 motherboard 在 cpu 之后创建",
                file=sys.stderr,
            )
        return 1

    print("  all cellZones non-empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
