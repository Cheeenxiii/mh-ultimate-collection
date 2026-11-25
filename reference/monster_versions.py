#!/usr/bin/env python3
"""Whether a 3U or GU monster version differs from MH4U's, per axis, from the game files.

Decision 0004's amendment ports a 3U or GU version of a monster MH4U has only when it differs
from MH4U's: its moves (action handlers and the motions they start), its model, or its monster
data beyond values MH4U's version already has. This tool records the comparison for every row
of `data/catalog/versions.csv`, as counts only (names, ids and counts; no game data).

    monster_versions.py --rows data/catalog/versions.csv --mh4u-romfs ... --mh3u-romfs ... \
        --mhxx-romfs ... --mhxx-update-romfs ... --mh4u-vt ... --mh3u-vt ... --mhxx-vt ... -o out.csv

The row file supplies the pairing (`source_game`, `monster`, `mh4u_id`, `source_file`,
`source_url`); every count and verdict is rewritten. The vt TSVs are the class vtables
`reference/mt_vtables.py` recovers, kept outside the repository. The verdict rule and the
columns are in data/catalog/versions.md.
"""
from __future__ import annotations

import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import monster_motions  # noqa: E402

from mhuc import monsterdata  # noqa: E402
from mhuc.formats import arc, mod, romfs  # noqa: E402

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


def moves(files, game, em4, src):
    a = inventory(files, "mh4u", em4)
    b = inventory(files, game, src)
    la, lb = motion_lists(files, "mh4u", em4), motion_lists(files, game, src)
    r = monster_motions.compare(a, b)
    detail = dict(common=r["common"], compared=len(r["same"]) + len(r["different"]),
                  same=len(r["same"]), different=len(r["different"]),
                  skipped=sum(r["skipped"].values()))
    if r["different"] and la and lb:
        s = monster_motions.content_split(a, b, "mh4u", la, game, lb)
        detail.update(same_motion=len(s["same"]), one_track=len(s["same_track"]),
                      elsewhere=len(s["elsewhere"]), diff_motion=len(s["different"]),
                      unresolved=len(s["unresolved"]))
    else:
        detail.update(same_motion=0, one_track=0, elsewhere=0, diff_motion=0, unresolved=0)
    detail["only_b"] = len(set(b) - set(a))
    detail["only_b_motion"] = sum(1 for k in set(b) - set(a) if b[k]["how"] == "constant")
    detail["mh4u_actions"], detail["source_actions"] = len(a), len(b)
    detail["shared"] = (game == "mhxx"
                        and mhxx_class(files, src) != f"uEm{int(src[2:5]):03d}_00")
    return detail


def models(files, game, path):
    return {e.path: e.data for e in files.entries(game, path)
            if e.type_id == MODEL_CLASS and e.data[:4] == b"MOD\0"}


def main_rig(files, game, em):
    if game == "mh4u":
        path = f"/data/{em}.arc"
    else:
        path = f"/arc/enemy/{em}.arc"
    found = models(files, game, path)
    keys = [em] + ([em.split("_")[0] + "_00"] if "_" in em else [])
    for key in keys:
        for p, d in found.items():
            q = p.replace("\\", "/")
            if q.split("/")[-2] == "mod" and q.split("/")[-1] == key:
                h = mod.header(d)
                bones = mod.bones(d, h)
                return dict(bones=h["bones"], skeleton=tuple(sorted((b["id"], b["parent_id"]) for b in bones)),
                            meshes=h["meshes"], vertices=h["vertices"], indices=h["indices"])
    return None


def model_axis(files, game, em4, src):
    a = main_rig(files, "mh4u", em4)
    b = main_rig(files, game, src)
    if a is None or b is None:
        return "not compared", "no main body model found"
    same = a["bones"] == b["bones"] and a["skeleton"] == b["skeleton"]
    detail = (f"bones {a['bones']}/{b['bones']}; skeleton {'same' if a['skeleton'] == b['skeleton'] else 'differs'}; "
              f"vertices {a['vertices']}/{b['vertices']}; indices {a['indices']}/{b['indices']}")
    return ("same rig" if same else "differs"), detail


