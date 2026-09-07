import argparse
import re
import struct
from pathlib import Path

from extract_pck import read_pck


ACTION_PATTERN = re.compile(r"^#\s+CAkActionPlay\[\d+\]\s+(\d+)")
SOURCE_PATTERN = re.compile(r"^#\s+Source\s+(\d+)")


def event_sources(path):
    actions = {}
    current_action = None
    for line in path.read_text(encoding="utf-8").splitlines():
        action_match = ACTION_PATTERN.match(line)
        if action_match:
            current_action = int(action_match.group(1))
            actions.setdefault(current_action, set())
            continue
        source_match = SOURCE_PATTERN.match(line)
        if current_action is not None and source_match:
            actions[current_action].add(int(source_match.group(1)))
    return actions


def pck_entries(path):
    banks, sounds, externals = read_pck(path)
    return {entry["id"]: entry for entry in banks + sounds + externals}


def bnk_entries(path):
    data = path.read_bytes()
    position = 0
    index = None
    media = None
    while position + 8 <= len(data):
        tag = data[position:position + 4]
        size = struct.unpack_from("<I", data, position + 4)[0]
        start = position + 8
        end = start + size
        if tag == b"DIDX":
            index = data[start:end]
        elif tag == b"DATA":
            media = (start, data)
        position = end
    if index is None or media is None:
        return {}
    media_start, bank_data = media
    entries = {}
    for position in range(0, len(index), 12):
        media_id, offset, size = struct.unpack_from("<III", index, position)
        entries[media_id] = {"data": bank_data[media_start + offset:media_start + offset + size]}
    return entries


def extract(txtp_path, pck_path, bnk_path, output):
    actions = event_sources(txtp_path)
    packed = pck_entries(pck_path)
    embedded = bnk_entries(bnk_path)
    with pck_path.open("rb") as stream:
        for action_id, source_ids in actions.items():
            action_output = output / str(action_id)
            action_output.mkdir(parents=True, exist_ok=True)
            for source_id in sorted(source_ids):
                destination = action_output / f"{source_id}.wem"
                if source_id in packed:
                    entry = packed[source_id]
                    stream.seek(entry["offset"])
                    destination.write_bytes(stream.read(entry["size"]))
                elif source_id in embedded:
                    destination.write_bytes(embedded[source_id]["data"])
    all_sources = set().union(*actions.values()) if actions else set()
    found = set(packed) | set(embedded)
    print(f"Actions: {len(actions)}")
    print(f"Sources: {len(all_sources)}")
    print(f"Extracted: {len(all_sources & found)}")
    print(f"Missing: {len(all_sources - found)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("txtp", type=Path)
    parser.add_argument("pck", type=Path)
    parser.add_argument("bnk", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    extract(args.txtp, args.pck, args.bnk, args.output)


if __name__ == "__main__":
    main()
