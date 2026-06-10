#!/usr/bin/env python3
"""topoSet 后检查各 cellZone 是否非空 (避免薄层未分到单元导致 split 失败)。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CASE = Path(__file__).resolve().parent.parent
ZONES = ["cpu", "vc", "motherboard", "fins", "chassis", "screen", "air"]
CELL_ZONES = CASE / "constant" / "polyMesh" / "cellZones"


def count_zone_labels(text: str, zone: str) -> int:
    pattern = rf"\b{re.escape(zone)}\b\s*\{{[\s\S]*?cellLabels\s+List<label>\s*\n\s*(\d+)"
    match = re.search(pattern, text)
    if match:
        return int(match.group(1))
    return 0


def main() -> int:
    if not CELL_ZONES.exists():
        print(f"ERROR: missing {CELL_ZONES}", file=sys.stderr)
        return 1

    text = CELL_ZONES.read_text()
    failed = []
    print("cellZone audit:")
    for zone in ZONES:
        n = count_zone_labels(text, zone)
        status = "ok" if n > 0 else "EMPTY"
        print(f"  {zone:12s}  {n:6d} cells  [{status}]")
        if n == 0:
            failed.append(zone)

    if failed:
        print(
            f"ERROR: empty cellZones: {', '.join(failed)}",
            file=sys.stderr,
        )
        print(
            "提示: 检查 blockMeshDict z 向分辨率与 topoSetDict 包络框是否对齐",
            file=sys.stderr,
        )
        return 1

    print("  all cellZones non-empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
