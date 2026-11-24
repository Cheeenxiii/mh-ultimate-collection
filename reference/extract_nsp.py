#!/usr/bin/env python3
"""Extract the program code (ExeFS → NSO → text/rodata/data) from your own Switch NSP.

The Switch counterpart of `extract_ncch.py`. An NSP is a PFS0 holding NCAs; the program
NCA's first section is the ExeFS (a PFS0 with `main`, `main.npdm`, `rtld`, `sdk`, ...),
each executable an NSO with LZ4-compressed segments. Update NSPs carry the whole ExeFS
in their program NCA (only the RomFS is a BKTR patch), so an update is extracted as is.

Keys are never stored or printed: `--keys` (prod.keys) gives `header_key`, the
`key_area_key_*` and `titlekek_*`; the title key comes from the NSP's own ticket or from
`--title-keys` (title.keys). Everything written to <outdir> is game data: keep it out of
any repository.

usage: extract_nsp.py <nsp> --keys prod.keys [--title-keys title.keys] -o <outdir>
                      [--nso main] [--all-nso] [--list]

Writes to <outdir>:
    <nso>.text.bin / .rodata.bin / .data.bin   decompressed segments
    <nso>.image.bin                            segments at their memory offsets (bss not included)
    main.npdm                                  as stored
    info.txt                                   counts, sizes, versions, ids and hashes only

Format references: switchbrew.org/wiki/NCA, /NSO, /NPDM, /Ticket; hactool's documentation.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import struct
import sys
from dataclasses import dataclass, field
from typing import BinaryIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aes128

MEDIA = 0x200
CONTENT_TYPES = {0: "program", 1: "meta", 2: "control", 3: "manual", 4: "data", 5: "publicdata"}
KAEK_NAMES = {0: "application", 1: "ocean", 2: "system"}


class NspError(ValueError):
    pass


def _read_at(f: BinaryIO, off: int, size: int) -> bytes:
    f.seek(off)
    d = f.read(size)
    if len(d) != size:
        raise NspError(f"truncated: wanted 0x{size:X} bytes at 0x{off:X}")
    return d


# ── Keys ────────────────────────────────────────────────────────────────────

def parse_keyfile(text: str) -> dict[str, bytes]:
    """`name = hex` lines (prod.keys / title.keys); comments and blanks ignored."""
    keys = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].split(";", 1)[0].strip()
        if not line or "=" not in line:
            continue
        name, val = (s.strip() for s in line.split("=", 1))
        try:
            keys[name.lower()] = bytes.fromhex(val)
        except ValueError:
            continue
    return keys


@dataclass
class Keys:
    prod: dict[str, bytes]
    titles: dict[str, bytes] = field(default_factory=dict)   # rights id hex → encrypted title key

    def get(self, name: str) -> bytes:
        k = self.prod.get(name)
        if k is None:
            raise NspError(f"key '{name}' missing from the key file")
        return k


# ── PFS0 ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PfsEntry:
    name: str
    offset: int     # absolute, within the containing stream
    size: int


def parse_pfs0(head: bytes, base: int = 0) -> list[PfsEntry]:
    """Parse a PFS0 header; `head` must hold the whole header and string table."""
    if head[:4] != b"PFS0":
        raise NspError("not a PFS0")
    n, strsz = struct.unpack_from("<II", head, 4)
    ent_end = 0x10 + n * 0x18
    data_start = ent_end + strsz
    if len(head) < data_start:
        raise NspError("PFS0 header truncated")
    strtab = head[ent_end:data_start]
    out = []
    for i in range(n):
        off, size, noff = struct.unpack_from("<QQI", head, 0x10 + i * 0x18)
        name = strtab[noff:strtab.index(b"\0", noff)].decode("utf-8")
        out.append(PfsEntry(name, base + data_start + off, size))
    return out


def pfs0_header_size(first: bytes) -> int:
    n, strsz = struct.unpack_from("<II", first, 4)
    return 0x10 + n * 0x18 + strsz


def read_pfs0(f: BinaryIO, base: int = 0) -> list[PfsEntry]:
    first = _read_at(f, base, 0x10)
    if first[:4] != b"PFS0":
        raise NspError("not a PFS0 (NSP)")
    return parse_pfs0(_read_at(f, base, pfs0_header_size(first)), base)


# ── NCA ─────────────────────────────────────────────────────────────────────

@dataclass
class NcaSection:
    index: int
    start: int          # bytes, relative to the NCA
    end: int
    fs_type: int        # 0 RomFS, 1 PFS0
    hash_type: int      # 2 hierarchical SHA-256, 3 IVFC
    crypt_type: int     # 1 none, 2 XTS, 3 CTR, 4 BKTR
    ctr_upper: bytes    # 8 bytes, as stored
    hash_data: bytes


@dataclass
class Nca:
    offset: int         # in the NSP
    magic: str
    content_type: str
    key_generation: int
    kaek_index: int
    content_size: int
    program_id: int
    rights_id: bytes
    sdk_version: int
    sections: list[NcaSection]
    key_area: list[bytes]
    ctr_key: bytes | None = None

    @property
    def has_rights(self) -> bool:
        return any(self.rights_id)


def decrypt_nca_header(enc: bytes, header_key: bytes) -> bytes:
    if len(enc) < 0xC00:
        raise NspError("NCA header truncated")
    first = aes128.xts_decrypt(header_key, enc[:0x400], 0)
    magic = first[0x200:0x204]
    if magic == b"NCA3":
        return first + aes128.xts_decrypt(header_key, enc[0x400:0xC00], 2)
    if magic == b"NCA2":   # each FS header is its own sector 0
        return first + b"".join(aes128.xts_decrypt(header_key, enc[0x400 + i * 0x200:0x600 + i * 0x200], 0)
                                for i in range(4))
    raise NspError("NCA header did not decrypt (wrong header_key, or not an NCA)")


def parse_nca_header(hdr: bytes, offset: int = 0) -> Nca:
    magic = hdr[0x200:0x204].decode("ascii")
    ctype = hdr[0x205]
    kg = max(hdr[0x206], hdr[0x220])
    content_size, program_id = struct.unpack_from("<QQ", hdr, 0x208)
    sdk = struct.unpack_from("<I", hdr, 0x21C)[0]
    sections = []
    for i in range(4):
        start, end = struct.unpack_from("<II", hdr, 0x240 + i * 0x10)
        if start == end == 0:
            continue
        fsh = hdr[0x400 + i * 0x200:0x600 + i * 0x200]
        if hashlib.sha256(fsh).digest() != hdr[0x280 + i * 0x20:0x2A0 + i * 0x20]:
            raise NspError(f"NCA section {i}: FS header hash mismatch")
        sections.append(NcaSection(i, start * MEDIA, end * MEDIA, fsh[2], fsh[3], fsh[4],
                                   fsh[0x140:0x148], fsh[8:0x100]))
    key_area = [hdr[0x300 + i * 0x10:0x310 + i * 0x10] for i in range(4)]
    return Nca(offset, magic, CONTENT_TYPES.get(ctype, str(ctype)), kg, hdr[0x207],
               content_size, program_id, hdr[0x230:0x240], sdk, sections, key_area)


def master_index(key_generation: int) -> int:
    return key_generation - 1 if key_generation > 0 else 0


def resolve_ctr_key(nca: Nca, keys: Keys, ticket_keys: dict[str, bytes]) -> bytes:
    idx = master_index(nca.key_generation)
    if nca.has_rights:
        rid = nca.rights_id.hex()
        enc = ticket_keys.get(rid) or keys.titles.get(rid)
        if enc is None:
            raise NspError(f"no title key for rights id {rid[:16]}… (ticket or title.keys)")
        return aes128.ecb_decrypt(keys.get(f"titlekek_{idx:02x}"), enc)
    kaek = keys.get(f"key_area_key_{KAEK_NAMES.get(nca.kaek_index, 'application')}_{idx:02x}")
    return aes128.ecb_decrypt(kaek, nca.key_area[2])


def section_ctr_iv(sec: NcaSection, offset_in_nca: int) -> bytes:
    """Counter block for byte `offset_in_nca` (16-aligned): reversed upper half, block index."""
    return sec.ctr_upper[::-1] + (offset_in_nca >> 4).to_bytes(8, "big")


class SectionReader:
    """Random access to one decrypted NCA section (offsets relative to the section)."""

    def __init__(self, f: BinaryIO, nca: Nca, sec: NcaSection):
        if sec.crypt_type not in (1, 3):
            kind = {2: "XTS", 4: "BKTR"}.get(sec.crypt_type, str(sec.crypt_type))
            raise NspError(f"section {sec.index}: {kind} sections are not supported")
        self.f, self.nca, self.sec = f, nca, sec

    @property
    def size(self) -> int:
        return self.sec.end - self.sec.start

    def read(self, off: int, size: int) -> bytes:
        if off < 0 or off + size > self.size:
            raise NspError("read past the end of the section")
        a = off & ~0xF
        b = (off + size + 0xF) & ~0xF
        raw = _read_at(self.f, self.nca.offset + self.sec.start + a, b - a)
        if self.sec.crypt_type == 3:
            raw = aes128.ctr_crypt(self.nca.ctr_key, section_ctr_iv(self.sec, self.sec.start + a), raw)
        return raw[off - a:off - a + size]


def pfs0_region(sec: NcaSection) -> tuple[int, int, bytes, int, int, int]:
    """For a hierarchical-SHA-256 PFS0 section: (pfs off, size, master hash, block, hash off, hash size)."""
    hd = sec.hash_data
    master = hd[0:0x20]
    block, layers = struct.unpack_from("<II", hd, 0x20)
    if sec.hash_type != 2 or layers != 2:
        raise NspError(f"section {sec.index}: not a hierarchical-SHA-256 PFS0")
    hoff, hsize, poff, psize = struct.unpack_from("<QQQQ", hd, 0x28)
    return poff, psize, master, block, hoff, hsize


def verify_pfs0_hashes(rd: SectionReader, sec: NcaSection) -> int:
    """Check the hash table against the master hash, and every block against the table."""
    poff, psize, master, block, hoff, hsize = pfs0_region(sec)
    table = rd.read(hoff, hsize)
    if hashlib.sha256(table).digest() != master:
        raise NspError(f"section {sec.index}: master hash mismatch (wrong key?)")
    n = (psize + block - 1) // block
    for i in range(n):
        chunk = rd.read(poff + i * block, min(block, psize - i * block))
        if hashlib.sha256(chunk).digest() != table[i * 0x20:(i + 1) * 0x20]:
            raise NspError(f"section {sec.index}: block {i} hash mismatch")
    return n


# ── Tickets ─────────────────────────────────────────────────────────────────

def ticket_title_key(tik: bytes) -> tuple[str, bytes]:
    """Common ticket → (rights id hex, encrypted title key)."""
    sig_sizes = {0x10000: 0x200, 0x10001: 0x100, 0x10002: 0x3C, 0x10003: 0x200,
                 0x10004: 0x100, 0x10005: 0x3C}
    st = struct.unpack_from("<I", tik, 0)[0]
    if st not in sig_sizes:
        raise NspError("unknown ticket signature type")
    body = 4 + sig_sizes[st]
    body = (body + 0x3F) & ~0x3F
    if tik[body + 0x141] != 0:
        raise NspError("personalized ticket: its title key is RSA-wrapped; use --title-keys")
    return tik[body + 0x160:body + 0x170].hex(), tik[body + 0x40:body + 0x50]


# ── NSO / LZ4 ───────────────────────────────────────────────────────────────

def lz4_block_decompress(src: bytes, out_size: int) -> bytes:
    out = bytearray()
    i, n = 0, len(src)
    while i < n:
        tok = src[i]
        i += 1
        lit = tok >> 4
        if lit == 15:
            while True:
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        out += src[i:i + lit]
        i += lit
        if i >= n:
            break
        off = src[i] | (src[i + 1] << 8)
        i += 2
        if off == 0:
            raise NspError("LZ4: zero offset")
        ml = tok & 15
        if ml == 15:
            while True:
                b = src[i]
                i += 1
                ml += b
                if b != 255:
                    break
        ml += 4
        start = len(out) - off
        if start < 0:
            raise NspError("LZ4: offset before start")
        if off >= ml:
            out += out[start:start + ml]
        else:
            for k in range(ml):
                out.append(out[start + k])
    if len(out) != out_size:
        raise NspError(f"LZ4: got 0x{len(out):X} bytes, expected 0x{out_size:X}")
    return bytes(out)


@dataclass
class Nso:
    build_id: bytes
    segments: dict[str, tuple[int, bytes]]   # name → (memory offset, data)
    bss_size: int
    flags: int

    def image(self) -> bytes:
        end = max(off + len(d) for off, d in self.segments.values())
        img = bytearray(end)
        for off, d in self.segments.values():
            img[off:off + len(d)] = d
        return bytes(img)


def parse_nso(data: bytes) -> Nso:
    if data[:4] != b"NSO0":
        raise NspError("not an NSO")
    flags = struct.unpack_from("<I", data, 0xC)[0]
    hdrs = [struct.unpack_from("<III", data, o) for o in (0x10, 0x20, 0x30)]
    bss = struct.unpack_from("<I", data, 0x3C)[0]
    csizes = struct.unpack_from("<III", data, 0x60)
    segs = {}
    for k, name in enumerate(("text", "rodata", "data")):
        foff, moff, size = hdrs[k]
        raw = data[foff:foff + csizes[k]]
        seg = lz4_block_decompress(raw, size) if flags & (1 << k) else raw[:size]
        if flags & (8 << k):
            want = data[0xA0 + k * 0x20:0xC0 + k * 0x20]
            if hashlib.sha256(seg).digest() != want:
                raise NspError(f"NSO {name}: hash mismatch")
        segs[name] = (moff, seg)
    return Nso(data[0x40:0x60], segs, bss, flags)


def npdm_info(data: bytes) -> dict[str, object]:
    if data[:4] != b"META":
        raise NspError("not an NPDM")
    flags = data[0xC]
    return {"is_64bit": bool(flags & 1), "address_space": (flags >> 1) & 7,
            "title": data[0x20:0x30].split(b"\0")[0].decode("ascii", "replace")}


# ── Driver ──────────────────────────────────────────────────────────────────

def open_ncas(f: BinaryIO, keys: Keys) -> tuple[list[Nca], list[PfsEntry], dict[str, bytes]]:
    entries = read_pfs0(f)
    tickets = {}
    for e in entries:
        if e.name.endswith(".tik"):
            rid, tk = ticket_title_key(_read_at(f, e.offset, e.size))
            tickets[rid] = tk
    ncas = []
    hk = keys.get("header_key")
    for e in entries:
        if e.name.endswith(".nca"):
            nca = parse_nca_header(decrypt_nca_header(_read_at(f, e.offset, 0xC00), hk), e.offset)
            ncas.append(nca)
    return ncas, entries, tickets


def program_exefs(f: BinaryIO, keys: Keys) -> tuple[Nca, SectionReader, list[PfsEntry], int]:
    ncas, _, tickets = open_ncas(f, keys)
    progs = [n for n in ncas if n.content_type == "program"]
    if not progs:
        raise NspError("no program NCA in this NSP")
    nca = progs[0]
    nca.ctr_key = resolve_ctr_key(nca, keys, tickets)
    sec = next((s for s in nca.sections if s.fs_type == 1), None)
    if sec is None:
        raise NspError("program NCA has no PFS0 (ExeFS) section")
    rd = SectionReader(f, nca, sec)
    blocks = verify_pfs0_hashes(rd, sec)
    poff = pfs0_region(sec)[0]
    first = rd.read(poff, 0x10)
    head = rd.read(poff, pfs0_header_size(first))
    return nca, rd, parse_pfs0(head, poff), blocks


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def extract(nsp: str, keys: Keys, outdir: str, nsos: list[str], all_nso: bool = False) -> list[str]:
    os.makedirs(outdir, exist_ok=True)
    info = [f"source: {os.path.basename(nsp)}", f"aes backend: {aes128.backend()}"]
    with open(nsp, "rb") as f:
        ncas, entries, tickets = open_ncas(f, keys)
        info.append(f"nsp files: {len(entries)} ({sum(e.name.endswith('.nca') for e in entries)} NCA, "
                    f"{len(tickets)} ticket)")
        for n in ncas:
            info.append(f"nca {n.content_type}: {n.magic}, program id {n.program_id:016x}, key generation "
                        f"{n.key_generation}, sdk {n.sdk_version >> 24}.{(n.sdk_version >> 16) & 255}."
                        f"{(n.sdk_version >> 8) & 255}, size 0x{n.content_size:X}, "
                        f"{'title key' if n.has_rights else 'key area'}, sections "
                        + ", ".join(f"{s.index}:{'pfs0' if s.fs_type == 1 else 'romfs'}/"
                                    f"{ {1: 'none', 2: 'xts', 3: 'ctr', 4: 'bktr'}.get(s.crypt_type, '?') }"
                                    f"/0x{s.end - s.start:X}" for s in n.sections))
        _, rd, exefs, blocks = program_exefs(f, keys)
        info.append(f"exefs: {len(exefs)} files ({', '.join(e.name for e in exefs)}), "
                    f"{blocks} hash blocks verified")
        by_name = {e.name: e for e in exefs}
        if "main.npdm" in by_name:
            e = by_name["main.npdm"]
            npdm = rd.read(e.offset, e.size)
            with open(os.path.join(outdir, "main.npdm"), "wb") as o:
                o.write(npdm)
            ni = npdm_info(npdm)
            info.append(f"npdm: title {ni['title']}, {'AArch64' if ni['is_64bit'] else 'AArch32'}, "
                        f"address space type {ni['address_space']}")
        want = [e.name for e in exefs if not e.name.endswith(".npdm")] if all_nso else nsos
        for name in want:
            if name not in by_name:
                raise NspError(f"ExeFS has no '{name}'")
            e = by_name[name]
            nso = parse_nso(rd.read(e.offset, e.size))
            for seg, (moff, d) in nso.segments.items():
                with open(os.path.join(outdir, f"{name}.{seg}.bin"), "wb") as o:
                    o.write(d)
                info.append(f"{name}.{seg}: mem 0x{moff:X}, size 0x{len(d):X}, sha256 {sha256(d)}")
            img = nso.image()
            with open(os.path.join(outdir, f"{name}.image.bin"), "wb") as o:
                o.write(img)
            info.append(f"{name}: build id {nso.build_id[:20].hex()}, bss 0x{nso.bss_size:X}, "
                        f"image 0x{len(img):X}, sha256 {sha256(img)}")
    with open(os.path.join(outdir, "info.txt"), "w") as o:
        o.write("\n".join(info) + "\n")
    return info


def load_keys(prod: str, titles: str | None) -> Keys:
    with open(prod) as fh:
        k = Keys(parse_keyfile(fh.read()))
    if titles:
        with open(titles) as fh:
            k.titles = parse_keyfile(fh.read())
    return k


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("nsp")
    ap.add_argument("--keys", required=True, help="prod.keys")
    ap.add_argument("--title-keys", help="title.keys (when the NSP has no ticket)")
    ap.add_argument("-o", "--outdir", required=False)
    ap.add_argument("--nso", action="append", help="ExeFS executables to extract (default: main)")
    ap.add_argument("--all-nso", action="store_true")
    ap.add_argument("--list", action="store_true", help="only list the NCAs and ExeFS")
    a = ap.parse_args(argv)
    try:
        keys = load_keys(a.keys, a.title_keys)
        if a.list:
            with open(a.nsp, "rb") as f:
                ncas, _, _ = open_ncas(f, keys)
                for n in ncas:
                    print(n.content_type, n.magic, f"{n.program_id:016x}", "kg", n.key_generation,
                          [(s.index, s.fs_type, s.crypt_type, hex(s.end - s.start)) for s in n.sections])
                _, _, exefs, _ = program_exefs(f, keys)
                for e in exefs:
                    print(" ", e.name, hex(e.size))
            return 0
        if not a.outdir:
            ap.error("-o is required unless --list")
        for line in extract(a.nsp, keys, a.outdir, a.nso or ["main"], a.all_nso):
            print(line)
    except (NspError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
