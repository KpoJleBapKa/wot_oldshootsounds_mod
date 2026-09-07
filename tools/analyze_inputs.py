import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

from bwxml import decode, find_matching_values, find_sound_records


ASSET_SUFFIXES = {".bnk", ".wem", ".pck", ".xml"}
VERSION_PATTERN = re.compile(r"<version>\s*([^<]+?)\s*</version>")


def sha256_stream(stream):
    digest = hashlib.sha256()
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            return digest.hexdigest().upper()
        digest.update(chunk)


def sha256_file(path):
    with path.open("rb") as stream:
        return sha256_stream(stream)


def read_version(root):
    content = (root / "version.xml").read_text(encoding="utf-8-sig")
    match = VERSION_PATTERN.search(content)
    if not match:
        raise ValueError(f"Version not found in {root / 'version.xml'}")
    return match.group(1).strip()


def inventory_loose_assets(root, version):
    audio_root = root / "res" / "audioww"
    assets = []
    for path in sorted(audio_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in ASSET_SUFFIXES:
            assets.append({
                "client_version": version,
                "filename": path.name,
                "full_path": str(path.resolve()),
                "source": "loose",
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    return assets


def inventory_package_assets(root, version):
    package_root = root / "res" / "packages"
    assets = []
    packages = []
    for path in sorted(package_root.glob("audioww*.pkg")):
        package = {
            "client_version": version,
            "filename": path.name,
            "full_path": str(path.resolve()),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        packages.append(package)
        with zipfile.ZipFile(path) as archive:
            for entry in sorted(archive.infolist(), key=lambda item: item.filename):
                suffix = Path(entry.filename).suffix.lower()
                if entry.is_dir() or suffix not in ASSET_SUFFIXES:
                    continue
                with archive.open(entry) as stream:
                    digest = sha256_stream(stream)
                assets.append({
                    "client_version": version,
                    "filename": Path(entry.filename).name,
                    "full_path": f"{path.resolve()}!/{entry.filename}",
                    "source": "package",
                    "source_package": path.name,
                    "size": entry.file_size,
                    "sha256": digest,
                })
        print(f"Inventoried {path.name}", flush=True)
    return assets, packages


def vehicle_records(root):
    scripts_path = root / "res" / "packages" / "scripts.pkg"
    records = {}
    with zipfile.ZipFile(scripts_path) as archive:
        for entry in archive.infolist():
            parts = Path(entry.filename).parts
            if len(parts) != 5 or parts[:3] != ("scripts", "item_defs", "vehicles") or not entry.filename.endswith(".xml"):
                continue
            data = archive.read(entry)
            document = decode(data)
            vehicle_sounds = find_sound_records(document)
            gun_shot_sounds = find_matching_values(document, lambda value: value.startswith("shot_"))
            sounds = sorted({record["value"] for record in gun_shot_sounds})
            vehicle_id = f"{parts[3]}/{Path(parts[4]).stem}"
            records[vehicle_id] = {
                "id": vehicle_id,
                "nation": parts[3],
                "name": Path(parts[4]).stem,
                "source": entry.filename,
                "shot_sound_tokens": sounds,
                "gun_shot_sounds": gun_shot_sounds,
                "vehicle_sounds": vehicle_sounds,
            }
    return records


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    project_root = Path(__file__).resolve().parents[1]
    sides = {
        "old": project_root / "OLD_WOT_ROOT",
        "current": project_root / "CURRENT_WOT_ROOT",
    }
    inventory = {"clients": {}, "assets": [], "packages": []}
    vehicles = {}
    for side, root in sides.items():
        version = read_version(root)
        inventory["clients"][side] = {"root": str(root.resolve()), "version": version}
        inventory["assets"].extend(inventory_loose_assets(root, version))
        assets, packages = inventory_package_assets(root, version)
        inventory["assets"].extend(assets)
        inventory["packages"].extend(packages)
        vehicles[side] = vehicle_records(root)
    old_ids = set(vehicles["old"])
    current_ids = set(vehicles["current"])
    old_vehicles = [vehicles["old"][key] for key in sorted(old_ids)]
    new_vehicles = [vehicles["current"][key] for key in sorted(current_ids - old_ids)]
    retained_vehicles = []
    for key in sorted(old_ids & current_ids):
        retained_vehicles.append({
            "id": key,
            "old": vehicles["old"][key],
            "current": vehicles["current"][key],
        })
    write_json(project_root / "inventory" / "sound_assets.json", inventory)
    write_json(project_root / "mapping" / "old_vehicles.json", old_vehicles)
    write_json(project_root / "mapping" / "new_vehicles.json", new_vehicles)
    write_json(project_root / "mapping" / "retained_vehicles.json", retained_vehicles)
    print(f"Old vehicles: {len(old_vehicles)}")
    print(f"Retained vehicles: {len(retained_vehicles)}")
    print(f"New vehicles: {len(new_vehicles)}")
    print(f"Audio assets: {len(inventory['assets'])}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise
