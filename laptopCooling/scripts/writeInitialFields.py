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
T_DIMS = "[0 0 0 1 0 0 0]"  # K
H_DIMS = "[0 2 -2 0 0 0 0]"  # J/kg, sensibleEnthalpy
CP_AIR = 1005.0  # J/kg/K, 与 constant/air/thermophysicalProperties 一致
H0 = CP_AIR * T0
P0 = 101325.0
R_AIR = 287.0
RHO0 = P0 / (R_AIR * T0)
U_FAN = (0.0, 2.0, 0.0)  # m/s, 模拟风扇进风
EXT_HTC = 8.0  # W/m^2/K, 固体外表面自然对流
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
        f"dimensions      {T_DIMS};",
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
            lines += [
                f"    {p}",
                "    {",
                "        type                compressible::turbulentTemperatureRadCoupledMixed;",
                "        Tnbr                T;",
                "        qr                  none;",
                "        qrNbr               none;",
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


def write_air_h(patches: list[str]) -> None:
    """heRhoThermo 能量方程求解 h；初值需与 T 一致 (h = Cp*T)。"""
    lines = [
        foam_header("h"),
        f"dimensions      {H_DIMS};",
        f"internalField   uniform {H0};",
        "boundaryField",
        "{",
    ]
    for p in patches:
        if p.startswith("air_to_"):
            lines += [
                f"    {p}",
                "    {",
                "        type            zeroGradient;",
                "    }",
            ]
        elif p in {"fanInlet", "exhaust"}:
            lines += [
                f"    {p}",
                "    {",
                "        type            fixedValue;",
                f"        value           uniform {H0};",
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
    (CASE / "0" / "air" / "h").write_text("\n".join(lines) + "\n")


def write_air_rho(patches: list[str]) -> None:
    lines = [
        foam_header("rho"),
        "dimensions      [1 -3 0 0 0 0 0];",
        f"internalField   uniform {RHO0};",
        "boundaryField",
        "{",
    ]
    for p in patches:
        if p == "exhaust":
            lines += [
                f"    {p}",
                "    {",
                "        type            fixedValue;",
                f"        value           uniform {RHO0};",
                "    }",
            ]
        else:
            lines += [
                f"    {p}",
                "    {",
                "        type            calculated;",
                f"        value           uniform {RHO0};",
                "    }",
            ]
    lines.append("}")
    (CASE / "0" / "air" / "rho").write_text("\n".join(lines) + "\n")


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
            lines += [
                f"    {p}",
                "    {",
                "        type            fixedFluxPressure;",
                "        value           uniform 0;",
                "    }",
            ]
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
        f"dimensions      {T_DIMS};",
        f"internalField   uniform {T0};",
        "boundaryField",
        "{",
    ]
    for p in patches:
        if p.startswith(f"{region}_to_"):
            nbr = p.replace(f"{region}_to_", "")
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
                    "        type                compressible::turbulentTemperatureRadCoupledMixed;",
                    "        Tnbr                T;",
                    "        qr                  none;",
                    "        qrNbr               none;",
                    "        kappaMethod         solidThermo;",
                    f"        value               uniform {T0};",
                    "    }",
                ]
        else:
            lines += [
                f"    {p}",
                "    {",
                "        type            externalWallHeatFluxTemperature;",
                "        mode            coefficient;",
                f"        h               uniform {EXT_HTC};",
                f"        Ta              constant {T0};",
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
            write_air_h(patches)
            write_air_rho(patches)
            write_air_U(patches)
            write_air_p(patches)
            if ENABLE_RADIATION:
                write_air_qr(patches)
        else:
            write_solid_p(region, patches)
            write_solid_T(region, patches)
        extra = ""
        if region == FLUID:
            extra = ", h, rho" + (", qr" if ENABLE_RADIATION else "")
        print(f"  wrote 0/{region}/ fields ({len(patches)} patches{extra})")


if __name__ == "__main__":
    main()