def data_axis(files, game, em4, src):
    if game == "mhxx":
        ents = files.entries(game, f"/arc/enemy/{src}.arc")
        hits = [e for e in ents if "/hit_data/" in e.path.replace("\\", "/")]
        def any_of(ty):
            got = [e.data for e in hits if e.type_id == ty]
            if len(got) != 1:
                raise KeyError(f"{src}: {len(got)} hit_data entries of {ty:#x}")
            return got[0]
        source = monsterdata.from_mhxx(
            pick(ents, 0x48E8AC29, "dt_tune/"), pick(ents, 0x59D9C3DA, "dt_base/"),
            pick(ents, 0x1BBC291E, "dt_base/"), pick(ents, 0x1AC7B52D, "/body_data/"),
            pick(ents, 0x1AC7B52D, "/cam_body_data/"), any_of(0x5653C1B0), any_of(0x70BB64BA))
    else:
        ents = files.entries(game, f"/arc/enemy/{src}.arc")
        source = monsterdata.from_mh3u(
            pick(ents, 0x4DEE8265, "em_status"), pick(ents, 0x1AC7B52D, "em_body"),
            pick(ents, 0x1AC7B52D, "em_cambody"), pick(ents, 0x5653C1B0, "em_hitsize"),
            pick(ents, 0x0C6016B9, "em_hitdata"))
    ents4 = files.entries("mh4u", "/data/em_data.arc")
    ref = monsterdata.from_mh4u(pick(ents4, 0x0A0E48D4, f"/{em4}/"), pick(ents4, 0x3D8BBBAC, f"/{em4}/"))
    verdicts = dict(monsterdata.compare(source, ref))
    missing = [f for f, v in verdicts.items() if v == "absent in MH4U"]
    extra = []
    m = re.match(r"source parts \[([^\]]*)\], MH4U's \[([^\]]*)\]", verdicts.get("break parts", ""))
    if m:
        s, f = ({x.strip() for x in m.group(1).split(",") if x.strip()},
                {x.strip() for x in m.group(2).split(",") if x.strip()})
        extra = sorted(s - f)
    return ("differs" if missing or extra else "same"), verdicts, missing, extra


def pick(ents, type_id, *words):
    hits = [e.data for e in ents if e.type_id == type_id and all(w in e.path.replace("\\", "/") for w in words)]
    if len(hits) != 1:
        raise KeyError(f"{len(hits)} entries of {type_id:#x} with {words}")
    return hits[0]


def data_detail(verdicts):
    def get(k, d="absent"):
        return verdicts.get(k, d)
    hp = get("base HP")
    hz = get("hitzone table")
    hz = "8/8" if hz == "equal" else (hz.replace(" of 8 rows equal", "/8 rows") if "rows equal" in hz else hz)
    pm = re.match(r"(\d+) of 8", get("part table"))
    parts = pm.group(1) if pm else "-"
    vm = re.match(r"(\d+) groups \(MH4U (\d+)\)", get("attack volumes"))
    vol = f"{vm.group(1)}/{vm.group(2)}" if vm else get("attack volumes")
    rec = get("attack records")
    rm = re.match(r"(\d+) of (\d+) records equal", rec)
    sm = re.search(r"source has (\d+)", rec)
    rec = (f"{rm.group(1)}/{rm.group(2)}" if rm else rec) + (f" (source {sm.group(1)})" if sm else "")
    return (f"HP {hp}; hitzones {hz}; parts {parts}/8; attack volumes {vol}; "
            f"attack records {rec}; break parts {get('break parts')}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", required=True, help="data/catalog/versions.csv (the pairing)")
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
    out = []
    for row in rows:
        game = "mh3u" if row["source_game"] == "MH3U" else "mhxx"
        em4, src = row["mh4u_id"], row["source_file"]
        dverdict, verdicts, missing, extra = data_axis(files, game, em4, src)
        ddetail = data_detail(verdicts)
        if missing:
            ddetail += "; fields MH4U lacks: " + ", ".join(missing)
        if extra:
            ddetail += "; parts MH4U lacks: " + ", ".join(extra)
        try:
            m = moves(files, game, em4, src)
            if m["mh4u_actions"] < 50 or m["source_actions"] < 50:
                mverdict = "not compared"
                mdetail = f"inventory too small ({m['mh4u_actions']} vs {m['source_actions']} actions)"
            elif m["compared"] < 10:
                mverdict = "not compared"
                mdetail = f"action ids do not line up ({m['compared']} compared of {m['common']} common)"
            else:
                diff, only = m.get("diff_motion", 0), m["only_b_motion"]
                mverdict = "differs" if (diff or only) else "same"
                mdetail = (("shared family class; " if m.get("shared") else "")
                           + f"common {m['common']}; compared {m['compared']}; same index {m['same']}; "
                           f"different index {m['different']}; source-only {m['only_b']} ({only} start a motion); "
                           f"content: same {m['same_motion']}, one-track {m['one_track']}, "
                           f"elsewhere {m['elsewhere']}, different {diff}, unresolved {m['unresolved']}")
        except Exception as e:
            mverdict, mdetail = "not compared", f"{type(e).__name__}: {e}"
        overdict, odetail = model_axis(files, game, em4, src)
        axes = (dverdict, mverdict, overdict)
        if "differs" in axes:
            verdict = "differs"
        elif all(x in ("same", "same rig") for x in axes):
            verdict = "doesn't differ"
        else:
            verdict = "not decided"
        out.append([row["source_game"], row["monster"], em4, src, dverdict, ddetail, mverdict, mdetail,
                    overdict, odetail, verdict, row.get("source_url", "")])
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_game", "monster", "mh4u_id", "source_file", "data", "data_detail",
                    "moves", "moves_detail", "model", "model_detail", "verdict", "source_url"])
        w.writerows(out)
    counts = collections.Counter(r[10] for r in out)
    print(f"{len(out)} rows: " + ", ".join(f"{k} {v}" for k, v in counts.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
