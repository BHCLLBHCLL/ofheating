#!/usr/bin/env python3
"""topoSet 后检查各 cellZone 单元数。

v2412 的 constant/polyMesh/cellZones 常为多行 cellLabels 或不含内联计数;
以 log.topoSet / sets/<zone> 为主要依据, cellZones 文件为辅助。
"""

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


def set_file_count(name: str) -> int | None:
    """读取 constant/polyMesh/sets/<name> 第一行的列表长度。"""
    path = SETS_DIR / name
    if not path.exists():
        return None
    text = path.read_text(errors="replace")
    m = re.search(r"^\s*(\d+)\s*\(", text, re.MULTILINE)
    return int(m.group(1)) if m else None


def counts_from_topo_log(text: str) -> dict[str, int]:
    """从 log.topoSet 提取各 zone 最终单元数。"""
    counts: dict[str, int] = {}
    for line in text.splitlines():
        m = re.search(r"cellZoneSet\s+(\w+)\s+now size\s+(\d+)", line)
        if m:
            counts[m.group(1)] = int(m.group(2))
            continue
        m = re.search(r"Using zone\s+(\w+)\s+with\s+(\d+)\s+cells", line)
        if m:
            zone, n = m.group(1), int(m.group(2))
            counts[zone] = max(counts.get(zone, 0), n)
    return counts


def counts_from_cellzones_file(text: str) -> dict[str, int]:
    """解析 cellZones (兼容单行/多行 cellLabels)。"""
    counts = {z: 0 for z in ZONES}
    if "format      binary" in text:
        return counts

    current: str | None = None
    expect_count = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in ZONES:
            current = stripped
            expect_count = False
            continue
        if stripped == "}":
            current = None
            expect_count = False
            continue
        if not current:
            continue

        m = re.search(r"cellLabels\s+List<label>\s+(\d+)", line)
        if m:
            counts[current] = int(m.group(1))
            current = None
            expect_count = False
            continue
        if stripped == "cellLabels":
            expect_count = True
            continue
        if expect_count and "List<label>" in stripped:
            m = re.search(r"List<label>\s+(\d+)", stripped)
            if m:
                counts[current] = int(m.group(1))
                current = None
                expect_count = False
            continue
        if expect_count and stripped.isdigit():
            counts[current] = int(stripped)
            current = None
            expect_count = False

    return counts


def merge_counts(*sources: dict[str, int]) -> dict[str, int]:
    """合并多来源计数, 取各 zone 最大值。"""
    merged = {z: 0 for z in ZONES}
    for src in sources:
        for z in ZONES:
            merged[z] = max(merged[z], src.get(z, 0))
    # cellZoneSet 写入后 sets/<zone> 与 cellSet 内容一致
    for z in ZONES:
        merged[z] = max(merged[z], set_file_count(z) or 0)
        cs = CELL_SETS.get(z)
        if cs:
            merged[z] = max(merged[z], set_file_count(cs) or 0)
    return merged


def zone_names_in_cellzones(text: str) -> list[str]:
    """列出 cellZones 文件中的 zone 名 (不要求有 cellLabels)。"""
    names: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s in ZONES or s == "_v2412_pad":
            names.append(s)
    return names


def main() -> int:
    log_counts: dict[str, int] = {}
    if LOG_TOPO.exists():
        log_counts = counts_from_topo_log(LOG_TOPO.read_text(errors="replace"))

    file_counts: dict[str, int] = {z: 0 for z in ZONES}
    zone_names: list[str] = []
    if CELL_ZONES.exists():
        cz_text = CELL_ZONES.read_text(errors="replace")
        file_counts = counts_from_cellzones_file(cz_text)
        zone_names = zone_names_in_cellzones(cz_text)

    counts = merge_counts(log_counts, file_counts)
    failed = [z for z in ZONES if counts[z] == 0]

    print("cellZone audit:")
    for zone in ZONES:
        n = counts[zone]
        status = "ok" if n > 0 else "EMPTY"
        src = []
        if log_counts.get(zone, 0) > 0:
            src.append("log")
        if file_counts.get(zone, 0) > 0:
            src.append("cellZones")
        if (set_file_count(zone) or 0) > 0:
            src.append(f"sets/{zone}")
        cs = CELL_SETS.get(zone, "")
        if cs and (set_file_count(cs) or 0) > 0:
            src.append(f"sets/{cs}")
        src_txt = f"  ({', '.join(src)})" if src else ""
        print(f"  {zone:12s}  {n:6d} cells  [{status}]{src_txt}")

    if zone_names:
        print(f"  cellZones file lists: {', '.join(zone_names)}")

    if failed:
        print(f"ERROR: empty cellZones: {', '.join(failed)}", file=sys.stderr)
        if log_counts and any(log_counts.get(z, 0) > 0 for z in failed):
            print(
                "提示: log.topoSet 显示 zone 已创建, 但无法从磁盘确认;"
                " 请检查 constant/polyMesh/cellZones 并继续查看 log.splitMeshRegions",
                file=sys.stderr,
            )
        return 1

    print("  all cellZones non-empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
