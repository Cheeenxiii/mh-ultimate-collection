"""The MT Framework class-id hash: ~crc32(name) & 0x7FFFFFFF.

An ARC entry names its file type by this hash of the resource class's name ("rTexture"), and
the engine's class registry (MH4UltimateDC's config/mt_classes.tsv) lists the same ids.
Source: mhff n3ds/arc.py (gen_file_type_codes), MH4UltimateDC docs/research/mt-classes.md.
"""
from __future__ import annotations

import zlib


def class_id(name: str) -> int:
    """The class id of `name` (a resource class such as "rTexture")."""
    return (zlib.crc32(name.encode("ascii")) ^ 0xFFFFFFFF) & 0x7FFFFFFF


# Resource classes and the file extensions tools give them. Extensions are a community
# convention (mhff's table), not something the archive stores; the archive stores the id.
EXTENSIONS: dict[str, str] = {
    "rArchive": "arc", "rCameraList": "lcm", "rChainCol": "ccl", "rCnsTinyChain": "ctc",
    "rCollision": "sbc", "rEffectAnim": "ean", "rEffectList": "efl", "rEffectSequence": "esq",
    "rEnemyCmd": "emc",
    "rEnemyData": "emd", "rEnemyDtBase": "dtbase", "rEnemyDtBaseParts": "dtbparts", "rEnemyTuneData": "etd",
    "rEventActorTbl": "evt", "rGrass2": "gr2",
    "rGrass2Setting": "gr2s", "rGrassWind": "grw", "rItemPopList": "ipl", "rItemPopSet": "ips",
    "rLayout": "lyt", "rLayoutAnimeList": "lanl", "rLayoutFont": "lfd", "rLayoutMessage": "lmd",
    "rLtProceduralTexture": "ptex", "rLtShader": "lfx", "rLtSoundBank": "sbk",
    "rLtSoundCategoryFilter": "cfl", "rLtSoundRequest": "srq", "rLtSoundReverb": "rev_ctr",
    "rLtSoundSourceADPCM": "mca", "rLtSoundStreamRequest": "stq", "rMHSoundEmitter": "ses",
    "rMHSoundSequence": "mss", "rMaterial": "mrl", "rMhMotionEffect": "mef", "rModel": "mod",
    "rProofEffectList": "pel", "rProofEffectMotSequenceList": "psl",
    "rMotionList": "lmt", "rMovieOnDisk": "moflex", "rQuestData": "mib", "rScheduler": "sdl",
    "rSoundAttributeSe": "ase", "rSoundCurveSet": "scs", "rSoundDirectionalSet": "sds",
    "rStageAreaInfo": "sai", "rStageCameraData": "scd", "rStageInfoSet": "sis",
    "rTexture": "tex", "rGUIMessage": "gmd", "rEmSetList": "esl", "rSetEmMain": "sem",
    "rRem": "rem", "rGUI": "gui", "rGUIFont": "gfd", "rAreaInfo": "areainfo",
}

_BY_ID = {class_id(n): n for n in EXTENSIONS}
_BY_EXT: dict[str, str] = {}
for _name, _ext in EXTENSIONS.items():
    _BY_EXT.setdefault(_ext, _name)


def name_of(cid: int) -> str | None:
    """The class name for an id, when it is one of EXTENSIONS'."""
    return _BY_ID.get(cid)


def extension_of(cid: int) -> str:
    """A file extension for a class id: the known one, else the id in 8 hex digits."""
    name = _BY_ID.get(cid)
    return EXTENSIONS[name] if name else f"{cid:08X}"


def id_of_extension(ext: str) -> int:
    """The class id for an extension made by extension_of (known name, or 8 hex digits)."""
    ext = ext.lstrip(".")
    if ext in _BY_EXT:
        return class_id(_BY_EXT[ext])
    if len(ext) == 8:
        try:
            return int(ext, 16)
        except ValueError:
            pass
    raise ValueError(f"unknown extension .{ext}: name the file <name>.<8 hex digits of the class id>")
