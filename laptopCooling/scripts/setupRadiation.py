#!/usr/bin/env python3
"""
为 viewFactor 辐射模型配置空气域:
  - 写入 v2412 createViewFactors 所需的 viewFactorsDict
  - 为 polyMesh/boundary 参与面添加 viewFactorWall 组
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meshBoundary import patch_names_from_boundary

CASE = Path(__file__).resolve().parent.parent
AIR = "air"
SKIP_PATCHES = {
    "fanInletLeft",
    "fanInletRight",
    "exhaustLeft",
    "exhaustRight",
    "bottomWall",
}
INGROUPS_LINE = "        inGroups        2(wall viewFactorWall);"

VIEW_FACTORS_DICT_BODY = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      viewFactorsDict;
}

// OpenFOAM v2412 createViewFactors
viewFactorModel     viewFactor2AI;
raySearchEngine     voxel;
agglomerate         false;
nRayPerFace         100;
writeViewFactors    true;
writeRays           false;

nTriPerVoxelMax     50;
depthMax            5;
"""


def ensure_view_factors_dict() -> None:
    """覆盖写入 viewFactorsDict (避免 templates/ 缓存旧版缺少 viewFactorModel)。"""
    path = CASE / "constant" / AIR / "viewFactorsDict"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(VIEW_FACTORS_DICT_BODY)


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


def validate_boundary(text: str) -> None:
    m = re.search(r"^(\d+)\s*\n\(\s*$", text, re.MULTILINE)
    if not m:
        raise RuntimeError("boundary: missing patch count/list header")
    declared = int(m.group(1))
    names = patch_names_from_boundary(text)
    if declared != len(names):
        raise RuntimeError(
            f"boundary: declared {declared} patches, parsed {len(names)}: {names}"
        )


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
    ensure_view_factors_dict()
    print("  viewFactorsDict written (viewFactorModel=viewFactor2AI)")
    patches = patch_air_boundary()
    print(f"  viewFactorWall enabled on {len(patches)} air patches:")
    for name in patches:
        print(f"    - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
