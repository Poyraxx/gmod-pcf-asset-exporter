from pathlib import Path
import re
import shutil
import os

MATERIAL_SUFFIXES = [
    ".vmt",
    ".vtf",
]

MODEL_SUFFIXES = [
    ".mdl",
    ".phy",
    ".vvd",
    ".dx80.vtx",
    ".dx90.vtx",
    ".sw.vtx",
    ".ani",
]

SOUND_SUFFIXES = [
    ".wav",
    ".mp3",
    ".ogg",
]

ALL_SUFFIXES = sorted(
    MATERIAL_SUFFIXES + MODEL_SUFFIXES + SOUND_SUFFIXES,
    key=len,
    reverse=True
)

VMT_TEXTURE_KEYS = {
    "$basetexture",
    "$bumpmap",
    "$normalmap",
    "$detail",
    "$envmapmask",
    "$phongexponenttexture",
    "$lightwarptexture",
    "$selfillummask",
    "$blendmodulatetexture",
    "$texture2",
    "$basetexture2",
}

PARTICLE_NAME_EXCLUDE = {
    "dmx",
    "pcf",
    "particles",
    "particle",
    "materials",
    "material",
    "models",
    "model",
    "sound",
    "sounds",
    "operator",
    "renderer",
    "initializer",
    "emitter",
    "control_point",
    "children",
    "sequence",
    "snapshot",
    "true",
    "false",
    "null",
    "none",
}

PARTICLE_NAME_BAD_FRAGMENTS = [
    "cparticle",
    "dme",
    "operator",
    "initializer",
    "renderer",
    "emitter",
    "movement",
    "random",
    "radius",
    "alpha",
    "color",
    "colour",
    "velocity",
    "sequence",
    "control",
    "position",
    "rotation",
    "gravity",
    "noise",
    "lifespan",
    "lifetime",
    "material",
    "texture",
    "sprite",
    "scale",
    "sort",
    "max",
    "min",
    "time",
    "fade",
]

PARTICLE_NAME_BAD_PREFIXES = (
    "m_",
    "$",
    "c_",
    "op_",
    "init_",
    "render_",
)


def pause():
    input("\nPress Enter to exit...")


def norm(s: str) -> str:
    s = str(s)
    s = s.replace("\\", "/")
    s = s.strip().strip('"').strip("'").lower()
    s = s.lstrip("/")

    while s.startswith("./"):
        s = s[2:]

    return s


def rel(path: Path, root: Path) -> str:
    return norm(str(path.relative_to(root)))


def has_suffix(path: str, suffixes: list[str]) -> bool:
    path = norm(path)
    return any(path.endswith(suf) for suf in suffixes)


def remove_known_suffix(path: str) -> str:
    path = norm(path)

    for suf in ALL_SUFFIXES:
        if path.endswith(suf):
            return path[:-len(suf)]

    return path


def extract_ascii_strings(data: bytes):
    for m in re.finditer(rb"[\x20-\x7E]{3,350}", data):
        yield m.group(0).decode("latin-1", errors="ignore")


def extract_utf16le_strings(data: bytes):
    pattern = rb"(?:[\x20-\x7E]\x00){3,350}"

    for m in re.finditer(pattern, data):
        try:
            yield m.group(0).decode("utf-16le", errors="ignore")
        except Exception:
            pass


def extract_all_strings(path: Path):
    try:
        data = path.read_bytes()
    except Exception:
        return []

    strings = set()
    strings.update(extract_ascii_strings(data))
    strings.update(extract_utf16le_strings(data))

    return list(strings)



