#!/usr/bin/env python3
"""The in-image action-start record a source monster's move passes to the engine, and its
MH4U counterpart.

Some of MH3U's Rathian handlers pass the engine a pointer into the game's image instead of
starting their animations themselves: 0x0068dd78 (3/5) and 0x0083cc24 (action 4) hand
0x00b0b168 and 0x00b0b194 to the two readers 0x0084704c and 0x00847134. MH4U's paired handlers
do the same with records of their own: 0x006d5e98 (3/5 and 3/9) hands 0x00e09558 to the
readers 0x00938748 and 0x00938834. The 44-byte record holds two animation starts, the two
animations a turn takes, two integers and a threshold and a clamp (specs/actiondata.md).

The two games' records are the same size and the readers read the same offsets, but not every
field means the same thing: the motion indices are numbered differently, and MH4U passes the
two words at +0x0C and +0x1C as a flag word while MH3U's copies of them reach a callee that
never reads them. So a record cannot be copied across games; `rebuild` makes MH4U's from
MH3U's: the motions go through the same-animation map, the two integers and the two floats
are carried, and the two flag words come from MH4U's own records.

    show   --game mh3u|mh4u --exheader EXHEADER --code CODE --address ADDR [--count N]
    curve  --game mh3u|mh4u --exheader EXHEADER --code CODE --address ADDR
    check  --mh3u-exheader .. --mh3u-code .. --mh4u-exheader .. --mh4u-code .. \
           [--mh3u-romfs ROMFS --mh4u-romfs ROMFS]

`check` is the procedure behind checks N1 to N4 of specs/actiondata.md: it verifies that
3/5's two records carry the same integers and floats, that the four motion fields pair
animations with the same LMT signature (frames and loop frame, the R1 comparison), that
MH4U's own records all hold the same flag word, and then rebuilds 3/5's record and compares
it with MH4U's own. It also rebuilds action 4's record, which has no MH4U counterpart to
compare (MH4U's uEm001 has no action 4). Counts and field names only, never the games'
values in a file; stdout is for reading the dumps, not for committing.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RECORD = 0x2C           # bytes
CURVE_KEY = 0x08        # bytes per (time, value) key
CURVE_KEYS_MAX = 0x1000 // CURVE_KEY
MH3U_SHARED = 0x00B0B168    # 3/5's record, passed by 0x0068dd78
MH3U_ACTION4 = 0x00B0B194   # action 4's record, passed by 0x0083cc24
MH3U_CURVES = "0x00c4ed68,0x00c4eef0,0x00c4ef28"   # action 4's sub-handlers pass these
MH4U_RECORDS = 0x00E09558   # uEm001's records; the first is 3/5's, passed by 0x006d5e98
MH4U_RECORD_COUNT = 4


@dataclass(frozen=True)
class Field:
    offset: int
    size: int
    kind: str          # u16, s32, f32
    name: str
    role: str          # motion, argument, flag, float


# The readers' offsets. "a" is the quartet the second reader (3U 0x00847134 / MH4U 0x00938834)
# starts, "b" the first reader's (3U 0x0084704C / MH4U 0x00938748); the turn pair and the two
# floats sit at the end.
FIELDS = (
    Field(0x00, 2, "u16", "motion a", "motion"),
    Field(0x04, 4, "s32", "argument a1", "argument"),
    Field(0x08, 4, "s32", "argument a2", "argument"),
    Field(0x0C, 4, "u32", "flags a", "flag"),
    Field(0x10, 2, "u16", "motion b", "motion"),
    Field(0x14, 4, "s32", "argument b1", "argument"),
    Field(0x18, 4, "s32", "argument b2", "argument"),
    Field(0x1C, 4, "u32", "flags b", "flag"),
    Field(0x20, 2, "u16", "turn motion a", "motion"),
    Field(0x22, 2, "u16", "turn motion b", "motion"),
    Field(0x24, 4, "f32", "threshold", "float"),
    Field(0x28, 4, "f32", "clamp", "float"),
)
BY_NAME = {f.name: f for f in FIELDS}
FORMAT = {"u16": "<H", "u32": "<I", "s32": "<i", "f32": "<f"}


class RecordError(ValueError):
    """A record the conversion cannot build."""


def read_record(data: bytes, offset: int = 0) -> dict[str, int | float]:
    """A 44-byte record as {field name: value}. `data` starts at the record."""
    if len(data) < offset + RECORD:
        raise RecordError(f"{RECORD} bytes needed, {len(data) - offset} given")
    return {f.name: struct.unpack_from(FORMAT[f.kind], data, offset + f.offset)[0] for f in FIELDS}


def write_record(record: dict[str, int | float]) -> bytes:
    """The record's bytes, the inverse of read_record."""
    data = bytearray(RECORD)
    for f in FIELDS:
        struct.pack_into(FORMAT[f.kind], data, f.offset, record[f.name])
    return bytes(data)


