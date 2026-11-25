"""MT Framework layouts (`.lyt`, rLayout): MH4U's HUD and menu layouts (specs/lyt.md).

A layout is a header, a table of texture slots, a depth-first chain of object records and a
table of root pointers. Families of panes are grouped under type-2 root records: the game
registers one runtime object per type-2 node (the root count is header +0x08), and every
non-root record that follows a root in the file belongs to it until the next root or the
`0xff` terminator. Four types carry drawable data: picture (0), group (1), text (3) and
touch boundary (4); type 5 never occurs in MH4U.

The layout is MH4U's `rLayout` resource (class id `0x15302ef4`), loaded from the language's
`<lang>\\data\\core_*.arc` archive. Loaders name their layouts by path (`lyt\\quest\\ui202`
and so on) from tables in the code, so the file itself stores no path.

Source: our reading of MH4U USA v1.3.0's code - the loader `0x00aed0a0` (magic, version,
rebasing, texture slots, node chain), `sMhLayout::registerLayout` `0x00c0f424` (the root
count) and the node converter `0x00b039dc` (record sizes and the per-type fields). Checked on
every MH4U layout (specs/lyt.md, check LY1).
"""
from __future__ import annotations

import struct
import zlib
from collections import Counter
from dataclasses import dataclass

MAGIC = b"lyt\0"
VERSION = 0x70C
HEADER = 0x30

# Node record size by type, from the interface of the loader's type dispatch (`0x00aed280`):
# 0 picture, 1 group, 2 root, 3 text, 4 boundary, 5 a sixth kind that never occurs.
NODE_SIZES: dict[int, int] = {0: 0x6C, 1: 0x38, 2: 0x28, 3: 0x7C, 4: 0x30, 5: 0x88}
TYPE_NAMES: dict[int, str] = {
    0: "picture", 1: "group", 2: "root", 3: "text", 4: "boundary", 5: "unknown",
}
TERMINATOR = 0xFF
ZERO_AFTER_TERMINATOR = 0x10


class LytError(ValueError):
    pass


@dataclass(frozen=True)
class Texture:
    """One 8-byte texture slot: the word the loader fills and a path, or None for an empty slot."""
    slot: int
    path: str | None


@dataclass(frozen=True)
class Node:
    offset: int
    type: int
    depth: int
    name_hash: int
    name: str
    size: int                  # the +0x10 word; its meaning is unknown (specs/lyt.md)
    fields: dict               # the type's own fields, by name from specs/lyt.md
    raw: bytes                 # the whole record, unchanged

    @property
    def type_name(self) -> str:
        return TYPE_NAMES.get(self.type, f"0x{self.type:02x}")


@dataclass(frozen=True)
class Layout:
    version: int
    root_count: int
    textures: tuple[Texture, ...]
    nodes: tuple[Node, ...]
    roots: tuple[int, ...]     # indices into nodes, in file order
    data: bytes

    def children(self, root: int) -> tuple[Node, ...]:
        """The nodes a root owns: the records after it, up to the next root or the terminator."""
        if root not in self.roots:
            raise LytError(f"node {root} is not a root")
        end = next((i for i in self.roots if i > root), len(self.nodes))
        return self.nodes[root + 1:end]

    def find(self, name: str) -> Node | None:
        return next((n for n in self.nodes if n.name == name), None)


def _cstring(data: bytes, off: int) -> str:
    if off >= len(data):
        raise LytError(f"string offset 0x{off:x} is outside the file")
    end = data.find(b"\0", off)
    if end < 0:
        raise LytError(f"string at 0x{off:x} has no terminator")
    try:
        return data[off:end].decode("ascii")
    except UnicodeDecodeError as e:
        raise LytError(f"string at 0x{off:x} is not ASCII") from e