def is_likely_particle_system_name(value: str) -> bool:
    """
    Checks whether a readable string extracted from a PCF binary is likely to be a particle system name.
    This is not a full PCF parser; it uses safe heuristics over readable strings.
    """
    raw = str(value).strip().strip('"').strip("'")

    if not raw:
        return False

    if "/" in raw or "\\" in raw:
        return False

    if "." in raw:
        return False

    if len(raw) < 3 or len(raw) > 96:
        return False

    if not re.fullmatch(r"[A-Za-z0-9_\-:]+", raw):
        return False

    low = raw.lower()

    if low in PARTICLE_NAME_EXCLUDE:
        return False

    if low.startswith(PARTICLE_NAME_BAD_PREFIXES):
        return False

    if any(fragment in low for fragment in PARTICLE_NAME_BAD_FRAGMENTS):
        return False

    # Purely numeric values are not particle system names.
    if low.replace("-", "").replace("_", "").isdigit():
        return False

    return True


def extract_particle_system_names_from_pcf(pcf_path: Path):
    """
    Attempts to extract particle system names from a PCF file.
    The manifest stores both the raw names and PrecacheParticleSystem lines.
    """
    names = set()

    for s in extract_all_strings(pcf_path):
        candidate = str(s).strip().strip('"').strip("'")

        if is_likely_particle_system_name(candidate):
            names.add(candidate)

    return sorted(names, key=lambda x: x.lower())

def add_alias(alias_map: dict, alias: str, asset: str):
    alias = norm(alias)

    if not alias:
        return

    if alias not in alias_map:
        alias_map[alias] = set()

    alias_map[alias].add(asset)


def build_asset_index(root: Path | None, prefix: str, kind: str):
    alias_map = {}
    all_assets = set()

    if root is None or not root.exists():
        return alias_map, all_assets

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        r = rel(path, root)

        if kind == "materials" and not has_suffix(r, MATERIAL_SUFFIXES):
            continue

        if kind == "models" and not has_suffix(r, MODEL_SUFFIXES):
            continue

        if kind == "sound" and not has_suffix(r, SOUND_SUFFIXES):
            continue

        asset = f"{prefix}/{r}"
        all_assets.add(asset)

        add_alias(alias_map, r, asset)
        add_alias(alias_map, f"{prefix}/{r}", asset)

        if prefix == "sound":
            add_alias(alias_map, f"sounds/{r}", asset)

        no_ext = remove_known_suffix(r)

        if no_ext != r:
            if kind in {"materials", "sound"}:
                add_alias(alias_map, no_ext, asset)
                add_alias(alias_map, f"{prefix}/{no_ext}", asset)

                if prefix == "sound":
                    add_alias(alias_map, f"sounds/{no_ext}", asset)

            if kind == "models" and r.endswith(".mdl"):
                add_alias(alias_map, no_ext, asset)
                add_alias(alias_map, f"{prefix}/{no_ext}", asset)

    return alias_map, all_assets


def tokenize_string(s: str):
    s = norm(s)
    tokens = set()

    for m in re.findall(r"[a-z0-9_\-./\\]+", s, flags=re.I):
        t = norm(m)
        t = t.strip(".")

        if not t:
            continue

        if "/" not in t and not has_suffix(t, ALL_SUFFIXES):
            continue

        tokens.add(t)

    return tokens


def expand_token(token: str):
    token = norm(token)

    candidates = set()
    candidates.add(token)

    prefixes = [
        "materials/",
        "models/",
        "sound/",
        "sounds/",
    ]

    stripped_versions = {token}

    for p in prefixes:
        if token.startswith(p):
            stripped_versions.add(token[len(p):])

    for item in list(stripped_versions):
        item = norm(item)

        no_ext = remove_known_suffix(item)

        candidates.add(item)
        candidates.add(no_ext)

        candidates.add("materials/" + item)
        candidates.add("models/" + item)
        candidates.add("sound/" + item)
        candidates.add("sounds/" + item)

        candidates.add("materials/" + no_ext)
        candidates.add("models/" + no_ext)
        candidates.add("sound/" + no_ext)
        candidates.add("sounds/" + no_ext)

    return {norm(x) for x in candidates if x}


