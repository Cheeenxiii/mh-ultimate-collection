"""A ported monster's own sound set: MH3U's or MHXX's files converted to what MH4U loads.

MH4U names a monster's sound in its resource record by one path, `sound\\call\\em\\emNNN`: the sound
call (`MSS`), a table of the sound events each motion plays. The call names its requests (`SREQ`,
one record per request id), a request names its banks (`SNDB`), and a bank names the waves (`MADP`).
All four live in the monster's own archive (`/data/emNNN.arc`), so a port's archive must hold all
four under its own id's paths (specs/sound.md, check SN7).

The source games lay the set out differently before conversion:

- MH3U keeps the call (`mss`) in `arc/enemy/emNNN.arc` and the waves, bank and request in a
  separate `arc/sound/se/em/emNNN/snd_emNNN.arc`, under `sound\\se\\em\\emNNN\\wav\\`;
- MHXX keeps all four in `arc/enemy/emNNN_VV.arc`, under `sound\\se\\em\\emNNN_VV\\wav\\`, plus the
  common bank `sound\\se\\com\\snd_com_qst` and its waves under `sound\\se\\com\\wav\\`.

A conversion moves every path to the ported id's own namespace so a port never shadows MH4U's own
monster or another port: `sound\\se\\em\\em126\\wave\\...`, `sound\\se\\em\\em126\\snd_em126` (bank
and request) and `sound\\call\\em\\em126`. The common bank is copied into the port's namespace too,
so the port's request ids are answered by its own game's sounds.

What each kind needs (specs/sound.md, "What a converter must produce"):

- waves: MH3U's version 4 mono header moves to MH4U's version 5, the audio is copied bit for bit;
  MHXX's waves are already version 5 and are copied as they are;
- banks: MH3U's `SNDB` 10 container is MH4U's `SNDB` 11, so the version moves and the paths are
  rewritten; MHXX's `SBKR` 4 flags and entry parameters are MHGU's, converted back by the rules
  MHGU Definitive Edition established (check S3);
- requests: MH3U's `SREQ` 6 records keep their id, bank entry index, bank index and level, and the
  words whose version 6 packing is known are brought to version 8's form; MHXX's `SRQR` 5 records
  are 100 bytes against MH4U's 92, so words 0 to 21 are kept and word 8 gains MH4U's bit 16;
- sound calls: all three versions share the layout; MH3U's 2048-row table becomes MH4U's 512 and
  the records move, which is all `sound.write_sequence` does.

Game data never enters the repository: the converter reads the player's own archives and writes
only into the mod folder the caller names.
"""
from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field

from .formats import arc, classid, sound

SOURCE_GAMES = ("mh3u", "mhxx")
REGISTRY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "ids", "registry.csv")

# MH4U's sound classes, the types the port's archive entries carry. extensions come from classid.
SEQUENCE = classid.class_id("rMHSoundSequence")
WAVE = classid.class_id("rLtSoundSourceADPCM")
BANK = classid.class_id("rLtSoundBank")
REQUEST = classid.class_id("rLtSoundRequest")


class ConvertError(ValueError):
    pass


@dataclass(frozen=True)
class Row:
    """The registry row of a ported monster."""
    id: int
    key: str
    source_game: str
    source_key: str
    name: str
    stand_in: int
    files: str = ""


@dataclass
class SoundSet:
    """A monster's sound resources as its own game ships them, path and bytes each."""
    waves: dict[str, bytes] = field(default_factory=dict)
    banks: dict[str, bytes] = field(default_factory=dict)
    requests: dict[str, bytes] = field(default_factory=dict)
    sequences: dict[str, bytes] = field(default_factory=dict)

