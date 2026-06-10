#!/usr/bin/env python3
"""topoSet 后检查各 cellZone 单元数 (解析 cellLabels 行, 不依赖脆弱正则)。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CASE = Path(__file__).resolve().parent.parent
ZONES = ["cpu", "vc", "motherboard", "fins", "chassis", "screen", "air"]
CELL_ZONES = CASE / "constant" / "polyMesh" / "cellZones"


def zone_cell_counts(text: str) -> dict[str, int]:
    """按 zone 块名解析 cellLabels 数量。"""
    counts = {z: 0 for z in ZONES}
    chunks = re.split(r"(?:^|\n)\s*(\w+)\s*\{", text)
    # chunks[0]=header, chunks[1]=name1, chunks[2]=body1, ...
    for i in range(1, len(chunks) - 1, 2):
        name = chunks[i].strip()
        body = chunks[i + 1]
        if name not in ZONES:
            continue
        m = re.search(r"cellLabels\s+List<label>\s+(\d+)", body)
        if m:
            counts[name] = int(m.group(1))
    return counts


def main() -> int:
    if not CELL_ZONES.exists():
        print(f"ERROR: missing {CELL_ZONES}", file=sys.stderr)
        return 1

    text = CELL_ZONES.read_text()
    counts = zone_cell_counts(text)
    failed = [z for z in ZONES if counts[z] == 0]

    print("cellZone audit:")
    for zone in ZONES:
        n = counts[zone]
        status = "ok" if n > 0 else "EMPTY"
        print(f"  {zone:12s}  {n:6d} cells  [{status}]")

    if failed:
        print(f"ERROR: empty cellZones: {', '.join(failed)}", file=sys.stderr)
        print("提示: 检查 topoSetDict 是否全部使用 cellSet+setToCellZone", file=sys.stderr)
        return 1

    print("  all cellZones non-empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
