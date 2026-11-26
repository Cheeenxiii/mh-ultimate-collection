#!/usr/bin/env python3
"""A runtime monster module's family list, discovered from its directory.

The Rathian modules are split one C file per action family under
`mods/uc_runtime/src/monsters/<key>/`, so the action-slice issues each add one file and nothing
shared. This tool writes the header the module includes: one `extern` per family file and the
list the module's dispatch iterates. The build runs it (the runtime's Makefile) for every
monster key, so adding a file puts the family in the list and no slice edits a list.

A family file `cat0.c` must export `const MhucFamily mhuc_<tag>_family_cat0` (the stem, with
every non-alphanumeric byte replaced by `_`); a file that doesn't fails the link, naming the
symbol. `<tag>` is the module's short C name: `3u` for `rathian-3u`, `gu` for `rathian-gu`. The
header is generated, never committed.

    gen_families.py --dir <family dir> --out <families.h> [--tag <tag>]

Licence: GPL-3.0-or-later.
"""
from __future__ import annotations

import argparse
import os
import re

DEFAULT_TAG = "3u"


def symbol(path: str, tag: str) -> str:
    """The `const MhucFamily` a family file must export, from its file name."""
    stem = os.path.splitext(os.path.basename(path))[0]
    name = re.sub(r"[^0-9A-Za-z_]", "_", stem)
    if not name or name[0].isdigit():
        name = "_" + name
    return f"mhuc_{tag}_family_{name}"


def guard(directory: str) -> str:
    """The header's guard, from the family directory's name (`rathian-3u`)."""
    name = os.path.basename(os.path.normpath(directory))
    return "MHUC_" + re.sub(r"[^0-9A-Za-z]", "_", name).upper() + "_FAMILIES_H"


def family_files(directory: str) -> list[str]:
    """The family files in the directory, in name order. A leading dot or underscore file is
    not one (an editor's or the generator's own)."""
    names = sorted(
        n for n in os.listdir(directory)
        if n.endswith(".c") and not n.startswith((".", "_"))
    )
    return [os.path.join(directory, n) for n in names]


def render(families: list[str], directory: str, tag: str) -> str:
    """The generated header for `directory`'s family files."""
    symbols = [symbol(f, tag) for f in families]
    duplicate = next((s for i, s in enumerate(symbols) if s in symbols[:i]), None)
    if duplicate:
        raise SystemExit(f"two family files export {duplicate}: rename one")
    shown = os.path.relpath(directory) if not os.path.isabs(directory) else directory
    header_guard = guard(directory)
    lines = [
        f"/* Generated from the .c files in {shown}/ by tools/gen_families.py. Do not edit: add a family",
        " * file to the directory and the build writes it here.",
        " * Licence: GPL-3.0-or-later. */",
        f"#ifndef {header_guard}",
        f"#define {header_guard}",
        "",
        '#include "family.h"',
        "",
        "/* One MhucFamily per file in the directory, in name order; the module's dispatch tries",
        " * them in turn. */",
    ]
    lines += [f"extern const MhucFamily {s};" for s in symbols]
    if symbols:
        lines += ["", f"static const MhucFamily *const mhuc_{tag}_families[] = {{"]
        lines += [f"    &{s}," for s in symbols]
        lines += ["};"]
    else:
        lines += ["", f"static const MhucFamily *const mhuc_{tag}_families[] = {{ 0 }};"]
    lines += [f"#define MHUC_{tag.upper()}_FAMILY_COUNT {len(symbols)}", "",
              f"#endif /* {header_guard} */", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True,
                    help="the family directory (mods/uc_runtime/src/monsters/rathian-3u)")
    ap.add_argument("--out", required=True, help="the header to write")
    ap.add_argument("--tag", default=DEFAULT_TAG,
                    help=f"the module's short C name: 3u for rathian-3u, gu for rathian-gu "
                         f"(default: {DEFAULT_TAG})")
    args = ap.parse_args(argv)
    if not re.fullmatch(r"[0-9A-Za-z_]+", args.tag):
        ap.error(f"--tag {args.tag!r} is not a C identifier fragment")
    families = family_files(args.dir)
    header = render(families, args.dir, args.tag)
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
