import argparse
import copy
import json
import re
import shutil
import struct
import subprocess
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


STATE_WORK_UNIT_ID = "{2919E36D-D7A0-482C-9D63-0D8F398C9469}"
STATE_GROUP_ID = "{94AF04AB-50F8-4D8F-9E12-EF87EF6A78A7}"
STATE_IDS = {
    "None": "{F1945C64-4568-4C30-8128-1460D9EBB041}",
    "STATE_viewPlayMode_arcade": "{38532EFB-0C84-4858-9839-3FFE7D765E45}",
    "STATE_viewPlayMode_sniper": "{B84360EE-0891-43A8-9F9B-76A898F6C9B6}",
    "STATE_viewPlayMode_strategic": "{851DD47E-B7C7-4DEA-A07F-83D254EF6192}",
    "STATE_viewPlayMode_arcade_ceilless": "{460305C3-914D-4E7A-B2FF-B5E3FEE9D830}",
    "STATE_viewPlayMode_sniper_ceilless": "{2E037C3D-50E0-434A-B018-29231D9083D7}",
}
ATTENUATION_WORK_UNIT_ID = "{FDC8E3CF-67CA-424D-8EA4-187769599D6D}"
ATTENUATIONS = {
    "pc": ("ATT_weapons_600m_pc", "{F5F841B7-AB14-4CB0-B423-F01D30E84D85}"),
    "npc": ("ATT_weapons_600m_npc", "{0CB36698-89E7-4341-AE96-3F9C2FD78FA8}"),
}
NAMESPACE = uuid.UUID("319cbfa9-a9c8-4859-8648-bdcf616968a0")
WOT_HEADER_XOR = {
    8: 0xD2F5B297,
    16: 0xD10C0503,
    20: 0x6B0403D4,
}


def guid(value):
    return "{" + str(uuid.uuid5(NAMESPACE, value)).upper() + "}"


def short_id(value):
    result = 2166136261
    for char in value.lower():
        result = ((result ^ ord(char)) * 16777619) & 0xFFFFFFFF
    return str(result)


def run(command, maximum_return_code=0):
    result = subprocess.run([str(value) for value in command])
    if result.returncode > maximum_return_code:
        raise subprocess.CalledProcessError(result.returncode, command)


def write_xml(path, root):
    ET.indent(root, space="\t")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def add_property(parent, name, property_type, value):
    property_list = parent.find("PropertyList")
    if property_list is None:
        property_list = ET.Element("PropertyList")
        parent.insert(0, property_list)
    previous = property_list.find("Property[@Name='{}']".format(name))
    if previous is not None:
        property_list.remove(previous)
    ET.SubElement(property_list, "Property", {"Name": name, "Type": property_type, "Value": str(value)})


def add_reference(parent, name, object_name, object_id, work_unit_id):
    reference_list = parent.find("ReferenceList")
    if reference_list is None:
        reference_list = ET.Element("ReferenceList")
        property_list = parent.find("PropertyList")
        parent.insert(1 if property_list is not None else 0, reference_list)
    previous = reference_list.find("Reference[@Name='{}']".format(name))
    if previous is not None:
        reference_list.remove(previous)
    reference = ET.SubElement(reference_list, "Reference", {"Name": name})
    ET.SubElement(reference, "ObjectRef", {"Name": object_name, "ID": object_id, "WorkUnitID": work_unit_id})


def prepare_import(project_root, build_root, manifest):
    if manifest.get("format") != "dynamic-full-v1":
        raise RuntimeError("Full dynamic audio manifest is required")
    events = defaultdict(dict)
    txtp_names = {}
    node_properties = {}
    wav_root = Path(manifest["wav_root"])
    lines = ["Audio File\tObject Path\tObject Type"]
    sequence = [0]

    def emit(node, parent_path, name):
        object_path = parent_path + "\\" + name
        sequence[0] += 1
        if node["kind"] == "sound":
            audio_path = Path(node["wav"]) if "wav" in node else wav_root / (str(node["wem"]) + ".wav")
            lines.append("{}\t{}\tSound SFX".format(audio_path, object_path))
        else:
            object_type = "Random Container" if node["kind"] == "random" else "Blend Container"
            lines.append("\t{}\t{}".format(object_path, object_type))
            for child in node["children"]:
                emit(child, object_path, "n{:05d}".format(sequence[0]))
        node_properties[name] = node

    actor_root = "\\Actor-Mixer Hierarchy\\Default Work Unit"
    for event in sorted(manifest["events"], key=lambda item: item["event"]):
        event_name = event["event"]
        for branch_record in sorted(event["branches"], key=lambda item: item["branch"]):
            branch = branch_record["branch"]
            events[event_name][branch] = branch_record
            txtp_names[(event_name, branch)] = Path(branch_record["txtp"]).name
            container_name = "{}__branch_{:02d}".format(event_name, branch)
            root = branch_record["root"]
            if root["kind"] == "sound":
                root = {"kind": "layer", "children": [root]}
            emit(root, actor_root, container_name)
    import_path = build_root / "audio_import.tsv"
    import_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return events, txtp_names, node_properties, import_path