def rebuild(source: dict[str, int | float], motion_map: dict[int, int],
            flags: int) -> dict[str, int | float]:
    """MH4U's record from MH3U's: motions through `motion_map`, flags from MH4U's own records."""
    missing = sorted({source[f.name] for f in FIELDS
                      if f.role == "motion" and source[f.name] not in motion_map})
    if missing:
        raise RecordError("no target motion for " + ", ".join(f"0x{m:x}" for m in missing))
    return {
        f.name: (motion_map[source[f.name]] if f.role == "motion"
                 else flags if f.role == "flag" else source[f.name])
        for f in FIELDS
    }


def compare(rebuilt: dict[str, int | float],
            target: dict[str, int | float]) -> dict[str, list[str]]:
    """Per role, the field names that differ between a rebuilt record and MH4U's own."""
    out: dict[str, list[str]] = {}
    for f in FIELDS:
        if rebuilt[f.name] != target[f.name]:
            out.setdefault(f.role, []).append(f.name)
    return out


def image_record(code, address: int) -> dict[str, int | float]:
    """The record at `address` in a monster_actions.Code image."""
    start = address - code.base
    return read_record(bytes(code.data[start:start + RECORD]))


def read_curve(data: bytes, offset: int = 0) -> list[tuple[float, float]]:
    """A value curve's (time, value) keys, the ending key included: a negative time ends it."""
    keys: list[tuple[float, float]] = []
    while len(keys) < CURVE_KEYS_MAX:
        at = offset + len(keys) * CURVE_KEY
        if at + CURVE_KEY > len(data):
            raise RecordError("curve runs past the data with no ending key")
        time, value = struct.unpack_from("<ff", data, at)
        keys.append((time, value))
        if time < 0:
            return keys
    raise RecordError(f"no ending key in the first {CURVE_KEYS_MAX} keys")


def image_curve(code, address: int) -> list[tuple[float, float]]:
    start = address - code.base
    return read_curve(bytes(code.data[start:]))


def motion_lists(romfs_path: str, arc_path: str) -> list:
    """A monster's LMT files, in file order, each as monster_motions.read_lmt's animation list."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
    import monster_motions

    from mhuc.formats import arc, romfs

    image = romfs.open_image(romfs_path)
    wanted = "/" + arc_path.lstrip("/")
    for entry in image.files():
        if entry.path == wanted:
            archive = arc.read(image.read(entry))
            return [monster_motions.read_lmt(e.data) for e in archive.entries
                    if e.file_name.endswith(".lmt")]
    raise RecordError(f"{arc_path} isn't in {romfs_path}")


def signature(lmts: list, game: str, motion: int):
    """The animation `motion` names in `lmts`, or None when the index is outside the files."""
    import monster_motions

    file, slot = monster_motions.decode_motion(game, motion)
    if file >= len(lmts) or slot >= len(lmts[file]):
        return None
    return lmts[file][slot]


def same_animation(a, b) -> bool:
    if a is None or b is None:
        return False
    import monster_motions

    return monster_motions.same_motion(a, b)


def candidates(lmts: list, game: str, source_signature) -> list[int]:
    """Every index of `lmts` whose animation has the source's signature."""
    out = []
    for file, animations in enumerate(lmts):
        for slot, animation in enumerate(animations):
            if animation is not None and same_animation(source_signature, animation):
                out.append(file << 8 | slot if game != "mh3u" else file * 100 + slot)
    return out


def _load(args, prefix: str):
    import monster_actions

    class CodeArgs:
        module = None
        crs = None
        base = 0x02000000

    code_args = CodeArgs()
    code_args.exheader = getattr(args, f"{prefix}exheader")
    code_args.code = getattr(args, f"{prefix}code")
    code_args.range = (0, 0)
    return monster_actions.load_code(code_args)


def cmd_show(args) -> int:
    code = _load(args, "")
    for i in range(args.count):
        address = args.address + i * RECORD
        record = image_record(code, address)
        fields = ", ".join(f"{f.name}={record[f.name]}" for f in FIELDS)
        print(f"0x{address:08x}  {fields}")
    return 0


def cmd_curve(args) -> int:
    code = _load(args, "")
    keys = image_curve(code, args.address)
    print(f"0x{args.address:08x}: {len(keys) - 1} key(s) and the ending key")
    for time, value in keys:
        print(f"  time={time:g} value={value:g}")
    return 0


def _flags(records: list[dict]) -> int:
    values = {r[f.name] for r in records for f in FIELDS if f.role == "flag"}
    if len(values) != 1:
        raise RecordError("MH4U's own records disagree on the flag word: "
                          + ", ".join(f"0x{v:x}" for v in sorted(values)))
    return values.pop()


