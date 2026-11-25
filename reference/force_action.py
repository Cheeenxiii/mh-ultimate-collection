#!/usr/bin/env python3
"""Force one monster action in MHXX or MH3U through Azahar's GDB stub, for debugging a move.

A monster's current action is a category byte and an index byte. Where they sit:
  MHXX  category `this+0x6bf0`, index `this+0x6bf1`; dispatcher `roEm001` + 0x9704.
  MH3U  work = *(this+0x1a48); category `work+0xdf`, index `work+0xe0`; dispatcher 0x00687d30.

Start the game in Azahar with the GDB stub on, stand in the area with the target monster as
the only large one, then run this. It breaks at the dispatcher, writes the pair into the
enemy the dispatcher was called for, reads it back, and continues: that enemy's next action
is the forced one. Addresses only: nothing is read from or written to a file.

usage: force_action.py mh3u --action 3/17 [--port 24689]
       force_action.py mhxx --base 0x02000000 --action 3/17 [--port 24689]
"""
from __future__ import annotations

import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trace_calls import Rsp  # noqa: E402

# The dispatcher, and where it reads the pair from. Offsets in docs/checks.md, R1p.
MH3U_DISPATCHER = 0x00687D30
MHXX_DISPATCHER = 0x9704          # from the roEm001 module's base
MH3U_WORK = 0x1A48                # work = *(this + 0x1a48)
MH3U_CATEGORY = 0xDF
MHXX_CATEGORY = 0x6BF0


def parse_action(text: str) -> tuple[int, int]:
    """`3/17` or `0x03/0x11` as two bytes."""
    cat_text, sep, index_text = text.partition("/")
    if not sep or not cat_text or not index_text:
        raise ValueError(f"action {text!r} is not a category/index pair, as 3/17")
    cat, index = int(cat_text, 0), int(index_text, 0)
    if not (0 <= cat <= 255 and 0 <= index <= 255):
        raise ValueError(f"action {text!r} has a byte outside 0..255")
    return cat, index


def dispatcher_address(game: str, base: int = 0) -> int:
    if game == "mh3u":
        return MH3U_DISPATCHER
    if not base:
        raise ValueError("mhxx needs --base: the roEm001 module's load address")
    return base + MHXX_DISPATCHER


def pair_address(game: str, this: int, read32) -> int:
    """Where the category and index bytes are for the enemy at `this`."""
    if game == "mh3u":
        work = read32(this + MH3U_WORK)
        if not work:
            raise ValueError(f"monster at {this:#x} has no work block ({MH3U_WORK:#x})")
        return work + MH3U_CATEGORY
    return this + MHXX_CATEGORY


def write_pair_packet(addr: int, category: int, index: int) -> bytes:
    return b"M%x,2:%02x%02x" % (addr, category, index)


def read32_packet(addr: int) -> bytes:
    return b"m%x,4" % addr


def read32(rsp: Rsp, addr: int) -> int:
    reply = rsp.cmd(read32_packet(addr))
    if not reply or reply.startswith(b"E"):
        raise OSError(f"can't read {addr:#x}: {reply!r}")
    return struct.unpack("<I", bytes.fromhex(reply.decode()))[0]


def force(game: str, base: int, category: int, index: int, port: int) -> str:
    dispatcher = dispatcher_address(game, base)
    rsp = Rsp(port)
    try:
        rsp.cmd(b"?")
        rsp.cmd(b"Z0,%x,4" % dispatcher)
        rsp.send(b"c")
        while True:
            reply = rsp.recv()
            if reply.startswith((b"W", b"X")):
                raise SystemExit("the emulated program exited before the dispatcher ran")
            if reply.startswith((b"T", b"S")):
                break
        registers = rsp.registers()
        this = registers[0]
        addr = pair_address(game, this, lambda a: read32(rsp, a))
        was = rsp.cmd(b"m%x,2" % addr)
        rsp.cmd(write_pair_packet(addr, category, index))
        back = rsp.cmd(b"m%x,2" % addr)
        if back.lower() != f"{category:02x}{index:02x}".encode():
            raise OSError(f"wrote {addr:#x} but read back {back!r}")
        rsp.cmd(b"z0,%x,4" % dispatcher)
        return f"{game}: forced {category}/{index} on this={this:#x}, pair {addr:#x} (was {was.decode()})"
    finally:
        try:
            rsp.send(b"D")
        except (EOFError, OSError):
            pass


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("game", choices=("mh3u", "mhxx"))
    ap.add_argument("--action", required=True, help="the action to force, as category/index")
    ap.add_argument("--base", type=lambda s: int(s, 0), default=0, help="MHXX: the roEm001 module's base")
    ap.add_argument("--port", type=int, default=24689, help="the GDB stub's port")
    a = ap.parse_args()
    try:
        category, index = parse_action(a.action)
        print(force(a.game, a.base, category, index, a.port))
    except (OSError, ValueError) as e:
        print(f"force_action.py: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
