import json
import re
import subprocess
from pathlib import Path


FIELD_PATTERNS = {
    "sample_rate": re.compile(r"^sample rate: (\d+) Hz$", re.MULTILINE),
    "channels": re.compile(r"^channels: (\d+)$", re.MULTILINE),
    "duration_seconds": re.compile(r"^stream total samples: \d+ \((?:\d+:)?([0-9.]+) seconds\)$", re.MULTILINE),
    "codec": re.compile(r"^encoding: (.+)$", re.MULTILINE),
}


def metadata(executable, path):
    result = subprocess.run([str(executable), "-m", str(path)], capture_output=True, text=True, check=True)
    values = {}
    for field, pattern in FIELD_PATTERNS.items():
        match = pattern.search(result.stdout)
        values[field] = match.group(1) if match else None
    if values["sample_rate"] is not None:
        values["sample_rate"] = int(values["sample_rate"])
    if values["channels"] is not None:
        values["channels"] = int(values["channels"])
    if values["duration_seconds"] is not None:
        values["duration_seconds"] = float(values["duration_seconds"])
    return values


def main():
    project_root = Path(__file__).resolve().parents[1]
    executable = project_root / "tools" / "vendor" / "vgmstream" / "vgmstream-cli.exe"
    media_root = project_root / "work" / "media"
    records = []
    for path in sorted(media_root.rglob("*.wem")):
        relative = path.relative_to(media_root)
        side, event, action, filename = relative.parts
        record = {
            "side": side,
            "event": event,
            "action_id": int(action),
            "wem_id": int(path.stem),
            "path": str(path.resolve()),
            "size": path.stat().st_size,
        }
        record.update(metadata(executable, path))
        records.append(record)
    output = project_root / "inventory" / "wem_sources.json"
    output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"WEM records: {len(records)}")


if __name__ == "__main__":
    main()
