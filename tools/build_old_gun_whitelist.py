import json
import pprint
from pathlib import Path


def gun_location(path):
    marker = "/guns/"
    if marker not in path:
        return None
    for suffix in ("/effects", "/multiGunEffects"):
        if path.endswith(suffix):
            prefix, gun = path.split(marker, 1)
            return prefix.rsplit("/", 1)[-1], gun[:-len(suffix)]
    return None


def gun_mode(path):
    return "multi" if path.endswith("/multiGunEffects") else "single"


def effect_events(calibers):
    result = {}
    for category in calibers:
        if not category["old"] or not category["current"]:
            continue
        old_record = category["old"][0]
        current_record = category["current"][0]
        if not old_record["player_events"] or not old_record["npc_events"]:
            continue
        result[category["effect"]] = {
            "origin": category["effect"],
            "player_event": old_record["player_events"][0],
            "npc_event": old_record["npc_events"][0],
            "current_player_event": current_record["player_events"][0],
            "current_npc_event": current_record["npc_events"][0],
        }
    return result


def build(project_root):
    retained = json.loads((project_root / "mapping" / "retained_vehicles.json").read_text(encoding="utf-8"))
    calibers = json.loads((project_root / "mapping" / "calibers.json").read_text(encoding="utf-8"))
    events = effect_events(calibers)
    vehicles = {}
    used_effects = set()
    conflicts = []
    for record in retained:
        vehicle_key = record["id"].replace("/", ":", 1)
        turrets = {}
        for gun_record in record["old"]["gun_shot_sounds"]:
            location = gun_location(gun_record["path"])
            mode = gun_mode(gun_record["path"])
            effects = gun_record["value"].split() if mode == "multi" else [gun_record["value"]]
            if location is None or not any(effect in events for effect in effects):
                continue
            turret_name, gun_name = location
            effect_values = []
            for effect in effects:
                event_data = events.get(effect)
                effect_values.append({
                    "effect": effect,
                    "player_event": "oldshoot_" + event_data["player_event"].lower() if event_data is not None else None,
                    "npc_event": "oldshoot_" + event_data["npc_event"].lower() if event_data is not None else None,
                })
                if event_data is not None:
                    used_effects.add(effect)
            value = {"mode": mode, "effects": effect_values}
            guns = turrets.setdefault(turret_name, {})
            previous = guns.get(gun_name)
            if previous is not None and previous["mode"] == "multi" and mode == "single":
                continue
            if previous is not None and previous["mode"] == "single" and mode == "multi":
                guns[gun_name] = value
                continue
            previous_events = tuple((item["player_event"], item["npc_event"]) for item in previous["effects"]) if previous is not None else None
            current_events = tuple((item["player_event"], item["npc_event"]) for item in value["effects"])
            if previous is not None and previous_events != current_events:
                conflicts.append({"vehicle": vehicle_key, "turret": turret_name, "gun": gun_name, "effects": sorted({item["effect"] for item in previous["effects"] + value["effects"]})})
                continue
            guns[gun_name] = value
        if turrets:
            vehicles[vehicle_key] = {turret: dict(sorted(guns.items())) for turret, guns in sorted(turrets.items())}
    effect_records = {}
    for effect in sorted(used_effects):
        data = events[effect]
        effect_records[effect] = {
            "origin": data["origin"],
            "player_event": "oldshoot_" + data["player_event"].lower(),
            "npc_event": "oldshoot_" + data["npc_event"].lower(),
            "source_player_event": data["player_event"],
            "source_npc_event": data["npc_event"],
        }
    return {
        "source_version": "1.29.1.1 #721",
        "target_version": "2.4.0.0 #935",
        "vehicle_count": len(vehicles),
        "gun_count": sum(len(guns) for turrets in vehicles.values() for guns in turrets.values()),
        "effect_count": len(effect_records),
        "effects": effect_records,
        "vehicles": dict(sorted(vehicles.items())),
        "conflicts": conflicts,
    }


def sound_event_injector_config(whitelist):
    gun_effects = {}
    for effect, data in whitelist["effects"].items():
        gun_effects["oldshoot_" + effect] = {
            "origin": data["origin"],
            "effects": {
                "shotSound": {
                    "wwsoundPC": [data["player_event"]],
                    "wwsoundNPC": [data["npc_event"]],
                }
            },
        }
    guns = {}
    for vehicle, vehicle_turrets in whitelist["vehicles"].items():
        guns[vehicle] = {}
        for turret, vehicle_guns in vehicle_turrets.items():
            for gun, data in vehicle_guns.items():
                key = turret + "/" + gun
                if data["mode"] == "single":
                    guns[vehicle][key] = {"effects": "oldshoot_" + data["effects"][0]["effect"]}
                else:
                    guns[vehicle][key] = {
                        "multiGunEffects": ["oldshoot_" + item["effect"] if item["player_event"] is not None else item["effect"] for item in data["effects"]]
                    }
    return {"gun_effects": gun_effects, "guns": guns}


def runtime_data(whitelist):
    result = {}
    for vehicle, turrets in whitelist["vehicles"].items():
        result[vehicle] = {}
        for turret, guns in turrets.items():
            result[vehicle][turret] = {}
            for gun, data in guns.items():
                if data["mode"] == "single":
                    effect = data["effects"][0]
                    result[vehicle][turret][gun] = (effect["player_event"], effect["npc_event"])
                else:
                    result[vehicle][turret][gun] = {
                        "multi": tuple((effect["effect"], effect["player_event"], effect["npc_event"]) for effect in data["effects"])
                    }
    return result


def main():
    project_root = Path(__file__).resolve().parents[1]
    whitelist = build(project_root)
    injector_config = sound_event_injector_config(whitelist)
    runtime = runtime_data(whitelist)
    mapping_root = project_root / "mapping"
    source_root = project_root / "src" / "configs"
    source_root.mkdir(parents=True, exist_ok=True)
    (mapping_root / "old_vehicle_guns.json").write_text(json.dumps(whitelist, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    (source_root / "oldshoot_guns.json").write_text(json.dumps(injector_config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    runtime_root = project_root / "src" / "scripts" / "client" / "gui" / "mods"
    runtime_root.mkdir(parents=True, exist_ok=True)
    runtime_source = "VEHICLE_GUN_EVENTS = " + pprint.pformat(runtime, width=200, sort_dicts=True) + "\n"
    (runtime_root / "oldshoot_data.py").write_text(runtime_source, encoding="utf-8")
    print("Vehicles: {}".format(whitelist["vehicle_count"]))
    print("Guns: {}".format(whitelist["gun_count"]))
    print("Effects: {}".format(whitelist["effect_count"]))
    print("Conflicts: {}".format(len(whitelist["conflicts"])))


if __name__ == "__main__":
    main()