def find_assets_used_in_file(path: Path, alias_maps: dict):
    found = {
        "materials": set(),
        "models": set(),
        "sound": set(),
    }

    strings = extract_all_strings(path)

    for s in strings:
        tokens = tokenize_string(s)

        for token in tokens:
            candidates = expand_token(token)

            for kind, alias_map in alias_maps.items():
                for c in candidates:
                    if c in alias_map:
                        found[kind] |= alias_map[c]

    return found


def parse_vmt_dependencies(vmt_asset: str, materials_root: Path | None, material_alias_map: dict, all_materials: set):
    used = set()

    if materials_root is None:
        return used

    if not vmt_asset.startswith("materials/"):
        return used

    relative_inside_materials = vmt_asset[len("materials/"):]
    vmt_path = materials_root / relative_inside_materials

    if not vmt_path.exists():
        return used

    try:
        text = vmt_path.read_text(errors="ignore")
    except Exception:
        return used

    for line in text.splitlines():
        line = line.strip()

        if not line or line.startswith("//"):
            continue

        parts = re.findall(r'"([^"]+)"|(\S+)', line)
        flat = [a or b for a, b in parts]

        if len(flat) < 2:
            continue

        key = flat[0].lower()
        value = norm(flat[1])

        if key not in VMT_TEXTURE_KEYS:
            continue

        if value.startswith("materials/"):
            value = value[len("materials/"):]

        value_no_ext = remove_known_suffix(value)

        direct_vtf = "materials/" + value_no_ext + ".vtf"

        if direct_vtf in all_materials:
            used.add(direct_vtf)

        for c in expand_token(value):
            if c in material_alias_map:
                for asset in material_alias_map[c]:
                    if asset.endswith(".vtf"):
                        used.add(asset)

    return used


def add_model_sidecars(model_asset: str, all_models: set):
    used = set()

    if not model_asset.startswith("models/"):
        return used

    if not model_asset.endswith(".mdl"):
        return used

    base = model_asset[:-4]

    for suf in MODEL_SUFFIXES:
        candidate = base + suf

        if candidate in all_models:
            used.add(candidate)

    return used


def scan_model_for_extra_refs(model_asset: str, models_root: Path | None, alias_maps: dict):
    found = {
        "materials": set(),
        "models": set(),
        "sound": set(),
    }

    if models_root is None:
        return found

    if not model_asset.startswith("models/"):
        return found

    relative_inside_models = model_asset[len("models/"):]
    model_path = models_root / relative_inside_models

    if not model_path.exists():
        return found

    return find_assets_used_in_file(model_path, alias_maps)


def merge_found(total: dict, found: dict):
    for k in total:
        total[k] |= found.get(k, set())


def resolve_dependencies(used_input: dict, roots: dict, alias_maps: dict, all_assets: dict):
    used = {
        "materials": set(used_input["materials"]),
        "models": set(used_input["models"]),
        "sound": set(used_input["sound"]),
    }

    parsed_vmts = set()
    parsed_mdls = set()

    changed = True

    while changed:
        changed = False

        new_used = {
            "materials": set(),
            "models": set(),
            "sound": set(),
        }

        for item in list(used["materials"]):
            if item.endswith(".vmt") and item not in parsed_vmts:
                parsed_vmts.add(item)

                deps = parse_vmt_dependencies(
                    vmt_asset=item,
                    materials_root=roots["materials"],
                    material_alias_map=alias_maps["materials"],
                    all_materials=all_assets["materials"],
                )

                new_used["materials"] |= deps

        for item in list(used["models"]):
            if item.endswith(".mdl"):
                new_used["models"] |= add_model_sidecars(
                    model_asset=item,
                    all_models=all_assets["models"],
                )

        for item in list(used["models"]):
            if item.endswith(".mdl") and item not in parsed_mdls:
                parsed_mdls.add(item)

                found_inside_model = scan_model_for_extra_refs(
                    model_asset=item,
                    models_root=roots["models"],
                    alias_maps=alias_maps,
                )

                merge_found(new_used, found_inside_model)

        before = sum(len(v) for v in used.values())
        merge_found(used, new_used)
        after = sum(len(v) for v in used.values())

        if after > before:
            changed = True

    return used


