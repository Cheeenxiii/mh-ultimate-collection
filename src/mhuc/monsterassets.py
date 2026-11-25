"""Build a ported monster's mod folder from its source game's archive (docs/architecture.md#monsters).

MH4U loads a monster's model, materials, textures and motion lists from one archive, `/data/em<id>.arc`, by
the paths the monster's resource table names. This module turns the source game's own monster archive into
that archive for a ported id:

- **models, materials and textures are taken as they are.** MOD is version 0xE6, MRL 0x20 and TEX 0xA5 in
  MH3U and MH4U ([mod.md](../specs/mod.md), checks M1 to M3; [tex.md](../specs/tex.md), check T1), so only
  their paths change. The material files' texture paths are absolute, so those are rewritten in place; the
  material and mesh names, which the model hashes, stay the source's.
- **motion lists are converted** from LMT version 66 to version 67, the version MH4U reads
  ([lmt.md](../specs/lmt.md), `lmt.convert`).
- **the rest is left out** and why is in docs/architecture.md: the monster's data files become MH4U's `.emd`
  and `.etd` through `mhuc monsterdata`, and the AI script, the sound and the effects belong to their own
  work.

Every path the archive holds is built from the target monster id, so a ported monster's files never collide
with the MH4U monster whose tables stand in for it.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .formats import arc, lmt

MODEL, MATERIAL, TEXTURE, MOTION = "rModel", "rMaterial", "rTexture", "rMotionList"
TAKEN = (MODEL, MATERIAL, TEXTURE)          # same format in MH3U and MH4U; only the path changes
TEXTURE_PATH = re.compile(rb"enemy\\[^\x00]{1,62}")


class ConvertError(ValueError):
    pass


@dataclass
class Mod:
    """A ported monster's RomFS files: one archive, `data/em<id>.arc`, of the entries below."""
    monster_id: int
    entries: list[arc.Entry]

    @property
    def archive_path(self) -> str:
        return f"data/em{self.monster_id:03d}.arc"

    def archive(self) -> bytes:
        return arc.write(arc.Archive(0x13, self.entries))

    def write(self, out_dir: str) -> str:
        """The mod folder's RomFS file under `out_dir`; returns its path."""
        dest = os.path.join(out_dir, "romfs", *self.archive_path.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(self.archive())
        return dest


def source_stem(src: arc.Archive) -> str:
    """The source's own file name, `em001` for MH3U's Rathian, from its model entry under `enemy\\emNNN\\mod\\`."""
    stems = {e.path.split("\\")[1] for e in src.entries
             if e.type_name == MODEL and e.path.startswith("enemy\\") and "\\mod\\" in e.path}
    if len(stems) != 1:
        raise ConvertError(f"{len(stems)} monster file names in the archive, expected one model under "
                           "enemy\\emNNN\\mod\\")
    return stems.pop()


def _rename(name: str, stem: str, target: str) -> str:
    """`em001_tail` as `em125_tail`: the source file name at the start of the file's name, the rest kept."""
    if not name.startswith(stem):
        raise ConvertError(f"{name} doesn't start with the source's file name {stem}")
    return target + name[len(stem):]


def _material(data: bytes, stem: str, target: str) -> bytes:
    """A material file with its absolute texture paths moved to the target's folder and names.

    The paths look like `enemy\\em001\\mod\\em001_BM`; the source and target file names are both three digits,
    so the substitution keeps every string's length and the file's other offsets."""
    old = f"enemy\\{stem}\\mod\\{stem}".encode("ascii")
    new = f"enemy\\{target}\\mod\\{target}".encode("ascii")
    return data.replace(old, new)


def convert(src: bytes, monster_id: int) -> Mod:
    """The mod for `monster_id` (124 and up, [data/ids](../../data/ids/README.md)) from the source archive."""
    if not 1 <= monster_id < 1000:
        raise ConvertError(f"monster id {monster_id} isn't a file id (1 to 999)")
    archive = arc.read(src)
    stem = source_stem(archive)
    target = f"em{monster_id:03d}"
    if len(stem) != len(target):
        raise ConvertError(f"the source's file name {stem} and the target's {target} differ in length; the "
                           "material files' texture paths are rewritten in place")
    entries: list[arc.Entry] = []
    for e in archive.entries:
        if e.type_name in TAKEN and e.path.startswith(f"enemy\\{stem}\\mod\\"):
            base = e.path.rsplit("\\", 1)[1]
            data = _material(e.data, stem, target) if e.type_name == MATERIAL else e.data
            entries.append(arc.Entry(f"enemy\\{target}\\mod\\{_rename(base, stem, target)}", e.type_id, data))
    motions = sorted((e for e in archive.entries
                      if e.type_name == MOTION and e.path.startswith(f"enemy\\{stem}\\mot\\")),
                     key=lambda e: e.path)
    for i, e in enumerate(motions):
        entries.append(arc.Entry(f"enemy\\{target}\\mot\\{target}_{i}", e.type_id, lmt.convert(e.data)))
    _check(entries, archive, stem, target)
    return Mod(monster_id, entries)


def _check(entries: list[arc.Entry], src: arc.Archive, stem: str, target: str) -> None:
    """Refuse a mod the game can't read: no model, material or motion, or a texture a material names is absent."""
    kinds = {e.type_name for e in src.entries}
    for kind in (MODEL, MATERIAL, MOTION):
        if kind not in kinds:
            raise ConvertError(f"the source archive holds no {kind}")
    if not any(e.type_name == MODEL for e in entries):
        raise ConvertError(f"no model under enemy\\{stem}\\mod\\")
    paths = {e.path for e in entries}
    for e in entries:
        if e.type_name == MATERIAL:
            for path in TEXTURE_PATH.findall(e.data):
                if path.decode("ascii") not in paths:
                    raise ConvertError(f"{e.path} names {path.decode('ascii')}, which the mod doesn't hold")
