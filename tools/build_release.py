import argparse
import shutil
import subprocess
import zipfile
from pathlib import Path


def run(command):
    subprocess.run([str(value) for value in command], check=True)


def build(args):
    project_root = Path(__file__).resolve().parents[1]
    source_mods = project_root / "src" / "scripts" / "client" / "gui" / "mods"
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
    shutil.copy2(project_root / "src" / "audioww" / "oldshoot.bnk", payload_audio)
    for compiled_file in compiled.glob("*.pyc"):
        shutil.copy2(compiled_file, payload_mods)
    readme = "Double-click Install-OldShootSounds.cmd and select the World of Tanks root folder.\n\nThe installer detects the active res_mods version from paths.xml and merges oldshoot.bnk into audio_mods.xml.\n"
    (release_root / "README.txt").write_text(readme, encoding="utf-8")
    archive_path = project_root / "dist" / "OldShootSounds.zip"
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(release_root.rglob("*")):
            if path.is_file():
                archive.write(path, Path("OldShootSounds") / path.relative_to(release_root))
    print("Release: {}".format(release_root))
    print("Archive: {}".format(archive_path))
    print("Size: {}".format(archive_path.stat().st_size))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python2", required=True)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