def asset_to_file(asset: str, roots: dict):
    if asset.startswith("materials/"):
        root = roots.get("materials")
        rel_path = asset[len("materials/"):]
        return root / rel_path if root else None

    if asset.startswith("models/"):
        root = roots.get("models")
        rel_path = asset[len("models/"):]
        return root / rel_path if root else None

    if asset.startswith("sound/"):
        root = roots.get("sound")
        rel_path = asset[len("sound/"):]
        return root / rel_path if root else None

    return None


def safe_folder_name_from_pcf(pcf: Path, pcf_root: Path):
    relative = pcf.relative_to(pcf_root).with_suffix("")
    raw = str(relative).replace("\\", "__").replace("/", "__")

    raw = re.sub(r"[^a-zA-Z0-9_\-]+", "_", raw)
    raw = raw.strip("_")

    if not raw:
        raw = pcf.stem

    return raw


def copy_file(src: Path, dst: Path, errors: list):
    try:
        if not src.exists():
            errors.append(f"Not found: {src}")
            return False

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        return True

    except Exception as e:
        errors.append(f"Could not copy: {src} -> {dst} | {e}")
        return False


def copy_asset_to_package(asset: str, roots: dict, package_dir: Path, errors: list):
    src = asset_to_file(asset, roots)

    if src is None:
        errors.append(f"Missing root folder: {asset}")
        return False

    if asset.startswith("materials/"):
        dst = package_dir / asset
    elif asset.startswith("models/"):
        dst = package_dir / asset
    elif asset.startswith("sound/"):
        dst = package_dir / asset
    else:
        errors.append(f"Unknown asset type: {asset}")
        return False

    return copy_file(src, dst, errors)


def write_manifest(package_dir: Path, pcf: Path, pcf_root: Path, used: dict, errors: list):
    manifest = package_dir / "manifest.txt"
    particle_systems = extract_particle_system_names_from_pcf(pcf)

    lines = []
    lines.append("PCF Asset Export Manifest")
    lines.append("=========================")
    lines.append("")
    lines.append(f"PCF: {pcf}")
    lines.append(f"PCF relative: {pcf.relative_to(pcf_root)}")
    lines.append("")

    lines.append(f"[particle_systems] count={len(particle_systems)}")

    for name in particle_systems:
        lines.append(name)

    lines.append("")

    lines.append(f"[precache_lua] count={len(particle_systems)}")

    for name in particle_systems:
        lines.append(f'PrecacheParticleSystem("{name}")')

    lines.append("")

    for kind in ["materials", "models", "sound"]:
        lines.append(f"[{kind}] count={len(used[kind])}")

        for asset in sorted(used[kind]):
            lines.append(asset)

        lines.append("")

    if errors:
        lines.append("[errors]")

        for err in errors:
            lines.append(err)

        lines.append("")

    manifest.write_text("\n".join(lines), encoding="utf-8")


def export_one_pcf(pcf: Path, pcf_root: Path, output_root: Path, roots: dict, alias_maps: dict, all_assets: dict):
    direct_used = find_assets_used_in_file(pcf, alias_maps)
    used = resolve_dependencies(direct_used, roots, alias_maps, all_assets)

    folder_name = safe_folder_name_from_pcf(pcf, pcf_root)
    package_dir = output_root / folder_name

    errors = []

    # Copy the PCF file into the package as well.
    pcf_dst = package_dir / "particles" / pcf.relative_to(pcf_root)
    copy_file(pcf, pcf_dst, errors)

    for kind in ["materials", "models", "sound"]:
        for asset in sorted(used[kind]):
            copy_asset_to_package(asset, roots, package_dir, errors)

    write_manifest(package_dir, pcf, pcf_root, used, errors)

    return package_dir, used, errors



