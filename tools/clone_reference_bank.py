import argparse
import struct
from pathlib import Path

from extract_pck import read_pck

WOT_HEADER_XOR = {
    8: 0xD2F5B297,
    16: 0xD10C0503,
    20: 0x6B0403D4,
}
WPN_EVENTS = (
    "wpn_automatic_npc",
    "wpn_automatic_pc",
    "wpn_huge_npc",
    "wpn_huge_pc",
    "wpn_large_dual_npc",
    "wpn_large_dual_pc",
    "wpn_large_extra_npc",
    "wpn_large_extra_pc",
    "wpn_large_npc",
    "wpn_large_pc",
    "wpn_main_dual_npc",
    "wpn_main_dual_pc",
    "wpn_main_extra_dual_npc",
    "wpn_main_extra_dual_pc",
    "wpn_main_extra_npc",
    "wpn_main_extra_pc",
    "wpn_main_npc",
    "wpn_main_pc",
    "wpn_meduim_npc",
    "wpn_meduim_pc",
    "wpn_small_npc",
    "wpn_small_pc",
)


def short_id(value):
    result = 2166136261
    for char in value.lower():
        result = ((result * 16777619) & 0xFFFFFFFF) ^ ord(char)
    return result


def chunks(data):
    result = []
    position = 0
    while position + 8 <= len(data):
        tag = data[position:position + 4]
        size = struct.unpack_from("<I", data, position + 4)[0]
        start = position + 8
        end = start + size
        if end > len(data):
            raise RuntimeError("Invalid {} chunk size".format(tag.decode("ascii", errors="replace")))
        result.append((tag, data[start:end]))
        position = end
    if position != len(data):
        raise RuntimeError("Trailing bank data")
    return result


def encode_chunk(tag, payload):
    return tag + struct.pack("<I", len(payload)) + payload


def decode_header(data):
    result = bytearray(data)
    if result[:4] != b"BKHD":
        raise RuntimeError("Invalid bank header")
    version = struct.unpack_from("<I", result, 8)[0]
    if version == 150:
        return result
    if version != (150 ^ WOT_HEADER_XOR[8]):
        raise RuntimeError("Unknown bank header encoding")
    for offset, key in WOT_HEADER_XOR.items():
        struct.pack_into("<I", result, offset, struct.unpack_from("<I", result, offset)[0] ^ key)
    return result


def encode_header(data):
    result = bytearray(data)
    if struct.unpack_from("<I", result, 8)[0] != 150:
        raise RuntimeError("Unexpected decoded bank version")
    for offset, key in WOT_HEADER_XOR.items():
        struct.pack_into("<I", result, offset, struct.unpack_from("<I", result, offset)[0] ^ key)
    return result


def hirc_records(payload):
    if len(payload) < 4:
        raise RuntimeError("Invalid HIRC chunk")
    count = struct.unpack_from("<I", payload, 0)[0]
    records = []
    position = 4
    for _ in range(count):
        if position + 5 > len(payload):
            raise RuntimeError("Truncated HIRC record")
        object_type = payload[position]
        size = struct.unpack_from("<I", payload, position + 1)[0]
        start = position + 5
        end = start + size
        if size < 4 or end > len(payload):
            raise RuntimeError("Invalid HIRC record size")
        records.append((object_type, bytearray(payload[start:end])))
        position = end
    if position != len(payload):
        raise RuntimeError("Trailing HIRC data")
    return records


def encode_hirc(records):
    result = bytearray(struct.pack("<I", len(records)))
    for object_type, payload in records:
        result.extend(struct.pack("<BI", object_type, len(payload)))
        result.extend(payload)
    return bytes(result)


def didx_ids(payload):
    if len(payload) % 12:
        raise RuntimeError("Invalid DIDX chunk")
    return {struct.unpack_from("<I", payload, position)[0] for position in range(0, len(payload), 12)}


def pck_table(data, position, section_size):
    if section_size == 0:
        return [], position
    section_end = position + section_size
    count = struct.unpack_from("<I", data, position)[0]
    position += 4
    if count == 0:
        return [], section_end
    entry_size = (section_size - 4) // count
    if entry_size not in (20, 24):
        raise RuntimeError("Unsupported PCK table entry size: {}".format(entry_size))
    offsets = [position + index * entry_size for index in range(count)]
    return offsets, section_end


