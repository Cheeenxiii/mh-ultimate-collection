"""A ported monster's name and notes text, from its source game's own tables.

MH4U answers a monster's name and Hunter's Notes text by the monster id: `emName` and `emExp`
in `core_common.arc` are `rLayoutMessage` tables whose message N names id N
(specs/lmd.md, reference/README.md#mh4u-monster-tables). A ported id has no message there,
so the mod needs its own. The **name** is the registry's (`data/ids/registry.csv`); the
**notes** come from the source game's own table, recorded per id in `data/ids/notes.csv`:

    id,source_game,source_file,source_entry,source_index

`source_file` is a path in that game's RomFS (`arc/ID/ID_gallery_eng.arc`,
`table/HN_MonsterListMsg_jpn.gmd`); `source_entry` is the GMD's path inside that ARC, empty
when the file is a GMD itself; `source_index` is the string's index in the table (a GMD's
strings are in section order, and MH3U's Hunter's Notes and MHXX's monster list are ordered
tables, not id-indexed ones). The index is a fact read from the source game in the port's
session; the checker checks the shape, the game-files test checks the source resolves.

The result is a small table the plugin reads from its mod folder, `text/monster_text.bin`:

    "MHUT", u32 version (1), u32 count,
    count x (u32 id, u32 name units, u32 notes units, UTF-16LE name, UTF-16LE notes)

Game data never enters the repository: the builder reads the player's own dumps and writes
only the file the caller names, outside the repository.
"""
from __future__ import annotations

import csv
import os
import struct
from dataclasses import dataclass

from .formats import arc, gmd, romfs

MAGIC = b"MHUT"
VERSION = 1
REGISTRY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "ids", "registry.csv")
NOTES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "ids", "notes.csv")
COLUMNS = ("id", "source_game", "source_file", "source_entry", "source_index")
SOURCE_GAMES = ("mh3u", "mhxx")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TextError(ValueError):
    pass


@dataclass(frozen=True)
class PortedRow:
    """A registry monster row and the source of its notes."""
    id: int
    name: str
    source_game: str
    source_file: str
    source_entry: str
    source_index: int


@dataclass(frozen=True)
class TextEntry:
    id: int
    name: str
    notes: str


def registry_rows(path: str | None = None) -> list[dict[str, str]]:
    with open(path or REGISTRY, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("kind") == "monster"]


