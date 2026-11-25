#!/usr/bin/env python3
"""Whether a player would notice a 3U or GU monster version differ from MH4U's, per axis.

Decision 0004's amendment gives a 3U or GU version of a monster MH4U has its own id only when a
player would easily notice the difference: attacks met in a normal fight that MH4U's version
lacks or has, a mesh or textures that look different, or a breakable part, weakness or HP that
differ noticeably. This tool records that comparison for every row of
`data/catalog/versions.csv`, as counts, names and action ids only (no game data).

    monster_versions.py --rows data/catalog/versions.csv --attacks data/catalog/attacks.csv \
        --mh4u-romfs ... --mh3u-romfs ... --mhxx-romfs ... --mhxx-update-romfs ... \
        --mh4u-vt ... --mh3u-vt ... --mhxx-vt ... -o out.csv

The row file supplies the pairing (`source_game`, `monster`, `mh4u_id`, `source_file`,
`source_url`); every verdict and its evidence are rewritten. `attacks.csv` holds the wiki's
attack list per game and monster, with the page it came from. The vt TSVs are the class vtables
`reference/mt_vtables.py` recovers, kept outside the repository.

Moves: a shared action id that starts a different animation is a visible difference; so is a
source-only action that starts an animation MH4U's lists do not hold and that the source's AI
script (reference/monster_emc.py) names; and so is an attack list the wiki shows on one side of
the two pages. Data: HP 10% or more apart, a weakness 10 points or more on a used hitzone row,
or a different set of breakable parts. Model: a bound box that differs where the games share a
bind space, never bone numbering or a re-atlas. The exact rule and the thresholds are in
data/catalog/versions.md.
"""
from __future__ import annotations

import argparse
import collections
import csv
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import monster_motions  # noqa: E402

from mhuc import monsterdata  # noqa: E402
from mhuc.formats import arc, mod, romfs, tex  # noqa: E402

DISPATCH_SLOT = {"mh4u": 44, "mh3u": 50, "mhxx": 122}
MOTION = {"mh4u": 0x0094E318, "mhxx": 0x008EB108, "mh3u": 0x00828828}
MODEL_CLASS = 0x58A15856

# reference/README.md "Ids and classes" and "MH3U's factory"
MH4U_EXTRA = {"uEm001": [2, 3, 4, 5, 6], "uEm007": [8], "uEm009": [10], "uEm011": [12, 80, 121],
              "uEm016": [13, 14], "uEm017": [18], "uEm019": [45, 112], "uEm020": [90],
              "uEm022": [21, 91, 92], "uEm023": [93, 120], "uEm024": [110], "uEm025": [94],
              "uEm026": [95], "uEm027": [96], "uEm028": [29, 97], "uEm031": [82], "uEm034": [35],
              "uEm038": [39, 40, 41, 115], "uEm036": [37], "uEm042": [43, 113], "uEm044": [98],
              "uEm048": [49, 114], "uEm052": [53, 54, 55], "uEm058": [59, 60], "uEm065": [66],
              "uEm068": [69, 70, 71], "uEm073": [74, 75, 76], "uEm077": [78, 79, 117],
              "uEm081": [84, 85, 86, 87, 104, 123], "uEm083": [111], "uEm088": [122],
              "uEm099": [100, 119], "uEm101": [102], "uEm105": [106], "uEm107": [108, 109]}
MH3U_CLASS = {"uEm002": [1, 2, 62, 63, 64, 65], "uEm003": [3, 51], "uEm004": [4, 52],
              "uEm005": [5, 53], "uEm006": [6, 58], "uEm007": [7, 71], "uEm008": [8, 54],
              "uEm009": [9, 55], "uEm010": [10, 13], "uEm011": [11, 48], "uEm012": [12, 14, 45],
              "uEm015": [15, 68, 69], "uEm017": [16, 17, 21], "uEm019": [19, 57],
              "uEm020": [20, 70], "uEm025": [25, 85], "uEm027": [27, 28, 49, 78],
              "uEm030": [30, 31], "uEnemy": [32, 50], "uEm034": [34, 77],
              "uEm036": [36, 37, 38, 39], "uEm040": [40, 79, 80, 81, 82, 83, 84],
              "uEm041": [41, 72], "uEm042": [42, 43, 44], "uEm046": [46, 73],
              "uEm059": [59, 60, 61], "uEm066": [66, 67]}
