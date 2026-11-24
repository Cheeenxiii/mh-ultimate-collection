"""The reference games' tables (reference/games/<name>/) and the code they fit.

`mh4u` stands for the fork's own config/, so cross-game tools treat MH4U like the others.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re

import fork

GAMES = os.path.join(fork.HERE, "games")


def game_config(name: str, games: str = GAMES) -> tuple[dict, str]:
    """A reference game's game.json and its folder."""
    folder = os.path.join(games, name)
    path = os.path.join(folder, "game.json")
    if not re.fullmatch(r"[a-z0-9_]+", name) or not os.path.exists(path):
        known = sorted(d for d in os.listdir(games) if os.path.exists(os.path.join(games, d, "game.json"))) \
            if os.path.isdir(games) else []
        raise SystemExit(f"no reference game {name!r} in {games} (known: mh4u, {', '.join(known) or 'none'})")
    with open(path) as f:
        return json.load(f), folder


def resolve_args(args: argparse.Namespace, games: str = GAMES) -> dict | None:
    """Fills the tables left unset: the fork's config/ for mh4u, the game's folder otherwise
    (no hooks, no tunables). Returns the game's game.json, or None for mh4u."""
    extra = args.extra or []
    if args.game in ("", "mh4u"):
        cfg = os.path.join(fork.ROOT, "config")
        dump = os.path.join(fork.ROOT, "baserom", "update_v130")
        args.exheader = args.exheader or os.path.join(dump, "exheader.bin")
        args.code = args.code or os.path.join(dump, "code.bin")
        args.functions = args.functions or os.path.join(cfg, "functions.tsv")
        args.extra = [os.path.join(cfg, "extra_entries.txt")] + extra
        args.hooks = os.path.join(cfg, "hooks.txt") if args.hooks is None else args.hooks
        args.tunables = os.path.join(cfg, "tunables.txt") if args.tunables is None else args.tunables
        return None
    game, folder = game_config(args.game, games)
    if not args.exheader or not args.code:
        raise SystemExit(f"{args.game} needs --exheader and --code from your own dump of it")
    args.functions = args.functions or os.path.join(folder, "functions.tsv")
    if not os.path.exists(args.functions):
        raise SystemExit(f"{args.game} has no function table yet ({args.functions})")
    own = os.path.join(folder, "extra_entries.txt")
    args.extra = ([own] if os.path.exists(own) else []) + extra
    args.hooks = args.hooks or None
    args.tunables = args.tunables or None
    return game


def check_game_code(game: dict, code: bytes) -> None:
    """A reference game's tables fit only the code its game.json names."""
    sha1 = hashlib.sha1(code).hexdigest()
    if sha1 != game["code_sha1"]:
        raise SystemExit(f"this code (sha1 {sha1}) isn't {game['name']}'s ({game['code_sha1']}): "
                         "its tables would point into the wrong code")
