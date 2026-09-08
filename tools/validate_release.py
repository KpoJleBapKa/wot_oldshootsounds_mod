import importlib.util
import json
import struct
import sys
import types
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


WOT_HEADER_XOR = {
    8: 0xD2F5B297,
    16: 0xD10C0503,
    20: 0x6B0403D4,
}
WOT_HEADER_VALUES = {
    8: 150,
    16: 393239870,
    20: 16,
}


class Descriptor:
    TYPE = "_ShotSoundEffectDesc"

    def __init__(self):
        self._soundName = (("current_pc",), ("current_npc",))


class EffectList:
    def __init__(self):
        self.value = Descriptor()

    def descriptors(self):
        return [self.value]


class Effects:
    def __init__(self):
        self.effectsList = EffectList()


class Gun:
    def __init__(self, name, effects=None):
        self.name = name
        self.effects = Effects() if effects is None else effects

    def copy(self):
        result = Gun(self.name)
        result.effects = self.effects
        return result


class Turret:
    def __init__(self, name, guns):
        self.name = name
        self.guns = tuple(guns)

    def copy(self):
        return Turret(self.name, self.guns)


class VehicleType:
    def __init__(self, name, turret_name, gun):
        self.name = name
        self.turrets = ((Turret(turret_name, (gun,)),),)


class Cache:
    def __init__(self, vehicles, gun_effects):
        self.vehicles = vehicles
        self.gunEffects = gun_effects

    def getVehicles(self):
        return self.vehicles


class EventHook:
    def __init__(self):
        self.handler = None

    def __iadd__(self, handler):
        self.handler = handler
        return self


class CurrentVehicle:
    def __init__(self):
        self.in_hangar = True

    def isInHangar(self):
        return self.in_hangar


class KeyEvent:
    def __init__(self, key):
        self.key = key