MHXX_SHARED_CLASS = {2: "uEm001_00", 5: "uEm004_00", 15: "uEm014_00", 16: "uEm014_00",
                     72: "uEm071_00"}   # families with no module of their own


class GameFiles:
    def __init__(self, args):
        self.args = args
        self._rom = {}
        self._vt = {}
        self._code = {}
        self._module_bases = None

    def rom(self, game):
        path = {"mh4u": self.args.mh4u_romfs, "mh3u": self.args.mh3u_romfs,
                "mhxx": self.args.mhxx_romfs, "mhxx_upd": self.args.mhxx_update_romfs}[game]
        if game not in self._rom:
            self._rom[game] = romfs.open_image(path)
        return self._rom[game]

    def file(self, game, path):
        r = self.rom(game)
        hit = [e for e in r.files() if e.path == path]
        if len(hit) != 1:
            raise KeyError(f"{game}: {len(hit)} files named {path}")
        return r.read(hit[0])

    def entries(self, game, path):
        return arc.read(self.file(game, path)).entries

    def vt(self, game):
        if game not in self._vt:
            out = {}
            with open({"mh4u": self.args.mh4u_vt, "mh3u": self.args.mh3u_vt,
                       "mhxx": self.args.mhxx_vt}[game]) as f:
                for line in f:
                    if line.startswith(("#", "name\t")) or not line.strip():
                        continue
                    p = line.rstrip("\n").split("\t")
                    out[p[0]] = [int(x, 16) if x else None for x in p[9].split(",")]
            self._vt[game] = out
        return self._vt[game]

    def module_bases(self):
        """The base each MHXX module had when mt_vtables.py wrote the TSV: modules loaded one
        after another from 0x02000000, each aligned to 0x10000."""
        if self._module_bases is None:
            import cro as crolib
            crs = crolib.Cro(self.file("mhxx_upd", "/modules_MasterRelease/static.crs"))
            names = sorted(e.path for e in self.rom("mhxx_upd").files()
                           if e.path.startswith("/modules_MasterRelease/") and e.path.endswith(".cro"))
            base, out = 0x02000000, {}
            for p in names:
                ld = crolib.load(self.file("mhxx_upd", p), base, crolib.static_segments(crs))
                out[p.rsplit("/", 1)[-1]] = base
                base = (base + len(ld.image) + 0xFFFF) & ~0xFFFF
            self._module_bases = out
        return self._module_bases


def id_class(game, em):
    n = int(em[2:])
    if game == "mh4u":
        for cls, ids in MH4U_EXTRA.items():
            if n in ids:
                return cls
        return f"uEm{n:03d}"
    for cls, ids in MH3U_CLASS.items():
        if n in ids:
            return cls
    return f"uEm{n:03d}"


def mhxx_class(files, em):
    mm = int(em[2:5])
    vt = files.vt("mhxx")
    cls = f"uEm{mm:03d}_00"
    if cls in vt and vt[cls][DISPATCH_SLOT["mhxx"]] is not None:
        return cls
    cls = MHXX_SHARED_CLASS.get(mm)
    if cls and cls in vt:
        return cls
    raise KeyError(f"mhxx {em}: no class or shared class found")


def mhxx_module(files, em):
    cls = mhxx_class(files, em)
    return int(re.search(r"uEm(\d{3})", cls).group(1))


