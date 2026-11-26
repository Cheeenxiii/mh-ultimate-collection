---
class: rEnemyCmd
extension: emc
games: MH4U and MHXX (version 0x20120804); MH3U (version 0x20110601)
status: unverified
---

# EMC: enemy AI scripts

A monster's AI: top-level selectors and action scripts in a bytecode. A converted monster
brings its own. MH3U's EMC is older than MH4U's: the file shape, the class and the action
scheme are shared, but the version word, the number of group rows and the instruction table
differ (checks A1 to A4), so an MH3U file does not load in MH4U as it is. What a converter
must do is at [the end](#what-a-converter-must-do).

**Source.** MHGU Definitive Edition, `tools/emc.py` (GPL-3.0-or-later) for the first layout
and the bytecode heuristic; our reading of the loaders and length helpers for the version and
group rules. Addresses are USA v1.3.0 for MH4U.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `EMC\0` | verified | MHGU-DE `emc.py`; checks A1, A2 |
| 0x04 | u32 | version | verified | check A1; the loader refuses any other value (A4) |
| 0x08 | u32 | group-row count | verified | check A1; the loader does not read it (A4) |
| 0x0C | u32 | zero | verified | check A2 |
| 0x10 | {u32 count, u32 table offset, u32 0, u32 0} × group count | group table | verified | check A2; the loader reads count and table offset (A4) |

The version is `0x20110601` in MH3U and `0x20120804` in MH4U and MHXX. The group-row count is
13 in MH3U, 23 in MH4U and 21 in MHXX, and every file of a game agrees (A1). The loaders ignore
the count and read a fixed number of rows — 13, 23 and 21 — from the group table (A4), so the
rows, not the count, are what a file must have.

## Group script table

At the row's table offset, `count` rows:

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | script length, padding excluded | verified | check A2 |
| 0x04 | u32 | script offset, from the file's start | verified | check A2; the loader stores this (A4) |
| 0x08 | u32 | zero | verified | check A2 |
| 0x0C | u32 | zero | verified | check A2 |

Each script is `length` bytes followed by zeroes to the next 16-byte boundary, and its last
byte is `0xff`. The length is what the script table says; the `0xff` is the bytecode's end
marker, and a script cut past the table must end there to cut cleanly (A2).

## The instruction stream

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0 | u8 | opcode | verified | check A2; the game's length table (below) |
| +1 | u8 | block sub-code, or the first argument | verified | check A2; block rules below |
| +2.. | u8[] | further arguments, or a case value | verified | check A2; the length table |
| — | — | what each opcode and argument does | unverified | MHGU-DE's heuristic |

A script is a sequence of instructions. The game reads an instruction's length from a byte
table indexed by the opcode:

- a table value below `0x80` is the number of argument bytes after the opcode;
- a value of `0x80` or more opens a block, and the next byte is its sub-code: `0x00` opens the
  block and the table value's low nibble is the block's argument count; `0x01` is a case whose
  value is one to four bytes, chosen by the table value's high nibble (`0x8`, `0x9`, `0xA`,
  `0xB`); `0x02` is the else; `0xff` ends the block.

`00 cat num` starts a native action of the monster class, `14 nn` runs action script `nn` of
group 1, `02 ..` is a weighted choice, and the other opcodes open condition blocks. Those
meanings are MHGU-DE's and are not checked here; what is checked is the instruction lengths.
MH3U's table has no value above `0x83`, so a case there carries a one-byte value; MH4U's
`0x90`, `0xA0` and `0xB0` values carry two, three and four.

### The tables

| Game | Opcodes | Length table | Length helper | Status | Source |
|---|---|---|---|---|---|
| MH3U | 113 | `0x00b11325` in `code.bin` | `0x0084d31c` | verified | A3; our reading of the helper |
| MH4U | 146 | `0x00ffe9f4` in `code.bin` | `0x00935524` | verified | A3; our reading of the helper |
| MHXX | 167 | MHGU's, `0x01732c8c` in MHGU's main | — | verified | A3; every MHXX script cuts with it |
| MHGU | 167 | `0x01732c8c` in its main | — | unverified | MHGU-DE |

MH4U's 146-opcode table is MHGU's first 146; MHXX's scripts cut with MHGU's 167 but not with
MH4U's 146 (A3). The three games' tables differ in more than length: 15 opcodes that 3U and
MH4U both have take a different number of arguments (A3):

