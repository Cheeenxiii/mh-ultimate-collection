"""MT Framework Mobile models (`.mod`, rModel, version 0xE6), as specs/mod.md lays them out: the header (verified,
check M2) and the 48-byte mesh records (fields from MHGU Definitive Edition's `mod.py`, after RevilLib: unverified,
check M3). `info` gives a summary of counts, `bones` the bone records (check M4) and `check` check M3's counts.
"""
from __future__ import annotations

import struct
from collections import Counter

MESH = 0x30
GROUP = 0x20
BONE = 0x18


class ModError(ValueError):
    pass


def header(d: bytes) -> dict:
    if len(d) < 0x40 or d[:4] != b"MOD\0":
        raise ModError("not a MOD")
    (version, bones, meshes, materials, vertices, indices) = struct.unpack_from("<HHHHII", d, 4)[0:6]
    w = struct.unpack_from("<12I", d, 0x10)
    return {"version": version, "bones": bones, "meshes": meshes, "materials": materials, "vertices": vertices,
            "indices": indices, "edges": w[1], "vertex_buffer_size": w[2], "groups": w[4], "skins": w[5],
            "bones_at": w[6], "groups_at": w[7], "materials_at": w[8], "meshes_at": w[9], "vertex_buffer_at": w[10],
            "index_buffer_at": w[11]}


def meshes(d: bytes, h: dict | None = None) -> list[dict]:
    h = h or header(d)
    at = h["meshes_at"]
    if at + MESH * h["meshes"] > len(d):
        raise ModError("mesh table outside the file")
    out = []
    for i in range(h["meshes"]):  # "group" is a group id (group_ids), not an index: check M3
        o = at + MESH * i
        draw, nverts, data0, data1, vstart, vstream, vfmt, istart, icount, ivoff = struct.unpack_from("<HHIIIIIIII",
                                                                                                    d, o)
        skin, env = d[o + 0x28], d[o + 0x29]
        out.append({"draw_mode": draw, "vertices": nverts, "group": data0 & 0xFFF, "material": data0 >> 12 & 0xFFF,
                    "lod": data0 >> 24, "stride": data1 >> 16 & 0xFF, "vertex_start": vstart,
                    "vertex_stream_offset": vstream, "vertex_format": vfmt, "index_start": istart,
                    "index_count": icount, "index_value_offset": ivoff, "skin_bone_begin": skin, "envelopes": env})
    return out


def group_ids(d: bytes, h: dict | None = None) -> list[int]:
    """The first u32 of each 0x20-byte group entry: the id a mesh's group field names (check M3)."""
    h = h or header(d)
    if h["groups_at"] + GROUP * h["groups"] > len(d):
        raise ModError("group table outside the file")
    return [struct.unpack_from("<I", d, h["groups_at"] + GROUP * i)[0] for i in range(h["groups"])]


def bones(d: bytes, h: dict | None = None) -> list[dict]:
    """The bone records at `bones_at` (check M4), one 0x18-byte record per bone. `parent` is the
    index of the parent's entry (0xFF at the root) and `parent_id` resolves it to the parent's bone
    id. `mirror`, `furthest`, `parent_distance` and `position` are the names MHGU-DE's `mod.py` gives
    the rest of the record; check M4 reads them but doesn't explain them."""
    h = h or header(d)
    n, at = h["bones"], h["bones_at"]
    if n and (at < 0x40 or at + n * BONE > len(d)):
        raise ModError("bone table outside the file")
    out = []
    for i in range(n):
        o = at + i * BONE
        bid, parent, mirror = d[o], d[o + 1], d[o + 2]
        furthest, distance = struct.unpack_from("<ff", d, o + 4)
        x, y, z = struct.unpack_from("<3f", d, o + 0x0C)
        out.append({"index": i, "id": bid, "parent": parent, "mirror": mirror,
                    "furthest": furthest, "parent_distance": distance, "position": (x, y, z)})
    ids = [b["id"] for b in out]
    for b in out:
        if b["parent"] != 0xFF and b["parent"] >= n:
            raise ModError(f"bone {b['index']} has parent {b['parent']}, past the {n} bones")
        b["parent_id"] = 0xFF if b["parent"] == 0xFF else ids[b["parent"]]
    return out


def info(d: bytes) -> dict:
    h = header(d)
    ms = meshes(d, h)
    return {"header": h, "meshes": len(ms), "vertex_formats": sorted({m["vertex_format"] for m in ms}),
            "strides": sorted({m["stride"] for m in ms}), "materials_used": sorted({m["material"] for m in ms})}


def check(d: bytes) -> Counter:
    """Check M3: the mesh records against the header and the buffers."""
    c = Counter()
    try:
        h = header(d)
        ms = meshes(d, h)
        ids = set(group_ids(d, h))
    except (ModError, struct.error):
        c["M3 not readable"] += 1
        return c
    c["M3 readable"] += 1
    c["M3 mesh vertices sum to the header's" if sum(m["vertices"] for m in ms) == h["vertices"] else
      "M3 mesh vertices don't sum to the header's"] += 1
    c["M3 materials within the count" if all(m["material"] < max(h["materials"], 1) for m in ms) else
      "M3 a material index over the count"] += 1
    c["M3 group ids in the group table" if all(m["group"] in ids for m in ms) or not h["groups"] else
      "M3 a group id not in the group table"] += 1
    ib_entries = (len(d) - h["index_buffer_at"]) // 2
    c["M3 index ranges inside the index buffer" if all(m["index_start"] + m["index_count"] <= ib_entries
                                                       for m in ms) else "M3 an index range past the buffer"] += 1
    vb_end = h["vertex_buffer_at"] + h["vertex_buffer_size"]
    c["M3 vertex streams inside the vertex buffer" if all(
        h["vertex_buffer_at"] + m["vertex_stream_offset"] + m["stride"] * (m["vertex_start"] + m["vertices"])
        <= vb_end for m in ms) else "M3 a vertex stream past the buffer"] += 1
    for m in ms:
        c[f"M3 stride {m['stride']}"] += 1
    return c
