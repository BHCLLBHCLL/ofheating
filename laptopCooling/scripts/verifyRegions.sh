#!/bin/sh
# 检查 splitMeshRegions 后各区域 polyMesh/boundary 是否齐全

set -e
cd "${0%/*}/.." || exit 1

REGIONS="air cpu vc motherboard fins chassis screen"
missing=""

for r in $REGIONS; do
    if [ ! -f "constant/$r/polyMesh/boundary" ]; then
        missing="$missing $r"
    fi
done

if [ -n "$missing" ]; then
    echo "ERROR: 以下区域缺少 constant/<region>/polyMesh/boundary:$missing"
    echo "提示: 查看 log.splitMeshRegions / log.topoSet"
    if [ -f constant/polyMesh/boundary ]; then
        echo "注意: 发现 constant/polyMesh/boundary (默认区域网格未归位)"
    fi
    exit 1
fi

echo "  all region meshes present"
