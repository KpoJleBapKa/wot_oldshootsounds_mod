import json
import zipfile
from pathlib import Path

from bwxml import decode, find_sound_records


def wwise_hash(name):
    value = 2166136261
    for byte in name.lower().encode("utf-8"):
        value = ((value * 16777619) & 0xFFFFFFFF) ^ byte
    return value


def read_effects(root):
    package = root / "res" / "packages" / "scripts.pkg"
    source = "scripts/item_defs/vehicles/common/gun_effects.xml"
    with zipfile.ZipFile(package) as archive:
        document = decode(archive.read(source))
    records = []
    for record in find_sound_records(document):
        if not record["path"].startswith("shot_"):
            continue
        records.append({
            "effect": record["path"].split("/", 1)[0],
            "path": record["path"],
            "player_events": [event for event in record["wwsoundPC"] if isinstance(event, str)],
            "npc_events": [event for event in record["wwsoundNPC"] if isinstance(event, str)],
        })
    return records


def main():
    project_root = Path(__file__).resolve().parents[1]
    roots = {
        "old": project_root / "OLD_WOT_ROOT",
        "current": project_root / "CURRENT_WOT_ROOT",
    }
    effects = {side: read_effects(root) for side, root in roots.items()}
    current_events = {}
    for record in effects["current"]:
        for purpose, field in (("player gunshot", "player_events"), ("other tank gunshot", "npc_events")):
            for event in record[field]:
                current_events[event] = {
                    "event_id": wwise_hash(event),
                    "event_name": event,
                    "purpose": purpose,
                    "source": "CURRENT_WOT_ROOT/res/packages/scripts.pkg!/scripts/item_defs/vehicles/common/gun_effects.xml",
                }
    categories = {}
    for side, records in effects.items():
        for record in records:
            category = categories.setdefault(record["effect"], {"effect": record["effect"], "old": [], "current": []})
            category[side].append(record)
    mapping_root = project_root / "mapping"
    mapping_root.mkdir(parents=True, exist_ok=True)
    (mapping_root / "gun_events.json").write_text(json.dumps(sorted(current_events.values(), key=lambda item: item["event_name"]), indent=2) + "\n", encoding="utf-8")
    (mapping_root / "calibers.json").write_text(json.dumps(sorted(categories.values(), key=lambda item: item["effect"]), indent=2) + "\n", encoding="utf-8")
    print(f"Old gun effect records: {len(effects['old'])}")
    print(f"Current gun effect records: {len(effects['current'])}")
    print(f"Current firing events: {len(current_events)}")
    print(f"Gun effect categories: {len(categories)}")


if __name__ == "__main__":
    main()