def build_indexes(roots: dict):
    alias_maps = {
        "materials": {},
        "models": {},
        "sound": {},
    }

    all_assets = {
        "materials": set(),
        "models": set(),
        "sound": set(),
    }

    if roots.get("materials"):
        alias_maps["materials"], all_assets["materials"] = build_asset_index(
            root=roots["materials"],
            prefix="materials",
            kind="materials",
        )

    if roots.get("models"):
        alias_maps["models"], all_assets["models"] = build_asset_index(
            root=roots["models"],
            prefix="models",
            kind="models",
        )

    if roots.get("sound"):
        alias_maps["sound"], all_assets["sound"] = build_asset_index(
            root=roots["sound"],
            prefix="sound",
            kind="sound",
        )

    return alias_maps, all_assets


def print_index_summary(all_assets: dict):
    print("\n========== INDEX ==========")
    print(f"Material files: {len(all_assets['materials'])}")
    print(f"Model files: {len(all_assets['models'])}")
    print(f"Sound files: {len(all_assets['sound'])}")


def empty_used_dict():
    return {
        "materials": set(),
        "models": set(),
        "sound": set(),
    }


def collect_used_for_all_pcfs(pcfs: list[Path], roots: dict, alias_maps: dict, all_assets: dict):
    """
    Collects all assets used by all PCF files into one shared pool.
    Used by Mode 2 / Workshop export.
    """
    total_used = empty_used_dict()
    per_pcf_results = []

    for pcf in pcfs:
        direct_used = find_assets_used_in_file(pcf, alias_maps)
        used = resolve_dependencies(direct_used, roots, alias_maps, all_assets)
        merge_found(total_used, used)
        per_pcf_results.append((pcf, used))

    return total_used, per_pcf_results


def export_workshop_bundle(pcfs: list[Path], pcf_root: Path, output_root: Path, roots: dict, alias_maps: dict, all_assets: dict):
    """
    Collects all PCF files and their used assets into one addon/workshop folder.

    Example output:
    output_root/
      particles/
      materials/
      models/
      sound/

    This mode does not create manifests.
    """
    errors = []
    used_total, per_pcf_results = collect_used_for_all_pcfs(
        pcfs=pcfs,
        roots=roots,
        alias_maps=alias_maps,
        all_assets=all_assets,
    )

    # Copy all PCF files into the shared particles folder inside the workshop output.
    for pcf in pcfs:
        dst = output_root / "particles" / pcf.relative_to(pcf_root)
        copy_file(pcf, dst, errors)

    # Copy every shared used asset into one materials/models/sound structure.
    for kind in ["materials", "models", "sound"]:
        for asset in sorted(used_total[kind]):
            copy_asset_to_package(asset, roots, output_root, errors)

    return used_total, per_pcf_results, errors


def ask_export_mode():
    print("\nChoose export mode:")
    print("1 - Separate folder per PCF + manifest.txt + PrecacheParticleSystem list")
    print("2 - Workshop/addon mode: one folder, shared particles/materials/models/sound, no manifest")

    while True:
        choice = input("\nChoice [1/2]: ").strip()

        if choice in {"1", "2"}:
            return choice

        print("[ERROR] Please enter 1 or 2.")


def ask_path(title: str, required: bool = False):
    while True:
        value = input(title).strip().strip('"')

        if not value and not required:
            return None

        if not value and required:
            print("[ERROR] This field cannot be empty.")
            continue

        path = Path(value).resolve()

        if not path.exists():
            print(f"[ERROR] Folder not found: {path}")
            continue

        if not path.is_dir():
            print(f"[ERROR] This is not a folder: {path}")
            continue

        return path


