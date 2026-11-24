"""Recompile a reference game with the fork's recompiler, from its tables in games/<name>/.

usage: recompile_game.py <game> --exheader exheader.bin --code code.bin -o OUT
Then build and test OUT with the fork's recomp.build and recomp.gametest.
"""
from __future__ import annotations

import argparse
import struct
import sys

import fork  # noqa: F401  (puts the fork's tools on sys.path)

import codebin2elf  # noqa: E402
import exheader as exh  # noqa: E402
import games
import recompile as R  # noqa: E402
from recomp.analysis import Image  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("game", help="a folder in games/")
    ap.add_argument("--exheader", required=True)
    ap.add_argument("--code", required=True)
    ap.add_argument("--extra", action="append", default=None, help="more entry point lists")
    ap.add_argument("--no-data-pointers", action="store_true")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args(argv)
    args.functions = args.hooks = args.tunables = None
    game = games.resolve_args(args)
    if game is None:
        raise SystemExit("for MH4U itself, use the fork's tools/recompile.py")
    with open(args.exheader, "rb") as f:
        raw = f.read()
    header = exh.parse(raw)
    with open(args.code, "rb") as f:
        code = codebin2elf.load_code(header, f.read())
    games.check_game_code(game, code)
    img = Image(code, header.text.address, R.code_size(header, code))
    segs = None if args.no_data_pointers else [(header.ro.address, header.ro.size),
                                               (header.data.address, header.data.size)]
    title_id = struct.unpack_from("<Q", raw, 0x200)[0]
    res = R.recompile(img, R.load_entries(args.functions, args.extra), args.out, data_segments=segs,
                      title_id=title_id, hooks={}, tunables={})
    for k, v in res["report"].items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