def dispatcher(files, game, em):
    if game == "mhxx":
        cls = mhxx_class(files, em)
        d = files.vt("mhxx")[cls][DISPATCH_SLOT["mhxx"]]
        name = f"roEm{mhxx_module(files, em):03d}.cro"
        if name in files.module_bases():
            return 0x02000000 + (d - files.module_bases()[name])
        return d
    slots = files.vt(game).get(id_class(game, em))
    if not slots or slots[DISPATCH_SLOT[game]] is None:
        raise KeyError(f"{game} {em}: no dispatcher slot")
    return slots[DISPATCH_SLOT[game]]


def code_and_tables(files, game, em):
    import monster_actions

    if game == "mhxx":
        import cro as crolib
        mm = mhxx_module(files, em)
        rel = f"/modules_MasterRelease/roEm{mm:03d}.cro"
        for rom in ("mhxx_upd", "mhxx"):
            try:
                src = files.file(rom, rel)
                break
            except KeyError:
                src = None
        if src is not None:
            crs = crolib.Cro(files.file("mhxx_upd", "/modules_MasterRelease/static.crs"))
            ld = crolib.load(src, 0x02000000, crolib.static_segments(crs))
            lo, hi = ld.text
            return (monster_actions.Code(ld.image, ld.base, lo, hi), None,
                    set(crolib.entry_points(ld, crs)))
        if "mhxx" not in files._code:
            raise KeyError("mhxx: the update's code.bin is needed for a class without a module "
                           "(pass --mhxx-update-exheader/--mhxx-update-code)")
        data, text, _ = files._code["mhxx"]
        d = dispatcher(files, "mhxx", em)
        return monster_actions.Code(data, text, d - 0x20000, d + 0x20000), None, None
    if game not in files._code:
        header = open({"mh4u": files.args.mh4u_exheader, "mh3u": files.args.mh3u_exheader}[game], "rb").read()
        code = open({"mh4u": files.args.mh4u_code, "mh3u": files.args.mh3u_code}[game], "rb").read()
        import fork  # noqa: F401  (puts the fork's tools on sys.path)

        import codebin2elf
        import exheader as exh
        h = exh.parse(header)
        data = codebin2elf.load_code(h, code)
        table = monster_motions.functions_table(monster_motions.default_functions(game))
        files._code[game] = (data, h.text.address, table)
    data, text, table = files._code[game]
    d = dispatcher(files, game, em)
    return monster_actions.Code(data, text, d - 0x20000, d + 0x20000), table, None


def inventory_with_calls(code, dispatcher, follow_tails):
    import monster_actions

    top = monster_actions.find_switch(code, dispatcher, limit=12)
    if top is None:
        raise ValueError(f"no switch on the category at 0x{dispatcher:08x}")
    cats, _ = top
    out = []
    for cat, block in sorted(cats.items()):
        first = monster_actions.case(code, block)
        fn = monster_actions.category_function(code, block)
        start, limit = (fn, 24) if fn is not None else (block, 6)
        sw = monster_actions.find_switch(code, start, limit)
        if sw is None:
            for target in reversed([c for c in first.get("calls", []) if code.lo <= c < code.hi]):
                sw2 = monster_actions.find_switch(code, target, 24)
                if sw2 is not None and sw2[0]:
                    start, sw = target, sw2
                    break
        if sw is None and follow_tails and first.get("kind") == "tail" and first.get("handler"):
            target = first["handler"]
            if code.lo <= target < code.hi:
                sw = monster_actions.find_switch(code, target, 24)
                if sw is not None:
                    start = target
        if sw is None:
            out.append(monster_actions.Action(cat, None, block, fn,
                                              **(monster_actions.case(code, fn) if fn is not None else first)))
            continue
        for idx, target in sorted(sw[0].items()):
            out.append(monster_actions.Action(cat, idx, target, fn, **monster_actions.case(code, target)))
    return out


