"""解析 OpenFOAM polyMesh/boundary 中的 patch 名。"""

from __future__ import annotations

import re


def patch_names_from_boundary(text: str) -> list[str]:
    """仅返回顶层 patch 名 (name 行后紧跟 '{', 排除 '{' / '}' 等)。"""
    lines = text.splitlines()
    start = 0
    for i in range(1, len(lines)):
        if re.fullmatch(r"\d+", lines[i - 1].strip()) and lines[i].strip() == "(":
            start = i + 1
            break

    names: list[str] = []
    i = start
    while i < len(lines):
        if lines[i].strip() == ")":
            break
        if (
            i + 1 < len(lines)
            and re.match(r"^    \S+$", lines[i])
            and lines[i + 1].strip() == "{"
        ):
            names.append(lines[i].strip())
        i += 1
    return names
