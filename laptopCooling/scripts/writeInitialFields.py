#!/usr/bin/env python3
"""
在 splitMeshRegions 之后为各区域生成 0/ 初始场与耦合边界。
OpenFOAM v2412 / chtMultiRegionSimpleFoam
"""

from pathlib import Path
import re

CASE = Path(__file__).resolve().parent.parent
REGIONS = ["air", "cpu", "vc", "motherboard", "fins", "chassis", "screen"]
FLUID = "air"
T0 = 298.0
P0 = 101325.0
U_FAN = (0.0, 2.0, 0.0)  # m/s, 模拟风扇进风


def read_patches(region: str) -> list[str]:
    boundary = CASE / "constant" / region / "polyMesh" / "boundary"
    if not boundary.exists():
        raise FileNotFoundError(f"Missing {boundary}")
    text = boundary.read_text()
    return re.findall(r"^\s{4}(\S+)\s*$", text, re.MULTILINE)


def foam_header(obj: str) -> str:
    return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      {obj};
}}

"""


def write_air_T(patches: list[str]) -> None:
    lines = [
        foam_header("T").replace("volScalarField", "volScalarField"),
        f"dimensions      [0 1 0 1 0 0 0];",
        f"internalField   uniform {T0};",
        "boundaryField",
        "{",
    ]
    for p in patches:
        if p.startswith("air_to_"):
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


def write_air_U(patches: list[str]) -> None:
    lines = [
        """FoamFile
{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}

""",
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
        f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      {field};
}}

""",
        "dimensions      [1 -1 -2 0 0 0 0];",
        f"internalField   uniform 0;",
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


def write_solid_T(region: str, patches: list[str]) -> None:
    lines = [
        f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      T;
}}

""",
        "dimensions      [0 1 0 1 0 0 0];",
        f"internalField   uniform {T0};",
        "boundaryField",
        "{",
    ]
    for p in patches:
        if p.startswith(f"{region}_to_"):
            nbr = p.replace(f"{region}_to_", "")
            sample = f"{nbr}_to_{region}"
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
        else:
            write_solid_T(region, patches)
        print(f"  wrote 0/{region}/ fields ({len(patches)} patches)")


if __name__ == "__main__":
    main()
