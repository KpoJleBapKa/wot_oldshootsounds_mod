import importlib.util
import json
import subprocess
import struct
import sys
import tempfile
import types
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from mod_version import read_version


sys.dont_write_bytecode = True


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

    def __init__(self, player_event="current_pc", npc_event="current_npc"):
        self._soundName = ((player_event,), (npc_event,))


class EffectList:
    def __init__(self, player_event="current_pc", npc_event="current_npc"):
        self.value = Descriptor(player_event, npc_event)

    def descriptors(self):
        return [self.value]


class Effects:
    def __init__(self, player_event="current_pc", npc_event="current_npc"):
        self.effectsList = EffectList(player_event, npc_event)


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
    def __init__(self, name, turret_name, gun, level=10):
        self.name = name
        self.level = level
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


def validate_runtime(project_root, whitelist, version):
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
    standard_gun = Gun("new_standard_gun", Effects("wpn_large_PC", "wpn_large_NPC"))
    standard_multi_gun = Gun("new_standard_multi_gun", [Effects("wpn_main_PC", "wpn_main_NPC"), Effects("wpn_special_PC", "wpn_special_NPC")])
    unknown_gun = Gun("new_unknown_gun", Effects("wpn_special_PC", "wpn_special_NPC"))
    configured_vehicle = VehicleType(vehicle_name, turret_name, shared_gun)
    configured_dual_vehicle = VehicleType(dual_vehicle_name, dual_turret_name, dual_gun)
    standard_vehicle = VehicleType("newnation:NewVehicle", turret_name, standard_gun)
    standard_multi_vehicle = VehicleType("newnation:NewMultiVehicle", turret_name, standard_multi_gun)
    tier_eleven_vehicle = VehicleType("newnation:TierElevenVehicle", turret_name, standard_gun, 11)
    unknown_vehicle = VehicleType("newnation:SpecialVehicle", turret_name, unknown_gun)
    gun_effects = {effect["effect"]: Effects() for effect in dual_data["effects"]}
    vehicles_module = types.ModuleType("items.vehicles")
    vehicles_module.VehicleType = VehicleType
    vehicles_module.g_cache = Cache([configured_vehicle, configured_dual_vehicle, standard_vehicle, standard_multi_vehicle, tier_eleven_vehicle, unknown_vehicle], gun_effects)
    items_module = types.ModuleType("items")
    items_module.vehicles = vehicles_module
    debug_module = types.ModuleType("debug_utils")
    debug_module.LOG_CURRENT_EXCEPTION = lambda: None
    logs = []
    debug_module.LOG_NOTE = lambda *args: logs.append(args)
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
    standard_actual_gun = standard_vehicle.turrets[0][0].guns[0]
    standard_multi_actual_gun = standard_multi_vehicle.turrets[0][0].guns[0]
    tier_eleven_actual_gun = tier_eleven_vehicle.turrets[0][0].guns[0]
    unknown_actual_gun = unknown_vehicle.turrets[0][0].guns[0]
    actual = configured_gun.effects.effectsList.descriptors()[0]._soundName
    single_expected = ((events["player_event"],), (events["npc_event"],))
    if configured_gun is shared_gun or actual != single_expected:
        raise RuntimeError("Configured gun was not safely patched")
    if shared_gun.effects.effectsList.descriptors()[0]._soundName != (("current_pc",), ("current_npc",)):
        raise RuntimeError("Shared gun leaked into an unconfigured vehicle")
    standard_actual = standard_actual_gun.effects.effectsList.descriptors()[0]._soundName
    if standard_actual_gun is standard_gun or standard_actual != (("oldshoot_wpn_large_pc",), ("oldshoot_wpn_large_npc",)):
        raise RuntimeError("Tier I-X standard gun was not patched")
    standard_multi_actual = [effect.effectsList.descriptors()[0]._soundName for effect in standard_multi_actual_gun.effects]
    if standard_multi_actual_gun is standard_multi_gun or standard_multi_actual != [(("oldshoot_wpn_main_pc",), ("oldshoot_wpn_main_npc",)), (("wpn_special_PC",), ("wpn_special_NPC",))]:
        raise RuntimeError("Tier I-X standard multi-gun was not safely patched")
    if tier_eleven_actual_gun is not standard_gun or standard_gun.effects.effectsList.descriptors()[0]._soundName != (("wpn_large_PC",), ("wpn_large_NPC",)):
        raise RuntimeError("Tier XI vehicle was unexpectedly patched")
    if unknown_actual_gun is not unknown_gun or unknown_gun.effects.effectsList.descriptors()[0]._soundName != (("wpn_special_PC",), ("wpn_special_NPC",)):
        raise RuntimeError("Unknown gun effect was unexpectedly patched")
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
    if not any("version {}".format(version) in str(entry) for entry in logs):
        raise RuntimeError("Runtime log does not contain the mod version")


