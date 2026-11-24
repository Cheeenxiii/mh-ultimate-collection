"""mhuc's command line: `mhuc <command> ...`; `mhuc --help` lists the commands."""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys

from . import __version__, entropy, survey
from .crypto import dlccrypt
from .formats import arc, classid, gmd, romfs, tex, xfs
from .quests import quest


def _read(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def cmd_arc(args) -> int:
    if args.action == "list":
        a = arc.read(_read(args.file))
        print(f"ARC version 0x{a.version:x}, {len(a.entries)} files")
        for e in a.entries:
            print(f"{len(e.data):>10}  {e.type_name or '?':<24} {e.file_name}")
    elif args.action == "extract":
        a = arc.read(_read(args.file))
        for e in a.entries:
            dest = os.path.join(args.out, *e.file_name.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(e.data)
        with open(os.path.join(args.out, "arc.json"), "w") as f:
            json.dump({"version": a.version, "order": [e.file_name for e in a.entries]}, f, indent=1)
        print(f"{len(a.entries)} files to {args.out}")
    else:  # pack
        meta_path = os.path.join(args.file, "arc.json")
        meta = json.loads(_read(meta_path)) if os.path.exists(meta_path) else {}
        names = meta.get("order") or sorted(
            os.path.relpath(os.path.join(d, n), args.file).replace(os.sep, "/")
            for d, _, files in os.walk(args.file) for n in files if n != "arc.json")
        entries = [arc.entry_from_file(n, _read(os.path.join(args.file, *n.split("/")))) for n in names]
        data = arc.write(arc.Archive(meta.get("version", args.version), entries))
        with open(args.out, "wb") as f:
            f.write(data)
        print(f"{len(entries)} files to {args.out}")
    return 0


def cmd_classid(args) -> int:
    for name in args.names:
        print(f"{classid.class_id(name):08X}  {name}")
    return 0


def cmd_gmd(args) -> int:
    json.dump(gmd.to_json(gmd.read(_read(args.file))), sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


def cmd_tex(args) -> int:
    t = tex.read(_read(args.file))
    if args.action == "info":
        print(f"{t.width}x{t.height} {t.fmt}, {len(t.levels)} mip levels, version 0x{t.version:x}")
    else:
        w, h, rgba = tex.to_rgba(t, flip_y=args.flip_y)
        tex.write_ppm(args.out, w, h, rgba)
        print(f"{w}x{h} to {args.out}")
    return 0


def cmd_romfs(args) -> int:
    for f in romfs.open_image(args.image).files():
        print(f"{f.size:>10}  {f.path}")
    return 0


def cmd_survey(args) -> int:
    print(survey.report(survey.survey(args.image, args.workers)))
    return 0


def cmd_entropy(args) -> int:
    print(entropy.report(entropy.walk(args.paths)))
    return 0


def cmd_xfs(args) -> int:
    x = xfs.read(_read(args.file))
    json.dump({"endian": x.endian, "version": [x.version, x.subversion],
               "classes": [{"dti_id": f"0x{c.dti_id:08X}",
                            "props": [{"name": p.name, "type": p.type_name, "attr": p.attr} for p in c.props]}
                           for c in x.classes],
               "root": x.root}, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


DECRYPT = {"mh4u-save": "mh4u_save_decrypt", "mh4u-dlc": "mh4u_dlc_decrypt",
           "mhxx-dlc": "mhxx_dlc_decrypt", "mh3u-dlc": "mh3u_dlc_decrypt"}


def cmd_decrypt(args) -> int:
    key = _read(args.key).rstrip(b"\r\n")
    data = _read(args.file)
    fn = getattr(dlccrypt, DECRYPT[args.kind])
    try:
        plain = fn(data, key, args.mode) if args.kind == "mh4u-save" else fn(data, key)
    except dlccrypt.CryptoError as e:
        print(f"mhuc decrypt: {e}", file=sys.stderr)
        return 1
    with open(args.out, "wb") as f:
        f.write(plain)
    print(f"{len(plain)} bytes to {args.out}")
    return 0


def cmd_encrypt(args) -> int:
    key = _read(args.key).rstrip(b"\r\n")
    out = dlccrypt.mh4u_save_encrypt(_read(args.file), key, args.mode, args.seed)
    with open(args.out, "wb") as f:
        f.write(out)
    print(f"{len(out)} bytes to {args.out}")
    return 0


def _quest_files(kind: str, path: str):
    """(name, parsed) for every quest in a file: an Extra Data quest file, a .mib, an MHXX .arc or a .quest."""
    data = _read(path)
    if kind == "mh4u":
        if data[4:8] == b"v005" and len(data) < quest.SLOT:
            return [(os.path.basename(path), quest.parse_mib4(data))]
        return [(name, quest.parse_mib4(body)) for _, name, body in quest.mh4u_slots(data)]
    if kind == "mh3u":
        if data[:4] == b"QTDS":
            return [(os.path.basename(path), quest.parse_qtds(data))]
        return [(name, quest.parse_qtds(rec)) for _, name, rec in quest.mh3u_slots(data)]
    a = arc.read(data)  # mhxx: a quest archive, every part read
    parts: dict = {}
    for e in a.entries:
        n = e.file_name.split("/")[-1]
        if e.type_name == "rQuestData":
            parts["mib"] = quest.parse_mibxx(e.data)
        elif e.type_name == "rSetEmMain":
            parts.setdefault("sem", {})[n] = quest.parse_sem(e.data)
        elif e.type_name == "rEmSetList":
            parts.setdefault("esl", {})[n] = quest.parse_esl(e.data)
        elif e.type_name == "rRem":
            parts.setdefault("rem", {})[n] = quest.parse_rem(e.data)
        elif n.startswith("supp_"):
            parts["supply"] = quest.parse_supply(e.data)
    return [(os.path.basename(path), parts)]


def cmd_quest(args) -> int:
    if args.action == "dump":
        out = {name: q for p in args.paths for name, q in _quest_files(args.kind, p)}
        json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    ok = bad = 0  # check: parse everything, print counts only
    for p in args.paths:
        try:
            ok += len(_quest_files(args.kind, p))
        except (struct.error, UnicodeDecodeError, ValueError, IndexError) as e:
            bad += 1
            print(f"{os.path.basename(p)}: {e}", file=sys.stderr)
    print(f"{ok} quests read, {bad} files failed")
    return 1 if bad else 0


def cmd_mib(args) -> int:
    from .quests import mibwrite
    if args.action == "export":
        obj = mibwrite.model_to_json(mibwrite.mib4_model(_read(args.src)))
        with open(args.dst, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write("\n")
    else:
        with open(args.src, encoding="utf-8") as f:
            mib = mibwrite.mib4_build(mibwrite.model_from_json(json.load(f)))
        quest.parse_mib4(mib)  # refuse to write what the reader can't read back
        with open(args.dst, "wb") as f:
            f.write(mib)
    print(f"{args.src} -> {args.dst}")
    return 0


def cmd_questslot(args) -> int:
    if args.action == "get":
        if len(args.paths) != 1 or args.slot is None or not args.out:
            print("mhuc questslot get: one quest file, with --slot and --out", file=sys.stderr)
            return 2
        found = {k: body for k, _, body in quest.mh4u_slots(_read(args.paths[0]))}
        if args.slot not in found:
            print(f"mhuc questslot get: slot {args.slot} is empty", file=sys.stderr)
            return 1
        with open(args.out, "wb") as f:
            f.write(quest.mh4u_slot_mib(found[args.slot]))
        print(f"slot {args.slot} -> {args.out}")
        return 0
    if args.action == "check":
        used = good = 0
        for p in args.paths:
            for k, name, body in quest.mh4u_slots(_read(p)):
                used += 1
                try:
                    quest.mh4u_slot_mib(body)
                    good += 1
                except quest.QuestError as e:
                    print(f"{os.path.basename(p)} slot {k} ({name}): {e}", file=sys.stderr)
        print(f"{used} used slots, {good} with a matching hash and size")
        return 0 if used == good else 1
    if len(args.paths) != 1 or args.slot is None or not args.out or (args.mib is None) == (args.from_slot is None):
        print("mhuc questslot put: one quest file, with --slot, --out and one of --mib, --from-slot", file=sys.stderr)
        return 2
    data = _read(args.paths[0])
    if any(k == args.slot for k, _, _ in quest.mh4u_slots(data)) and not args.replace:
        print(f"mhuc questslot put: slot {args.slot} holds a quest; pass --replace to overwrite it", file=sys.stderr)
        return 1
    if args.mib:
        mib, name = _read(args.mib), os.path.basename(args.mib)
    else:
        found = {k: body for k, _, body in quest.mh4u_slots(data)}
        if args.from_slot not in found:
            print(f"mhuc questslot put: slot {args.from_slot} is empty", file=sys.stderr)
            return 1
        mib = quest.mh4u_slot_mib(found[args.from_slot])
        name = None
    if args.id is not None or args.title is not None:
        try:
            mib = quest.mib4_patch(mib, args.id, args.title)
        except quest.QuestError:  # a longer title: lay the quest out again (check Q18)
            from .quests import mibwrite
            mib = mibwrite.mib4_build(mibwrite.mib4_set_texts(mibwrite.mib4_model(mib), 0, args.title))
            mib = quest.mib4_patch(mib, args.id)
            print("the title didn't fit in place: the quest was laid out again", file=sys.stderr)
    name = args.name or (f"m{args.id:05d}.mib" if args.id is not None else name)
    if not name:
        print("mhuc questslot put: give --name or --id for a copied slot", file=sys.stderr)
        return 2
    new = quest.mh4u_put_slot(data, args.slot, quest.mh4u_pack_slot(mib, name))
    with open(args.out, "wb") as f:
        f.write(new)
    print(f"{name} ({len(mib)} bytes) in slot {args.slot}, {len(new)} bytes to {args.out}")
    return 0


def cmd_extdata(args) -> int:
    from . import extdata
    if args.action == "testkit":
        if not args.key or not args.out:
            print("mhuc extdata testkit EXTDATA_DIR --key K --out DIR", file=sys.stderr)
            return 2
        files = {n: _read(os.path.join(args.file, n)) for n in sorted(os.listdir(args.file))
                 if n.startswith(("quest", "otomo"))}
        out, notes = extdata.testkit(files, _read(args.key).rstrip(b"\r\n"))
        os.makedirs(args.out, exist_ok=True)
        for n, d in out.items():
            with open(os.path.join(args.out, n), "wb") as f:
                f.write(d)
        text = ("MH Ultimate Collection in-game test kit (specs/quest.md Q17, Q19; specs/extdata.md E4).\n"
                "Back up your Extra Data first, then copy these files over it and open the downloaded "
                "quests and the DLC Palicos.\n\n" + "\n".join("- " + n for n in notes) + "\n")
        with open(os.path.join(args.out, "TESTKIT.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        print(text, end="")
        return 0
    with open(args.file, "rb") as f:
        data = f.read()
    if args.action == "rename":
        if args.kind != "otomo" or args.slot is None or args.name is None or not args.out:
            print("mhuc extdata rename: otomo only, with --slot, --name and --out", file=sys.stderr)
            return 2
        new = extdata.rename_palico(data, args.slot, args.name, args.last_byte)
        with open(args.out, "wb") as f:
            f.write(new)
        print(f"slot {args.slot} renamed, {len(new)} bytes to {args.out}")
        return 0
    if args.kind == "card":
        out = extdata.card_summary(data)
        if args.action == "dump":
            out = {"used": out, "guild_quests": [extdata.parse_guild_quest(r)
                                                 for r in extdata.card_records(data, "guild_quests") if any(r)]}
    else:
        slots = extdata.otomo_slots(data)
        out = slots if args.action == "dump" else {"palicos": len(slots)}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


def cmd_catalog(args) -> int:
    from . import catalog
    text = catalog.render(args.dir)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


def cmd_convert(args) -> int:
    need = (args.what, args.src, args.template, args.texts, args.id, args.out)
    if args.what != "quest" or None in need:
        print("mhuc convert quest QUEST.json --from mhxx --template T.json --texts TEXTS.json --id N "
              "[--tables DIR] --out OUT.json  (docs/architecture.md#quests)", file=sys.stderr)
        return 2
    from .quests import convert

    def load(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    src = load(args.src)
    if isinstance(src, dict) and "mib" not in src and len(src) == 1:  # mhuc quest dump's {name: parts}
        src = next(iter(src.values()))
    try:
        out = convert.convert_mhxx(src, load(args.template), convert.load_tables(args.tables), args.id,
                                   load(args.texts))
    except convert.ConvertError as e:
        print(f"mhuc convert: {e}", file=sys.stderr)
        return 1
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"{args.out}: {len(out['placeholders'])} placeholders to record (docs/sources.md#authored-register); "
          "build it with mhuc mib import")
    return 0


def cmd_idnames(args) -> int:
    import csv as _csv

    from . import catalog
    from .quests import idnames
    out_real = os.path.realpath(args.out)
    repo = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if out_real == repo or out_real.startswith(repo + os.sep):
        print("mhuc idnames: the table is derived from the game's files; write it outside the repository",
              file=sys.stderr)
        return 2
    game = {"mh4u": "MH4U", "mh3u": "MH3U"}[args.kind]
    known = {r["monster"] for r in catalog.read_table(os.path.join(repo, "data", "catalog", "monsters.csv"))
             if r["game"] == game}
    obs = []
    for p in args.paths:
        for _, q in _quest_files(args.kind, p):
            if args.kind == "mh4u":
                ids, title = {d["monster"] for w in q["large_waves"] for d in w}, q["text"]["eng"]["title"]
            else:
                ids, title = {m["type"] for m in q["monsters"] if m["type"]}, q["name"]["eng"]
            text = idnames.fetch_page(f"{title} ({game} Quest)", args.cache)
            if text and ids:
                obs.append((ids, idnames.categories(text, game, known)))
    res = idnames.infer(obs)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["id", "name", "candidates"])
        for i, c in res.items():
            w.writerow([i, c[0] if len(c) == 1 else "", "; ".join(c)])
    one = sum(1 for c in res.values() if len(c) == 1)
    print(f"{len(obs)} quests with a wiki page; {len(res)} ids, {one} with one name; table in {args.out}")
    return 0


def cmd_mod(args) -> int:
    from .formats import mod as modfile
    out = {os.path.basename(p): modfile.info(_read(p)) for p in args.paths}
    json.dump(out, sys.stdout, indent=1)
    print()
    return 0


def cmd_emd(args) -> int:
    from collections import Counter

    from . import survey
    total: Counter = Counter()
    for p in args.paths:
        st: dict = {}
        survey.survey_arc(_read(p), st)
        total.update(st.get("emd", Counter()))
    for k, v in sorted(total.items()):
        print(f"{k}: {v}")
    return 0 if total else 1


def cmd_monsterdata(args) -> int:
    from . import monsterdata
    from .formats import arc

    def entries(path: str) -> list:
        return arc.read(_read(path)).entries

    def pick(ents: list, type_id: int, *words: str) -> bytes:
        hits = [e.data for e in ents if e.type_id == type_id and all(w in e.path.replace("\\", "/") for w in words)]
        if len(hits) != 1:
            raise SystemExit(f"{len(hits)} entries of class {type_id:#010x} named with {words} (expected 1)")
        return hits[0]

    ents4 = entries(args.mh4u)
    mh4u = monsterdata.from_mh4u(pick(ents4, 0x0A0E48D4, args.id + ""), pick(ents4, 0x3D8BBBAC, args.id))
    for game, path in (("mhxx", args.mhxx), ("mh3u", args.mh3u)):
        if not path:
            continue
        ents = entries(path)
        if game == "mhxx":
            src = monsterdata.from_mhxx(pick(ents, 0x48E8AC29, "dt_tune/"), pick(ents, 0x59D9C3DA, "dt_base/"),
                                        pick(ents, 0x1BBC291E, "dt_base/"), pick(ents, 0x1AC7B52D, "/body_data/"),
                                        pick(ents, 0x1AC7B52D, "cam_body_data/"),
                                        pick(ents, 0x5653C1B0, "enemy/hit_data/"), pick(ents, 0x70BB64BA, "hit_data/"))
        else:
            src = monsterdata.from_mh3u(pick(ents, 0x4DEE8265, "em_status"), pick(ents, 0x1AC7B52D, "em_body"),
                                        pick(ents, 0x1AC7B52D, "em_cambody"), pick(ents, 0x5653C1B0, "em_hitsize"),
                                        pick(ents, 0x0C6016B9, "em_hitdata"))
        print(f"{game} -> MH4U {args.id}:")
        for name, verdict in monsterdata.compare(src, mh4u):
            print(f"  {name}: {verdict}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="mhuc",
        description="MH Ultimate Collection's toolkit: read, write and convert the files of MH4U, MH3U and MHXX")
    ap.add_argument("--version", action="version", version=f"mhuc {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("arc", help="MT Framework ARC archives")
    p.add_argument("action", choices=["list", "extract", "pack"])
    p.add_argument("file", help="the archive (list, extract) or the folder (pack)")
    p.add_argument("out", nargs="?", help="output folder (extract) or archive (pack)")
    p.add_argument("--version", type=lambda s: int(s, 0), default=0x13, help="ARC version for pack (0x13)")
    p.set_defaults(func=cmd_arc)

    p = sub.add_parser("classid", help="class-id hash of type names")
    p.add_argument("names", nargs="+")
    p.set_defaults(func=cmd_classid)

    p = sub.add_parser("gmd", help="GMD text tables")
    p.add_argument("action", choices=["dump"])
    p.add_argument("file")
    p.set_defaults(func=cmd_gmd)

    p = sub.add_parser("tex", help="3DS textures")
    p.add_argument("action", choices=["info", "decode"])
    p.add_argument("file")
    p.add_argument("out", nargs="?")
    p.add_argument("--flip-y", action="store_true", help="rows stored bottom-up")
    p.set_defaults(func=cmd_tex)

    p = sub.add_parser("romfs", help="list the files of a RomFS image (romfs.bin)")
    p.add_argument("action", choices=["list"])
    p.add_argument("image")
    p.set_defaults(func=cmd_romfs)

    p = sub.add_parser("survey", help="run the specs' with-game-files checks over a RomFS image; counts only")
    p.add_argument("image")
    p.add_argument("--workers", type=int, default=4, help="processes (each holds one archive in memory)")
    p.set_defaults(func=cmd_survey)

    p = sub.add_parser("entropy", help="size, block alignment and byte entropy of files (encrypted?); counts only")
    p.add_argument("paths", nargs="+", help="files or folders")
    p.set_defaults(func=cmd_entropy)

    p = sub.add_parser("xfs", help="MT XFS serialised objects (.supp, .pop, ...) as JSON, schema included")
    p.add_argument("action", choices=["dump"])
    p.add_argument("file")
    p.set_defaults(func=cmd_xfs)

    p = sub.add_parser("decrypt", help="decrypt a DLC or Extra Data file (the key comes from a file you supply)")
    p.add_argument("kind", choices=sorted(DECRYPT))
    p.add_argument("file")
    p.add_argument("out")
    p.add_argument("--key", required=True, help="a file holding the key's bytes (never kept in this repository)")
    p.add_argument("--mode", choices=dlccrypt.MH4U_SAVE_MODES, default="normal", help="mh4u-save only")
    p.set_defaults(func=cmd_decrypt)

    p = sub.add_parser("encrypt", help="encrypt an MH4U save or Extra Data file again (the key comes from a file)")
    p.add_argument("kind", choices=["mh4u-save"])
    p.add_argument("file")
    p.add_argument("out")
    p.add_argument("--key", required=True, help="a file holding the key's bytes (never kept in this repository)")
    p.add_argument("--mode", choices=dlccrypt.MH4U_SAVE_MODES, default="normal")
    p.add_argument("--seed", type=lambda v: int(v, 0), default=0x1234, help="the 16-bit XOR seed")
    p.set_defaults(func=cmd_encrypt)

    p = sub.add_parser("quest", help="read quests: MH4U .mib, MHXX quest .arc, MH3U QTDS, or Extra Data quest files")
    p.add_argument("action", choices=["dump", "check"])
    p.add_argument("kind", choices=["mh4u", "mhxx", "mh3u"])
    p.add_argument("paths", nargs="+")
    p.set_defaults(func=cmd_quest)

    p = sub.add_parser("mib", help="MH4U .mib as editable JSON: export a quest, import (build) it back")
    p.add_argument("action", choices=["export", "import"])
    p.add_argument("src", help="the .mib (export) or the JSON (import)")
    p.add_argument("dst")
    p.set_defaults(func=cmd_mib)

    p = sub.add_parser("questslot", help="MH4U Extra Data quest slots (decrypted): check hashes, put a .mib")
    p.add_argument("action", choices=["check", "get", "put"])
    p.add_argument("paths", nargs="+")
    p.add_argument("--slot", type=int)
    p.add_argument("--mib")
    p.add_argument("--replace", action="store_true", help="allow overwriting a used slot")
    p.add_argument("--from-slot", type=int, help="copy the quest stored in this slot instead of --mib")
    p.add_argument("--id", type=int, help="give the quest this id (and the name mNNNNN.mib)")
    p.add_argument("--title", help="a new title in all five languages (a longer one lays the quest out again)")
    p.add_argument("--name", help="the slot's file name (default: the .mib's, or mNNNNN.mib with --id)")
    p.add_argument("--out")
    p.set_defaults(func=cmd_questslot)

    p = sub.add_parser("extdata", help="MH4U Extra Data besides quests (decrypted): card* and otomo1")
    p.add_argument("action", choices=["dump", "check", "rename", "testkit"],
                   help="check prints counts only; rename edits a Palico's name (check E4); testkit takes the "
                        "encrypted Extra Data folder and builds the files for checks Q17, Q19 and E4")
    p.add_argument("kind", nargs="?", choices=["card", "otomo"], default="otomo")
    p.add_argument("file", help="a decrypted file, or for testkit the Extra Data folder")
    p.add_argument("--key", help="testkit: a file holding the save key (never kept in this repository)")
    p.add_argument("--slot", type=int)
    p.add_argument("--name")
    p.add_argument("--last-byte", type=lambda v: int(v, 0))
    p.add_argument("--out")
    p.set_defaults(func=cmd_extdata)

    p = sub.add_parser("catalog", help="what MH4U already has of 3U's and GU's monsters and maps (data/catalog)")
    p.add_argument("action", choices=["overlap"])
    p.add_argument("--dir", default=os.path.join(os.path.dirname(__file__), "..", "..", "data", "catalog"))
    p.add_argument("--out", help="write the Markdown here instead of printing it")
    p.set_defaults(func=cmd_catalog)

    p = sub.add_parser("mod", help="MT Mobile models: header and mesh summary (specs/mod.md)")
    p.add_argument("action", choices=["info"])
    p.add_argument("paths", nargs="+")
    p.set_defaults(func=cmd_mod)

    p = sub.add_parser("emd", help="check E1 (specs/emd.md) on ARCs holding .emd/.etd pairs (data/em_data.arc)")
    p.add_argument("action", choices=["check"])
    p.add_argument("paths", nargs="+")
    p.set_defaults(func=cmd_emd)

    p = sub.add_parser("monsterdata", help="rebuild an MH4U monster's .etd/.emd values from MHXX's or MH3U's own "
                                           "files and compare (counts only; specs/dttune.md, specs/dtbase.md, "
                                           "specs/dtbparts.md, specs/emstatus.md)")
    p.add_argument("--mh4u", required=True, help="MH4U data/em_data.arc")
    p.add_argument("--id", required=True, help="the monster's MH4U name in em_data.arc, e.g. em001")
    p.add_argument("--mhxx", help="the monster's MHXX archive, e.g. arc/enemy/em001_00.arc")
    p.add_argument("--mh3u", help="the monster's MH3U archive, e.g. arc/enemy/em001.arc")
    p.set_defaults(func=cmd_monsterdata)

    p = sub.add_parser("idnames", help="monster ids to names from quests and the wiki's quest pages (table "
                                       "written outside the repository)")
    p.add_argument("kind", choices=["mh4u", "mh3u"])
    p.add_argument("paths", nargs="+", help="decrypted Extra Data quest files (or .mib / QTDS files)")
    p.add_argument("--cache", required=True, help="a folder for the fetched wiki pages")
    p.add_argument("--out", required=True, help="the CSV to write, outside the repository")
    p.set_defaults(func=cmd_idnames)

    p = sub.add_parser("convert", help="convert a source game's quest into an MH4U .mib model (JSON)")
    p.add_argument("what", nargs="?", choices=["quest"])
    p.add_argument("src", nargs="?", help="the quest as `mhuc quest dump mhxx` prints it")
    p.add_argument("--from", dest="game", choices=["mhxx"], default="mhxx")
    p.add_argument("--template", help="an MH4U quest as `mhuc mib export` writes it, for what isn't converted")
    p.add_argument("--texts", help="JSON: for each of eng, fre, spa, ger, ita, the 7 MH4U strings")
    p.add_argument("--id", type=int, help="the MH4U quest id to give it")
    p.add_argument("--tables", default=os.path.join(os.path.dirname(__file__), "..", "..", "data", "idmap",
                                                     "mhxx-mh4u"))
    p.add_argument("--out")
    p.set_defaults(func=cmd_convert)

    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "arc" and args.action in ("extract", "pack") and not args.out:
        print("mhuc arc: extract and pack need an output", file=sys.stderr)
        return 2
    if args.command == "tex" and args.action == "decode" and not args.out:
        print("mhuc tex decode: needs an output .ppm", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
