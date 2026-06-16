# GMod PCF Asset Exporter

GMod PCF Asset Exporter is a Python tool for organizing Garry's Mod particle assets.

It scans `.pcf` particle files and tries to detect the materials, models, and sounds used by each PCF. Then, it creates a separate export folder for every PCF file and copies the related assets into organized subfolders.

## Features

* Scans all `.pcf` files inside a selected folder
* Extracts readable asset references from PCF binary data
* Detects related:

  * Materials
  * Models
  * Sounds
* Copies each PCF into its own organized folder
* Preserves Garry's Mod folder structure
* Copies VMT texture dependencies such as VTF files
* Copies model sidecar files such as `.vvd`, `.phy`, `.dx90.vtx`, and `.sw.vtx`
* Creates a `manifest.txt` file for every exported PCF
* Does not modify or delete original files

## Example Output

If you have a PCF file named:

```text
poyraxpcf.pcf
```

The tool creates an output folder like this:

```text
exported/
└── poyraxpcf/
    ├── particles/
    │   └── poyraxpcf.pcf
    ├── materials/
    │   └── ...
    ├── models/
    │   └── ...
    ├── sound/
    │   └── ...
    └── manifest.txt
```

## Use Case

This tool is useful when you have a large Garry's Mod addon or particle pack with mixed files and you want to separate each PCF with only the assets it uses.

It can help with:

* Cleaning large addon folders
* Organizing particle effects
* Preparing assets for release
* Finding dependencies of PCF files
* Creating smaller PCF-specific packages

## Requirements

* Python 3.10 or newer
* Windows, Linux, or macOS

No external Python packages are required.

## How to Use

Download or clone this repository:

```bash
git clone https://github.com/poyraxx/gmod-pcf-asset-exporter.git
cd gmod-pcf-asset-exporter
```

Run the script:

```bash
python pcf_asset_exporter.py
```

The tool will ask for the following folders:

```text
PCF folder path:
Materials folder path:
Models folder path:
Sound folder path:
Output folder:
```

Example:

```text
PCF folder path:
D:\gmod_temp\particles

Materials folder path:
D:\gmod_temp\materials

Models folder path:
D:\gmod_temp\models

Sound folder path:
D:\gmod_temp\sound

Output folder:
D:\gmod_temp\exported
```

After the scan is completed, each PCF file will have its own exported folder.

## Windows Batch Launcher

You can also create a `run.bat` file:

```bat
@echo off
title GMod PCF Asset Exporter
python pcf_asset_exporter.py
pause
```

Then double-click `run.bat` to start the tool.

## How It Works

The tool reads PCF files as binary data and extracts readable strings from them. These strings are compared against the files inside your `materials`, `models`, and `sound` folders.

For example, if a PCF contains a reference like:

```text
effects/fire_smoke
```

and your materials folder contains:

```text
materials/effects/fire_smoke.vmt
```

the tool will detect it as a used material and copy it into the PCF export folder.

The tool also reads `.vmt` files to find related `.vtf` texture files.

For models, if a `.mdl` file is detected, the tool also tries to copy related files such as:

```text
.vvd
.phy
.dx80.vtx
.dx90.vtx
.sw.vtx
.ani
```

## Limitations

PCF files are binary files, so this tool works by extracting readable strings from them. Because of that, detection may not be perfect in every case.

Some sound references may use sound script names instead of direct file paths. For example:

```text
Weapon_AR2.Single
```

In that case, the tool may not be able to resolve the exact `.wav`, `.mp3`, or `.ogg` file unless the real file path is present in the PCF data.

Always check the generated `manifest.txt` files after exporting.

## Safety

This tool only copies files into the output folder. It does not delete, move, or modify the original addon files.

## Recommended Folder Structure

Your source folder can look like this:

```text
source/
├── particles/
├── materials/
├── models/
└── sound/
```

The exported folder will look like this:

```text
exported/
├── particle_file_1/
│   ├── particles/
│   ├── materials/
│   ├── models/
│   ├── sound/
│   └── manifest.txt
│
└── particle_file_2/
    ├── particles/
    ├── materials/
    ├── models/
    ├── sound/
    └── manifest.txt
```

## License

This project is open-source and can be used, modified, and distributed freely.

## Disclaimer

This project is not affiliated with Facepunch Studios, Valve, or Garry's Mod.

Garry's Mod and Source Engine related names belong to their respective owners.
