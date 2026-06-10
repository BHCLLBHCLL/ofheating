#!/bin/bash
# 为各固体区域复制通用 fvSchemes / fvSolution

SOLIDS="cpu vc motherboard fins chassis screen"

for r in $SOLIDS; do
    mkdir -p system/$r
    cp system/solid/fvSchemes system/$r/fvSchemes
    cp system/solid/fvSolution system/$r/fvSolution
done

echo "Solid region system files copied."