| Opcode | MH3U | MH4U |
|---|---|---|
| `0x01` | 3 arguments | 4 |
| `0x0b` | block, 0 arguments | block, 1 |
| `0x11` | block, 0 | block, 1 |
| `0x16` | block, 0 | block, 1 |
| `0x1b` | 5 arguments | 6 |
| `0x1d` | block, 1 | block, 2 |
| `0x2e` | block, 0 | block, 1 |
| `0x33` | block, 0 | block, 1 |
| `0x4b` | block, 2 | block, 3 |
| `0x57` | block, 0 | block, 1 |
| `0x58` | block, 0 | block, 1 |
| `0x67` | block, 1 | block, 0 |
| `0x6c` | block, 2 | block, 3 |
| `0x6d` | block, 0 | block, 1 |
| `0x70` | block, 0 | block, 1 |

All 15 are used by MH3U's files (A3). What the byte an opcode gains in MH4U means, and what the
one `0x67` loses, is at [the added argument](#the-added-argument): MH4U's evaluator reads it
and MH3U's has no byte to read, so a converter writes the entry MH3U's own code uses, never a
pad (check A5).

## The added argument

MH4U's evaluator reads the byte each of the 14 opcodes gains and MH3U's has none. The byte's
place and what it does are read in MH4U's recompiled code (handler addresses below are USA
v1.3.0's; check A5). A **linear** opcode (`0x01`, `0x1b`) gains it before its first argument; a
**block** opcode gains it right after the sub-code, and only on the open form (`sub-code 0x00`),
because a case's value width and the else and end forms are the same in both games.

| Opcode | MH4U handler | What MH4U's evaluator does with the added byte | MH3U's evaluator instead | Filler |
|---|---|---|---|---|
| `0x01` | `0x0094fbdc` → `0x0092ce60` | indexes the per-monster state bytes at work `+0x278 + n` | reads work `+0x2b4`, the only entry | 0, verified |
| `0x0b` | `0x0094ff24` → `0x0092b4d4` | selects a target point, `work +0x218 + 16n` | checks the one fixed target at work `+0x38`/`+0x288` | 0, verified |
| `0x11` | `0x00950188` | indexes the state byte at work `+0x27c + n` | reads work `+0x2b6` | 0, verified |
| `0x16` | `0x009505b0` → `0x0092b4d4` | the block's comparison value, a target point's distance | compares with the fixed first target | 0, verified |
| `0x1b` | `0x00950808` | indexes the state byte at work `+0x27e + n`, then the `0x01` condition's arguments | reads work `+0x2b7` | 0, verified |
| `0x1d` | `0x00950920` | selects a target point for the heading test | turns to the fixed target (`0x00584cd8`, work `+0x38`/`+0x288`) | 0, verified |
| `0x2e` | `0x00951274` | selects a target point for the angle test | the fixed target | 0, verified |
| `0x33` | `0x0095162c` | selects a target point, three of its fields | the fixed target's three fields | 0, verified |
| `0x4b` | `0x009520d0` → `0x009412f4` | the branch index moves to the second argument; the added one indexes the state byte in each branch | branch index is the first argument, no state index | 0, verified |
| `0x57` | `0x0095265c` | nothing: the byte is in the instruction but the handler never reads it (reserved) | — | 0 |
| `0x58` | `0x0095267c` | the block's comparison value | passes 0 as that value | 0, verified |
| `0x6c` | `0x00952d40` | selects a target point; the two angle bounds follow it | the fixed target, bounds as two arguments | 0, verified |
| `0x6d` | `0x00952e90` | indexes the state byte at work `+0x278 + n` | reads work `+0x2b4` | 0, verified |
| `0x70` | `0x00952f58` | selects a target point, `work +0x21c + 16n` | compares a threshold from a global object (`[0x00c1bff8] +0x4044`), not an entry | **unverified** |

`0x67` loses its open form's argument: MH4U's handler (`0x00952ac8`) calls its two helpers with
the constant 0 where MH3U reads the byte, so only the byte 0 has a translation (check A5). The
game's own files use 0 in 83 of 85 open `0x67` blocks; `em018` (Gobul) and `em019` (Agnaktor)
use `0x17` and `0x1d`, and those two files are refused.

A value MH3U's evaluator *computes* rather than takes from an entry cannot be turned into a
fixed byte, so `0x70` is unverified and the converter refuses a file that uses it: 14 of the 91
MH3U files do.

## Groups

| Group | MH3U | MH4U | MHXX |
|---|---|---|---|
| rows in the file | 13 | 23 | 21 |
| pointers in the class | 13, at `rEnemyCmd+0x64` | 23, at `+0x68` | 21, at `+0x64` |
| class size | `0x98` | `0xc8` | `0xb8` |

The group-pointer array ends the class in each game, so the group count is a property of the
class, not only of the file: `0x64 + 13 × 4 = 0x98` in MH3U, `0x68 + 23 × 4 = 0xc4` in MH4U's
`0xc8`, and `0x64 + 21 × 4 = 0xb8` in MHXX. Group 0 holds the top-level selectors and group 1
the action scripts (MHGU-DE, unverified); the roles of groups 2 to 12 are unverified. MH4U's
own EMCs fill some of groups 13 to 22 (A1), which MH3U does not have; a converted 3U file
leaves them empty.

## The loaders

| Game | Class id | Vtable | Loader (slot 11) | Group loop |
|---|---|---|---|---|
| MH4U | `0x3aabba02` | `0x010a00b0` | `0x00be5248` | 23 |
| MH3U | `0x3aabba02` | `0x00cb9b50` | `0x0097efc0` | 13 |
| MHXX | `0x3aabba02` | `0x00d75080` | `0x009f72a0` | 21 |

Each loader reads the file through the resource system, compares bytes 0 and 4 with its own
magic and version, then allocates a pointer array per group and stores `file + script offset`
for each script row. It does not read the header's group count and does not use the script
length. A file whose version is not the loader's fails at the version check (A4).

## Checks

- **A1 (done):** a scan of every `rEnemyCmd` entry of each RomFS (the entries `mhuc survey`
  reads): MH4U 124 files, version `0x20120804`, 23 groups, 13,501 scripts; MHXX 139 files, the
  same version, 21 groups, 19,424 scripts; MH3U 91 files, version `0x20110601`, 13 groups,
  6,864 scripts. No file breaks the header shape.
- **A2 (done):** every script of every file has its table inside the file, its length and offset
  in range, zero reserved words, zero padding to 16 and a final `0xff`, and cuts cleanly with
  its game's length table. The per-file command:

  ```bash
  game_files/work/venv/bin/python reference/monster_emc.py <emc> \
      --lens <the game's ELF or flat code image> <table address> <op count> --check
  ```

  The tables are the ones in [The tables](#the-tables); for an ELF the argument is the virtual
  address, and for a flat image it is a file offset (a 3DS `code.bin` starts at address
  `0x00100000`, so subtract it; MHGU's main starts at 0, so the address `0x01732c8c` is also the
  offset). The whole-RomFS runs that produced the counts read the entries the same way: MH3U
  6,864 of 6,864 clean, MH4U 13,501 of 13,501, MHXX 19,424 of 19,424 with MHGU's 167.
- **A3 (done):** the three tables differ as the table above says: MH3U's 113-opcode table
  differs from MH4U's in the 15 opcodes listed, all of them used by MH3U's files; MH4U's 146
  equals MHGU's first 146 byte for byte; 1,968 of MHXX's 19,424 scripts name an opcode at or
  past MH4U's 146. What MH4U's interpreter does with such an opcode is unverified.
- **A4 (done):** the loaders at the addresses above compare the magic and version and loop a
  fixed 13, 23 or 21 group rows. A file of another version stops at the version check; a file
  with fewer rows than the loader reads makes the loader read the first script rows as group
  rows. The address of each check and loop is in the loaders' code (our reading).
- **A5 (done):** the added argument of each of the 14 opcodes that gain one in MH4U is read
  in MH4U's own evaluator, at the handler addresses in [The added argument](#the-added-argument)
  (MH4U USA v1.3.0's recompiled code); MH3U's evaluator, at the corresponding handlers, takes
  the entry or constant each table row names. `0x67`'s removed argument is 0 where MH4U's
  evaluator uses 0. The converter (`src/mhuc/formats/emc.py`) writes 0 for the 13 verified
  additions, refuses `0x70` (whose value MH3U computes), and refuses a `0x67` argument that is
  not 0. On the game's 91 MH3U files: 75 convert, 14 are refused for `0x70` and 2 for a non-zero
  `0x67`; every converted script cuts cleanly with MH4U's table, has 23 group rows with 0 to 12
  in the source's order, and names the same `00 cat num` actions and `14 nn` calls as the source
  did, each cut with its own game's table (`tests/test_with_game_files.py`,
  `test_every_mh3u_emc_converts_to_mh4us_and_keeps_every_action_and_script_call`). The tables
  are read from the games' decompressed code images (`MHUC_MH3U_CODE`, `MHUC_MH4U_CODE`); the
  repository holds no table bytes.

## What a converter must do

For an MH3U monster onto MH4U, the converter, in `mhuc` at build time:

1. Read the file with MH3U's layout: magic, version `0x20110601`, 13 group rows, each script by
   its length. Refuse anything else.
2. Cut each script with MH3U's 113-opcode table and write it again with MH4U's 146-opcode
   table. The 14 opcodes that gain an argument get 0 where [the added argument](#the-added-argument)
   puts it (a block: after its sub-code, on the open form only), `0x67` loses its argument (only
   0 converts), and `0x70` is refused; every other instruction is copied. End each script with
   `0xff`.
3. Write the header: magic unchanged, version `0x20120804`, group-row count 23, zero, and 23
   group rows. Rows 0 to 12 are the source's, in order; rows 13 to 22 have count 0 and offset
   0, which the loader skips. Recompute every script table and script offset, pad each script
   to 16 with zeroes.
4. Change no action pair (`00 cat num`) and no script call (`14 nn`), and keep group 1's script
   order: `14 nn` indexes it. Groups 0 to 12 keep their order, so a state the source game
   selects by group number selects the same group here.
5. Change no motion number: the EMC has none. An action's motion is the handler's (check R1);
   the port's own handler passes MH4U's form of her animation
   ([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)), and nothing
   translates a number at run time.
6. Install the result at the monster's `cmd` path (`enemy\emNNN\data\emNNN_cmd`) and add `cmd`
   to the id's `files` in [data/ids/registry.csv](../data/ids/registry.csv), so the resource
   record names it.
7. Check the result: 23 groups, every script cuts cleanly with MH4U's table (A2), then in game
   with [R3](../docs/checks.md#the-ported-ais-check-r3).

**The choice.** The mod converts the script rather than rewriting its logic in C (decision
0012 allows either). Conversion keeps every selector and branch the source has, needs no
per-monster C, and one converter serves every 3U monster; a rewrite would reimplement the same
conditions per monster and would still need each opcode's meaning. The price is the 15
translated opcodes: their added or removed argument is read in MH4U's evaluator (A5), and the
one value MH3U computes rather than stores (`0x70`) makes its file unconvertible.

**Action ids.** The scheme is shared: a pair is a category byte and an index byte, and every
pair runs the source's own handler (decision 0002's 2026-11-26 amendment). Cut with its table,
3U Rathian's EMC names 143 actions. Of the 17 ids MH4U's `uEm001` lacks, it names `7/64` and
category 4 ([reference](../reference/README.md#the-17-ids-mh4u-has-no-action-for)): `7/64`'s
own handler is translated in a category-7 slice
([#221](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/221) to
[#224](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/224)), and action 4's is
[#136](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/136). Until it lands, MH4U's
own category-4 handler runs for the index the 3U script asks, which is a 3U argument MH4U reads
as a case.

**MHXX is not a shortcut.** MHXX's EMC has MH4U's version word, so the GU port planned to ship
it as data, but it has 21 group rows and MHGU's 167-opcode table: a file for MH4U needs its
rows padded to 23, and 1,968 of MHXX's 19,424 scripts use opcodes MH4U's table does not have.
That is a follow-up for the MHXX ports, recorded in
[#48](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/48).

## Credits

MHGU Definitive Edition's `tools/emc.py` (GPL-3.0-or-later) for the header, the group/script
tables and the opcode heuristic; `reference/monster_emc.py` carries its reading. The loader
and length-table addresses are our reading of MH4U USA v1.3.0 and MH3U USA's code.
