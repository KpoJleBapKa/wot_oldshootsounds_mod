import argparse
import shutil
import subprocess
import zipfile
from pathlib import Path

from mod_version import read_version, sync_version_file


def run(command):
    subprocess.run([str(value) for value in command], check=True)


def sync_runtime_version(path, version):
    content = path.read_text(encoding="utf-8")
    version_line = "MOD_VERSION = {!r}".format(version)
    if content.startswith("MOD_VERSION = "):
        content = version_line + content[content.find("\n"):]
    else:
        content = version_line + "\n\n" + content
    path.write_bytes(content.encode("utf-8"))


def build_wgmods_materials(project_root, version):
    source_root = project_root / "wgmods"
    target_root = project_root / "dist" / "WGMods"
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True)
    for source in source_root.glob("*.md"):
        content = source.read_text(encoding="utf-8").replace("<MOD_VERSION>", version)
        (target_root / source.name).write_bytes(content.encode("utf-8"))
    return target_root


def build(args):
    project_root = Path(__file__).resolve().parents[1]
    version = read_version(project_root)
    sync_version_file(project_root, version)
    source_mods = project_root / "src" / "scripts" / "client" / "gui" / "mods"
    sync_runtime_version(source_mods / "oldshoot_data.py", version)
    compiler = project_root / "tools" / "compile_py2.py"
    compiled = project_root / "work" / "compiled"
    compiled.mkdir(parents=True, exist_ok=True)
    runtime_path = "scripts/client/gui/mods/{}"
    for name in ("mod_oldshoot.py", "oldshoot_data.py"):
        destination = compiled / (name + "c")
        run([args.python2, "-S", compiler, source_mods / name, destination, runtime_path.format(name)])
    release_root = project_root / "dist" / "OldShootSounds"
    if release_root.exists():
        shutil.rmtree(release_root)
    payload_mods = release_root / "payload" / "scripts" / "client" / "gui" / "mods"
    payload_audio = release_root / "payload" / "audioww"
    payload_mods.mkdir(parents=True)
    payload_audio.mkdir(parents=True)
    shutil.copy2(project_root / "installer" / "Install-OldShootSounds.ps1", release_root)
    shutil.copy2(project_root / "installer" / "Install-OldShootSounds.cmd", release_root)
    shutil.copy2(project_root / "installer" / "README.txt", release_root)
    shutil.copy2(project_root / "VERSION", release_root)
    shutil.copy2(project_root / "src" / "audioww" / "oldshoot.bnk", payload_audio)
    for compiled_file in compiled.glob("*.pyc"):
        shutil.copy2(compiled_file, payload_mods)
    archive_path = project_root / "dist" / "OldShootSounds-{}.zip".format(version)
    legacy_archive_path = project_root / "dist" / "OldShootSounds.zip"
    if legacy_archive_path.exists():
        legacy_archive_path.unlink()
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(release_root.rglob("*")):
            if path.is_file():
                archive.write(path, Path("OldShootSounds") / path.relative_to(release_root))
    wgmods_root = build_wgmods_materials(project_root, version)
    print("Version: {}".format(version))
    print("Release: {}".format(release_root))
    print("Archive: {}".format(archive_path))
    print("WGMods: {}".format(wgmods_root))
    print("Size: {}".format(archive_path.stat().st_size))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python2", required=True)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