def _text(data: bytes, off: int) -> str:
    """A NUL-terminated UTF-16LE string at a file offset."""
    if off % 2 or off >= len(data):
        raise LytError(f"text offset 0x{off:x} is outside the file or unaligned")
    end = off
    while end + 1 < len(data) and data[end:end + 2] != b"\0\0":
        end += 2
    if end + 1 >= len(data):
        raise LytError(f"text at 0x{off:x} has no terminator")
    return data[off:end].decode("utf-16-le")


def _fields(data: bytes, off: int, typ: int) -> dict:
    """The type's own fields, from the converter at 0x00b039dc."""
    if typ == 0:       # picture 0x6c
        x, y, z = struct.unpack_from("<3f", data, off + 0x14)
        w, h = struct.unpack_from("<2f", data, off + 0x20)
        sx, sy, rot = struct.unpack_from("<3f", data, off + 0x28)
        f34, f38, f3c = struct.unpack_from("<3f", data, off + 0x34)
        colors = struct.unpack_from("<4I", data, off + 0x40)
        f50, f54 = struct.unpack_from("<2f", data, off + 0x50)
        return {
            "x": x, "y": y, "z": z, "w": w, "h": h,
            "scale_x": sx, "scale_y": sy, "rotation": rot,
            "f34": f34, "f38": f38, "f3c": f3c,
            "colors": tuple(f"0x{c:08x}" for c in colors),
            "f50": f50, "f54": f54,
            "flags": data[off + 0x58], "byte_59": data[off + 0x59],
            "word_5c": struct.unpack_from("<I", data, off + 0x5C)[0],
            "word_60": struct.unpack_from("<I", data, off + 0x60)[0],
            "word_64": struct.unpack_from("<I", data, off + 0x64)[0],
            "word_68": struct.unpack_from("<I", data, off + 0x68)[0],
        }
    if typ == 1:       # group 0x38
        x, y = struct.unpack_from("<2f", data, off + 0x14)
        return {
            "x": x, "y": y,
            "words": struct.unpack_from("<7I", data, off + 0x1C),
        }
    if typ == 2:       # root 0x28
        x, y = struct.unpack_from("<2f", data, off + 0x14)
        return {
            "x": x, "y": y,
            "word_1c": struct.unpack_from("<I", data, off + 0x1C)[0],
            "float_20": struct.unpack_from("<f", data, off + 0x20)[0],
            "flags": struct.unpack_from("<I", data, off + 0x24)[0],
        }
    if typ == 3:       # text 0x7c
        return {
            "text": _text(data, struct.unpack_from("<I", data, off + 0x14)[0]),
            "words_18": struct.unpack_from("<2I", data, off + 0x18),
            "words_20": struct.unpack_from("<22I", data, off + 0x20),
            "flags": struct.unpack_from("<I", data, off + 0x78)[0],
        }
    if typ == 4:       # boundary 0x30
        x, y, w, h = struct.unpack_from("<4f", data, off + 0x14)
        return {
            "x": x, "y": y, "w": w, "h": h,
            "scale": struct.unpack_from("<2I", data, off + 0x24),
            "flags": data[off + 0x2C],
        }
    return {}