def run_installer(project_root, game_root):
    installer = project_root / "dist" / "OldShootSounds" / "Install-OldShootSounds.ps1"
    result = subprocess.run([
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(installer),
        "-GameRoot",
        str(game_root),
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Installer failed: {}".format(result.stderr.strip()))


def bank_names(path):
    document = ET.parse(path)
    return [node.text for node in document.findall("./loadBanks/bank/name")]


def validate_installer(project_root):
    work_root = project_root / "work"
    with tempfile.TemporaryDirectory(prefix="oldshoot_clean_", dir=work_root) as directory:
        game_root = Path(directory)
        (game_root / "paths.xml").write_text('<root><Paths><Path cacheSubdirs="true">./res_mods/9.9.9.9</Path></Paths></root>', encoding="utf-8")
        run_installer(project_root, game_root)
        target_root = game_root / "res_mods" / "9.9.9.9"
        audio_root = target_root / "audioww"
        script_root = target_root / "scripts" / "client" / "gui" / "mods"
        required = [audio_root / "oldshoot.bnk", script_root / "mod_oldshoot.pyc", script_root / "oldshoot_data.pyc"]
        if not all(path.is_file() for path in required):
            raise RuntimeError("Clean installation did not copy every payload file")
        if bank_names(audio_root / "audio_mods.xml") != ["oldshoot.bnk"]:
            raise RuntimeError("Clean installation created an invalid audio_mods.xml")
    with tempfile.TemporaryDirectory(prefix="oldshoot_merge_", dir=work_root) as directory:
        game_root = Path(directory)
        (game_root / "paths.xml").write_text('<root><Paths><Path cacheSubdirs="true">./res_mods/9.9.9.9</Path></Paths></root>', encoding="utf-8")
        audio_root = game_root / "res_mods" / "9.9.9.9" / "audioww"
        audio_root.mkdir(parents=True)
        audio_mods = audio_root / "audio_mods.xml"
        existing_xml = "<audio_mods.xml><loadBanks><bank><name>voiceover.bnk</name></bank><bank><name>other_mod.bnk</name></bank></loadBanks></audio_mods.xml>"
        audio_mods.write_text(existing_xml, encoding="utf-8")
        run_installer(project_root, game_root)
        run_installer(project_root, game_root)
        names = bank_names(audio_mods)
        if names != ["voiceover.bnk", "other_mod.bnk", "oldshoot.bnk"]:
            raise RuntimeError("Installer did not preserve or safely merge audio_mods.xml entries")
        backup = Path(str(audio_mods) + ".oldshoot.bak")
        if not backup.is_file() or bank_names(backup) != ["voiceover.bnk", "other_mod.bnk"]:
            raise RuntimeError("Installer did not preserve the original audio_mods.xml backup")


def validate_dynamic_audio(project_root, expected_events):
    manifest = json.loads((project_root / "work" / "old_event_dynamic" / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != "dynamic-full-v1" or manifest.get("event_count") != len(expected_events):
        raise RuntimeError("Dynamic audio manifest is invalid")
    if manifest.get("media_items", 0) < 800:
        raise RuntimeError("Full dynamic audio media set is missing")
    manifest_events = {event["event"] for event in manifest["events"]}
    if manifest_events != expected_events:
        raise RuntimeError("Dynamic audio events do not match the whitelist")

    def validate_node(node):
        if node["kind"] == "sound":
            if "wem" not in node:
                raise RuntimeError("Dynamic audio sound has no source")
            return
        if node["kind"] not in {"random", "layer"} or not node.get("children"):
            raise RuntimeError("Dynamic audio graph contains an invalid node")
        for child in node["children"]:
            validate_node(child)

    for event in manifest["events"]:
        for branch in event["branches"]:
            root = branch["root"]
            if root["kind"] != "layer":
                raise RuntimeError("Dynamic audio branch has no layered structure")
            validate_node(root)
    hierarchy_path = project_root / "work" / "wwise_build" / "OldShootSounds" / "Actor-Mixer Hierarchy" / "Default Work Unit.wwu"
    hierarchy = ET.parse(hierarchy_path).getroot()
    random_nodes = hierarchy.findall(".//RandomSequenceContainer")
    layer_nodes = hierarchy.findall(".//BlendContainer")
    sound_nodes = hierarchy.findall(".//Sound")
    if len(random_nodes) != manifest["nodes"]["random"] or len(layer_nodes) != manifest["nodes"]["layer"] or len(sound_nodes) != manifest["nodes"]["sound"]:
        raise RuntimeError("Compiled Wwise hierarchy does not match the dynamic manifest")
    for node in random_nodes:
        properties = {item.get("Name"): item.get("Value") for item in node.findall("PropertyList/Property")}
        child_count = len(node.findall("ChildrenList/*"))
        expected_avoid = "true" if child_count > 1 else "false"
        if properties.get("RandomOrSequence") != "1" or properties.get("NormalOrShuffle") != "1" or properties.get("RandomAvoidRepeating") != expected_avoid:
            raise RuntimeError("Compiled Wwise random container has invalid playback properties")
        if child_count > 1 and properties.get("RandomAvoidRepeatingCount") != str(child_count - 1):
            raise RuntimeError("Compiled Wwise random container has invalid repetition limit")


def validate(project_root):
    version = read_version(project_root)
    if (project_root / "VERSION").read_text(encoding="utf-8").strip() != version:
        raise RuntimeError("VERSION is not synchronized with the current Git branch")
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
    validate_dynamic_audio(project_root, expected_events)
    archive_path = project_root / "dist" / "OldShootSounds-{}.zip".format(version)
    required = {
        "OldShootSounds/Install-OldShootSounds.cmd",
        "OldShootSounds/Install-OldShootSounds.ps1",
        "OldShootSounds/VERSION",
        "OldShootSounds/payload/audioww/oldshoot.bnk",
        "OldShootSounds/payload/scripts/client/gui/mods/mod_oldshoot.pyc",
        "OldShootSounds/payload/scripts/client/gui/mods/oldshoot_data.pyc",
    }
    with zipfile.ZipFile(archive_path) as archive:
        archive_names = set(archive.namelist())
        if not required.issubset(archive_names):
            raise RuntimeError("Release archive is incomplete")
        forbidden = [name for name in archive_names if "voiceover" in name.lower() or Path(name).suffix.lower() in {".exe", ".dll"}]
        if forbidden:
            raise RuntimeError("Release archive contains forbidden files: {}".format(", ".join(forbidden)))
        if archive.read("OldShootSounds/VERSION").decode("utf-8").strip() != version:
            raise RuntimeError("Release archive contains the wrong version")
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
    wgmods_root = project_root / "dist" / "WGMods"
    if not wgmods_root.is_dir() or any("<MOD_VERSION>" in path.read_text(encoding="utf-8") for path in wgmods_root.glob("*.md")):
        raise RuntimeError("WGMods materials do not contain the current mod version")
    validate_runtime(project_root, whitelist, version)
    validate_installer(project_root)
    print("Version: {}".format(version))
    print("Vehicles: {}".format(len(vehicle_names)))
    print("Guns: {}".format(gun_count))
    print("Events: {}".format(len(actual_events)))
    print("Archive: OK")
    print("SoundBank WoT header: OK")
    print("Dynamic layered audio: OK")
    print("Runtime isolation: OK")
    print("Hangar F8 test: OK")
    print("Clean and merged installation: OK")


def main():
    validate(Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
