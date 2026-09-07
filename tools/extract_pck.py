import argparse
import struct
from pathlib import Path


def read_u32(stream):
    data = stream.read(4)
    if len(data) != 4:
        raise EOFError("Unexpected end of PCK")
    return struct.unpack("<I", data)[0]


def read_u64(stream):
    data = stream.read(8)
    if len(data) != 8:
        raise EOFError("Unexpected end of PCK")
    return struct.unpack("<Q", data)[0]


def skip_section(stream, size):
    stream.seek(size, 1)


def read_table(stream, section_size):
    if section_size == 0:
        return []
    section_start = stream.tell()
    count = read_u32(stream)
    if count == 0:
        stream.seek(section_start + section_size)
        return []
    entry_size = (section_size - 4) // count
    entries = []
    for _ in range(count):
        file_id = read_u32(stream)
        block_size = read_u32(stream)
        size = read_u64(stream) if entry_size == 0x18 else read_u32(stream)
        offset = read_u32(stream)
        language_id = read_u32(stream)
        if entry_size == 0x18:
            stream.seek(entry_size - 24, 1)
        entries.append({
            "id": file_id,
            "size": size,
            "offset": offset * block_size if block_size else offset,
            "language_id": language_id,
        })
    stream.seek(section_start + section_size)
    return entries


def read_pck(path):
    with path.open("rb") as stream:
        if stream.read(4) != b"AKPK":
            raise ValueError("Wrong PCK header magic")
        header_size = read_u32(stream)
        read_u32(stream)
        section_sizes = [read_u32(stream), read_u32(stream), read_u32(stream)]
        section_total = sum(section_sizes) + 0x10
        section_sizes.append(read_u32(stream) if section_total < header_size else 0)
        skip_section(stream, section_sizes[0])
        banks = read_table(stream, section_sizes[1])
        sounds = read_table(stream, section_sizes[2])
        externals = read_table(stream, section_sizes[3])
    return banks, sounds, externals


def extract(path, output, requested_ids):
    banks, sounds, externals = read_pck(path)
    selected = [entry for entry in sounds + externals if not requested_ids or entry["id"] in requested_ids]
    output.mkdir(parents=True, exist_ok=True)
    with path.open("rb") as stream:
        for entry in selected:
            stream.seek(entry["offset"])
            data = stream.read(entry["size"])
            if len(data) != entry["size"]:
                raise EOFError(f"Unexpected end of PCK media {entry['id']}")
            (output / f"{entry['id']}.wem").write_bytes(data)
    print(f"Banks: {len(banks)}")
    print(f"Sounds: {len(sounds)}")
    print(f"Externals: {len(externals)}")
    print(f"Extracted: {len(selected)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("ids", nargs="*", type=int)
    args = parser.parse_args()
    extract(args.source, args.output, set(args.ids))


if __name__ == "__main__":
    main()
