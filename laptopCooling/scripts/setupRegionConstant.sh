#!/bin/sh
# splitMeshRegions 后恢复各区域 constant 字典 (热物性 / 辐射等)

set -e
cd "${0%/*}/.." || exit 1

TPL="templates/constant"
REGIONS="air cpu vc motherboard fins chassis screen"

restore_file() {
    r="$1"
    f="$2"
    if [ ! -f "$TPL/$r/$f" ] && [ -f "constant/$r/$f" ]; then
        cp "constant/$r/$f" "$TPL/$r/$f"
    fi
    if [ -f "$TPL/$r/$f" ]; then
        cp "$TPL/$r/$f" "constant/$r/$f"
    fi
}

for r in $REGIONS; do
    mkdir -p "$TPL/$r" "constant/$r"
    if [ "$r" = "air" ]; then
        for f in thermophysicalProperties radiationProperties momentumTransport \
                 turbulenceProperties viewFactorsDict boundaryRadiationProperties; do
            restore_file "$r" "$f"
        done
    else
        for f in thermophysicalProperties radiationProperties; do
            restore_file "$r" "$f"
        done
    fi
    echo "  restored constant/$r/"
done

echo "Region constant dictionaries restored."
