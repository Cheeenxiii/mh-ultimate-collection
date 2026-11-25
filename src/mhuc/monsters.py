"""A ported monster's files: an MHXX monster archive turned into MH4U's and packed as a mod.

MH4U loads a monster's own files from two places:

- `data/emNNN.arc`, whose name the game builds from the monster id (`snprintf("data\\em%03d")`);
- the paths its resource record lists (reference/README.md#mh4u-monster-tables), which
  `mods/monster_ids` builds for a ported id: for each kind of file the port ships it rewrites
  the stand-in's path to the port's id, and for the kinds it doesn't ship it keeps the
  stand-in's path (data/ids/README.md, the `files` column).

A ported monster's id is in data/ids/registry.csv. Its source key (`em001` for GU Rathian)
names the MHXX archive `arc/enemy/em001_00.arc`. This module sorts that archive's entries into
what the row's `files` says the port ships, converts what needs converting, and writes the kept
entries as the port's own file tree (`enemy/em124/...`) inside MH4U's `/data/em124.arc` and the
mod folder the fork's mod manager installs.

The kinds it produces, and how:

- model, tail (rModel and their rMaterial files): taken as is (MOD 0xE6, MRL 0x20 in both
  games); the textures the materials name are converted and kept at MHXX's paths (below);
- motions (rMotionList): the first `files`' `motions=N` slots, taken as is (LMT 67 in both);
- camera (rCameraList): converted from MHXX's version 5 to MH4U's 4 (`camera.from_mhxx`,
  specs/camera.md);
- cmd (rEnemyCmd): taken as is (EMC 0x20120804 in both).

What it converts besides the camera: the archive container (ARC 0x11 in MHXX to 0x13 in MH4U)
and each texture (TEX 0xA6 in MHXX to 0xA5: the version field is the only byte that differs,
the pixel layout is the same). What it leaves out: the kinds the row's `files` doesn't list
(the plugin keeps the stand-in's path for those), and the entries that are not a kind a
monster's resource record names: shells (MH4U has its own projectile classes), effects
(EFL/EAN/PEL/PSL versions differ), the monster's data, collision and AI auxiliaries (MH4U reads
its own .emd/.etd and systems; the registry's stand-in answers until the port ships its own),
and the option motion list (MH4U has none per monster).

The material files keep their texture path strings as MHXX wrote them, so the textures are
kept at those paths: the path is part of the material data, and rewriting it would change bytes
whose meaning is not documented.
"""
from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass, field

from .formats import arc, camera, tex

SOURCE_ARC = "arc/enemy/{source_key}_{variant:02d}.arc"
REGISTRY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "ids", "registry.csv")

TEX_VERSION = 0xA5          # MH4U's; MHXX writes 0xA6 (specs/tex.md)
ARC_VERSION = 0x13          # MH4U's; MHXX writes 0x11 (specs/arc.md)
KINDS = ("model", "motions", "camera", "tail", "mef", "sound", "cmd", "efl")
PRODUCED = frozenset({"model", "motions", "camera", "tail", "cmd"})

# The reasons an entry is left out.
SOUND = "sound: converted by the sound mode of mhuc convert monster (--arc/--sound-arc)"
EFFECT = "effects: MHXX's EFL/EAN/PEL/PSL versions differ from MH4U's; effects are not ported yet"
CAMERA = "camera list: the registry's files doesn't list camera, so the record keeps the stand-in's"
MOTION_EFFECT = "motion effects: MHXX has PSL/PEL where MH4U has MEF"
SHELL = "shells: MH4U has its own projectile classes"
MONSTER_DATA = "monster data, collision and AI auxiliaries: MH4U reads its own .emd/.etd and \
systems, and the registry's stand-in answers until the port ships its own rows"
OPTION = "option motion list: MH4U has no per-monster option list"
OTHER = "not a kind the port uses"


class ConvertError(ValueError):
    pass


@dataclass
class Row:
    """One row of data/ids/registry.csv: what the port ships, from its `files` column."""
    id: int
    key: str
    source_game: str
    source_key: str
    name: str
    stand_in: int
    files: frozenset[str] = frozenset()
    motions: int = 0


@dataclass
class Report:
    """What the conversion kept, converted and left out, for the command's output and docs."""
    as_is: list[str] = field(default_factory=list)
    converted: list[str] = field(default_factory=list)
    left_out: dict[str, list[str]] = field(default_factory=dict)

    def leave(self, reason: str, path: str) -> None:
        self.left_out.setdefault(reason, []).append(path)