def inventory(files, game, em):
    code, table, entries = code_and_tables(files, game, em)
    d = dispatcher(files, game, em)
    try:
        actions = inventory_with_calls(code, d, False)
        if len(actions) < 50:
            more = inventory_with_calls(code, d, True)
            if len(more) > len(actions):
                actions = more
    except ValueError:
        if not entries:
            raise
        best = []
        for a in sorted(entries):
            try:
                acts = inventory_with_calls(code, a, True)
            except Exception:
                continue
            if len(acts) >= 20:
                best.append((len(acts), a))
        if not best:
            raise
        actions = inventory_with_calls(code, max(best)[1], True)
    if entries is not None:
        entries |= {a.handler for a in actions if a.handler}
        entries |= {a.fn for a in actions if a.fn}
    rows = {}
    for a in actions:
        handler = a.handler if a.kind == "tail" else None
        m = monster_motions.motion_for(code, handler, table, entries, MOTION[game])
        rows[(a.cat, a.idx)] = dict(motion=m["motion"], how=m["how"], handler=handler)
    return rows


LMT_CLASS = 0x76820D81


def lmts(files, game, em):
    """A monster's motion lists, indexed by the file number a motion index encodes.

    MH4U and MHXX pack a motion index as file << 8 | slot; MH3U as file * 100 + slot and names
    its files `mot_emNNN_{file}00`. A variant's archive can hold the base monster's lists
    (MH4U em003 holds em001's), and a list can be absent from the archive (MH4U em045 holds
    em019's files 0, 2, 3 and 4), so the list is indexed by the number in the file name and
    absent files stay None.
    """
    if game == "mh4u":
        path = f"/data/{em}.arc"
    else:
        path = f"/arc/enemy/{em}.arc"
    got = {}
    for e in files.entries(game, path):
        if e.type_id != LMT_CLASS:
            continue
        q = e.path.replace("\\", "/")
        if "/mot/" not in q:
            continue
        name = q.rsplit("/", 1)[-1]
        if game == "mh3u":
            m = re.fullmatch(rf"mot_{re.escape(em)}_(\d+)00", name)
        else:
            m = re.fullmatch(r"(?:mot_)?em\d{3}(?:_\d{2})?_(\d+)", name)
        if not m:
            continue
        got[int(m.group(1))] = e.data
    if not got:
        return []
    out = [None] * (max(got) + 1)
    for f, data in got.items():
        out[f] = monster_motions.read_lmt(data)
    return out


def motion_lists(files, game, em):
    try:
        out = lmts(files, game, em)
        if out:
            return out
    except KeyError:
        pass
    if game == "mhxx" and "_" in em:
        return lmts(files, game, em.split("_")[0] + "_00")
    return []



