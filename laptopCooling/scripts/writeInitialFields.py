#!/usr/bin/env python3
"""
在 splitMeshRegions 之后为各区域生成 0/ 初始场与耦合边界。
OpenFOAM v2412 / chtMultiRegionSimpleFoam + viewFactor 辐射 (默认开启)
"""

from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meshBoundary import patch_names_from_boundary

CASE = Path(__file__).resolve().parent.parent
REGIONS = ["air", "cpu", "vc", "motherboard", "fins", "chassis", "screen"]
FLUID = "air"
T0 = 298.0
P0 = 101325.0
U_FAN = (0.0, 2.0, 0.0)  # m/s, 模拟风扇进风
ENABLE_RADIATION = True


def boundary_path(region: str) -> Path:
    candidates = [CASE / "constant" / region / "polyMesh" / "boundary"]
    if region == FLUID:
        candidates.append(CASE / "constant" / "polyMesh" / "boundary")
    for path in candidates:
        if path.exists():
            return path
    hint = []
    root_mesh = CASE / "constant" / "polyMesh" / "boundary"
    if root_mesh.exists():
        hint.append("found constant/polyMesh/boundary (run relocateRegionMeshes.sh)")
    for child in sorted((CASE / "constant").glob("*/polyMesh/boundary")):
        hint.append(str(child.parent.parent.name))
    extra = f" Existing regions: {', '.join(hint)}" if hint else ""
    raise FileNotFoundError(
        f"Missing mesh boundary for region '{region}'.{extra}"
    )


def read_patches(region: str) -> list[str]:
    return patch_names_from_boundary(boundary_path(region).read_text())


def foam_header(obj: str, field_class: str = "volScalarField") -> str:
    return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       {field_class};
    object      {obj};
}}