def validate_runtime(project_root, whitelist):
    configurations = []
    for vehicle_name, turrets in whitelist["vehicles"].items():
        for turret_name, guns in turrets.items():
            for gun_name, data in guns.items():
                configurations.append((vehicle_name, turret_name, gun_name, data))
    vehicle_name, turret_name, gun_name, data = next(item for item in configurations if item[3]["mode"] == "single")
    dual_vehicle_name, dual_turret_name, dual_gun_name, dual_data = next(item for item in configurations if item[0] == "ussr:R165_Object_703_II_siege_mode")
    events = data["effects"][0]
    shared_gun = Gun(gun_name)
    dual_gun = Gun(dual_gun_name, [])
    configured_vehicle = VehicleType(vehicle_name, turret_name, shared_gun)
    configured_dual_vehicle = VehicleType(dual_vehicle_name, dual_turret_name, dual_gun)
    untouched_vehicle = VehicleType("newnation:NewVehicle", turret_name, shared_gun)
    gun_effects = {effect["effect"]: Effects() for effect in dual_data["effects"]}
    vehicles_module = types.ModuleType("items.vehicles")
    vehicles_module.VehicleType = VehicleType
    vehicles_module.g_cache = Cache([configured_vehicle, configured_dual_vehicle, untouched_vehicle], gun_effects)
    items_module = types.ModuleType("items")
    items_module.vehicles = vehicles_module
    debug_module = types.ModuleType("debug_utils")
    debug_module.LOG_CURRENT_EXCEPTION = lambda: None
    debug_module.LOG_NOTE = lambda *args: None
    keys_module = types.ModuleType("Keys")
    keys_module.KEY_F8 = 119
    played_sounds = []
    def play_sound(event):
        played_sounds.append(event)
        return True
    sound_groups_module = types.ModuleType("SoundGroups")
    sound_groups_module.g_instance = types.SimpleNamespace(playSound2D=play_sound)
    current_vehicle = CurrentVehicle()
    current_vehicle_module = types.ModuleType("CurrentVehicle")
    current_vehicle_module.g_currentVehicle = current_vehicle
    input_handler_module = types.ModuleType("gui.InputHandler")
    input_handler_module.g_instance = types.SimpleNamespace(onKeyDown=EventHook())
    messages = []
    system_messages_module = types.ModuleType("gui.SystemMessages")
    system_messages_module.SM_TYPE = types.SimpleNamespace(Information=1)
    system_messages_module.pushMessage = lambda message, type: messages.append((message, type))
    sys.modules["items"] = items_module
    sys.modules["items.vehicles"] = vehicles_module
    sys.modules["debug_utils"] = debug_module
    sys.modules["Keys"] = keys_module
    sys.modules["SoundGroups"] = sound_groups_module
    sys.modules["CurrentVehicle"] = current_vehicle_module
    sys.modules["gui.InputHandler"] = input_handler_module
    sys.modules["gui.SystemMessages"] = system_messages_module
    client_root = project_root / "src" / "scripts" / "client"
    sys.path.insert(0, str(client_root))
    try:
        spec = importlib.util.spec_from_file_location("gui.mods.mod_oldshoot", client_root / "gui" / "mods" / "mod_oldshoot.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(client_root))
    configured_gun = configured_vehicle.turrets[0][0].guns[0]
    untouched_gun = untouched_vehicle.turrets[0][0].guns[0]
    actual = configured_gun.effects.effectsList.descriptors()[0]._soundName
    single_expected = ((events["player_event"],), (events["npc_event"],))
    if configured_gun is shared_gun or actual != single_expected:
        raise RuntimeError("Configured gun was not safely patched")
    if untouched_gun is not shared_gun or shared_gun.effects.effectsList.descriptors()[0]._soundName != (("current_pc",), ("current_npc",)):
        raise RuntimeError("Shared gun leaked into an unconfigured vehicle")
    configured_dual_gun = configured_dual_vehicle.turrets[0][0].guns[0]
    if configured_dual_gun is dual_gun or len(configured_dual_gun.effects) != len(dual_data["effects"]):
        raise RuntimeError("Configured multi-gun was not safely cloned")
    for actual_effect, expected_effect in zip(configured_dual_gun.effects, dual_data["effects"]):
        actual = actual_effect.effectsList.descriptors()[0]._soundName
        expected = ((expected_effect["player_event"],), (expected_effect["npc_event"],)) if expected_effect["player_event"] is not None else (("current_pc",), ("current_npc",))
        if actual != expected:
            raise RuntimeError("Configured multi-gun effect was not patched")
    future_vehicle = vehicles_module.VehicleType(vehicle_name, turret_name, shared_gun)
    future_actual = future_vehicle.turrets[0][0].guns[0].effects.effectsList.descriptors()[0]._soundName
    if future_actual != single_expected:
        raise RuntimeError("VehicleType hook did not patch a future vehicle")
    key_handler = input_handler_module.g_instance.onKeyDown.handler
    if key_handler is None:
        raise RuntimeError("Hangar sound test hotkey was not installed")
    key_handler(KeyEvent(keys_module.KEY_F8))
    key_handler(KeyEvent(keys_module.KEY_F8))
    if played_sounds != ["oldshoot_wpn_automatic_pc", "oldshoot_wpn_small_pc"] or len(messages) != 2:
        raise RuntimeError("Hangar sound test did not play the first event")
    current_vehicle.in_hangar = False
    key_handler(KeyEvent(keys_module.KEY_F8))
    if len(played_sounds) != 2:
        raise RuntimeError("Hangar sound test was active outside the hangar")


def validate(project_root):
    whitelist = json.loads((project_root / "mapping" / "old_vehicle_guns.json").read_text(encoding="utf-8"))
    retained = json.loads((project_root / "mapping" / "retained_vehicles.json").read_text(encoding="utf-8"))
    retained_names = {record["id"].replace("/", ":", 1) for record in retained}
    vehicle_names = set(whitelist["vehicles"])
    if whitelist["conflicts"] or not vehicle_names.issubset(retained_names):
        raise RuntimeError("Whitelist contains conflicts or non-retained vehicles")
    gun_count = sum(len(guns) for turrets in whitelist["vehicles"].values() for guns in turrets.values())
    if len(vehicle_names) != whitelist["vehicle_count"] or gun_count != whitelist["gun_count"]:
        raise RuntimeError("Whitelist counts are inconsistent")
    expected_events = set()
    for data in whitelist["effects"].values():
        expected_events.add(data["player_event"])
        expected_events.add(data["npc_event"])
    soundbanks_info = ET.parse(project_root / "work" / "wwise_build" / "GeneratedSoundBanks" / "SoundbanksInfo.xml")
    actual_events = {node.get("Name") for node in soundbanks_info.findall(".//SoundBank[ShortName='oldshoot']/Events/Event")}
    if actual_events != expected_events:
        raise RuntimeError("SoundBank events do not match the whitelist")
    required_dual_vehicles = {"ussr:R165_Object_703_II", "uk:GB142_FV230_Canopener"}
    if not required_dual_vehicles.issubset(vehicle_names):
        raise RuntimeError("Required multi-gun vehicles are missing")
    required_dual_events = {
        "oldshoot_wpn_main_dual_pc",
        "oldshoot_wpn_main_dual_npc",
        "oldshoot_wpn_main_extra_dual_pc",
        "oldshoot_wpn_main_extra_dual_npc",
        "oldshoot_wpn_large_dual_pc",
        "oldshoot_wpn_large_dual_npc",
    }
    if not required_dual_events.issubset(actual_events):
        raise RuntimeError("Required multi-gun SoundBank events are missing")
    archive_path = project_root / "dist" / "OldShootSounds.zip"
    required = {
        "OldShootSounds/Install-OldShootSounds.cmd",
        "OldShootSounds/Install-OldShootSounds.ps1",
        "OldShootSounds/payload/audioww/oldshoot.bnk",
        "OldShootSounds/payload/scripts/client/gui/mods/mod_oldshoot.pyc",
        "OldShootSounds/payload/scripts/client/gui/mods/oldshoot_data.pyc",
    }
    with zipfile.ZipFile(archive_path) as archive:
        if not required.issubset(set(archive.namelist())):
            raise RuntimeError("Release archive is incomplete")
    for name in ("mod_oldshoot.pyc", "oldshoot_data.pyc"):
        path = project_root / "dist" / "OldShootSounds" / "payload" / "scripts" / "client" / "gui" / "mods" / name
        if path.read_bytes()[:4] != b"\x03\xf3\x0d\x0a":
            raise RuntimeError("Invalid Python 2.7 bytecode header")
    bank_path = project_root / "dist" / "OldShootSounds" / "payload" / "audioww" / "oldshoot.bnk"
    bank = bank_path.read_bytes()
    if bank[:4] != b"BKHD" or len(bank) < 24:
        raise RuntimeError("Invalid SoundBank header")
    for offset, expected in WOT_HEADER_VALUES.items():
        raw_value = struct.unpack_from("<I", bank, offset)[0]
        if raw_value ^ WOT_HEADER_XOR[offset] != expected:
            raise RuntimeError("SoundBank header is not fully WoT-obfuscated")
    validate_runtime(project_root, whitelist)
    print("Vehicles: {}".format(len(vehicle_names)))
    print("Guns: {}".format(gun_count))
    print("Events: {}".format(len(actual_events)))
    print("Archive: OK")
    print("SoundBank WoT header: OK")
    print("Runtime isolation: OK")
    print("Hangar F8 test: OK")


def main():
    validate(Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