def moves_visible(files, game, em4, src):
    """Whether the source version's actions would look different in a normal fight.

    A shared action id that starts a different animation is a visible difference (the same
    action plays another motion). Among the ids only the source has, one that starts an
    animation MH4U's lists do not contain and that the source's AI script picks is a new move;
    one the AI script does not name, or whose animation is one MH4U already plays, is not.
    An inventory whose action ids do not line up is not compared.
    """
    try:
        a = inventory(files, "mh4u", em4)
        b = inventory(files, game, src)
    except (ValueError, KeyError) as e:
        return "not compared", f"{type(e).__name__}: {e}"
    r = monster_motions.compare(a, b)
    compared = len(r["same"]) + len(r["different"])
    if compared < 10:
        return ("not compared",
                f"action ids do not line up ({compared} compared of {r['common']} common)")
    la, lb = motion_lists(files, "mh4u", em4), motion_lists(files, game, src)
    split = monster_motions.content_split(a, b, "mh4u", la, game, lb) if (r["different"] and la and lb) else None
    diff = [k for k, *_ in split["different"]] if split else []
    only = sorted(set(b) - set(a))
    only_motion = [k for k in only if b[k]["how"] == "constant"]
    try:
        refs = emc_actions(files, game, src)
    except KeyError:
        refs = None
    ai = [k for k in only_motion if refs is not None and k in refs]
    # Which animations MH4U's lists hold, so a source-only action that reuses one is not new.
    sig4 = set()
    for anims in la:
        if anims:
            sig4 |= {sig for sig in anims if sig}
    known, new, new_other, unresolved = [], [], [], []
    for k in only_motion:
        f, slot = monster_motions.decode_motion(game, b[k]["motion"])
        sig = lb[f][slot] if f < len(lb) and lb[f] and slot < len(lb[f]) else None
        if sig is None:
            unresolved.append(k)
        elif sig in sig4:
            known.append(k)
        elif k[0] == 7:
            # Category 7's shared handler can start more than one motion, so a source-only
            # action's first constant is not reliable enough to call the animation new.
            unresolved.append(k)
        elif k in ai:
            new.append(k)
        else:
            new_other.append(k)
    shared = (game == "mhxx" and mhxx_class(files, src) != f"uEm{int(src[2:5]):03d}_00")
    detail = (("shared family class; " if shared else "")
              + f"common {r['common']}; {compared} compared; {len(r['same'])} start the same animation, "
              f"{len(diff)} a different one"
              + (f" ({monster_motions.fmt_ids(diff).replace(chr(10), ' ')})" if diff else "")
              + f"; source-only {len(only)} ({len(only_motion)} start a motion"
              + (f"; the AI script names {len(ai)} of those" if refs is not None else "; no AI script found")
              + ")")
    if refs is not None:
        detail += "; AI-picked: " + (monster_motions.fmt_ids(ai).replace("\n", " ") or "none")
        detail += "; not named by the AI script: " + (
            monster_motions.fmt_ids([k for k in only if k not in ai]).replace("\n", " ") or "none")
    if known:
        detail += "; " + str(len(known)) + " start an animation MH4U already holds"
    if new:
        detail += "; new animations the AI picks: " + monster_motions.fmt_ids(new).replace("\n", " ")
    if new_other:
        detail += ("; new animations not named by the AI script: "
                   + monster_motions.fmt_ids(new_other).replace("\n", " "))
    if unresolved:
        detail += ("; animation not in either game's own lists: "
                   + monster_motions.fmt_ids(unresolved).replace("\n", " "))
    return ("differs" if (diff or new) else "same"), detail


def emc_actions(files, game, em):
    """The native actions the source monster's AI script starts, or None if the archive has none."""
    import monster_emc

    path = f"/data/{em}.arc" if game == "mh4u" else f"/arc/enemy/{em}.arc"
    for e in files.entries(game, path):
        if e.type_id == 0x3AABBA02:
            return monster_emc.actions(e.data)
    return None


def _breakable(part_table):
    """The parts with a break record: a break level or a second-level HP other than 0xFFFF."""
    if not part_table or len(part_table) != 80:
        return None
    out = []
    for i in range(8):
        r = struct.unpack_from("<HBBBBHH", part_table, 10 * i)
        if r[1] or r[5] != 0xFFFF:
            out.append(i)
    return out


def _used_rows(records):
    out = set()
    for r in records or []:
        if len(r) >= 10:
            row = struct.unpack_from("<H", r, 6)[0]
            if row < 8:
                out.add(row)
    return out


def data_visible(files, game, em4, src):
    """HP, weaknesses and breakable parts under the thresholds in data/catalog/versions.md.

    HP differs by 10% or more, a weakness by 10 points or more on a hitzone row both games' body
    records use, and a breakable part when the set of parts with a break record differs. The
    values themselves are never written.
    """
    source = _source_data(files, game, src)
    ents4 = files.entries("mh4u", "/data/em_data.arc")
    ref = monsterdata.from_mh4u(pick(ents4, 0x0A0E48D4, f"/{em4}/"), pick(ents4, 0x3D8BBBAC, f"/{em4}/"))
    hp_s, hp_4 = source.get("base HP"), ref.get("base HP")
    hp_rel = abs(hp_s - hp_4) / max(hp_s, hp_4) if hp_s and hp_4 else 0
    hp_diff = hp_rel >= 0.10
    hs, h4 = source.get("hitzone table"), ref.get("hitzone table")
    rows = sorted(_used_rows(source.get("body records")) & _used_rows(ref.get("body records")))
    cells = [abs(hs[row * 10 + col] - h4[row * 10 + col]) for row in rows for col in range(8)] if hs and h4 else []
    over = sum(1 for d in cells if d >= 10)
    weak_diff = over > 0
    bps, bp4 = _breakable(source.get("part table")), _breakable(ref.get("part table"))
    extra = sorted(set(bps) - set(bp4)) if bps is not None and bp4 is not None else []
    missing = sorted(set(bp4) - set(bps)) if bps is not None and bp4 is not None else []
    bp_diff = bool(extra or missing)
    weak = (f"differ by 10 points or more on {over} cells" if weak_diff else "within 10 points")
    detail = (f"HP {'differs by 10% or more' if hp_diff else 'within 10%'}; weaknesses {weak}"
              f" on the {len(rows)} rows both body records use; ")
    detail += (f"breakable parts differ (source only {extra}, MH4U only {missing})" if bp_diff
               else "breakable parts same")
    return ("differs" if (hp_diff or weak_diff or bp_diff) else "same"), detail