"""


def write_air_T(patches: list[str]) -> None:
    lines = [
        foam_header("T"),
        "dimensions      [0 1 0 1 0 0 0];",
        f"internalField   uniform {T0};",
        "boundaryField",
        "{",
    ]
    for p in patches:
        if p.startswith("air_to_") and ENABLE_RADIATION:
            lines += [
                f"    {p}",
                "    {",
                "        type                compressible::turbulentTemperatureRadCoupledMixed;",
                "        Tnbr                T;",
                "        qr                  qr;",
                "        qrNbr               none;",
                "        kappaMethod         fluidThermo;",
                f"        value               uniform {T0};",
                "    }",
            ]
        elif p.startswith("air_to_"):
            nbr = p.replace("air_to_", "")
            lines += [
                f"    {p}",
                "    {",
                "        type                compressible::thermalBaffle;",
                "        sampleMode          nearestCell;",
                f"        samplePatch         {nbr}_to_air;",
                "        targetMethod        meshWave;",
                "        Tnbr                T;",
                "        kappaMethod         fluidThermo;",
                f"        value               uniform {T0};",
                "    }",
            ]
        elif p == "fanInlet":
            lines += [
                f"    {p}",
                "    {",
                "        type            fixedValue;",
                f"        value           uniform {T0};",
                "    }",
            ]
        elif p == "exhaust":
            lines += [
                f"    {p}",
                "    {",
                "        type            inletOutlet;",
                f"        inletValue      uniform {T0};",
                f"        value           uniform {T0};",
                "    }",
            ]
        else:
            lines += [
                f"    {p}",
                "    {",
                "        type            zeroGradient;",
                "    }",
            ]
    lines.append("}")
    out = CASE / "0" / "air" / "T"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")


def write_air_qr(patches: list[str]) -> None:
    lines = [
        foam_header("qr"),
        "dimensions      [1 0 -3 0 0 0 0];",
        "internalField   uniform 0;",
        "boundaryField",
        "{",
    ]
    for p in patches:
        if p in {"fanInlet", "exhaust"}:
            lines += [
                f"    {p}",
                "    {",
                "        type            zeroGradient;",
                "    }",
            ]
        elif p.startswith("air_to_"):
            lines += [
                f"    {p}",
                "    {",
                "        type                greyDiffusiveRadiationViewFactor;",
                "        emissivityMode      solidRadiation;",
                "        qro                 uniform 0;",
                "        value               uniform 0;",
                "    }",
            ]
        else:
            lines += [
                f"    {p}",
                "    {",
                "        type                greyDiffusiveRadiationViewFactor;",
                "        emissivityMode      lookup;",
                "        qro                 uniform 0;",
                "        value               uniform 0;",
                "    }",
            ]
    lines.append("}")
    (CASE / "0" / "air" / "qr").write_text("\n".join(lines) + "\n")


def write_air_U(patches: list[str]) -> None:
    lines = [
        foam_header("U", "volVectorField"),
        "dimensions      [0 1 -1 0 0 0 0];",
        "internalField   uniform (0 0 0);",
        "boundaryField",
        "{",
    ]
    for p in patches:
        if p.startswith("air_to_"):
            lines += [f"    {p}", "    {", "        type            noSlip;", "    }"]
        elif p == "fanInlet":
            lines += [
                f"    {p}",
                "    {",
                "        type            fixedValue;",
                f"        value           uniform ({U_FAN[0]} {U_FAN[1]} {U_FAN[2]});",
                "    }",
            ]
        elif p == "exhaust":
            lines += [
                f"    {p}",
                "    {",
                "        type            pressureInletOutletVelocity;",
                "        value           uniform (0 0 0);",
                "    }",
            ]
        else:
            lines += [f"    {p}", "    {", "        type            noSlip;", "    }"]
    lines.append("}")
    (CASE / "0" / "air" / "U").write_text("\n".join(lines) + "\n")


def write_air_p(patches: list[str], field: str = "p_rgh") -> None:
    lines = [
        foam_header(field),
        "dimensions      [1 -1 -2 0 0 0 0];",
        "internalField   uniform 0;",
        "boundaryField",
        "{",
    ]
    for p in patches:
        if p == "exhaust":
            lines += [f"    {p}", "    {", "        type            fixedValue;", "        value           uniform 0;", "    }"]
        elif p == "fanInlet":
            lines += [f"    {p}", "    {", "        type            zeroGradient;", "    }"]
        else:
            lines += [f"    {p}", "    {", "        type            fixedFluxPressure;", "        value           uniform 0;", "    }"]
    lines.append("}")
    out_dir = CASE / "0" / "air"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / field).write_text("\n".join(lines) + "\n")
    if field == "p_rgh":
        p_lines = lines.copy()
        p_text = "\n".join(p_lines).replace("object      p_rgh", "object      p")
        p_text = p_text.replace("uniform 0;", f"uniform {P0};")
        (out_dir / "p").write_text(p_text + "\n")


def write_solid_p(region: str, patches: list[str]) -> None:
    """heSolidThermo/basicThermo 要求 0/<region>/p (MUST_READ)。"""
    lines = [
        foam_header("p"),
        "dimensions      [1 -1 -2 0 0 0 0];",
        f"internalField   uniform {P0};",
        "boundaryField",
        "{",
    ]
    for p in patches:
        lines += [f"    {p}", "    {", "        type            zeroGradient;", "    }"]
    lines.append("}")
    out = CASE / "0" / region / "p"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")


def write_solid_T(region: str, patches: list[str]) -> None:
    lines = [
        foam_header("T"),
        "dimensions      [0 1 0 1 0 0 0];",
        f"internalField   uniform {T0};",
        "boundaryField",
        "{",
    ]
    for p in patches:
        if p.startswith(f"{region}_to_"):
            nbr = p.replace(f"{region}_to_", "")
            sample = f"{nbr}_to_{region}"
            if ENABLE_RADIATION and nbr == FLUID:
                lines += [
                    f"    {p}",
                    "    {",
                    "        type                compressible::turbulentTemperatureRadCoupledMixed;",
                    "        Tnbr                T;",
                    "        qr                  none;",
                    "        qrNbr               qr;",
                    "        kappaMethod         solidThermo;",
                    f"        value               uniform {T0};",
                    "    }",
                ]
            else:
                lines += [
                    f"    {p}",
                    "    {",
                    "        type                compressible::thermalBaffle;",
                    "        sampleMode          nearestCell;",
                    f"        samplePatch         {sample};",
                    "        targetMethod        meshWave;",
                    "        Tnbr                T;",
                    "        kappaMethod         solidThermo;",
                    f"        value               uniform {T0};",
                    "    }",
                ]
        else:
            lines += [
                f"    {p}",
                "    {",
                "        type            externalWallHeatFlux;",
                "        Q               uniform 0;",
                "        h               uniform 8;",
                f"        Ta              uniform {T0};",
                "        kappaMethod     solidThermo;",
                f"        value           uniform {T0};",
                "    }",
            ]
    lines.append("}")
    out = CASE / "0" / region / "T"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")


def main() -> None:
    for region in REGIONS:
        patches = read_patches(region)
        if region == FLUID:
            write_air_T(patches)
            write_air_U(patches)
            write_air_p(patches)
            if ENABLE_RADIATION:
                write_air_qr(patches)
        else:
            write_solid_p(region, patches)
            write_solid_T(region, patches)
        extra = ", qr" if region == FLUID and ENABLE_RADIATION else ""
        print(f"  wrote 0/{region}/ fields ({len(patches)} patches{extra})")


if __name__ == "__main__":
    main()
