# GMod PCF Asset Exporter

GMod PCF Asset Exporter is a Python tool for organizing Garry's Mod particle assets.

It scans `.pcf` particle files, extracts readable asset references from PCF binary data, and copies the related materials, models, and sounds into clean output folders.

The tool has two export modes:

1. **Per-PCF Package Mode**: creates a separate folder for each PCF file and writes a `manifest.txt` file.
2. **Workshop/Add-on Mode**: creates one shared Garry's Mod add-on style folder with `particles`, `materials`, `models`, and `sound` folders.

Original source files are never deleted, moved, or modified. The tool only copies files into the selected output folder.

## Repository Description

A Python tool that exports Garry's Mod PCF particle files with their related materials, models, and sounds, either as separate per-PCF packages or as one Workshop-ready add-on folder.

## Features

- Scans all `.pcf` files inside a selected folder
- Extracts readable asset references from PCF binary data
- Detects related:
  - Materials
  - Models
  - Sounds
- Supports two export modes
- Preserves Garry's Mod folder structure
- Copies VMT texture dependencies such as `.vtf` files
- Copies model sidecar files such as `.vvd`, `.phy`, `.dx90.vtx`, and `.sw.vtx`
- Generates `PrecacheParticleSystem("...")` lines in Mode 1 manifests
- Does not modify or delete original files
- Requires no external Python packages

## Export Modes

### Mode 1: Per-PCF Package Mode

This mode creates a separate package folder for every PCF file.

Each package contains:

```text
pcf_name/
├── particles/
├── materials/
├── models/
├── sound/
└── manifest.txt
```

The `manifest.txt` file includes:

- The PCF path
- Detected particle system names
- Ready-to-copy `PrecacheParticleSystem("...")` Lua lines
- Used materials
- Used models
- Used sounds
- Copy warnings or errors, if any

Example manifest section:

```text
[particle_systems] count=4
hpw_apparation_black
hpw_apparation_black_impact
hpw_apparation_white
hpw_apparation_white_impact

[precache_lua] count=4
PrecacheParticleSystem("hpw_apparation_black")
PrecacheParticleSystem("hpw_apparation_black_impact")
PrecacheParticleSystem("hpw_apparation_white")
PrecacheParticleSystem("hpw_apparation_white_impact")
```

### Mode 2: Workshop/Add-on Mode

This mode collects all PCF files and all used assets into one shared folder.

It is designed for creating a clean Workshop/add-on upload structure.

Output example:

```text
output/
├── particles/
│   ├── effect_1.pcf
│   └── effect_2.pcf
├── materials/
│   └── ...
├── models/
│   └── ...
└── sound/
    └── ...
```

This mode does **not** create `manifest.txt` files.

Use this mode when you want all PCF files and their shared dependencies inside one add-on folder.

## Requirements

- Python 3.10 or newer
- Windows, Linux, or macOS

No external Python packages are required.

## Installation

Clone the repository:

```bash
git clone https://github.com/poyraxx/gmod-pcf-asset-exporter.git
cd gmod-pcf-asset-exporter
```

Or download the script manually and place it inside any folder you want.

## Usage

Run the script:

```bash
python pcf_asset_exporter_dual_mode_en.py
```

The tool will ask you to choose an export mode:

```text
1 - Separate folder per PCF + manifest.txt + PrecacheParticleSystem list
2 - Workshop/addon mode: one folder, shared particles/materials/models/sound, no manifest
```

Then it will ask for source folders:

```text
Enter the PCF folder path:
Enter the materials folder path, or leave empty:
Enter the models folder path, or leave empty:
Enter the sound folder path, or leave empty:
Output folder:
```

Example:

```text
Enter the PCF folder path:
D:\gmod_temp\particles

Enter the materials folder path, or leave empty:
D:\gmod_temp\materials

Enter the models folder path, or leave empty:
D:\gmod_temp\models

Enter the sound folder path, or leave empty:
D:\gmod_temp\sound

Output folder:
D:\gmod_temp\exported
```

## Windows Batch Launcher

A simple `.bat` launcher can be used on Windows:

```bat
@echo off
title GMod PCF Asset Exporter
python pcf_asset_exporter_dual_mode_en.py
pause
```

Double-click the `.bat` file to run the exporter in a terminal window.

## How It Works

PCF files are binary files. This tool does not fully decode or compile PCF data.

Instead, it extracts readable ASCII and UTF-16 strings from PCF files and compares those strings against indexed files inside your selected `materials`, `models`, and `sound` folders.

For example, if a PCF contains this readable reference:

```text
effects/fire_smoke
```

and your materials folder contains:

```text
materials/effects/fire_smoke.vmt
```

the tool can detect that material and copy it into the output folder.

The tool also reads `.vmt` files and attempts to copy related `.vtf` texture files.

For models, if a `.mdl` file is detected, the tool also tries to copy related sidecar files:

```text
.mdl
.vvd
.phy
.dx80.vtx
.dx90.vtx
.sw.vtx
.ani
```

## Limitations

PCF files are binary files, so detection is based on readable strings and heuristics. It may not be perfect for every PCF file.

Some sounds may be referenced through Source Engine sound script names instead of direct file paths. For example:

```text
Weapon_AR2.Single
```

If the real `.wav`, `.mp3`, or `.ogg` path is not present in the PCF data, the tool may not be able to resolve it automatically.

Particle system names are also detected heuristically from readable strings. The generated `PrecacheParticleSystem("...")` lines should be reviewed before use.

## Safety

This tool only copies files. It does not delete, move, or edit your original files.

Still, it is recommended to review the output before publishing or uploading it to the Steam Workshop.

## Suggested Repository Name

```text
gmod-pcf-asset-exporter
```

## License

This project is open-source. You may use, modify, and distribute it freely.

## Disclaimer

This project is not affiliated with Facepunch Studios, Valve, or Garry's Mod.

Garry's Mod and Source Engine related names belong to their respective owners.