def _source_data(files, game, src):
    if game == "mhxx":
        ents = files.entries(game, f"/arc/enemy/{src}.arc")
        hits = [e for e in ents if "/hit_data/" in e.path.replace("\\", "/")]

        def any_of(ty):
            got = [e.data for e in hits if e.type_id == ty]
            if len(got) != 1:
                raise KeyError(f"{src}: {len(got)} hit_data entries of {ty:#x}")
            return got[0]

        return monsterdata.from_mhxx(
            pick(ents, 0x48E8AC29, "dt_tune/"), pick(ents, 0x59D9C3DA, "dt_base/"),
            pick(ents, 0x1BBC291E, "dt_base/"), pick(ents, 0x1AC7B52D, "/body_data/"),
            pick(ents, 0x1AC7B52D, "/cam_body_data/"), any_of(0x5653C1B0), any_of(0x70BB64BA))
    ents = files.entries(game, f"/arc/enemy/{src}.arc")
    return monsterdata.from_mh3u(
        pick(ents, 0x4DEE8265, "em_status"), pick(ents, 0x1AC7B52D, "em_body"),
        pick(ents, 0x1AC7B52D, "em_cambody"), pick(ents, 0x5653C1B0, "em_hitsize"),
        pick(ents, 0x0C6016B9, "em_hitdata"))


def pick(ents, type_id, *words):
    hits = [e.data for e in ents if e.type_id == type_id and all(w in e.path.replace("\\", "/") for w in words)]
    if len(hits) != 1:
        raise KeyError(f"{len(hits)} entries of {type_id:#x} with {words}")
    return hits[0]


def models(files, game, path):
    return {e.path: e.data for e in files.entries(game, path)
            if e.type_id == MODEL_CLASS and e.data[:4] == b"MOD\0"}


def main_model(files, game, em):
    """The main body model: its rig, bound box, material names and texture files."""
    path = f"/data/{em}.arc" if game == "mh4u" else f"/arc/enemy/{em}.arc"
    found = models(files, game, path)
    keys = [em] + ([em.split("_")[0] + "_00"] if "_" in em else [])
    for key in keys:
        for p, d in found.items():
            q = p.replace("\\", "/")
            if q.split("/")[-2] == "mod" and q.split("/")[-1] == key:
                h = mod.header(d)
                o = h["materials_at"]
                return dict(path=q, bones=mod.bones(d, h), aabb=struct.unpack_from("<8f", d, 0x50),
                            materials=[d[o + 128 * i:o + 128 * (i + 1)].split(b"\0")[0].decode("ascii", "replace")
                                       for i in range(h["materials"])],
                            vertices=h["vertices"], indices=h["indices"], meshes=h["meshes"])
    return None


def _textures(files, game, path):
    out = {}
    for e in files.entries(game, path):
        q = e.path.replace("\\", "/")
        if "/mod/" not in q or e.type_id not in (0x241F5DEB, 0x4E397417):
            continue
        try:
            t = tex.read(e.data)
            out[q.rsplit("/", 1)[-1]] = f"{t.width}x{t.height} {t.fmt}"
        except (ValueError, struct.error):
            out[q.rsplit("/", 1)[-1]] = "unreadable"
    return out


