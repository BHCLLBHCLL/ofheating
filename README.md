# OpenFOAM 笔记本散热仿真

本仓库包含基于 **OpenFOAM v2412** 的 MacBook Pro 14" 笔记本散热共轭传热 (CHT) 算例。

## 算例

| 目录 | 说明 |
|------|------|
| [laptopCooling/](laptopCooling/) | 完整算例: CPU / 主板 / VC / 翅片 / 风扇 / 机壳 / 屏幕 |

## 快速开始

```bash
# Linux / WSL2
source /path/to/openfoam2412/etc/bashrc
cd laptopCooling
chmod +x Allrun Allclean
./Allrun
```

详细说明见 [laptopCooling/README.md](laptopCooling/README.md)。
