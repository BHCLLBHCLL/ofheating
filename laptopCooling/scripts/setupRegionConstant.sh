#!/bin/bash
# splitMeshRegions 后恢复各区域 constant 字典 (热物性 / 辐射等)

set -e
cd "${0%/*}/.." || exit 1

TPL="templates/constant"
REGIONS="air cpu vc motherboard fins chassis screen"

restore_region() {
    local r="$1"
    shift
    local files=("$@")
    mkdir -p "$TPL/$r" "constant/$r"
    for f in "${files[@]}"; do
        if [ ! -f "$TPL/$r/$f" ] && [ -f "constant/$r/$f" ]; then
            cp "constant/$r/$f" "$TPL/$r/$f"
        fi
        if [ -f "$TPL/$r/$f" ]; then
            cp "$TPL/$r/$f" "constant/$r/$f"
        fi
    done
    echo "  restored constant/$r/"
}

for r in $REGIONS; do
    if [ "$r" = "air" ]; then
        restore_region "$r" \
            thermophysicalProperties radiationProperties momentumTransport \
            viewFactorsDict boundaryRadiationProperties
    else
        restore_region "$r" thermophysicalProperties radiationProperties
    fi
done

echo "Region constant dictionaries restored."