def read_notes(path: str | None = None) -> list[dict[str, str]]:
    with open(path or NOTES, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows or tuple(rows[0]) != COLUMNS:
        raise TextError(f"{path or NOTES}: the header must be {','.join(COLUMNS)}")
    out = []
    for n, cells in enumerate(rows[1:], start=2):
        if len(cells) != len(COLUMNS):
            raise TextError(f"{path or NOTES}:{n}: needs {len(COLUMNS)} columns")
        out.append(dict(zip(COLUMNS, cells, strict=True)))
    return out


def check(registry: list[dict[str, str]], notes: list[dict[str, str]]) -> list[str]:
    """What is wrong with the notes table against the registry."""
    problems: list[str] = []
    by_id = {int(r["id"], 0): r for r in registry}
    seen: dict[int, str] = {}
    for n, row in enumerate(notes, start=2):
        where = f"notes.csv:{n}"
        try:
            ident = int(row["id"], 0)
        except ValueError:
            problems.append(f"{where}: id {row['id']!r} isn't a number")
            continue
        if ident in seen:
            problems.append(f"{where}: id {ident} is already on line {seen[ident]}")
        seen[ident] = str(n)
        if ident not in by_id:
            problems.append(f"{where}: id {ident} isn't a ported monster in the registry")
            continue
        row_registry = by_id[ident]
        if row["source_game"] != row_registry["source_game"]:
            problems.append(f"{where}: source_game {row['source_game']!r} isn't the registry's "
                            f"{row_registry['source_game']!r}")
        if row["source_game"] not in SOURCE_GAMES:
            problems.append(f"{where}: source_game {row['source_game']!r} isn't one of "
                            f"{', '.join(SOURCE_GAMES)}")
        if not row["source_file"].strip():
            problems.append(f"{where}: no source_file")
        elif row["source_file"].startswith("/"):
            problems.append(f"{where}: source_file is a RomFS path without its leading /")
        try:
            index = int(row["source_index"], 0)
        except ValueError:
            problems.append(f"{where}: source_index {row['source_index']!r} isn't a number")
            continue
        if index < 0:
            problems.append(f"{where}: source_index {index} is negative")
    for ident, row in sorted(by_id.items()):
        if ident not in seen:
            problems.append(f"id {ident} ({row['key']}) has no notes source")
    return problems


def _read_source(dumps: str, game: str, source_file: str, source_entry: str) -> bytes:
    path = os.path.join(dumps, game, "romfs.bin")
    if not os.path.isfile(path):
        raise TextError(f"{path}: no {game} RomFS in the dumps folder")
    image = romfs.open_image(path)
    outer = source_file.replace("\\", "/").lstrip("/")
    for f in image.files():
        if f.path.lstrip("/") == outer:
            data = image.read(f)
            break
    else:
        raise TextError(f"{game}: no {source_file!r} in the RomFS")
    if not source_entry:
        return data
    inner = source_entry.replace("\\", "/").lstrip("/")
    for e in arc.read(data).entries:
        if e.file_name.lstrip("/") == inner or e.path.lstrip("/") == inner:
            return e.data
    raise TextError(f"{game}: no {source_entry!r} in {source_file!r}")


def source_string(dumps: str, source_game: str, source_file: str, source_entry: str,
                  source_index: int) -> str:
    """One string of a source game's text table, by its index in the table."""
    data = _read_source(dumps, source_game, source_file, source_entry)
    try:
        table = gmd.read(data)
    except ValueError as e:
        raise TextError(f"{source_file}: {e}") from None
    if not 0 <= source_index < len(table.strings):
        raise TextError(f"{source_file}: no string {source_index} "
                        f"(the table has {len(table.strings)})")
    return table.strings[source_index]


def build(dumps: str, registry_path: str | None = None, notes_path: str | None = None) -> list[TextEntry]:
    """Every ported monster's name and source-game notes, in id order."""
    rows = registry_rows(registry_path)
    notes = {int(r["id"], 0): r for r in read_notes(notes_path)}
    problems = check(rows, list(notes.values()))
    if problems:
        raise TextError(problems[0])
    out = []
    for row in sorted(rows, key=lambda r: int(r["id"], 0)):
        ident = int(row["id"], 0)
        source = notes[ident]
        text = source_string(dumps, source["source_game"], source["source_file"],
                             source["source_entry"], int(source["source_index"], 0))
        # MH4U's own messages break lines with \n; the source games may use \r\n.
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if not text:
            raise TextError(f"id {ident}: the source string is empty")
        out.append(TextEntry(ident, row["name"], text))
    return out


def write(entries: list[TextEntry]) -> bytes:
    """The mod's text table: magic, version, count, then each entry's id, lengths and UTF-16LE."""
    out = bytearray(MAGIC)
    out += struct.pack("<2I", VERSION, len(entries))
    for e in entries:
        name = e.name.encode("utf-16-le")
        notes = e.notes.encode("utf-16-le")
        if len(name) % 2 or len(notes) % 2:
            raise TextError(f"id {e.id}: text is not UTF-16LE")
        out += struct.pack("<3I", e.id, len(name) // 2, len(notes) // 2)
        out += name + notes
    return bytes(out)


def read_mod_text(data: bytes) -> list[TextEntry]:
    """Read the mod's text table back (the plugin reads the same bytes)."""
    if len(data) < 12 or data[:4] != MAGIC:
        raise TextError("not a mod text table")
    version, count = struct.unpack_from("<2I", data, 4)
    if version != VERSION:
        raise TextError(f"text table version {version}, not {VERSION}")
    pos = 12
    entries = []
    for _ in range(count):
        if pos + 12 > len(data):
            raise TextError("the table ends inside an entry header")
        ident, name_units, notes_units = struct.unpack_from("<3I", data, pos)
        pos += 12
        size = (name_units + notes_units) * 2
        if pos + size > len(data):
            raise TextError("the table ends inside an entry")
        name = data[pos:pos + name_units * 2].decode("utf-16-le")
        pos += name_units * 2
        notes = data[pos:pos + notes_units * 2].decode("utf-16-le")
        pos += notes_units * 2
        entries.append(TextEntry(ident, name, notes))
    if pos != len(data):
        raise TextError("the table has bytes after its last entry")
    return entries


def write_file(path: str, entries: list[TextEntry]) -> None:
    """Write the mod's text table, refusing a path inside the repository."""
    real = os.path.realpath(path)
    if real == ROOT or real.startswith(ROOT + os.sep):
        raise TextError("the table comes from the game's files; write it outside the repository")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        f.write(write(entries))
