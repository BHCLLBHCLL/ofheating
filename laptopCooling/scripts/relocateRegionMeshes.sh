#!/bin/sh
# splitMeshRegions -overwrite 可能将某一区域留在 constant/polyMesh
# 本脚本将根目录 polyMesh 归位到 constant/air/polyMesh

set -e
cd "${0%/*}/.." || exit 1

if [ -f constant/polyMesh/boundary ] && [ ! -f constant/air/polyMesh/boundary ]; then
    echo "  relocating constant/polyMesh -> constant/air/polyMesh"
    mkdir -p constant/air
    mv constant/polyMesh constant/air/polyMesh
fi
