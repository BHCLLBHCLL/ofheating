#!/usr/bin/env python3
"""
为 viewFactor 辐射模型配置空气域参与面 (viewFactorWall)。
仅修改 constant/air/polyMesh/boundary 中各 patch 的 inGroups, 保持 OpenFOAM 语法完整。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CASE = Path(__file__).resolve().parent.parent
AIR = "air"
SKIP_PATCHES = {"fanInlet", "exhaust"}
INGROUPS_LINE = "        inGroups        2(wall viewFactorWall);"


def air_boundary_path() -> Path:
    primary = CASE / "constant" / AIR / "polyMesh" / "boundary"
    if primary.exists():
        return primary
    fallback = CASE / "constant" / "polyMesh" / "boundary"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        "Missing air polyMesh/boundary under constant/air or constant/"
    )


def patch_names(text: str) -> list[str]:
    """提取 boundary 列表中的 patch 名 (不含 FoamFile 块)。"""
    m = re.search(r"^\d+\s*\n\(\s*$", text, re.MULTILINE)
    if not m:
        return []
    names: list[str] = []
    in_list = False
    for line in text[m.end() :].splitlines():
        if line.strip() == ")":
            break
        if re.match(r"^    \S+$", line):
            in_list = True
            names.append(line.strip())
        elif in_list and line.strip() == "{":
            in_list = False
    return names


def validate_boundary(text: str) -> None:
    m = re.search(r"^(\d+)\s*\n\(\s*$", text, re.MULTILINE)
    if not m:
        raise RuntimeError("boundary: missing patch count/list header")
    declared = int(m.group(1))
    names = patch_names(text)
    if declared != len(names):
        raise RuntimeError(
            f"boundary: declared {declared} patches, parsed {len(names)}"
        )
    for name in names:
        block = re.search(
            rf"    {re.escape(name)}\s*\n    \{{",
            text,
            re.MULTILINE,
        )
        if not block:
            raise RuntimeError(f"boundary: patch '{name}' missing opening brace")


def patch_air_boundary() -> list[str]:
    boundary = air_boundary_path()
    lines = boundary.read_text().splitlines()
    out: list[str] = []
    patched: list[str] = []

    current_patch: str | None = None
    in_patch = False
    inserted_for_patch = False
    patch_has_ingroup = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # patch 名行: 四个空格 + 标识符, 下一行必须是 "{"
        if (
            re.match(r"^    \S+$", line)
            and i + 1 < len(lines)
            and lines[i + 1].strip() == "{"
        ):
            current_patch = stripped
            in_patch = True
            inserted_for_patch = False
            patch_has_ingroup = False
            out.append(line)
            i += 1
            continue

        if in_patch and current_patch:
            if "viewFactorWall" in line:
                patch_has_ingroup = True
            if stripped == "}":
                if (
                    current_patch not in SKIP_PATCHES
                    and not patch_has_ingroup
                    and not inserted_for_patch
                ):
                    raise RuntimeError(
                        f"boundary: failed to insert inGroups for {current_patch}"
                    )
                out.append(line)
                in_patch = False
                current_patch = None
                i += 1
                continue

            out.append(line)
            if (
                current_patch not in SKIP_PATCHES
                and not patch_has_ingroup
                and not inserted_for_patch
                and re.match(r"^\s+type\s+\S+;", line)
            ):
                out.append(INGROUPS_LINE)
                inserted_for_patch = True
                patched.append(current_patch)
            i += 1
            continue

        out.append(line)
        i += 1

    new_text = "\n".join(out) + "\n"
    validate_boundary(new_text)
    boundary.write_text(new_text)
    return patched


def main() -> int:
    patches = patch_air_boundary()
    print(f"  viewFactorWall enabled on {len(patches)} air patches:")
    for name in patches:
        print(f"    - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