def pck_id_offsets(data):
    if data[:4] != b"AKPK" or len(data) < 28:
        raise RuntimeError("Invalid PCK header")
    header_size = struct.unpack_from("<I", data, 4)[0]
    section_sizes = list(struct.unpack_from("<III", data, 12))
    section_total = sum(section_sizes) + 0x10
    section_sizes.append(struct.unpack_from("<I", data, 24)[0] if section_total < header_size else 0)
    position = 28 + section_sizes[0]
    offsets = []
    for section_size in section_sizes[1:]:
        table_offsets, position = pck_table(data, position, section_size)
        offsets.extend(table_offsets)
    return offsets


def package_ids(path):
    data = path.read_bytes()
    return {struct.unpack_from("<I", data, offset)[0] for offset in pck_id_offsets(data)}


def package_entries(path):
    data = path.read_bytes()
    result = {}
    banks, sounds, externals = read_pck(path)
    for entry in banks + sounds + externals:
        media = data[entry["offset"]:entry["offset"] + entry["size"]]
        if len(media) != entry["size"]:
            raise RuntimeError("Truncated PCK media: {}".format(entry["id"]))
        result[entry["id"]] = media
    return result


def allocate_id(label, used, assigned):
    suffix = 0
    while True:
        value = short_id(label if suffix == 0 else "{}_{}".format(label, suffix))
        if value not in used and value not in assigned:
            return value
        suffix += 1


def replacement_ids(bank_name, records, media_ids):
    object_ids = {struct.unpack_from("<I", payload, 0)[0] for _, payload in records}
    event_names = {short_id(name): name for name in WPN_EVENTS} if bank_name == "wpn" else {}
    replacements = {}
    used = object_ids | media_ids
    for object_type, payload in records:
        object_id = struct.unpack_from("<I", payload, 0)[0]
        if object_type == 4 and object_id in event_names:
            label = "oldshoot_" + event_names[object_id]
        else:
            label = "oldshoot_{}_{}".format(bank_name, object_id)
        replacements[object_id] = allocate_id(label, used, set(replacements.values()))
    for media_id in sorted(media_ids):
        replacements[media_id] = allocate_id("oldshoot_media_{}_{}".format(bank_name, media_id), used, set(replacements.values()))
    return replacements, event_names


def patch_records(records, replacements, required_ids):
    patterns = {struct.pack("<I", source): struct.pack("<I", target) for source, target in replacements.items()}
    counts = {source: 0 for source in replacements}
    result = []
    for object_type, source_payload in records:
        payload = bytes(source_payload)
        for source, target in patterns.items():
            count = payload.count(source)
            if count:
                payload = payload.replace(source, target)
                counts[struct.unpack("<I", source)[0]] += count
        result.append((object_type, payload))
    missing = [source for source in required_ids if counts[source] == 0]
    if missing:
        raise RuntimeError("Unpatched HIRC objects: " + ", ".join(str(value) for value in missing))
    return result, counts


def patch_didx(payload, replacements):
    result = bytearray(payload)
    for position in range(0, len(result), 12):
        media_id = struct.unpack_from("<I", result, position)[0]
        struct.pack_into("<I", result, position, replacements[media_id])
    return bytes(result)


def embedded_entries(didx, data):
    result = {}
    for position in range(0, len(didx), 12):
        media_id, offset, size = struct.unpack_from("<III", didx, position)
        media = data[offset:offset + size]
        if len(media) != size:
            raise RuntimeError("Truncated BNK media: {}".format(media_id))
        result[media_id] = media
    return result


def embed_media(source_chunks, source_package, records):
    didx_payloads = [payload for tag, payload in source_chunks if tag == b"DIDX"]
    data_payloads = [payload for tag, payload in source_chunks if tag == b"DATA"]
    if len(didx_payloads) != 1 or len(data_payloads) != 1:
        raise RuntimeError("Expected one DIDX and DATA chunk")
    didx = didx_payloads[0]
    embedded = embedded_entries(didx, data_payloads[0])
    packaged = package_entries(source_package)
    media = dict(embedded)
    media.update(packaged)
    new_didx = bytearray()
    new_data = bytearray()
    sizes = {}
    for position in range(0, len(didx), 12):
        media_id = struct.unpack_from("<I", didx, position)[0]
        payload = media[media_id]
        while len(new_data) % 16:
            new_data.append(0)
        new_didx.extend(struct.pack("<III", media_id, len(new_data), len(payload)))
        new_data.extend(payload)
        sizes[media_id] = len(payload)
    new_records = []
    converted = 0
    for object_type, source_payload in records:
        payload = bytearray(source_payload)
        if object_type == 2 and len(payload) >= 18:
            media_id = struct.unpack_from("<I", payload, 9)[0]
            if media_id in packaged:
                payload[8] = 0
                struct.pack_into("<I", payload, 13, sizes[media_id])
                converted += 1
        new_records.append((object_type, payload))
    return bytes(new_didx), bytes(new_data), new_records, converted


