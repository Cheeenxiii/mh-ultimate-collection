"""mhuc's command line: `mhuc <command> ...` (README.md lists the commands)."""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__, arc, classid, entropy, gmd, romfs, survey, tex, xfs


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


def cmd_pipeline(args) -> int:
    print(f"mhuc {args.command}: not implemented yet. It needs the game files and is planned in "
          "docs/design/ (the first session with game files fills it in).", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="mhuc", description="MH Ultimate Collection tools")
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

    for name, text in (("ingest", "read a dump into a work folder (needs game files)"),
                       ("convert", "convert a source game's assets for MH4U (needs game files)"),
                       ("build", "build the mod's romfs and plugins (needs game files)")):
        p = sub.add_parser(name, help=text)
        p.add_argument("rest", nargs=argparse.REMAINDER)
        p.set_defaults(func=cmd_pipeline)
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
