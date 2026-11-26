#!/usr/bin/env python3
"""The runtime module's family list, discovered from its directory.

The 3U Rathian's module is split one C file per action family under
`mods/uc_runtime/src/monsters/rathian-3u/`, so the ten action-slice issues (#217 to #229, and
action 4's #136) each add one file and nothing shared. This tool writes the header the module
includes: one `extern` per family file and the list the module's dispatch iterates. The build
runs it (the runtime's Makefile), so adding a file puts the family in the list and no slice
edits a list.

A family file `cat0.c` must export `const MhucFamily mhuc_3u_family_cat0` (the stem, with
every non-alphanumeric byte replaced by `_`); a file that doesn't fails the link, naming the
symbol. The header is generated, never committed.

    gen_families.py --dir <family dir> --out <families.h>

Licence: GPL-3.0-or-later.
"""
from __future__ import annotations

import argparse
import os
import re

PREFIX = "mhuc_3u_family_"
GUARD = "MHUC_RATHIAN_3U_FAMILIES_H"


def symbol(path: str) -> str:
    """The `const MhucFamily` a family file must export, from its file name."""
    stem = os.path.splitext(os.path.basename(path))[0]
    name = re.sub(r"[^0-9A-Za-z_]", "_", stem)
    if not name or name[0].isdigit():
        name = "_" + name
    return PREFIX + name


def family_files(directory: str) -> list[str]:
    """The family files in the directory, in name order. A leading dot or underscore file is
    not one (an editor's or the generator's own)."""
    names = sorted(
        n for n in os.listdir(directory)
        if n.endswith(".c") and not n.startswith((".", "_"))
    )
    return [os.path.join(directory, n) for n in names]


def render(families: list[str], directory: str) -> str:
    """The generated header for `directory`'s family files."""
    symbols = [symbol(f) for f in families]
    duplicate = next((s for i, s in enumerate(symbols) if s in symbols[:i]), None)
    if duplicate:
        raise SystemExit(f"two family files export {duplicate}: rename one")
    shown = os.path.relpath(directory) if not os.path.isabs(directory) else directory
    lines = [
        f"/* Generated from the .c files in {shown}/ by tools/gen_families.py. Do not edit: add a family",
        " * file to the directory and the build writes it here.",
        " * Licence: GPL-3.0-or-later. */",
        f"#ifndef {GUARD}",
        f"#define {GUARD}",
        "",
        '#include "family.h"',
        "",
        "/* One MhucFamily per file in the directory, in name order; the module's dispatch tries",
        " * them in turn. */",
    ]
    lines += [f"extern const MhucFamily {s};" for s in symbols]
    if symbols:
        lines += ["", "static const MhucFamily *const mhuc_3u_families[] = {"]
        lines += [f"    &{s}," for s in symbols]
        lines += ["};"]
    else:
        lines += ["", "static const MhucFamily *const mhuc_3u_families[] = { 0 };"]
    lines += [f"#define MHUC_3U_FAMILY_COUNT {len(symbols)}", "", f"#endif /* {GUARD} */", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True, help="the family directory (mods/uc_runtime/src/monsters/rathian-3u)")
    ap.add_argument("--out", required=True, help="the header to write")
    args = ap.parse_args(argv)
    families = family_files(args.dir)
    header = render(families, args.dir)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    # The build runs this before every make (a phony prerequisite), so it keeps the header's
    # mtime when the family set is unchanged: a removed file still regenerates it, and an
    # unchanged set doesn't rebuild the plugin.
    old = ""
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as f:
            old = f.read()
    if header != old:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(header)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