def main():
    os.system("title GMod PCF Asset Exporter")

    print("========================================")
    print("        GMod PCF Asset Exporter")
    print("========================================")
    print()
    print("Exports PCF assets in two different modes.")
    print("Mode 1: Separate package per PCF + manifest.")
    print("Mode 2: One folder for workshop/addon upload structure.")
    print("Does not touch original files; it only copies them.")
    print()

    mode = ask_export_mode()

    print()
    pcf_root = ask_path("Enter the PCF folder path: ", required=True)

    print()
    materials_root = ask_path("Enter the materials folder path, or leave empty: ", required=False)
    models_root = ask_path("Enter the models folder path, or leave empty: ", required=False)
    sound_root = ask_path("Enter the sound folder path, or leave empty: ", required=False)

    if mode == "1":
        default_output = pcf_root.parent / "__pcf_asset_exports_by_pcf"
    else:
        default_output = pcf_root.parent / "__pcf_workshop_export"

    print()
    output_value = input(f"Output folder [{default_output}]: ").strip().strip('"')

    if output_value:
        output_root = Path(output_value).resolve()
    else:
        output_root = default_output

    output_root.mkdir(parents=True, exist_ok=True)

    roots = {
        "materials": materials_root,
        "models": models_root,
        "sound": sound_root,
    }

    print("\nBuilding asset index...")
    alias_maps, all_assets = build_indexes(roots)
    print_index_summary(all_assets)

    pcfs = sorted(pcf_root.rglob("*.pcf"))

    print("\n========== PCF ==========")
    print(f"Found PCF files: {len(pcfs)}")

    if not pcfs:
        print("\n[ERROR] No PCF files were found in this folder.")
        pause()
        return

    if mode == "1":
        print("\nStarting Mode 1 export...")
        print("Each PCF will be exported into a separate folder and a manifest.txt file will be created.")

        total_used = {
            "materials": 0,
            "models": 0,
            "sound": 0,
        }

        total_errors = 0

        for pcf in pcfs:
            package_dir, used, errors = export_one_pcf(
                pcf=pcf,
                pcf_root=pcf_root,
                output_root=output_root,
                roots=roots,
                alias_maps=alias_maps,
                all_assets=all_assets,
            )

            particle_systems = extract_particle_system_names_from_pcf(pcf)

            print()
            print(f"PCF: {pcf.name}")
            print(f"Output: {package_dir}")
            print(f"  particle systems: {len(particle_systems)}")
            print(f"  materials: {len(used['materials'])}")
            print(f"  models: {len(used['models'])}")
            print(f"  sound: {len(used['sound'])}")

            if errors:
                print(f"  warnings/errors: {len(errors)}")
                total_errors += len(errors)

            for kind in total_used:
                total_used[kind] += len(used[kind])

        print("\n========== DONE ==========")
        print(f"Output folder: {output_root}")
        print()
        print("Example generated structure:")
        print("pcf_name/")
        print("  particles/")
        print("  materials/")
        print("  models/")
        print("  sound/")
        print("  manifest.txt")

        if total_errors:
            print(f"\nTotal warnings/errors: {total_errors}")

    else:
        print("\nStarting Mode 2 export...")
        print("All PCF files and their used assets will be collected into one workshop/addon folder.")
        print("This mode does not create manifest.txt files.")

        used_total, per_pcf_results, errors = export_workshop_bundle(
            pcfs=pcfs,
            pcf_root=pcf_root,
            output_root=output_root,
            roots=roots,
            alias_maps=alias_maps,
            all_assets=all_assets,
        )

        print("\n========== DONE ==========")
        print(f"Output folder: {output_root}")
        print()
        print("Workshop/addon structure:")
        print("particles/")
        print("materials/")
        print("models/")
        print("sound/")
        print()
        print("Collected file counts:")
        print(f"  PCF: {len(pcfs)}")
        print(f"  materials: {len(used_total['materials'])}")
        print(f"  models: {len(used_total['models'])}")
        print(f"  sound: {len(used_total['sound'])}")

        if errors:
            print(f"\nWarning/error count: {len(errors)}")
            print("First warnings:")
            for err in errors[:20]:
                print("  -", err)

        print("\nYou can use this folder as the base structure for addon/workshop upload.")

    pause()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\nUnexpected error:")
        print(e)
        pause()