def _parse_files(text: str, where: str) -> tuple[frozenset[str], int]:
    """A row's `files` column as the kinds it ships and its motion-slot count."""
    kinds: set[str] = set()
    motions = 0
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        kind, _, count = token.partition("=")
        kind = kind.strip()
        if kind not in KINDS:
            raise ConvertError(f"{where}: files names {kind!r}, not one of {', '.join(KINDS)}")
        if kind in kinds:
            raise ConvertError(f"{where}: files names {kind} twice")
        if kind == "motions":
            if not count.isdigit() or not 1 <= int(count) <= 6:
                raise ConvertError(f"{where}: motions needs a slot count in 1..6, as motions=5")
            motions = int(count)
        elif count:
            raise ConvertError(f"{where}: only motions takes a count, not {token!r}")
        kinds.add(kind)
    if not kinds:
        raise ConvertError(f"{where}: files is empty; name the kinds the port ships")
    return frozenset(kinds), motions


def registry_row(monster_id: int, path: str | None = None) -> Row:
    """The registry row for an id, or ConvertError when it isn't a ported monster."""
    with open(path or REGISTRY, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["id"] != str(monster_id) or row["kind"] != "monster":
                continue
            where = f"registry id {monster_id}"
            files, motions = _parse_files(row.get("files", ""), where)
            return Row(int(row["id"]), row["key"], row["source_game"], row["source_key"],
                       row["name"], int(row["stand_in"]), files, motions)
    raise ConvertError(f"id {monster_id} isn't a ported monster in {path or REGISTRY}")


def source_archive_path(row: Row, variant: int) -> str:
    return SOURCE_ARC.format(source_key=row.source_key, variant=variant)


def _prefix(source_key: str, variant: int) -> str:
    return f"{source_key}_{variant:02d}"


def _rename_mod_file(stem: str, source_key: str, new_key: str, variant: int) -> str | None:
    """MHXX's `em001_00_tail` -> MH4U's `em124_tail`; None when the stem isn't the monster's."""
    prefix = _prefix(source_key, variant)
    if stem == prefix:
        return new_key
    if stem.startswith(prefix + "_"):
        return new_key + stem[len(prefix):]
    return None


def _rename_motion(stem: str, source_key: str, new_key: str, variant: int) -> tuple[str, int] | None:
    """MHXX's `em001_00_3` -> MH4U's `em124_3`, slot 3."""
    match = re.fullmatch(rf"{re.escape(source_key)}_{variant:02d}_(\d+)", stem)
    return (f"{new_key}_{match.group(1)}", int(match.group(1))) if match else None


def _convert_texture(entry: arc.Entry) -> bytes:
    """A texture MH4U reads: the same bytes with TEX version 0xA6 changed to 0xA5."""
    image = tex.read(entry.data)
    image.version = TEX_VERSION
    return tex.write(image)


def _not_shipped(kind: str) -> str:
    return f"not in the row's files: {kind}"


def convert(data: bytes, row: Row, variant: int = 0) -> tuple[bytes, Report]:
    """MHXX's monster archive as MH4U's, and a report of each entry's kind.

    The port's own file tree is `enemy/<id>/...`: the model `enemy/emNNN/mod/emNNN`, the tail
    `..._tail`, the motions `enemy/emNNN/mot/emNNN_<slot>`, the camera `enemy/emNNN/mot/eNNN_cam`
    and the AI script `enemy/emNNN/data/emNNN_cmd`. The textures keep the paths MHXX's material
    files give them. Only the kinds in `row.files` are produced; the rest are left out with a
    reason, because the plugin keeps the stand-in's path for them.
    """
    missing = row.files - PRODUCED
    if missing:
        raise ConvertError(f"{', '.join(sorted(missing))}: not produced by this converter "
                           "(sound: its own mode; mef and efl: no converter yet)")
    archive = arc.read(data)
    new_key = f"em{row.id:03d}"
    prefix = _prefix(row.source_key, variant)
    report = Report()
    entries: list[arc.Entry] = []
    produced: set[str] = set()
    for entry in archive.entries:
        path = entry.file_name
        ext = path.rsplit(".", 1)[-1]
        stem = entry.path.replace("\\", "/").rsplit("/", 1)[-1]
        new_path: str | None = None      # the stem, without its extension
        data_out = entry.data
        kind: str | None = None
        change = ""
        if path.startswith("sound/"):
            report.leave(SOUND, path)
        elif path.startswith("shell/") or path.startswith("arc/shell/"):
            report.leave(SHELL, path)
        elif path.startswith("effect/"):
            report.leave(MOTION_EFFECT if "/mot/" in path or entry.type_name == "rMhMotionEffect"
                         else EFFECT, path)
        elif path.startswith(f"enemy/{row.source_key}/"):
            folder = path.split("/")[3] if path.count("/") >= 3 else ""
            if folder == "mod" and entry.type_name in ("rModel", "rMaterial"):
                kind = "tail" if "_tail" in stem else "model"
                renamed = _rename_mod_file(stem, row.source_key, new_key, variant)
                if kind in row.files and renamed:
                    new_path = f"enemy/{new_key}/mod/{renamed}"
                else:
                    report.leave(_not_shipped(kind) if kind not in row.files else MONSTER_DATA, path)
            elif folder == "mod" and entry.type_name == "rTexture":
                if "model" not in row.files:
                    report.leave(_not_shipped("model"), path)
                    continue
                new_path = entry.path.replace("\\", "/")     # the material file names this path
                try:
                    data_out = _convert_texture(entry)
                except ValueError as e:
                    report.leave(f"textures: {e}", path)
                    continue
                change = " (TEX 0xA6 -> 0xA5)"
            elif folder == "mot" and entry.type_name == "rMotionList":
                renamed = _rename_motion(stem, row.source_key, new_key, variant)
                if renamed is None:
                    report.leave(OPTION, path)
                elif renamed[1] >= row.motions:
                    report.leave(f"motion slot {renamed[1]} is above the row's motions="
                                 f"{row.motions}", path)
                else:
                    new_path = f"enemy/{new_key}/mot/{renamed[0]}"
                    kind = "motions"
            elif folder == "mot" and entry.type_name == "rCameraList":
                if "camera" not in row.files:
                    report.leave(CAMERA, path)
                else:
                    try:
                        data_out = camera.from_mhxx(entry.data)
                    except camera.CameraError as e:
                        raise ConvertError(f"{path}: {e}") from None
                    new_path = f"enemy/{new_key}/mot/e{row.id:03d}_cam"
                    kind = "camera"
                    change = " (LCM 5 -> 4)"
            else:
                report.leave(MONSTER_DATA, path)
        elif path.startswith("enemy/cmd_tbl/"):
            if entry.type_name == "rEnemyCmd" and "cmd" in row.files:
                new_path = f"enemy/{new_key}/data/{new_key}_cmd"
                kind = "cmd"
            elif entry.type_name == "rEnemyCmd":
                report.leave(_not_shipped("cmd"), path)
            else:
                report.leave(OTHER, path)
        elif path.startswith("enemy/em_option/"):
            report.leave(OPTION, path)
        elif path.startswith("enemy/"):
            report.leave(MONSTER_DATA, path)
        else:
            report.leave(OTHER, path)
        if new_path is None:
            continue
        if entry.type_name != "rTexture":      # a texture follows its model, it isn't its own kind
            assert kind is not None
            produced.add(kind)
        shown = f"{new_path}.{ext}"
        if change:
            report.converted.append(f"{path} -> {shown}{change}")
        elif shown != path:
            report.as_is.append(f"{path} -> {shown}")
        else:
            report.as_is.append(path)
        entries.append(arc.Entry(new_path.replace("/", "\\"), entry.type_id, data_out))
    for kind in sorted(row.files & PRODUCED):
        if kind not in produced:
            raise ConvertError(f"{kind}: the row's files lists it, but {prefix} has none")
    if not entries:
        raise ConvertError(f"{prefix}: no file of a kind the port ships")
    return arc.write(arc.Archive(ARC_VERSION, entries)), report


def build_mod(out_dir: str, row: Row, arc_data: bytes) -> str:
    """Write the mod folder: mod.json and the port's archive under romfs/. Returns its path."""
    romfs = os.path.join(out_dir, "romfs", "data")
    os.makedirs(romfs, exist_ok=True)
    game = {"mhxx": "GU", "mh3u": "3U"}.get(row.source_game, row.source_game.upper())
    archive_path = os.path.join(romfs, f"em{row.id:03d}.arc")
    with open(archive_path, "wb") as f:
        f.write(arc_data)
    manifest = {
        "name": f"{row.name} ({game}) files",
        "version": "1",
        "author": "MH Ultimate Collection",
        "description": f"{row.name}'s {', '.join(sorted(row.files))} from "
                       f"{row.source_game.upper()}, converted for MH4U. Needs the ported ids plugin.",
    }
    with open(os.path.join(out_dir, "mod.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return archive_path