def _rig_compare(a, b):
    """Same rig after contracting zero-length bones (MH3U's extra root sits at its parent's position)."""
    eps = 1e-3

    def normalized(bones):
        pos = {x["id"]: x["position"] for x in bones}
        par = {x["id"]: x["parent_id"] for x in bones}

        def empty(i):
            p = par.get(i)
            return p in pos and all(abs(x - y) < eps for x, y in zip(pos[i], pos[p], strict=True))

        def parent(i):
            p = par[i]
            while p in pos and empty(p):
                p = par[p]
            return p

        return {i: parent(i) for i in pos}, {i: empty(i) for i in pos}

    A, _ = normalized(a)
    B, empty_b = normalized(b)
    if any(i not in B for i in A):
        return False, "missing bones", []
    if any(B[i] != A[i] for i in A):
        return False, "a parent differs", []
    extras = [i for i in B if i not in A]
    if any(not empty_b[i] for i in extras):
        return False, "extra bones", extras
    return True, "same after dropping empty roots", extras


def model_visible(files, game, em4, src):
    """Whether the mesh or textures would look different, from what is in the model files.

    The rig is compared with zero-length bones contracted; a rig that differs only by such a
    bone is the same rig, and bone numbering alone is never a visible difference. The main
    body model's bound box is compared where the two games share a bind space (MHXX against
    MH4U); MH3U's bind space differs in every row, so its box is not comparable. Material names
    and texture files are recorded but do not decide either: MH4U splits the same skin into a
    different texture atlas.
    """
    a = main_model(files, "mh4u", em4)
    b = main_model(files, game, src)
    if a is None or b is None:
        return "not compared", "no main body model found"
    rig_ok, rig_why, extras = _rig_compare(a["bones"], b["bones"])
    va, vb = a["aabb"], b["aabb"]
    size = [abs(va[4 + k] - va[k]) for k in range(3)]
    rel = max((abs(vb[k] - va[k]) / s for k, s in enumerate(size)), default=99.0) if all(size) else 99.0
    bounds_same = True if game == "mh3u" else rel <= 0.02
    ta = _textures(files, "mh4u", f"/data/{em4}.arc")
    tb = _textures(files, game, f"/arc/enemy/{src}.arc")
    detail = (f"rig {'same' if rig_ok else 'differs: ' + rig_why}"
              + (f" (source-only bones {extras})" if extras else "")
              + f"; mesh bounds {'same' if bounds_same else f'differ by {rel*100:.0f}%'}"
              + (" (MH3U's bind space is not comparable)" if game == "mh3u" else "")
              + f"; vertices {a['vertices']}/{b['vertices']}; meshes {a['meshes']}/{b['meshes']}"
              + f"; materials {len(a['materials'])}/{len(b['materials'])}; textures {len(ta)}/{len(tb)} (re-atlased)")
    return ("differs" if not bounds_same else "same"), detail


def read_attacks(path):
    """(game, monster) -> [(attack name, page URL)], from data/catalog/attacks.csv."""
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.setdefault((row["game"], row["monster"]), []).append((row["attack"], row["source_url"]))
    return out


def attack_name(name):
    """The wiki's attack name without its translation marker or a trailing qualifier."""
    name = re.sub(r"\s*\(Unreviewed Translation\)\s*", "", name).strip()
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()


