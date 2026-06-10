#!/usr/bin/env python3
"""
为 viewFactor 辐射模型配置空气域参与面 (viewFactorWall) 并备份/恢复辐射字典。
"""

from __future__ import annotations

import re
from pathlib import Path

CASE = Path(__file__).resolve().parent.parent
AIR = "air"
SKIP_PATCHES = {"fanInlet", "exhaust"}


def patch_air_boundary() -> list[str]:
    boundary = CASE / "constant" / AIR / "polyMesh" / "boundary"
    if not boundary.exists():
        raise FileNotFoundError(f"Missing {boundary}")

    text = boundary.read_text()
    patched: list[str] = []

    def patch_block(match: re.Match[str]) -> str:
        name = match.group(1)
        body = match.group(2)
        if name in SKIP_PATCHES:
            return match.group(0)
        if "viewFactorWall" in body:
            return match.group(0)

        patched.append(name)
        lines = body.splitlines()
        out: list[str] = []
        inserted = False
        for line in lines:
            out.append(line)
            if not inserted and re.match(r"\s*type\s+\S+;", line):
                if "inGroups" not in body:
                    out.append("        inGroups        2(wall viewFactorWall);")
                inserted = True
        if not inserted:
            out.insert(0, "        inGroups        2(wall viewFactorWall);")
        return f"    {name}\n" + "\n".join(out) + "\n    }"

    new_text, count = re.subn(
        r"    (\S+)\s*\n    \{(.*?)\n    \}",
        patch_block,
        text,
        flags=re.DOTALL,
    )
    if count == 0:
        raise RuntimeError(f"No patches updated in {boundary}")

    boundary.write_text(new_text)
    return patched


def main() -> None:
    patches = patch_air_boundary()
    print(f"  viewFactorWall enabled on {len(patches)} air patches:")
    for name in patches:
        print(f"    - {name}")


if __name__ == "__main__":
    main()