def configure_dynamic_properties(project_root, node_properties):
    path = project_root / "Actor-Mixer Hierarchy" / "Default Work Unit.wwu"
    tree = ET.parse(path)
    document = tree.getroot()
    objects = {node.get("Name"): node for node in document.findall(".//*[@Name]")}
    for name, data in node_properties.items():
        node = objects.get(name)
        if node is None:
            raise RuntimeError("Imported audio object was not found: " + name)
        if "volume" in data:
            add_property(node, "Volume", "Real64", data["volume"])
        if "delay" in data:
            add_property(node, "InitialDelay", "Real64", data["delay"])
        if data["kind"] == "random":
            child_count = len(data["children"])
            add_property(node, "RandomOrSequence", "int16", 1)
            add_property(node, "NormalOrShuffle", "int16", 1)
            add_property(node, "RandomAvoidRepeating", "bool", "true" if child_count > 1 else "false")
            if child_count > 1:
                add_property(node, "RandomAvoidRepeatingCount", "int32", child_count - 1)
    write_xml(path, document)


def create_states(project_root):
    document = ET.Element("WwiseDocument", {"Type": "WorkUnit", "ID": STATE_WORK_UNIT_ID, "SchemaVersion": "119"})
    states = ET.SubElement(document, "States")
    work_unit = ET.SubElement(states, "WorkUnit", {"Name": "View Modes", "ID": STATE_WORK_UNIT_ID, "PersistMode": "Standalone"})
    children = ET.SubElement(work_unit, "ChildrenList")
    group = ET.SubElement(children, "StateGroup", {"Name": "STATE_viewPlayMode", "ID": STATE_GROUP_ID})
    group_children = ET.SubElement(group, "ChildrenList")
    for name, state_id in STATE_IDS.items():
        ET.SubElement(group_children, "State", {"Name": name, "ID": state_id})
    write_xml(project_root / "States" / "View Modes.wwu", document)


def create_attenuations(project_root, reference_root):
    source_path = reference_root / "Attenuations" / "Weapons.wwu"
    source_root = ET.parse(source_path).getroot()
    document = ET.Element("WwiseDocument", {"Type": "WorkUnit", "ID": ATTENUATION_WORK_UNIT_ID, "SchemaVersion": "119"})
    attenuations = ET.SubElement(document, "Attenuations")
    work_unit = ET.SubElement(attenuations, "WorkUnit", {"Name": "Weapons", "ID": ATTENUATION_WORK_UNIT_ID, "PersistMode": "Standalone"})
    children = ET.SubElement(work_unit, "ChildrenList")
    wanted = {value[0] for value in ATTENUATIONS.values()}
    for attenuation in source_root.findall(".//Attenuation"):
        if attenuation.get("Name") in wanted:
            children.append(copy.deepcopy(attenuation))
    if len(children) != len(wanted):
        raise RuntimeError("Required weapon attenuations were not found")
    write_xml(project_root / "Attenuations" / "Weapons.wwu", document)


def set_vorbis_conversion(project_root):
    path = project_root / "Conversion Settings" / "Default Work Unit.wwu"
    tree = ET.parse(path)
    conversion = tree.getroot().find(".//Conversion[@Name='Default Conversion Settings']")
    plugin_info = conversion.find("ConversionPluginInfoList/ConversionPluginInfo")
    platform = plugin_info.get("Platform")
    plugin_info.clear()
    plugin_info.set("Platform", platform)
    plugin = ET.SubElement(plugin_info, "ConversionPlugin", {"Name": "", "ID": guid("vorbis-plugin"), "PluginName": "Vorbis", "CompanyID": "0", "PluginID": "4"})
    properties = ET.SubElement(plugin, "PropertyList")
    ET.SubElement(properties, "Property", {"Name": "QualityFactor", "Type": "Real32", "Value": "8"})
    write_xml(path, tree.getroot())