def cmd_check(args) -> int:
    code3 = _load(args, "mh3u_")
    code4 = _load(args, "mh4u_")
    source = image_record(code3, args.mh3u_shared)
    action4 = image_record(code3, args.mh3u_action4)
    target = image_record(code4, args.mh4u_shared)
    mh4u_records = [image_record(code4, args.mh4u_records + i * RECORD)
                    for i in range(args.mh4u_count)]

    problems = 0
    # The four motions pair by field position: both games' readers start the same quartet's
    # motion, so the field is the same slot. The signature check (N2) is what confirms the
    # animations are the same; the map itself is that positional pairing.
    motion_map = {}
    for f in FIELDS:
        if f.role == "motion":
            motion_map[source[f.name]] = target[f.name]

    if args.mh3u_romfs and args.mh4u_romfs:
        lmts3 = motion_lists(args.mh3u_romfs, args.mh3u_arc)
        lmts4 = motion_lists(args.mh4u_romfs, args.mh4u_arc)
        print("animations (N2):")
        for f in FIELDS:
            if f.role != "motion":
                continue
            sig3 = signature(lmts3, "mh3u", source[f.name])
            sig4 = signature(lmts4, "mh4u", target[f.name])
            here = candidates(lmts4, "mh4u", sig3)
            ok = same_animation(sig3, sig4)
            problems += 0 if ok else 1
            print(f"  {f.name}: 3U 0x{source[f.name]:x} -> MH4U 0x{target[f.name]:x}: "
                  f"{'same animation' if ok else 'DIFFERENT animation'}"
                  f" (frame/loop signature, {len(here)} candidate(s))")
    else:
        print("animations: not checked (give --mh3u-romfs and --mh4u-romfs)")

    flags = _flags(mh4u_records)
    rebuilt = rebuild(source, motion_map, flags)
    differences = compare(rebuilt, target)
    print("3/5's record rebuilt from 3U's and compared with MH4U's own:")
    for role in ("argument", "float", "motion", "flag"):
        names = [f.name for f in FIELDS if f.role == role]
        bad = differences.get(role, [])
        print(f"  {role}: {len(names) - len(bad)} of {len(names)} equal"
              + (f", differ: {', '.join(bad)}" if bad else ""))
    problems += sum(len(v) for v in differences.values())
    print(f"  rebuilt == MH4U's: {len(FIELDS) - sum(len(v) for v in differences.values())} of "
          f"{len(FIELDS)} fields equal")

    rebuilt4 = rebuild(action4, motion_map, flags)
    print("action 4's record rebuilt (MH4U has no action 4 record to compare):")
    for f in FIELDS:
        print(f"  {f.name} = {rebuilt4[f.name]}")

    print("action 4's value curves (carried; the ending key is the constant past the last key):")
    for address in args.mh3u_curves:
        keys = image_curve(code3, address)
        if keys[-1][0] >= 0:
            problems += 1
        print(f"  0x{address:08x}: {len(keys) - 1} key(s), "
              f"end value {keys[-1][1]:g} after time {keys[-1][0]:g}")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("show", help="print records from one game's image")
    p.add_argument("--game", choices=("mh3u", "mh4u"), required=True)
    p.add_argument("--exheader", required=True)
    p.add_argument("--code", required=True)
    p.add_argument("--address", type=lambda s: int(s, 0), required=True)
    p.add_argument("--count", type=int, default=1)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("curve", help="print a value curve from one game's image")
    p.add_argument("--game", choices=("mh3u", "mh4u"), required=True)
    p.add_argument("--exheader", required=True)
    p.add_argument("--code", required=True)
    p.add_argument("--address", type=lambda s: int(s, 0), required=True)
    p.set_defaults(func=cmd_curve)

    p = sub.add_parser("check", help="the N1/N2 procedure: rebuild 3/5's record and compare")
    for prefix in ("mh3u_", "mh4u_"):
        flag = prefix.replace("_", "-")
        p.add_argument(f"--{flag}exheader", required=True)
        p.add_argument(f"--{flag}code", required=True)
    p.add_argument("--mh3u-shared", type=lambda s: int(s, 0), default=MH3U_SHARED)
    p.add_argument("--mh3u-action4", type=lambda s: int(s, 0), default=MH3U_ACTION4)
    p.add_argument("--mh3u-curves", type=lambda s: [int(x, 0) for x in s.split(",")],
                   default=[int(x, 0) for x in MH3U_CURVES.split(",")],
                   help="action 4's value curves in MH3U's image")
    p.add_argument("--mh4u-shared", type=lambda s: int(s, 0), default=MH4U_RECORDS)
    p.add_argument("--mh4u-records", type=lambda s: int(s, 0), default=MH4U_RECORDS)
    p.add_argument("--mh4u-count", type=int, default=MH4U_RECORD_COUNT)
    p.add_argument("--mh3u-romfs", help="MH3U's RomFS image, for the animation check")
    p.add_argument("--mh4u-romfs", help="MH4U's RomFS image, for the animation check")
    p.add_argument("--mh3u-arc", default="arc/enemy/em001.arc")
    p.add_argument("--mh4u-arc", default="data/em001.arc")
    p.set_defaults(func=cmd_check)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except RecordError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
