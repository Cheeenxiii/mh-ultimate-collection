#!/usr/bin/env python3
"""Log who calls chosen functions while a game runs in Azahar, through its GDB stub.

Sets an execution breakpoint on each address, and on every hit writes a row: epoch time,
seconds since start, function, label, the caller (LR), r0-r3 and sp. Each hit pauses the
game briefly, so a function's breakpoint is removed after --max hits or --per distinct
callers; play stays smooth once the busy ones are retired. Ctrl-C, or the game closing,
removes every breakpoint and detaches. Rows hold addresses and register values only.

Start Azahar first with the GDB stub on (qt-config.ini, [Debugging] use_gdbstub=true);
the script waits for it. See docs/checks.md, "Tracing engine calls in MHXX".

usage: trace_calls.py ADDR[=LABEL] ... [--port 24689] [--max 25] [--per 40] [--out calls.tsv]
"""
from __future__ import annotations

import argparse
import socket
import struct
import sys
import time


class Rsp:
    """The few GDB remote-protocol packets the tracer needs."""

    def __init__(self, port: int):
        while True:
            try:
                self.sock = socket.create_connection(("127.0.0.1", port))
                break
            except OSError:
                print("waiting for the GDB stub on port", port, file=sys.stderr)
                time.sleep(2)
        self.buf = b""

    def _read(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise EOFError("the stub closed the connection")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, data: bytes) -> None:
        packet = b"$" + data + b"#" + b"%02x" % (sum(data) & 0xFF)
        while True:
            self.sock.sendall(packet)
            ack = self._read(1)
            if ack == b"+":
                return
            if ack != b"-":
                self.buf = ack + self.buf
                return

    def recv(self) -> bytes:
        while self._read(1) != b"$":
            pass
        data = b""
        while (c := self._read(1)) != b"#":
            data += c
        self._read(2)
        self.sock.sendall(b"+")
        return data

    def cmd(self, data: bytes) -> bytes:
        self.send(data)
        return self.recv()

    def registers(self) -> tuple[int, ...]:
        return struct.unpack_from("<16I", bytes.fromhex(self.cmd(b"g").decode()), 0)


def parse_targets(specs: list[str]) -> dict[int, str]:
    targets = {}
    for spec in specs:
        addr, _, label = spec.partition("=")
        targets[int(addr, 16)] = label or addr
    return targets


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("targets", nargs="+", help="hex address, optionally =label")
    ap.add_argument("--port", type=int, default=24689)
    ap.add_argument("--max", type=int, default=25, help="retire a function after this many hits")
    ap.add_argument("--per", type=int, default=40, help="retire after this many distinct callers")
    ap.add_argument("--out", default="calls.tsv")
    a = ap.parse_args()
    targets = parse_targets(a.targets)

    rsp = Rsp(a.port)
    print("stop reason:", rsp.cmd(b"?").decode(), file=sys.stderr)
    hits = dict.fromkeys(targets, 0)
    callers: dict[int, set[int]] = {t: set() for t in targets}
    active = set(targets)
    for t in sorted(active):
        rsp.cmd(b"Z0,%x,4" % t)
    t0 = time.time()
    with open(a.out, "a") as out:
        out.write("# epoch\ttime\tfunction\tlabel\tlr\tr0\tr1\tr2\tr3\tsp\n")
        try:
            while active:
                rsp.send(b"c")
                reply = rsp.recv()
                if reply.startswith((b"W", b"X")):
                    print("the emulated program exited", file=sys.stderr)
                    break
                if not reply.startswith((b"T", b"S")):
                    continue
                r = rsp.registers()
                pc, lr = r[15], r[14]
                if pc not in targets:
                    continue
                hits[pc] += 1
                callers[pc].add(lr)
                now = time.time()
                regs = "\t".join(f"{v:#x}" for v in (r[0], r[1], r[2], r[3], r[13]))
                out.write(f"{now:.3f}\t{now - t0:.2f}\t{pc:#010x}\t{targets[pc]}\t{lr:#010x}\t{regs}\n")
                out.flush()
                rsp.cmd(b"z0,%x,4" % pc)          # step past the breakpoint
                rsp.send(b"s")
                rsp.recv()
                if hits[pc] < a.max and len(callers[pc]) < a.per:
                    rsp.cmd(b"Z0,%x,4" % pc)
                else:
                    active.discard(pc)
                    print("retired", hex(pc), targets[pc], "after", hits[pc], "hits", file=sys.stderr)
        except KeyboardInterrupt:
            pass
        except (EOFError, OSError) as e:
            print("connection ended:", e, file=sys.stderr)
            active.clear()
        finally:
            for t in active:
                try:
                    rsp.cmd(b"z0,%x,4" % t)
                except (EOFError, OSError):
                    break
            try:
                rsp.send(b"D")
            except (EOFError, OSError):
                pass
    print("hits:", {targets[t]: hits[t] for t in targets}, file=sys.stderr)


if __name__ == "__main__":
    main()