def patch_package(source, output, replacements):
    data = bytearray(source.read_bytes())
    for offset in pck_id_offsets(data):
        media_id = struct.unpack_from("<I", data, offset)[0]
        struct.pack_into("<I", data, offset, replacements[media_id])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


def build(source_bank, source_package, output_bank, output_package, bank_name, embed_package=False):
    decoded = decode_header(source_bank.read_bytes())
    source_chunks = chunks(decoded)
    hirc_payloads = [payload for tag, payload in source_chunks if tag == b"HIRC"]
    if len(hirc_payloads) != 1:
        raise RuntimeError("Expected one HIRC chunk")
    records = hirc_records(hirc_payloads[0])
    embedded_ids = set().union(*(didx_ids(payload) for tag, payload in source_chunks if tag == b"DIDX"))
    packed_ids = package_ids(source_package)
    media_ids = embedded_ids | packed_ids
    object_ids = {struct.unpack_from("<I", payload, 0)[0] for _, payload in records}
    overlap = object_ids & media_ids
    if overlap:
        raise RuntimeError("HIRC and media ID collision: " + ", ".join(str(value) for value in sorted(overlap)))
    embedded_didx = None
    embedded_data = None
    converted_streams = 0
    if embed_package:
        embedded_didx, embedded_data, records, converted_streams = embed_media(source_chunks, source_package, records)
    replacements, event_names = replacement_ids(bank_name, records, media_ids)
    patched_records, reference_counts = patch_records(records, replacements, object_ids)
    bank_id = short_id(output_bank.stem)
    result = bytearray()
    for tag, payload in source_chunks:
        if tag == b"BKHD":
            patched = bytearray(payload)
            if len(patched) < 8:
                raise RuntimeError("Invalid BKHD payload")
            struct.pack_into("<I", patched, 4, bank_id)
            result.extend(encode_chunk(tag, patched))
        elif tag == b"DIDX":
            result.extend(encode_chunk(tag, patch_didx(embedded_didx if embed_package else payload, replacements)))
        elif tag == b"DATA" and embed_package:
            result.extend(encode_chunk(tag, embedded_data))
        elif tag == b"STID":
            continue
        elif tag == b"HIRC":
            result.extend(encode_chunk(tag, encode_hirc(patched_records)))
        else:
            result.extend(encode_chunk(tag, payload))
    output_bank.parent.mkdir(parents=True, exist_ok=True)
    output_bank.write_bytes(encode_header(result))
    if output_package is not None:
        patch_package(source_package, output_package, replacements)
    mapped_events = {
        name: "oldshoot_" + name
        for event_id, name in event_names.items()
        if event_id in replacements
    }
    return {
        "bank": bank_name,
        "hirc_objects": len(records),
        "events": sum(1 for object_type, _ in records if object_type == 4),
        "mapped_events": mapped_events,
        "media": len(media_ids),
        "embedded_media": len(embedded_ids),
        "packaged_media": len(packed_ids),
        "patched_references": sum(reference_counts.values()),
        "converted_streams": converted_streams,
        "output_bank_bytes": output_bank.stat().st_size,
        "output_package_bytes": output_package.stat().st_size if output_package is not None else 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_bank", type=Path)
    parser.add_argument("source_package", type=Path)
    parser.add_argument("output_bank", type=Path)
    parser.add_argument("output_package", type=Path, nargs="?")
    parser.add_argument("--bank-name", required=True)
    parser.add_argument("--embed-package", action="store_true")
    args = parser.parse_args()
    if args.output_package is None and not args.embed_package:
        parser.error("output_package is required unless --embed-package is used")
    summary = build(args.source_bank, args.source_package, args.output_bank, args.output_package, args.bank_name, args.embed_package)
    for key, value in summary.items():
        print("{}: {}".format(key, value))


if __name__ == "__main__":
    main()