def wiki_visible(attacks, monster, source_game):
    """The wiki's attack lists: MH4U's against the source game's, normalized by name."""
    mh4 = attacks.get(("MH4U", monster)) or []
    src = attacks.get((source_game, monster)) or []
    mh4_url = mh4[0][1] if mh4 else ""
    src_url = src[0][1] if src else ""
    if not src:
        return "not compared", f"the wiki's {source_game} page has no attack list", mh4_url, src_url
    if not mh4:
        return "not compared", "the wiki's MH4U page has no attack list", mh4_url, src_url
    a = {attack_name(n) for n, _ in mh4}
    b = {attack_name(n) for n, _ in src}
    detail = f"source {len(b)} attacks, MH4U {len(a)}"
    if b - a:
        detail += "; the source adds " + ", ".join(sorted(b - a))
    if a - b:
        detail += "; MH4U has " + ", ".join(sorted(a - b))
    if not (a - b or b - a):
        detail += ", the same names"
    return ("differs" if (a - b or b - a) else "same"), detail, mh4_url, src_url


def verdict_of(axes):
    if "differs" in axes:
        return "differs"
    if all(x == "same" for x in axes):
        return "doesn't differ"
    return "not decided"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", required=True, help="data/catalog/versions.csv (the pairing)")
    ap.add_argument("--attacks", default=os.path.join(HERE, "..", "data", "catalog", "attacks.csv"),
                    help="data/catalog/attacks.csv (the wiki's attack lists)")
    ap.add_argument("--mh4u-romfs", required=True)
    ap.add_argument("--mh3u-romfs", required=True)
    ap.add_argument("--mhxx-romfs", required=True, help="MHXX base RomFS (data, motions)")
    ap.add_argument("--mhxx-update-romfs", required=True, help="MHXX v1.4 update RomFS (modules, code)")
    ap.add_argument("--mh4u-exheader", required=True)
    ap.add_argument("--mh4u-code", required=True)
    ap.add_argument("--mh3u-exheader", required=True)
    ap.add_argument("--mh3u-code", required=True)
    ap.add_argument("--mh4u-vt", required=True)
    ap.add_argument("--mh3u-vt", required=True)
    ap.add_argument("--mhxx-vt", required=True)
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args(argv)
    files = GameFiles(args)
    rows = list(csv.DictReader(open(args.rows, newline="", encoding="utf-8")))
    attacks = read_attacks(args.attacks)
    out = []
    for row in rows:
        game = "mh3u" if row["source_game"] == "MH3U" else "mhxx"
        em4, src = row["mh4u_id"], row["source_file"]
        try:
            dverdict, ddetail = data_visible(files, game, em4, src)
        except (ValueError, KeyError) as e:
            dverdict, ddetail = "not compared", f"{type(e).__name__}: {e}"
        mverdict, mdetail = moves_visible(files, game, em4, src)
        wverdict, wdetail, mh4u_url, src_url = wiki_visible(attacks, row["monster"], row["source_game"])
        # The code comparison decides `moves`; the wiki's list can add a difference but its
        # absence does not withhold the verdict the code reached.
        if wverdict == "differs":
            mverdict = "differs"
        elif mverdict == "same" and wverdict == "same":
            mverdict = "same"
        mdetail = f"code: {mdetail}; wiki: {wdetail}"
        try:
            overdict, odetail = model_visible(files, game, em4, src)
        except (ValueError, KeyError) as e:
            overdict, odetail = "not compared", f"{type(e).__name__}: {e}"
        out.append([row["source_game"], row["monster"], em4, src, dverdict, ddetail, mverdict, mdetail,
                    wverdict, wdetail, overdict, odetail,
                    verdict_of((dverdict, mverdict, overdict)),
                    row.get("source_url", ""), src_url, mh4u_url])
    header = ["source_game", "monster", "mh4u_id", "source_file", "data", "data_detail", "moves", "moves_detail",
              "wiki", "wiki_detail", "model", "model_detail", "verdict", "source_url",
              "attack_source_url", "attack_mh4u_url"]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(out)
    counts = collections.Counter(r[12] for r in out)
    print(f"{len(out)} rows: " + ", ".join(f"{k} {v}" for k, v in counts.most_common()))
    for ax, i in (("data", 4), ("moves", 6), ("wiki", 8), ("model", 10)):
        c = collections.Counter(r[i] for r in out)
        print(f"  {ax}: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
