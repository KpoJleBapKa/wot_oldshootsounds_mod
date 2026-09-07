import io
import struct


PACKED_SECTION_MAGIC = 0x62A14E45


class Node:
    def __init__(self, value=None):
        self.value = value
        self.children = []

    def add(self, name, node):
        self.children.append((name, node))


class Reader:
    def __init__(self, data):
        self.stream = io.BytesIO(data)
        self.strings = []

    def unpack(self, pattern):
        size = struct.calcsize(pattern)
        data = self.stream.read(size)
        if len(data) != size:
            raise EOFError("Unexpected end of packed XML")
        return struct.unpack(pattern, data)[0]

    def read_null_string(self):
        result = bytearray()
        while True:
            value = self.stream.read(1)
            if not value:
                raise EOFError("Unexpected end of packed XML string table")
            if value == b"\0":
                return result.decode("utf-8", errors="replace")
            result.extend(value)

    def read_string_table(self):
        while True:
            value = self.read_null_string()
            if not value:
                return
            self.strings.append(value)

    def read_data(self, descriptor, previous_offset):
        type_id = descriptor >> 28
        end_offset = descriptor & 0x0FFFFFFF
        size = end_offset - previous_offset
        if size < 0:
            raise ValueError("Invalid packed XML data offset")
        if type_id == 0:
            return self.read_section()
        data = self.stream.read(size)
        if len(data) != size:
            raise EOFError("Unexpected end of packed XML data")
        if type_id == 1:
            return Node(data.decode("utf-8", errors="replace"))
        if type_id == 2:
            if size == 0:
                return Node(0)
            if size not in (1, 2, 4, 8):
                raise ValueError(f"Unsupported packed XML integer size: {size}")
            return Node(int.from_bytes(data, byteorder="little", signed=True))
        if type_id == 3:
            if size % 4:
                raise ValueError(f"Unsupported packed XML float size: {size}")
            values = struct.unpack(f"<{size // 4}f", data)
            return Node(list(values))
        if type_id == 4:
            return Node(bool(size))
        if type_id in (5, 6):
            return Node(data)
        raise ValueError(f"Unsupported packed XML data type: {type_id}")

    def read_section(self):
        child_count = self.unpack("<H")
        own_descriptor = self.unpack("<I")
        children = [(self.unpack("<H"), self.unpack("<I")) for _ in range(child_count)]
        node = self.read_data(own_descriptor, 0)
        previous_offset = own_descriptor & 0x0FFFFFFF
        for name_index, descriptor in children:
            if name_index >= len(self.strings):
                raise ValueError(f"Invalid packed XML string index: {name_index}")
            node.add(self.strings[name_index], self.read_data(descriptor, previous_offset))
            previous_offset = descriptor & 0x0FFFFFFF
        return node

    def read(self):
        magic = self.unpack("<I")
        if magic != PACKED_SECTION_MAGIC:
            raise ValueError("Wrong packed XML header magic")
        version = self.unpack("<B")
        if version != 0:
            raise ValueError(f"Unsupported packed XML version: {version}")
        self.read_string_table()
        return self.read_section()


def decode(data):
    return Reader(data).read()


def find_sound_records(node, path=()):
    direct = {}
    for name, child in node.children:
        direct.setdefault(name, []).append(child.value)
    records = []
    if "wwsoundPC" in direct or "wwsoundNPC" in direct:
        records.append({
            "path": "/".join(path),
            "wwsoundPC": direct.get("wwsoundPC", []),
            "wwsoundNPC": direct.get("wwsoundNPC", []),
        })
    for name, child in node.children:
        records.extend(find_sound_records(child, path + (name,)))
    return records


def find_matching_values(node, predicate, path=()):
    records = []
    if isinstance(node.value, str) and predicate(node.value):
        records.append({"path": "/".join(path), "value": node.value})
    for name, child in node.children:
        records.extend(find_matching_values(child, predicate, path + (name,)))
    return records
