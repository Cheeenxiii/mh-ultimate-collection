# MHGU Switch as a code bridge (2026-11-24)

This session opened the maintainer's MHGU Switch v1.4.0 dump for code mapping, with the maintainer's explicit authorisation to use `game_files/prod.keys` and `title.keys` on the two MHGU NSPs only. It wrote a Switch extractor for the fork, settled the architecture, built an encoding-independent function matcher, mapped MHXX and MH4U to GU, chained in MHGU Definitive Edition's recorded pairs, and ran Rathian's worklist through GU. The maintainer asked to stop before the last lever (pairing Rathian's own code across games by action id) was tried. Scratch scripts and outputs are in `game_files/work/gusw/`, the extraction in `game_files/work/mhgu_switch/`, Definitive Edition's clone in `game_files/work/de/src/`. The repositories got counts, names and addresses only; no key or anything decrypted left `game_files/`.

## Done

| Task | Result | Where |
|---|---|---|
| Switch extractor | NSP (PFS0) → NCA (header AES-XTS, title key from the ticket or `title.keys`, or key area) → ExeFS (AES-CTR, hierarchical SHA-256 checked) → NSO (LZ4, segment hashes checked). Stdlib only; OpenSSL's libcrypto through `ctypes` when present. 26 tests on synthetic data, FIPS/NIST/IEEE vectors on both AES paths. On the v1.4.0 update: 663 hash blocks verified, all segment hashes match | fork PR #9: `tools/extract_nsp.py`, `tools/aes128.py`, `tests/test_extract_nsp.py` |
| Doctor and dumps | `mhgu_switch` in `dumps.json` as a code/format reference (shipped content stays English text); the doctor checks a Switch extraction and never extracts it itself (it needs the keys) | `tools/doctor.py`, `tools/workspace/dumps.json`, `tests/test_doctor.py` |
| Architecture | AArch32, ARM mode, clang, position-independent; monsters linked statically into `main` | monster-port.md, "MHGU Switch as a bridge" |
| GU classes | 3,205 classes from the emulated init functions; 3,193 with a vtable named by its `getDTI` slot (3,181 unique); 2,949 names shared with MHXX | same |
| MHXX ↔ GU map | 26,406 of 63,087 static functions (26,508 with `roEm001`, 97 of its 265 functions). Held out: 161 of 165 right, 0 wrong. Triangle with the MH4U↔MHXX map: 2,328 of 2,443 agree | same |
| MH4U ↔ GU map | 4,057 of 40,577; agrees with 12 of the 13 Definitive Edition pairs it covers | same |
| Definitive Edition | its GU and EUR v1.1 dumps are byte-identical to ours; 85 recorded pairs (59 C, 24 S, 2 W), all carried to USA v1.3.0 function starts through `eur_v110.txt`; 269 GU function names | mhgu-definitive-edition.md, monster-port.md |
| Worklist | of the 62: 2 resolved to MH4U, 28 placed in GU only, 32 not placed. Of the 33 call-site matches: 7 confirmed, 1 differs, 25 unchecked | monster-port.md; scratch `mport/actions/roEm001_imports_gu.tsv` |
| Housekeeping | STATUS no longer lists fork PR #4 and the default branch as waiting; the fork README's MHXX line names the module recompiles | STATUS.md, fork `.github/README.md` |

## What it changes for the plan

- **GU is the same game as MHXX where the code has evidence.** Same classes, near-identical vtables, no wrong match in the held-out test. Its differences are the compiler (clang vs armcc: other instructions, folded tiny functions) and the platform layers.
- **GU is a weak bridge to MH4U for this worklist.** The 62 functions are by construction the ones MHXX↔MH4U couldn't place; most of those placed in GU still have no MH4U counterpart, which points to "MH4U lacks it" (GU-era projectile and framework code) rather than to a missed match.
- **Definitive Edition's addresses are ours.** No rebuild is needed to use its notes: same bytes on both sides.

## Not done

- The matcher and the GU-side analysis are scratch scripts; they belong in the fork as tools with synthetic tests.
- Rathian's own code wasn't paired across games by action id on the GU side (GU's slot-125 dispatcher isn't parsed by `monster_actions.py`, which knows armcc's switch forms only). That is the next lever for the 32 unplaced functions.
- Definitive Edition's `tools/match4u.py` wasn't run: it needs numpy (not installed; a download needs the maintainer's yes) and its Ghidra-seeded names.
- The 62 still need their one-line entries (what it does, MH4U's way or "MH4U lacks it").
- RomFS and BKTR (the update's RomFS patch) are not in the extractor.

## Checklist for the next session

1. Scratch inputs: `game_files/work/gusw/` (`swan.py` functions, `dti.py` and `vt2.py` classes, `mxan.py` 3DS features, `xmap.py` the matcher: `xmap.py mhxx [--modules roEm001]`, `xmap.py mh4u [--de-seed]`; `heldout.py`, `evalall.py`, `depairs.py`, `resolve.py`). Each map takes 2 to 5 minutes under the 6 GB cap.
2. The worklist with GU addresses and DE names: `game_files/work/mport/actions/roEm001_imports_gu.tsv`.
3. Re-extract with `tools/extract_nsp.py <update nsp> --keys game_files/prod.keys --title-keys game_files/title.keys -o game_files/work/mhgu_switch --all-nso`, only with the maintainer's authorisation for the keys.
