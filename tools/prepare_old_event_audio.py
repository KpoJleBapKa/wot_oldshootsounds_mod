import argparse
import json
import re
import subprocess
from pathlib import Path

from extract_event_media import bnk_entries, pck_entries


WEM_PATTERN = re.compile(r"\bwem/(\d+)\.wem\b")
RANDOM_PATTERN = re.compile(r"(group\s*=\s*-R(\d+)>)(\d+)")


def source_events(project_root):
    whitelist = json.loads((project_root / "mapping" / "old_vehicle_guns.json").read_text(encoding="utf-8"))
    result = set()
    for effect in whitelist["effects"].values():
        result.add(effect["source_player_event"])
        result.add(effect["source_npc_event"])
    canonical = {}
    for event in result:
        canonical.setdefault(event.lower(), event)
    return [canonical[key] for key in sorted(canonical)]


def matching_txtp(txtp_root, event):
    prefix = event.lower() + " "
    return sorted(path for path in txtp_root.glob("*.txtp") if path.name.lower().startswith(prefix))


def extract_media(txtp_paths, pck_path, bnk_path, wem_root):
    source_ids = set()
    for path in txtp_paths:
        source_ids.update(int(value) for value in WEM_PATTERN.findall(path.read_text(encoding="utf-8")))
    packed = pck_entries(pck_path)
    embedded = bnk_entries(bnk_path)
    wem_root.mkdir(parents=True, exist_ok=True)
    extracted = 0
    with pck_path.open("rb") as stream:
        for source_id in sorted(source_ids):
            destination = wem_root / (str(source_id) + ".wem")
            if source_id in packed:
                entry = packed[source_id]
                stream.seek(entry["offset"])
                destination.write_bytes(stream.read(entry["size"]))
                extracted += 1
            elif source_id in embedded:
                destination.write_bytes(embedded[source_id]["data"])
                extracted += 1
    missing = sorted(source_ids - set(packed) - set(embedded))
    return len(source_ids), extracted, missing


def render(vgmstream, event_paths, output_root, variants):
    records = []
    for event, paths in event_paths.items():
        event_root = output_root / ("oldshoot_" + event.lower())
        event_root.mkdir(parents=True, exist_ok=True)
        for branch, txtp_path in enumerate(paths, 1):
            for variant in range(1, variants + 1):
                output = event_root / ("branch_{:02d}_variant_{:02d}.wav".format(branch, variant))
                random_index = [0]

                def select_random(match):
                    count = int(match.group(2))
                    choice = ((variant - 1) + random_index[0] * 3) % count + 1
                    random_index[0] += 1
                    return match.group(1) + str(choice)

                variant_txtp = txtp_path.with_name("__oldshoot_render.txtp")
                variant_txtp.write_text(RANDOM_PATTERN.sub(select_random, txtp_path.read_text(encoding="utf-8")), encoding="utf-8")
                process = subprocess.run([str(vgmstream), "-i", "-o", str(output), str(variant_txtp)], capture_output=True, text=True)
                variant_txtp.unlink(missing_ok=True)
                if process.returncode != 0:
                    raise RuntimeError("Failed to render {}: {}".format(txtp_path, process.stderr.strip()))
                records.append({
                    "event": "oldshoot_" + event.lower(),
                    "source_event": event,
                    "branch": branch,
                    "variant": variant,
                    "txtp": str(txtp_path),
                    "wav": str(output),
                    "size": output.stat().st_size,
                })
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", type=int, default=3)
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    txtp_root = project_root / "work" / "txtp" / "old_all"
    events = source_events(project_root)
    event_paths = {event: matching_txtp(txtp_root, event) for event in events}
    missing_events = [event for event, paths in event_paths.items() if not paths]
    if missing_events:
        raise RuntimeError("Missing TXTP events: " + ", ".join(missing_events))
    all_paths = sorted({path for paths in event_paths.values() for path in paths})
    total, extracted, missing = extract_media(
        all_paths,
        project_root / "work" / "banks" / "old" / "wpn.pck",
        project_root / "work" / "banks" / "old" / "wpn.bnk",
        txtp_root / "wem",
    )
    if missing:
        raise RuntimeError("Missing WEM sources: " + ", ".join(str(value) for value in missing))
    output_root = project_root / "work" / "old_event_wav"
    records = render(project_root / "tools" / "vendor" / "vgmstream" / "vgmstream-cli.exe", event_paths, output_root, args.variants)
    manifest = {
        "events": len(event_paths),
        "txtp_branches": len(all_paths),
        "variants_per_branch": args.variants,
        "wem_sources": total,
        "wem_extracted": extracted,
        "renders": records,
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Events: {}".format(len(event_paths)))
    print("TXTP branches: {}".format(len(all_paths)))
    print("WEM sources: {}".format(total))
    print("Rendered WAVs: {}".format(len(records)))


if __name__ == "__main__":
    main()