def obfuscate_bank_header(bank_path):
    bank = bytearray(bank_path.read_bytes())
    if bank[:4] != b"BKHD" or len(bank) < 24:
        raise RuntimeError("Invalid bank header")
    values = {offset: struct.unpack_from("<I", bank, offset)[0] for offset in WOT_HEADER_XOR}
    encoded = {offset: value ^ WOT_HEADER_XOR[offset] for offset, value in {8: 150, 16: 393239870, 20: 16}.items()}
    if values == encoded:
        return
    if values != {8: 150, 16: 393239870, 20: 16}:
        raise RuntimeError("Unknown bank header encoding")
    for offset, xor_key in WOT_HEADER_XOR.items():
        value = struct.unpack_from("<I", bank, offset)[0]
        struct.pack_into("<I", bank, offset, value ^ xor_key)
    bank_path.write_bytes(bank)


def preserve_license(project_path, license_path):
    if not project_path.is_file():
        return
    document = ET.parse(project_path).getroot()
    for prop in document.findall(".//Property[@Name='LicenseKey']"):
        value = prop.get("Value")
        if value:
            license_path.write_bytes(value.encode("utf-8"))
            return


def read_license(license_path):
    if not license_path.is_file():
        raise RuntimeError("Wwise license was not found. Apply it to the generated project first")
    value = license_path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError("Wwise license is empty")
    return value


def state_from_txtp(txtp_name):
    match = re.search(r"STATE_viewPlayMode=(STATE_viewPlayMode_[A-Za-z_]+)", txtp_name)
    return match.group(1) if match is not None else None


def configure_audio_objects(project_root, events, txtp_names):
    path = project_root / "Actor-Mixer Hierarchy" / "Default Work Unit.wwu"
    tree = ET.parse(path)
    document = tree.getroot()
    work_unit = document.find("AudioObjects/WorkUnit")
    work_unit_id = work_unit.get("ID")
    children = work_unit.find("ChildrenList")
    containers = {container.get("Name"): container for container in list(children)}
    event_targets = {}
    for event_name in sorted(events):
        branch_nodes = []
        branch_states = {}
        default_branch = None
        for branch in sorted(events[event_name]):
            container_name = "{}__branch_{:02d}".format(event_name, branch)
            node = containers[container_name]
            branch_nodes.append(node)
            state = state_from_txtp(txtp_names[(event_name, branch)])
            if state is None:
                default_branch = node
            else:
                branch_states[state] = node
        kind = "pc" if event_name.endswith("_pc") else "npc"
        if len(branch_nodes) == 1:
            target = branch_nodes[0]
            target.set("Name", event_name)
            target.set("ShortID", short_id(event_name))
            add_property(target, "3DSpatialization", "int16", "1" if kind == "pc" else "2")
            attenuation_name, attenuation_id = ATTENUATIONS[kind]
            add_reference(target, "Attenuation", attenuation_name, attenuation_id, ATTENUATION_WORK_UNIT_ID)
        else:
            target = ET.Element("SwitchContainer", {"Name": event_name, "ID": guid("container:" + event_name), "ShortID": short_id(event_name)})
            add_property(target, "3DSpatialization", "int16", "1")
            conversion = branch_nodes[0].find("ReferenceList/Reference[@Name='Conversion']/ObjectRef")
            output_bus = branch_nodes[0].find("ReferenceList/Reference[@Name='OutputBus']/ObjectRef")
            add_reference(target, "Conversion", conversion.get("Name"), conversion.get("ID"), conversion.get("WorkUnitID"))
            add_reference(target, "OutputBus", output_bus.get("Name"), output_bus.get("ID"), output_bus.get("WorkUnitID"))
            attenuation_name, attenuation_id = ATTENUATIONS["pc"]
            add_reference(target, "Attenuation", attenuation_name, attenuation_id, ATTENUATION_WORK_UNIT_ID)
            add_reference(target, "DefaultSwitchOrState", "STATE_viewPlayMode_arcade", STATE_IDS["STATE_viewPlayMode_arcade"], STATE_WORK_UNIT_ID)
            add_reference(target, "SwitchGroupOrStateGroup", "STATE_viewPlayMode", STATE_GROUP_ID, STATE_WORK_UNIT_ID)
            target_children = ET.SubElement(target, "ChildrenList")
            for node in branch_nodes:
                children.remove(node)
                target_children.append(node)
            grouping_info = ET.SubElement(target, "GroupingInfo")
            behavior_list = ET.SubElement(grouping_info, "GroupingBehaviorList")
            for node in branch_nodes:
                behavior = ET.SubElement(behavior_list, "GroupingBehavior")
                ET.SubElement(behavior, "ItemRef", {"Name": node.get("Name"), "ID": node.get("ID")})
            grouping_list = ET.SubElement(grouping_info, "GroupingList")
            fallback = default_branch
            if fallback is None:
                fallback = branch_states.get("STATE_viewPlayMode_arcade")
            if fallback is None:
                fallback = branch_nodes[0]
            for state_name, state_id in STATE_IDS.items():
                selected = branch_states.get(state_name, fallback)
                grouping = ET.SubElement(grouping_list, "Grouping")
                ET.SubElement(grouping, "SwitchRef", {"Name": state_name, "ID": state_id})
                item_list = ET.SubElement(grouping, "ItemList")
                ET.SubElement(item_list, "ItemRef", {"Name": selected.get("Name"), "ID": selected.get("ID")})
            children.append(target)
        event_targets[event_name] = (target.get("ID"), work_unit_id)
    write_xml(path, document)
    return event_targets