def read(data: bytes) -> Layout:
    if len(data) < HEADER:
        raise LytError("shorter than the 0x30-byte header")
    if data[:4] != MAGIC:
        raise LytError(f"not a layout: magic {data[:4]!r}")
    (version,) = struct.unpack_from("<I", data, 4)
    if version != VERSION:
        raise LytError(f"version 0x{version:x}, not 0x{VERSION:x}")
    (roots, textures, groups_text, pictures, unknown, texts, boundaries,
     texture_off, node_off, root_off) = struct.unpack_from("<10I", data, 8)
    if texture_off < HEADER or node_off <= texture_off or root_off <= node_off:
        raise LytError("the header's three offsets are not in file order")
    if texture_off + 8 * textures > node_off:
        raise LytError("the texture slots overlap the node chain")
    if root_off + 4 * roots != len(data):
        raise LytError(f"the root table would end at 0x{root_off + 4 * roots:x}, the file at 0x{len(data):x}")

    slots = []
    for i in range(textures):
        slot, path_off = struct.unpack_from("<II", data, texture_off + 8 * i)
        slots.append(Texture(slot, _cstring(data, path_off) if path_off else None))

    nodes: list[Node] = []
    pos = node_off
    while True:
        if pos + 4 > len(data):
            raise LytError("the node chain runs past the file")
        (typ,) = struct.unpack_from("<I", data, pos)
        if typ == TERMINATOR:
            break
        if typ not in NODE_SIZES:
            raise LytError(f"node type {typ} at 0x{pos:x}")
        size = NODE_SIZES[typ]
        if pos + size > len(data):
            raise LytError(f"{TYPE_NAMES[typ]} at 0x{pos:x} runs past the file")
        depth, name_hash, name_off, field = struct.unpack_from("<IIII", data, pos + 4)
        name = _cstring(data, name_off) if name_off else ""
        if name:
            if name_hash != (~zlib.crc32(name.encode("ascii")) & 0xFFFFFFFF):
                raise LytError(f"node {name!r} at 0x{pos:x} has hash 0x{name_hash:08x}")
        elif name_hash:
            raise LytError(f"unnamed node at 0x{pos:x} has hash 0x{name_hash:08x}")
        nodes.append(Node(pos, typ, depth, name_hash, name, field, _fields(data, pos, typ),
                          data[pos:pos + size]))
        pos += size

    if data[pos + 4:pos + 4 + ZERO_AFTER_TERMINATOR] != bytes(ZERO_AFTER_TERMINATOR):
        raise LytError("the terminator is not followed by 0x10 zero bytes")
    counts = Counter(n.type for n in nodes)
    for count, want, label in ((roots, counts[2], "root"), (groups_text, counts[1] + counts[3],
                                                            "group + text"),
                               (pictures, counts[0], "picture"), (texts, counts[3], "text"),
                               (boundaries, counts[4], "boundary")):
        if count != want:
            raise LytError(f"the header says {count} {label} nodes, the chain holds {want}")
    if unknown:
        raise LytError(f"the header's unknown count is {unknown}, not 0")
    return Layout(version, roots, tuple(slots), tuple(nodes),
                  tuple(i for i, n in enumerate(nodes) if n.type == 2), data)


def check(data: bytes) -> Counter:
    """Check LY1's per-file tallies: read the layout and count what it holds."""
    c: Counter = Counter()
    try:
        layout = read(data)
    except (LytError, struct.error, IndexError):
        c["LY1 not read"] += 1
        return c
    c["LY1 read"] += 1
    c[f"version 0x{layout.version:x}"] += 1
    c[f"{layout.root_count} roots"] += 1
    for node in layout.nodes:
        c[f"{node.type_name} nodes"] += 1
        if not node.name:
            c["unnamed nodes"] += 1
        elif node.type in (0, 1, 2, 4):
            c["named pane nodes"] += 1
    for t in layout.textures:
        c["texture paths" if t.path else "empty texture slots"] += 1
    texts = [n for n in layout.nodes if n.type == 3]
    if texts:
        c["text strings"] += len(texts)
        c["text strings with characters"] += sum(1 for n in texts if n.fields["text"])
    for root in layout.roots:
        if not layout.children(root):
            c["roots with no child"] += 1
    return c


def to_json(layout: Layout) -> dict:
    """The layout as JSON-able data for `mhuc lyt dump`; names and numbers only."""
    return {
        "version": f"0x{layout.version:x}",
        "root_count": layout.root_count,
        "textures": [{"slot": t.slot, "path": t.path} for t in layout.textures],
        "nodes": [
            {"offset": n.offset, "type": n.type_name, "depth": n.depth,
             "hash": f"0x{n.name_hash:08x}", "name": n.name, "size": n.size, **n.fields}
            for n in layout.nodes
        ],
    }
