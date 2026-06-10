#!/usr/bin/env python3
"""topoSet 后检查各 cellZone 非空, 并检测固体 zone 之间是否重叠。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CASE = Path(__file__).resolve().parent.parent
ZONES = ["cpu", "vc", "motherboard", "fins", "chassis", "screen", "air"]
SOLIDS = ["cpu", "vc", "motherboard", "fins", "chassis", "screen"]
CELL_ZONES = CASE / "constant" / "polyMesh" / "cellZones"


def parse_zone_cells(text: str) -> dict[str, set[int]]:
    zones: dict[str, set[int]] = {z: set() for z in ZONES}
    for zone in ZONES:
        # 匹配 zone 块: "motherboard\n{ ... cellLabels List<label> N ( ... )"
        pattern = (
            rf"(?:^|\()\s*{re.escape(zone)}\s*\{{[\s\S]*?"
            r"cellLabels\s+List<label>\s+(\d+)\s*\(([\s\S]*?)\)"
        )
        match = re.search(pattern, text)
        if not match:
            continue
        count = int(match.group(1))
        if count == 0:
            continue
        body = match.group(2)
        labels = [int(x) for x in re.findall(r"\b\d+\b", body)]
        zones[zone] = set(labels[:count])
    return zones


def main() -> int:
    if not CELL_ZONES.exists():
        print(f"ERROR: missing {CELL_ZONES}", file=sys.stderr)
        return 1

    text = CELL_ZONES.read_text()
    zones = parse_zone_cells(text)
    failed = []

    print("cellZone audit:")
    for zone in ZONES:
        n = len(zones.get(zone, set()))
        status = "ok" if n > 0 else "EMPTY"
        print(f"  {zone:12s}  {n:6d} cells  [{status}]")
        if n == 0:
            failed.append(zone)

    overlaps: list[tuple[str, str, int]] = []
    for i, z1 in enumerate(SOLIDS):
        for z2 in SOLIDS[i + 1 :]:
            common = zones.get(z1, set()) & zones.get(z2, set())
            if common:
                overlaps.append((z1, z2, len(common)))

    if overlaps:
        print("ERROR: overlapping solid cellZones:", file=sys.stderr)
        for z1, z2, n in overlaps:
            print(f"  {z1} ∩ {z2}: {n} cells", file=sys.stderr)
        return 1

    if failed:
        print(f"ERROR: empty cellZones: {', '.join(failed)}", file=sys.stderr)
        return 1

    print("  all cellZones non-empty, solids pairwise disjoint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