@dataclass
class Conversion:
    """The port's sound entries: archive path (no extension), type id and bytes, and what to know."""
    entries: list[tuple[str, int, bytes]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def kind(self, type_id: int) -> list[tuple[str, int, bytes]]:
        return [e for e in self.entries if e[1] == type_id]


def registry_row(monster_id: int, path: str | None = None) -> Row:
    """The registry row for a ported monster id, or ConvertError when it isn't one."""
    with open(path or REGISTRY, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["kind"] != "monster" or row["id"] != str(monster_id):
                continue
            return Row(int(row["id"]), row["key"], row["source_game"], row["source_key"],
                       row["name"], int(row["stand_in"]), row["files"])
    raise ConvertError(f"id {monster_id} isn't a ported monster in {path or REGISTRY}")


def read_sound_set(*archives: bytes) -> SoundSet:
    """Collect the four kinds from one or more ARC files, identified by their magic.

    MH3U splits the set over the monster's archive (the call) and its sound archive (everything
    else); MHXX keeps it whole. Pass the archives in any order.
    """
    found = SoundSet()
    for data in archives:
        if not data:
            continue
        try:
            archive = arc.read(data)
        except arc.ArcError as e:
            raise ConvertError(f"not a monster archive: {e}") from None
        for entry in archive.entries:
            body = entry.data
            if body[:4] == sound.WAVE_MAGIC:
                found.waves[entry.path] = body
            elif body[:4] in (sound.BANK_MAGIC, sound.BANK_GU_MAGIC):
                found.banks[entry.path] = body
            elif body[:4] in (sound.REQUEST_MAGIC, sound.GU_REQUEST_MAGIC):
                found.requests[entry.path] = body
            elif body[:4] == sound.SEQUENCE_MAGIC:
                found.sequences[entry.path] = body
    if not found.banks or not found.requests or not found.sequences:
        raise ConvertError("the archives hold no complete sound set (a call, a bank and a request)")
    return found


def _rename_stem(name: str, source_key: str, port_key: str) -> str:
    """MH3U's `em001_vo_hoeru` -> the port's `em126_vo_hoeru`; other names are kept."""
    if name.lower().startswith(source_key.lower()):
        tail = name[len(source_key):]
        if not tail or tail[0] == "_":
            return port_key + tail
    return name


class Names:
    """The port's paths for one source game's set: every kind's original path -> the port's."""

    def __init__(self, source_game: str, source_key: str, port_id: int):
        if source_game not in SOURCE_GAMES:
            raise ConvertError(f"{source_game} isn't a sound source mhuc converts (MH3U, MHXX)")
        self.source_game = source_game
        self.source_key = source_key
        self.port_id = port_id
        self.port_key = f"em{port_id:03d}"
        self._wave_re = self._wave_patterns()

    def _wave_patterns(self) -> list[tuple[re.Pattern, str]]:
        key = re.escape(self.source_key)
        patterns = [(re.compile(rf"^sound\\se\\em\\{key}(?:_\d\d)?\\wav\\(?P<rest>.+)$",
                                re.IGNORECASE),
                     rf"sound\se\em\{self.port_key}\wave")]
        if self.source_game == "mhxx":
            patterns.append((re.compile(r"^sound\\se\\com\\wav\\(?P<rest>.+)$", re.IGNORECASE),
                             rf"sound\se\em\{self.port_key}\common\wave"))
        return patterns

    def wave(self, path: str) -> str:
        for pattern, target in self._wave_re:
            match = pattern.match(path)
            if match:
                return target + "\\" + _rename_stem(match.group("rest"), self.source_key,
                                                    self.port_key)
        raise ConvertError(f"wave {path!r} isn't under the source's sound directories")

    def bank(self, path: str) -> str:
        key = re.escape(self.source_key)
        if re.match(rf"^sound\\se\\em\\{key}(?:_\d\d)?\\", path, re.IGNORECASE):
            return rf"sound\se\em\{self.port_key}\snd_em{self.port_id:03d}"
        if re.match(r"^sound\\se\\com\\", path, re.IGNORECASE):
            return rf"sound\se\em\{self.port_key}\snd_common"
        raise ConvertError(f"bank {path!r} isn't the monster's or the common one")

    def request(self, path: str) -> str:
        if re.match(rf"^sound\\se\\em\\{re.escape(self.source_key)}", path, re.IGNORECASE):
            return rf"sound\se\em\{self.port_key}\snd_em{self.port_id:03d}"
        raise ConvertError(f"request {path!r} isn't the monster's own")

    @property
    def sequence(self) -> str:
        return rf"sound\call\em\{self.port_key}"


def _request_v6_to_v8(words: tuple[int, ...]) -> tuple[int, ...]:
    """MH3U's 92-byte request record as MH4U's, changing only what is known to be a build value.

    Both records are 23 u32 at the same offsets, and the id (word 0), the bank entry index (2),
    the level (9) and the bank index (21) agree with MH4U's own records (check SN7). MH3U packs a
    build-time value into word 5's high half, so only the low half (the category) is kept, and
    word 22 is a build-time pointer slot, dropped to 0. Every other word is copied as MH3U wrote
    it: version 8's meanings for words 3, 4, 6 to 8 and 10 to 20 are not established, and MH4U's
    own files hold the same values (0xffffffff in word 8, 0 in word 10) on some records too, so a
    converter cannot re-pack them (specs/sound.md, "The request record's words").
    """
    if len(words) != sound.REQUEST_WORDS:
        raise ConvertError(f"{len(words)} request words, not {sound.REQUEST_WORDS}")
    return (words[0], words[1], words[2], words[3], words[4], words[5] & 0xFFFF, *words[6:22], 0)


def _bank_gu_to_4u(bank: sound.Bank, names: Names) -> sound.Bank:
    """MHXX's `SBKR` 4 bank as MH4U's `SNDB` 11: flags, entry parameters and types.

    MHGU's rules, read backwards (specs/sound.md, check S3): a group's 0x0800 marker and count
    become MH4U's 0x8000 marker, and the category in the group's x high byte moves into the flags'
    bits 11 to 14; the entry's byte 2 goes back to 8 and the 4-byte key MHGU moved to the end goes
    back to +12; the wave type becomes MH4U's rLtSoundSourceADPCM.
    """
    groups = []
    for group in bank.groups:
        if group.flags & 0x8000:
            groups.append(group)
            continue
        category = (group.x >> 24) & 0xF
        groups.append(sound.BankGroup(group.id, 0x8000 | (group.flags & 0x7FF) | (category << 11),
                                      group.first, group.x & 0xFFFFFF))
    entries = []
    for entry in bank.entries:
        if entry.type_id != sound.WAVE_TYPE_ID_GU:
            raise ConvertError(f"{entry.name}: type {entry.type_id:#x} isn't MHXX's wave")
        p = entry.params
        if len(p) != sound.BANK_PARAMS:
            raise ConvertError(f"{entry.name}: {len(p)} parameter bytes, not {sound.BANK_PARAMS}")
        params = p[0:2] + b"\x08" + p[3:12] + p[71:75] + p[12:71] + b"\x00"
        entries.append(sound.BankEntry(names.wave(entry.name), sound.WAVE_TYPE_ID, params))
    return sound.Bank(11, tuple(groups), tuple(entries), bank.tail)


def convert(sound_set: SoundSet, source_game: str, source_key: str, port_id: int) -> Conversion:
    """Convert one source game's sound set into the port's entries, all under its own id's paths."""
    names = Names(source_game, source_key, port_id)
    out = Conversion()
    for path, data in sound_set.waves.items():
        out.entries.append((names.wave(path), WAVE, sound.wave_to_v5(data)))
    for path, data in sound_set.banks.items():
        bank = sound.read_bank(data)
        if source_game == "mh3u":
            for entry in bank.entries:
                if entry.type_id != sound.WAVE_TYPE_ID:
                    raise ConvertError(f"{entry.name}: type {entry.type_id:#x} isn't MH3U's wave")
            converted = sound.Bank(11, bank.groups, bank.entries, bank.tail)
            body = sound.write_bank(converted, 11, names.wave)
        else:
            body = sound.write_bank(_bank_gu_to_4u(bank, names), 11)
        out.entries.append((names.bank(path), BANK, body))
    for path, data in sound_set.requests.items():
        if source_game == "mh3u":
            request = sound.read_request(data)
            records = tuple(sound.RequestRecord(_request_v6_to_v8(r.words)) for r in request.records)
            body = sound.write_request(records, tuple(names.bank(b) for b in request.banks))
        else:
            request = sound.read_request_gu(data)
            if request.record_size != 100:
                raise ConvertError(f"MHXX's request records are 100 bytes, this file's are "
                                   f"{request.record_size}")
            records = []
            for record in request.records:
                words = list(record.words[:22]) + [0]
                words[8] |= 0x10000
                records.append(sound.RequestRecord(tuple(words)))
            body = sound.write_request(tuple(records),
                                       tuple(names.bank(b) for b in request.banks))
        out.entries.append((names.request(path), REQUEST, body))
    if len(sound_set.sequences) != 1:
        raise ConvertError(f"the archives hold {len(sound_set.sequences)} sound calls; a port's "
                           "record names one")
    for _path, data in sound_set.sequences.items():
        sequence = sound.read_sequence(data)
        out.entries.append((names.sequence, SEQUENCE, sound.write_sequence(sequence)))
    if not out.entries:
        raise ConvertError("nothing to convert")
    # A port must never name a file it doesn't ship (issue #143): every bank entry names a wave in
    # the set and every request names a shipped bank.
    wave_paths = {path for path, type_id, _ in out.entries if type_id == WAVE}
    bank_paths = {path for path, type_id, _ in out.entries if type_id == BANK}
    for path, _type, data in out.kind(BANK):
        for entry in sound.read_bank(data).entries:
            if entry.name not in wave_paths:
                raise ConvertError(f"{path}: entry {entry.name!r} names no wave in the set")
    for path, _type, data in out.kind(REQUEST):
        for name in sound.read_request(data).banks:
            if name not in bank_paths:
                raise ConvertError(f"{path}: names bank {name!r}, which isn't in the set")
    waves = len(out.kind(WAVE))
    banks = len(out.kind(BANK))
    requests = len(out.kind(REQUEST))
    sequences = len(out.kind(SEQUENCE))
    out.notes.append(f"{waves} waves, {banks} banks, {requests} requests, {sequences} sound calls")
    if source_game == "mh3u":
        out.notes.append("request words 0-21 kept as MH3U wrote them, except word 5's high half "
                         "(a build value) and word 22 (a pointer slot); the low half of word 5 is "
                         "the category")
    else:
        out.notes.append("bank flags and entry parameters converted by reversing MHGU's rules; "
                         "request records go from 100 to 92 bytes with words 0-21 kept")
    return out