def create_events(project_root, event_targets):
    path = project_root / "Events" / "Default Work Unit.wwu"
    tree = ET.parse(path)
    document = tree.getroot()
    work_unit = document.find("Events/WorkUnit")
    work_unit_id = work_unit.get("ID")
    children = ET.SubElement(work_unit, "ChildrenList")
    event_ids = {}
    for event_name in sorted(event_targets):
        event_id = guid("event:" + event_name)
        event_ids[event_name] = event_id
        event = ET.SubElement(children, "Event", {"Name": event_name, "ID": event_id})
        event_children = ET.SubElement(event, "ChildrenList")
        action = ET.SubElement(event_children, "Action", {"Name": "", "ID": guid("action:" + event_name), "ShortID": short_id("action:" + event_name)})
        target_id, target_work_unit_id = event_targets[event_name]
        add_reference(action, "Target", event_name, target_id, target_work_unit_id)
    write_xml(path, document)
    return event_ids, work_unit_id


def create_soundbank(project_root, event_ids, event_work_unit_id):
    path = project_root / "SoundBanks" / "Default Work Unit.wwu"
    tree = ET.parse(path)
    document = tree.getroot()
    work_unit = document.find("SoundBanks/WorkUnit")
    children = ET.SubElement(work_unit, "ChildrenList")
    bank = ET.SubElement(children, "SoundBank", {"Name": "oldshoot", "ID": guid("bank:oldshoot")})
    inclusion_list = ET.SubElement(bank, "ObjectInclusionList")
    for event_name in sorted(event_ids):
        ET.SubElement(inclusion_list, "ObjectRef", {"Name": event_name, "ID": event_ids[event_name], "WorkUnitID": event_work_unit_id, "Origin": "Manual", "Filter": "7"})
    ET.SubElement(bank, "ObjectExclusionList")
    ET.SubElement(bank, "GameSyncExclusionList")
    write_xml(path, document)


def build(args):
    project_root = Path(__file__).resolve().parents[1]
    manifest_path = project_root / "work" / "old_event_dynamic" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    build_root = project_root / "work" / "wwise_build"
    wwise_project_root = build_root / "OldShootSounds"
    wwise_project = wwise_project_root / "OldShootSounds.wproj"
    license_path = project_root / "work" / "wwise_license.txt"
    preserve_license(wwise_project, license_path)
    license_key = read_license(license_path)
    if build_root.exists():
        shutil.rmtree(build_root)
    build_root.mkdir(parents=True)
    run([args.wwise_console, "create-new-project", wwise_project, "--platform", "Windows", "--quiet"])
    events, txtp_names, node_properties, import_path = prepare_import(project_root, build_root, manifest)
    run([args.wwise_console, "tab-delimited-import", wwise_project, import_path, "--quiet"])
    configure_dynamic_properties(wwise_project_root, node_properties)
    create_states(wwise_project_root)
    create_attenuations(wwise_project_root, project_root / "reference" / "9.13-Wot-gun-sounds-for-wot")
    set_vorbis_conversion(wwise_project_root)
    event_targets = configure_audio_objects(wwise_project_root, events, txtp_names)
    event_ids, event_work_unit_id = create_events(wwise_project_root, event_targets)
    create_soundbank(wwise_project_root, event_ids, event_work_unit_id)
    output_root = build_root / "GeneratedSoundBanks"
    run([args.wwise_console, "generate-soundbank", wwise_project, "--license", license_key, "--platform", "Windows", "--bank", "oldshoot", "--soundbank-path", "Windows", output_root, "--root-output-path", output_root, "--clear-audio-file-cache", "--quiet"], maximum_return_code=2)
    bank_path = output_root / "oldshoot.bnk"
    if not bank_path.exists():
        bank_path = output_root / "Windows" / "oldshoot.bnk"
    if not bank_path.exists():
        raise RuntimeError("oldshoot.bnk was not generated")
    destination = project_root / "src" / "audioww" / "oldshoot.bnk"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bank_path, destination)
    obfuscate_bank_header(destination)
    print("Events: {}".format(len(events)))
    print("Bank: {}".format(destination))
    print("Size: {}".format(destination.stat().st_size))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wwise-console", required=True)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
