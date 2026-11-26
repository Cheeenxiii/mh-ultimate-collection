---
class: rMhMotionEffect, rEffectSequence, rProofEffectMotSequenceList
extension: mef, esq, psl
games: MH4U, MH3U, MHXX
status: unverified
---

# Motion effects: MH4U's MEF, MH3U's ESQ and MHXX's PSL

A monster's visual effects are played at frames of its animations. Each game keeps that timing in a
resource of its own: MH4U in `rMhMotionEffect` (magic `MEF\0`, extension `mef`), MH3U in
`rEffectSequence` (`ESQ\0`, `esq`) and MHXX in `rProofEffectMotSequenceList` (`PSL\0`, `psl`).
MH4U's resource record names two MEF files per monster; MH3U ships one ESQ per monster (44 of its
85 monster archives have one); MHXX ships one PSL per motion list. MH4U's is what a port must
produce, the other two are what it must read.

**Source.** No public tool lays these out. The class names, ids and sizes come from the engines'
own class registries: MH4U's `config/mt_classes.tsv` (`rMhMotionEffect` `0x148b6f89`, size `0x88`;
its data class `cMhMotionEffectData` `0x61aeb049`, size `0x58`), MH3U's and MHXX's
`reference/games/*/mt_classes.tsv` (`rEffectSequence` `0x525bbf16`, `0x68`;
`rProofEffectMotSequenceList` `0x254309c9`, `0x68`). The paths are the games' own resource paths:
the MH4U records' data, MH3U's `code.bin` format strings and the MHXX archives. The containers
below are our own reading, checked on real files (FX1 to FX11), with MH4U's loaders
read for what the file has to satisfy: `rMhMotionEffect`'s load at `0x398f94` (vtable slot 11) and
`cMhMotionEffect`'s serializer at `0x390ccc`, and MH3U's ESQ loader at `0x3b30cc`. The MEF record
fields are placed from MH4U's own spawn and getter; the effect the record plays is not a field but
a (base, sub) pair the spawn derives from the record's type, time and bone through the tables
[MH4U's spawn tables](#mh4us-spawn-tables) lays out (FX10). The ESQ event's effect parameters and
the PSL body are still not placed: a converter must not map them until a check pins their
meaning.

## How a record names them

| Game | Resource | Path | What names it |
|---|---|---|---|
| MH4U | `rMhMotionEffect` | `effect\mef\em\emNNN_0` and `_1` | the monster resource record's `+0x14`: two path pointers ([reference/README.md](../reference/README.md#mh4u-monster-tables)). MH4U's data holds both strings for each of its ids |
| MH3U | `rEffectSequence` | `effect\esq\em\emNNN` | one per monster; the loader's format string `effect\esq\em\em%03d` is in MH3U's `code.bin`. Which record field selects it is unverified |
| MHXX | `rProofEffectMotSequenceList` | `effect\psl\enemy\emNNN\emNNN_RR\mot\emNNN_RR_K` | one per motion list `K` of rank `RR`; the paths are in the monster's rank archive. No path string was found in MHXX's `code.bin` or its CRO modules, so which record field selects it is unverified |

## MH4U MEF

The whole file is a 0x0C-byte header and a flat array of records; there is no header-size field.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MEF\0` | verified | ours; FX1 (150 entries, 96 distinct resource paths) |
| 0x04 | u32 | version, 9 in every file | verified | ours; FX1 |
| 0x08 | u32 | record count *n* | verified | ours; FX1 |
| 0x0C | 0x48 × *n* | *n* records, below; nothing follows them | verified | ours; FX1 (6,216 records, every file's size `0x0C + 0x48 * n`) |

### Record (0x48 bytes)

Each field below is read by MH4U's own effect code: the spawn at `0x391b28` (called when a motion
list's event fires) and the placement getter at `0x391904` it and the monster's parts call. A field
the spawn never reads is `unverified`. FX7 checks every record's fields stay in the ranges those
readers allow.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u8 | spawn filter bit: the spawn tests `[monster+0x30] & (1 << this)` (`0x391a54`); 0 to 31 | verified | ours, spawn `0x391b28`; FX7 |
| +0x01 | u8 | spawn slot mode: 0, 1 or 2; it picks the record's slot among four (`0x391ecc`) | verified | ours, spawn `0x391b28`; FX7 |
| +0x02 | u8 | spawn attach mode: 0 or 1; it is written to the spawn object's `+0x118` (`0x39224c`) | verified | ours, spawn `0x391b28`; FX7 |
| +0x03 | u8 | effect type: 0 to 14, the spawn's switch (`0x391c84`, jump table `0x391c94`); only 0, 1 and 5 occur | verified | ours, spawn `0x391b28`; FX7 |
| +0x04 | u16 | record key: unique within its file, 0 to 4505; the loader indexes the records by it (`0x398f94`), and the lookup `0x398f48` returns the record for a key | verified | ours, MH4U loader `0x398f94` and lookup `0x398f48`; FX3 |
| +0x06 | u16 | time/index into the per-type spawn table: the spawn passes it to `0x390c48`, which maps it through the entry table at `0xeede98`; 0 to 122 | verified | ours, spawn `0x391b28`; FX7 |
| +0x08 | u16 | bone: its low byte is passed to the effect spawn as the joint argument (`0x391c80`); the high byte is 0 in every record | verified | ours, spawn `0x391b28`; FX7 |
| +0x0A | s16 | passed to the spawn object's method at its vtable's +0x48 (`0x3920c0`); -1 to 243 | verified | ours, spawn `0x391b28`; FX7 |
| +0x0C | u16 | flags, low half: the spawn tests the 32-bit word at +0x0C (`0x392058`), whose low bits are 0x2 to 0x8000 | verified | ours, spawn `0x391b28`; FX7 |
| +0x0E | u16 | flags, high half: bits 0x10000 to 0x200000; 0, 4, 8, 16, 32, 36 or 64, so the word's set bits stay inside 0x7C1EFF | verified | ours, spawn `0x391b28`; FX7 |
| +0x10 | u32 | spawn mask bit: `0xFFFFFFFF` (no mask) or 0 to 7; the spawn tests `[monster+0x30] & (1 << this)` (`0x391fac`) | verified | ours, spawn `0x391b28`; FX7 |
| +0x14 | f32 | finite; the getter and the spawn never read it | unverified | ours; FX1, FX7 |
| +0x18 | f32 | position: the first of the three vectors the getter reads and the spawn copies to the spawn object's `+0x278` (`0x392064`); -4,400 to 7,000 | verified | ours, getter `0x391904`, spawn `0x391b28`; FX7 |
| +0x1C | f32 | position, as +0x18 | verified | ours; FX7 |
| +0x20 | f32 | position, as +0x18 (the vector's w is 1.0) | verified | ours; FX7 |
| +0x24 | u32 | always 0 (a spacer before the second vector) | verified | ours; FX1, FX7 |
| +0x28 | f32 | rotation: the second vector, copied to the spawn object's `+0x288`; -220 to 225 | verified | ours, getter `0x391904`, spawn `0x391b28`; FX7 |
| +0x2C | f32 | rotation, as +0x28 | verified | ours; FX7 |
| +0x30 | f32 | rotation, as +0x28 (the vector's w is 1.0) | verified | ours; FX7 |
| +0x34 | u32 | always 0 (a spacer before the third vector) | verified | ours; FX1, FX7 |
| +0x38 | f32 | scale: the third vector, copied to the spawn object's `+0x298`; -1.25 to 10.0 | verified | ours, getter `0x391904`, spawn `0x391b28`; FX7 |
| +0x3C | f32 | scale, as +0x38 | verified | ours; FX7 |
| +0x40 | f32 | scale, as +0x38 (the vector's w is 1.0) | verified | ours; FX7 |
| +0x44 | u32 | always 0 | verified | ours; FX1, FX7 |

The record carries **no effect id**: the spawn computes the effect from +0x03 and +0x06. What the
getter's vectors are called comes from their ranges; the spawn only copies them.

## How MH4U reads it

`rMhMotionEffect`'s load (`0x398f94`, vtable slot 11) checks the magic and the version byte 9,
reads the count and copies each 0x48-byte file record unchanged to `+0x08` of a
`cMhMotionEffectData` object. It then builds a table at the resource's `+0x80`: one u16 entry per
value from 0 to the largest record key, holding the record's index, with `0xFFFF` for a key no
record has; `+0x84` holds that length. The table is why the keys must be unique within a file; a
duplicate would leave one record unreachable.

- **The lookup** (`0x398f48`) takes a key and returns the record or 0: it compares the key with
  `+0x84`, reads the u16 at `+0x80 + 2*key`, rejects `0xFFFF`, checks the array at `+0x7c` and
  returns its entry (`+0x70` holds the array's length).
- **The two files.** The event player picks the record's file by key: a key below 2000 is looked
  up in the first file and one from 2000 up in the second (`0x390be4`: `key - 0x7d0 < 0x1b58`).
- **The spawn** (`0x391b28`) reads the record's fields into an effect object: the type selects a
  path (`0x391c84`), the bone and the time go to the effect's creation (`0x390c48`, `0x391c80`),
  the flags become the object's flag word (`0x392058`), the three vectors are copied
  (`0x392064`), and the mask bit picks which of the monster's four effect slots the record may
  use. The effect itself is derived through the tables below.

## MH4U's spawn tables

The spawn does not read an effect id from the record. It computes a **(base, sub)** pair from the
type (`+0x03`), time (`+0x06`) and bone (`+0x08`), and the pair indexes a table of
`effect\efl\...` resource paths. The tables are in `.data`; four readers do the work, and the
spawn's own switch on the type is the jump table at `0x391c94`.

| Table | Address | Shape | Read by | Entries |
|---|---|---|---|---|
| base by type | `0xeede7c` | u16, one per type | the spawn, `0x391cd4` | 14, types 0 to 13 |
| time table by type | `0xeede98` | u32, one per type, a pointer or 0 | `0x390c48` | 15, types 0 to 14 |
| a type's time table | the pointer | 8-byte records (u32 time, u32 joint table), ended by time `0xFFFFFFFF` | `0x390c48` | 174 records over the 8 types that have one |
| type 4's time table | `0xeed988` | u32, one per time | `0x390c48`, `0x390ca4` | 13, times 0 to 12 |
| base remap of types 5, 11 and 12 | `0xeed9bc`, `0xeedc0c`, `0xeede0c` | 8-byte records (u32 time, u32 base), ended by time `0xFFFFFFFF` | the spawn, `0x391d24`/`0x391d38` | 73, 63 and 13 records |
| joint segment table | a record's second word | 8-byte records (u32 key, u32 value), ended by key `0xFFFFFFFF` | `0x390ef8` | 1 to 10 records each, 187 tables |
| paths by base | `0xef895c` | u32, one per base, a pointer to an array | `0xc0a2a8` | 283, bases 0 to 282 |
| a base's path array | the pointer | u32 pointers to NUL-terminated paths, 0-terminated | `0xc0a2a8` | 0 to 172 per base |

Every row above is verified by FX10 against the image; what is a reading and not a check is what the
effect manager does with the path (step 5) and what the group names below mean.

**The arithmetic**, in the order the spawn and its readers do it:

1. **type → base.** `u16[type]` is the base (`0x391ce8`), masked to a byte at `0x391d78`.
   Types 5, 11 and 12 are the exception: the spawn maps the time through the type's own remap
   table first (`0x390ef8` with the table at `0xeed9bc`/`0xeedc0c`/`0xeede0c`) and uses the result
   as the base. Type 4 is the other exception: the base is `(u16[4] + time) & 0xFFFF`, then masked
   to a byte.
2. **type, time → joint table.** Type 4 indexes `0xeed988` with the time (`0x390ca4`); a 0 pointer
   there means no effect. Any other type reads its time table and needs a record whose first word
   is the time *exactly*; a terminator or a missing key means no effect.
3. **joint → sub.** `0x390ef8` takes the last segment record whose key is `<= joint` (the bone's
   low byte, `0x391c88`), writes `u16(joint + value - key)` to its out pointer, and returns
   success only when that value is below the *next* record's value (the terminator's value is the
   last bound). A joint outside every segment, or a wrapped u16, means no effect.
4. **base, sub → path.** `0xc0a2a8` reads `paths[base]`, then that array's `[sub]`, and gets a
   NUL-terminated path string. Both indexes are masked to a byte by the spawn (`0x391d74`).
   The game does **not** bound-check `sub` against the array's own length: it reads the word after
   an array's last entry if a sub points there.
5. **path → effect.** That path goes to the effect manager's method at its vtable `+0x38`, called
   with a context (`0x10e75f0`), the path and 1; the call returns the effect object the spawn
   fills. What the manager does with the path — load an `rEffectList` and start its effect — is a
   reading, not placed.

**What an entry names.** Every path in the table is an `rEffectList` (`efl`) resource path of the
form `effect\efl\...\..._NNN`. The base selects a group and the sub picks the file in it. The
groups are the game's own: base 0 `cm` (common effects), base 1 `qe`, base 2 `lb`, the `wp` (weapon)
entries, base 17 `otomo`, bases 18 to 91 the monsters (`em`), the `npc` and `event`
entries (109 and up), and the 20 `st` entries (stages); 73 entries have no path. A group can
span two monster files: base 19 holds both `em001` and `em002`, which share the class `uEm002`.
Type 5's remap table maps the time to bases 18 to 91, so a type-5 record's time selects the
monster's group and its bone selects the file.
A base holds 0 to 172 paths (2,899 in all).

**Bounds and dead reads** (checked, FX10): the base table holds 14 entries, so type 14's base read
(`0xeede7c + 28`) lands in the time-table pointer array and gives `0xd568`; type 14 has no time
table, so the spawn then returns without an effect and the bad base is never used. Type 4's time
table holds 13 entries but records' times reach 122; type 4 occurs in no record, so that read is
dead too. The base index is masked to a byte, so bases 256 to 282 cannot be reached by any record;
no base entry is null.

**What MH4U's own records reach** (FX10, all 150 monster-archive MEF entries and 6,216 records):
only types 0, 1 and 5 occur. Type 0's times are 0 and 7 (base 0, common effects), type 1's are 3,
6, 8, 13 and 14 (base 1), and type 5's are 73 values in the remap table's key set (bases 18 to
91). 6,205 records resolve through the five steps to one of 842 distinct paths; every one of them
has a sub inside its base array's own length. The other 11 records, in em020, em027, em031,
em082, em096 and em103, pass steps 1 and 2 but their bone's joint falls outside the segment
table's mapped range, so the spawn returns with no effect: MH4U's data itself has 11 records that
play nothing.

## Carrying a source effect into the tables

A ported monster's effect needs its own path in this table and a record that reaches it. Neither
needs a change to MH4U's code. The cheapest way is to make an unused type's chain the port's own.

**The chain to take.** Type 2 is used by no MH4U record (types 0, 1 and 5 only, FX10), its base
`u16[2] = 2` is reached from type 2 alone (the type base table gives 0, 1, 2, 3, 4, 17, 19, 109,
111 and 174, and the type 5/11/12 remaps give 18 to 91 and 111 to 187), and base 2's 61 paths are
`lb` effects no record reaches. So the port can own the whole type-2 chain without touching
anything MH4U plays:

1. its own **path array**: u32 pointers to NUL-terminated `effect\efl\em\emNNN\...` paths it
   ships, 0-terminated;
2. its own **time table**: 8-byte (u32 time, u32 segment table) records, `0xFFFFFFFF`-ended, one
   per effect group it carries;
3. its own **segment tables**: 8-byte (u32 joint, u32 sub) records, `0xFFFFFFFF`-ended, the
   terminator's value the bound (step 3 above);
4. two `.data` writes: `0xeede98 + 4*2` (the type-2 time-table pointer) and `0xef895c + 4*2`
   (base 2's path-array pointer). Both are writable and both are the values a plugin installs at
   boot; nothing in the fork changes.

The converter then writes each carried effect's MEF record with **type 2** at `+0x03`, the group's
**time key** at `+0x06`, and a **bone** whose low byte its segment table maps to the sub it wants
at `+0x08`; `+0x00` to `+0x02`, the flags, the `s16` and the three vectors are the source event's
own, as far as the placed correspondence goes ([What a converter does](#what-a-converter-does)).
`data/effectmap` therefore carries a source effect's `(time, bone)` rather than a target id, which
is the schema question decision 0015 leaves open.

**What it takes, and what it costs.**

| Path | Takes | Gives | Costs |
|---|---|---|---|
| The two-write overlay above | an unused type's chain (type 2 or 3), the port's arrays and paths | all of MH4U's tables stay as they are; two u32 writes; no code edit, no fork change | one effect group space per unused type; the port's arrays live in its allocation and must be ready before the first spawn |
| Grow the base table | a spare base slot | a new base id | none is spare: the index is a byte and all 283 entries (0 to 255 reachable) are non-null, so a new base needs the spawn's mask widened — a code change |
| Replace the spawn (decision 0012) | a plugin hook on `0x391b28` with its own C, written from the decompiled original | any type/time/bone numbering, any table layout, no `.data` writes | the spawn's other work too — slot selection, flags, vectors, the four effect slots — must be reimplemented, and a hook change rebuilds the game's code library |

The overlay is the cheapest and the one the worked case uses. Its one open link is the path: the
manager is handed an `effect\efl\...` string and must resolve it to the port's own arc. Whether a
path under a ported id's number (`effect\efl\em\em125\em125_000`) loads from the port's own
`data/em125.arc` is **unverified**; the alternative is to point base 2's paths at paths MH4U's
RomFS already holds and overwrite those resources in the mod, which changes MH4U's own effects.

## MH3U ESQ

One per monster, read in place inside its archive (`effect\esq\em\emNNN`, class id `0x525bbf16`).
Its 0x24-byte header holds **seven** section offsets at +0x08, not a header-size field and six
offsets: the loader relocates all seven into pointers (`0x3b30cc`), so the first is the start of
the first section and is `0x24` in every file.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `ESQ\0` | verified | ours; FX2 (44 entries) |
| 0x04 | u32 | version `0x20110217` in every file | verified | ours; FX2 |
| 0x08 | u32[7] | seven section offsets: the first is `0x24`, all are inside the file and non-decreasing, an empty section repeats its neighbour's offset | verified | ours, loader `0x3b30cc` relocates +0x08 to +0x20; FX2 |
| 0x24 | bytes | the seven sections, below | unverified | ours; FX2 |

### Sections

Section *i* runs from offset *i* to offset *i+1*; the seventh runs from the last offset to the end.
The sizes say which sections share an entry size (all 44 files):

| Section | Entry size | Contents |
|---|---|---|
| 0, 1, 2, 4 | 0x3C | the motion-effect events, below; 8,092 in the 44 files |
| 3 | 0x0C | the per-motion records the dispatch table selects (`0x332f18`: entry `(base + i) * 3 * 4`) |
| 5 | 0x10 | the per-motion dispatch table, below |
| 6 | — | a fixed 0x258 bytes, mostly `0xFF`; unplaced |

The player `0x332e8c` reads section 5 as a **per-motion dispatch table**: each 0x10-byte entry
holds five `(base u16, count u8)` pairs — bases at `+0x00`, `+0x02`, `+0x04`, `+0x06` and `+0x08`,
counts at `+0x0A` to `+0x0E`. The current motion selects the entry through the u16 table at section
0 (`0x332eb8`: a 16-bit table indexed by the motion index, plus a second table at +0x30 for indices
from 1000 up), and the entry's pairs select records from sections 3 and 4. Which pair is used
depends on the monster's state (`+0x12` and the bits at `0x332f50`/`0x332f5c`). What separates the
four event sections is still unverified: they may be the four event groups MH4U's motion lists
carry. The sizes are FX2's; the dispatch is the player's, `0x332e8c`.

### Event (0x3C bytes)

The events are the records the player copies to its stack and hands to the monster's spawn. Every
field below is read by `0x332e8c` or the spawn it calls (`0x332d8c` → `0x333a00`); the type mapper
`0x83de40` rewrites the last two words at run time. FX8 checks the ranges.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | motion index: `file * 100 + slot`, MH3U's numbering (`reference/monster_motions.py`), the file being the monster's motion list 0, 1, 2… | verified | ours, player `0x332e8c`; FX5 |
| +0x04 | f32 | frame in that animation; inside it for 7,976 of the 7,983 events whose animation the archive has, with 7 outside (FX5) | verified | ours, player `0x332e8c`; FX5 |
| +0x08 | u16 | effect type: 3, 35 or 36; the type mapper switches on it (`0x83de40`, where 35 and 36 are 0x23 and 0x24) | verified | ours, mapper `0x83de40`; FX8 |
| +0x0A | u16 | effect id in MH3U's own space, 0 to 1313: the spawn resolves the effect asset from it (`0x338b7c`); the mapper rewrites it into +0x38/+0x3A | verified | ours, spawn `0x333a00`; FX8 |
| +0x0C | s16 | passed to the spawn and stored as a float in the spawn object's `+0x238` (`0x333a00`); 0 to 255 | verified | ours, spawn `0x333a00`; FX8 |
| +0x0E | u8 | stored in the spawn object's `+0x2BC`; 0 to 2 | verified | ours, spawn `0x333a00`; FX8 |
| +0x0F | u8 | stored in the spawn object's `+0x2BD`; 0 to 3 | verified | ours, spawn `0x333a00`; FX8 |
| +0x10 | u16 | a spawn argument; 0 to 36,901, and no reader use is placed | unverified | ours, spawn `0x333a00`; FX8 |
| +0x12 | u16 | spawn path flag: 0, 1 or 2; nonzero makes the player call the monster's own spawn at vtable +0x9C instead of `0x332d8c` (`0x3330bc`) | verified | ours, player `0x332e8c`; FX8 |
| +0x14 | f32 | position: the first of the three vectors the spawn copies to the spawn object's `+0x240` (`0x333a00`); -500 to 2,300 | verified | ours, spawn `0x333a00`; FX8 |
| +0x18 | f32 | position, as +0x14 | verified | ours; FX8 |
| +0x1C | f32 | position, as +0x14 | verified | ours; FX8 |
| +0x20 | f32 | rotation: the second vector, copied to the spawn object's `+0x250`; -220 to 190 (one entry has a large negative value) | verified | ours, spawn `0x333a00`; FX8 |
| +0x24 | f32 | rotation, as +0x20 | verified | ours; FX8 |
| +0x28 | f32 | rotation, as +0x20 | verified | ours; FX8 |
| +0x2C | f32 | scale: the third vector, copied to the spawn object's `+0x260`; -2.8 to 13.4 | verified | ours, spawn `0x333a00`; FX8 |
| +0x30 | f32 | scale, as +0x2C | verified | ours; FX8 |
| +0x34 | f32 | scale, as +0x2C | verified | ours; FX8 |
| +0x38 | u16 | the effect id the type mapper writes at run time (`0x83de40`); the file carries a default, 32 in almost every event and 21 in the rest | unverified | ours; FX8 |
| +0x3A | u16 | the subtype the type mapper writes at run time; the file's value is 0 in almost every event, up to 120 in the rest | unverified | ours; FX8 |

An all-zero event is padding at the end of its section (49 across the 44 files). An event whose
motion slot the monster's own archive leaves empty is not padding: 60 of the 8,043 nonzero events
name one, which the archive may share from another monster's; 7 more name an animation whose frame
count the frame is past (FX5).

## MHXX PSL

One per motion list. A file with no effects is 8 bytes: magic, version and a slot count of 0
(seventeen do). Otherwise the header holds one u32 per animation slot, then one 12-byte descriptor
every 16 bytes for each slot that has effects, in slot order. The descriptors are at
`align(0x08 + 4*n*, 0x10) + 0x10*k*`; the lists start 4 bytes before the descriptor table's
16-byte end, because the last descriptor has no padding after its 12 bytes.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `PSL\\0` | verified | ours; FX2 (507 entries) |
| 0x04 | u16 | version, 2 in every file | verified | ours; FX2 |
| 0x06 | u16 | slot count *n* | verified | ours; FX2 |
| 0x08 | u32[*n*] | one offset per slot; slot 0's is 0 in every file, a slot with no effects is 0, and the *k*-th nonzero offset is `align(0x08 + 4*n*, 0x10) + 0x10*k*` (18,831 slots, 8,129 descriptors) | verified | ours; FX2 |
| descriptor +0x00 | u32 | the frame count of the animation in the slot the descriptor sits at | verified | ours; FX6 |
| descriptor +0x04 | u32 | `0x00200000` (8,117 descriptors) or `0x01200000` (12); the player's use is not read | verified | ours; FX9 |
| descriptor +0x08 | u32 | the file offset of the slot's effect list: strictly increasing, the first at the last descriptor's end, the last inside the file | verified | ours; FX9 |
| end | bytes | the per-slot effect lists: each runs from its offset to the next descriptor's, the last to the file's end; their contents are not laid out (an array of 0x10-byte records at the end of some lists is visible but not placed) | unverified | ours; FX9 |

One hundred and ten descriptors are in four PSLs whose motion list isn't in the same archive, so
their frame count has no local animation to compare with; of the 8,019 that do, 7,980 name an
animation in their slot and its frame count is that animation's, and 39 name a slot the archive
leaves empty (FX6).

- **FX7 (done, 2026-11-26).** The record fields MH4U's spawn and getter read stay in their readers'
  ranges: `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k consumer`. Procedure: read every
  `rMhMotionEffect` entry of MH4U's monster archives and check each record's `+0x00` to `+0x10`,
  the three vectors and the zero fields against the ranges and masks the spawn (`0x391b28`) and
  getter (`0x391904`) allow. Result: 150 entries, 6,216 records; `+0x00` <= 31, `+0x01` <= 2,
  `+0x02` <= 1, `+0x03` 0, 1 or 5, `+0x06` <= 122, `+0x08`'s high byte 0 in every record, `+0x0A`
  -1 to 243; the 32-bit word at `+0x0C` sets only bits inside `0x7C1EFF`; `+0x10` is `0xFFFFFFFF`
  or 0 to 7; `+0x24`, `+0x34` and `+0x44` are 0; the vectors are finite, the first from -4,400 to
  7,000, the second -220 to 225 and the third -1.25 to 10.0.
- **FX8 (done, 2026-11-26).** The ESQ event fields the player and spawn read stay in their readers'
  ranges: `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k consumer`. Procedure: read every ESQ
  of MH3U's monster archives, take each non-padding 0x3C event and check its scalars against the
  player (`0x332e8c`), spawn (`0x332d8c`/`0x333a00`) and mapper (`0x83de40`) uses. Result: 8,092
  events, 49 padding; `+0x08` is 3, 35 or 36; `+0x0A` <= 1313; `+0x0C` <= 255; `+0x0E` 0 to 2;
  `+0x0F` 0 to 3; `+0x12` 0 to 2; `+0x38` 0, 21 or 32; the three vectors are finite, the first
  -500 to 2,300, the second -220 to 190 (one entry has a large negative value) and the third -2.8
  to 13.4.
- **FX9 (done, 2026-11-26).** A PSL descriptor is three words every 16 bytes and its list starts
  where the slot order puts it: `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k
  descriptor_and_list`. Procedure: read every PSL of MHXX's monster archives, check each
  descriptor's flags, and check its list starts after the last descriptor's 12 bytes and the lists
  run in slot order to the file's end. Result: 507 PSLs, 18,831 slots, 8,129 descriptors; every
  descriptor's flags are `0x00200000` (8,117) or `0x01200000` (12); every first list starts at
  the descriptor table's 16-byte end minus 4; every later list follows its predecessor and the last
  is inside the file.

## A 3U effect's assets

Carrying an effect means carrying the resources its effect list names, not just the list. In all
three games an `rEffectList` (EFL) is one effect: its header's counts describe the effect's emitters
and its block holds the paths of the model and textures that effect uses ([efl](efl.md)). So the
asset set of one source effect is:

| Asset | 3U path (the block's strings) | MH4U path the pipeline expects | Class and version |
|---|---|---|---|
| the effect list | `effect\efl\em\emNNN\emNNN_NNN` | `effect\efl\em\emNNN\emNNN_NNN` | `rEffectList`; EFL version `0x30110616` in MH3U, `0x30111104` in MH4U |
| the effect model | `effect\mod\em\emNNN\emNNN_NNN` | `effect\base\em\emNNN\...` | `rModel`, MOD version `0xE6` in both (the word after it is the bone count: 44 in 3U's effect model, 43 in MH4U's) |
| its materials | (inside the model) | same | `rMaterial`, MRL version `0x20` in both; the shader-package ids are converted by [mfx](mfx.md) (X3) |
| its textures | `@effect\tex\em\emNNN\emNNN_NNN_BM` and the plain path | `@effect\base\..._BM`/`_BM_NOMIP` and the plain path | `rTexture`, TEX version `0x200000a5` (25 of 3U Rathian's 24 entries) or `0x201b00a5` in both |
| the effect's animation | not placed | `effect\base\em\emNNN\mot\...` | `rEffectAnim` (EAN), version `0x20100924` in both |

The paths in the second and third columns are the games' own strings, read from their code and their
EFL blocks; the classes and versions are read from the real archive entries of both games' `em001`
(a check, not a claim about every file).

The path conventions are the games' own. MH3U's code formats the list's and the model's paths from
the monster number and an index (`effect\efl\em\em%03d\em%03d_%03x` at `0xb01978`,
`effect\mod\em\em%03d\em%03d_%03x` at `0xb0199c`), and its EFL blocks name textures under
`effect\tex`; MH4U's code has no `effect\mod` or `effect\tex` string and puts both under
`effect\base`, with the effect animation under `...\mot\...`. MH3U's code has no
`effect\base`.

**The worked case: 3U Rathian's fireball.** Her archive (`/arc/enemy/em001.arc`) holds 19
`rEffectList`, 13 `rEffectAnim`, 3 `rMaterial`, 3 `rModel`, 24 `rTexture` and 1 `rEffectSequence`;
MH4U's `/data/em001.arc` holds 26, 1, 3, 3, 7 and 2 `rMhMotionEffect`. Her ESQ has only four
non-padding events: motion 70 at frames 25 and 70, type 36, effect id 338 in section 0 and 379 in
section 1, with `+0x38` 0 or 32 and `+0x3A` 0. Motion 70 is her motion list 0's last animation
(123 frames), and no action of hers starts it as its first motion. What is **not placed** is which
of the 19 effect lists those two ids name: MH3U's spawn puts the event's `+0x3A` through its type
mapper (`0x83de40`, which rewrites `+0x38` to 7 and `+0x3A` to the mapped id — 24 for id 379, and
it leaves id 338 unmapped) and then through `0x338b7c`, which returns a per-monster effect index
(7 for the unmapped path, `63 + a byte` for the mapped one); `0x334840` looks the `+0x0A` id up in
the monster's loaded effect lists. So the fireball's asset set is one of those 19 lists plus what
its block names, and whether motion 70 is the fireball is also unverified: her fireball *shot* is
spawned by her shell classes (`uShellEmBase00`, the setup block MH4U lacks), not by the ESQ.

**What `mhuc` does with them today.** `efl.from_mh3u` rewrites the version word and carries the
block unchanged ([efl](efl.md), EF3): the block's `effect\mod` and `effect\tex` paths stay 3U
paths, so a converted list would name resources MH4U does not have. `mod`, `mrl` and `tex` convert
the model, its materials and its textures (the shader ids through [mfx](mfx.md)); there is no
reader for `rEffectAnim` (EAN) in `src/mhuc`, so nothing checks or rewrites the effect's
animation. A port of an effect therefore needs three things the converter does not do yet: rewrite
the block's paths, carry the EAN (the version is already MH4U's), and split the effect list into
its own arc at the path the port's spawn table names.

## What a converter does

The converters are `src/mhuc/formats/mef.py` and, for the effect-id map, `src/mhuc/effectmap.py`
(whose tables ship empty, [data/effectmap](../data/effectmap/README.md)).

| Conversion | Carried | Skipped or refused |
|---|---|---|
| MEF (MH4U) -> MEF: `read_mef(...).to_bytes()`, `to_mh4u(data, "mh4u")` | every byte: the header from its fields, the records unchanged | nothing |
| ESQ (MH3U) -> its own form: `read_esq(...).to_bytes()`, `read_esq(...).events()` | the header, seven section offsets and body unchanged; each event's fields read | nothing (round trip only) |
| PSL (MHXX) -> its own form: `read_psl(...).to_bytes()`, `read_psl(...).descriptors`, `.lists()` | the header, slot table, descriptors and body unchanged; each descriptor's frame count, flags and list offset read | nothing (round trip only) |
| ESQ or PSL -> MEF: `to_mh4u(data, "mh3u"\|"mhxx")` | the source's container and fields are read and checked | **refused**: the target effect is not a field (it is derived from the type and the time), and the source scalars' correspondence is not placed |

The refusal is deliberate. Writing a MEF today would carry guesses into a port:

- **The effect identity is derived, not stored.** MH4U's record has no effect-id field: the
  spawn (`0x391b28`) takes the record's type (`+0x03`), time (`+0x06`) and bone (`+0x08`) through
  the tables [above](#mh4us-spawn-tables) and asks the manager for the path they name. A carried
  effect therefore needs a record with the port's own type/time/bone and the port's own tables
  installed ([Carrying a source effect](#carrying-a-source-effect-into-the-tables)); `to_mh4u`
  cannot write it without them. `data/effectmap`'s rows must carry the source effect's
  `(type, time, bone)` — or the port's group key and joint — rather than a target id, which is the
  schema change decision 0015 leaves open.
- **The ESQ's parameters are placed, but not their target fields.** Both games' spawns take three
  vectors in the same order, and the ESQ event's s16 `+0x0C` is the same kind of value as the MEF
  record's s16 `+0x0A` (each game's spawn passes it to its effect object), so the vectors and the
  s16 are the natural correspondence — but no check compares a source effect with a target
  record, so this is a reading, not verified. The other source scalars — the type `+0x08`, the id
  `+0x0A`, the bytes `+0x0E`/`+0x0F` and the flag `+0x12` — have no placed counterpart: the
  target's `+0x00`, `+0x01`, `+0x02`, `+0x03`, `+0x06`, `+0x08` and flags are set by MH4U's spawn
  for reasons the source does not express the same way.
- **The PSL's lists are not laid out.** A descriptor's frame count, flags and list offset are
  placed (FX6, FX9), but the bytes of the per-slot lists are not: the 0x10-byte records visible at
  the end of a list are not placed, so no PSL event can be read, let alone written as a MEF.
- **The key's namespace** is still the LMT event's, and MH3U's and MHXX's motion lists carry no
  such ids (every MH3U v66 event is one zero-bits event per group and MHXX's remaps are zero), so a
  port writes the event entries itself and keys the MEF to them ([specs/lmt.md](lmt.md), FX4 is
  the full pass).
- **The two files.** A key below 2000 is looked up in the first MEF and one from 2000 up in the
  second (the player, `0x390be4`), so a converter must split the records by key.

What is left for `to_mh4u`: the effectmap's target `(type, time)` rows for the source ids, the
source scalar -> target scalar correspondence for the ESQ, and the PSL list layout. Until then
`to_mh4u` raises with the reason, and no port ships `mef` or `efl`.

## Checks

- **FX1 (done, 2026-11-25).** Read every `rMhMotionEffect` entry of MH4U's monster archives and
  check the header and each record: `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k
  mh4u_motion_effect`, with the synthetic reader tests in `tests/test_effects.py`. Result: 150
  entries, 96 distinct resource paths and 6,216 records, all read; every file's size is
  `0x0C + 0x48 * n`; `+0x24`, `+0x34` and `+0x44` are 0 in every record; the bytes at `+0x07`,
  `+0x09` and `+0x0F` are 0 in every record; the three floats at `+0x38` are finite in every
  record. The value ranges in the record table are FX1's tally.
- **FX2 (done, 2026-11-25, re-run 2026-11-26).** Read every `rEffectSequence` and
  `rProofEffectMotSequenceList` entry of MH3U's and MHXX's monster archives: `MHUC_DUMPS=… python3
  -m pytest -q -m game_files -k "effect_sequence or mhxx_motion_effect"`. Result: 44 ESQ entries,
  every version `0x20110217`, every section 0 at `0x24`, every set of seven offsets inside the
  file and non-decreasing with five files repeating one offset, every section a whole number of
  its entry size, every seventh section `0x258` bytes; 507 PSL entries with 18,831 slots and
  8,129 descriptors, every version 2, slot 0's offset 0 in every file, every nonzero slot offset
  where the slot order puts it, seventeen 8-byte files with no slots. The sections are FX5's and
  FX8's, the descriptors FX6's and FX9's.
- **FX3 (done, 2026-11-25).** Every MEF file's record keys are unique, which the loader's
  key-to-record table needs, and the largest is 4505 (a u16's range is what the table holds).
  Procedure: read all 96 distinct MEF resource paths of MH4U's monster archives
  (`MHUC_DUMPS=… python3 -m pytest -q -m game_files -k effects_round_trip` plus the unit tests)
  and take the u16 at `+0x04` of every record; no file repeats a key, and the keys span 0 to 4505.
  The loader's use of the key is read from `0x398f94` and the lookup from `0x398f48`; the player
  passes a u16 key (`0x390be4`/`0x391a28`), and the data match says the motion list's event remap
  id is that key (FX4 is the full pass).
- **FX4 (open).** The motion lists' event remap ids are the MEF keys: every nonzero remap id of a
  motion list's four event groups should have a record in that list's MEF. Sample so far:
  `em001_0` 10 of 11, `em015_0` 24 of 25. A full pass reads every MH4U monster arc's motion lists
  and MEFs; it needs the same whole-archive pass as FX1 and has not run yet.
- **FX5 (done, 2026-11-26).** An ESQ event's motion and frame decode against the monster's own
  motion lists: `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k
  effect_sequence_event`, with the unit tests in `tests/test_effects.py`. Procedure: read every
  ESQ entry of MH3U's monster archives, take the 0x3C-byte events of sections 0, 1, 2 and 4, read
  `+0x00` as MH3U's motion index `file * 100 + slot` and `+0x04` as a frame, and compare the frame
  with the animation's frame count from the same archive. Result: 8,092 events, 49 all-zero
  padding entries, 7,976 whose animation is in the archive and whose frame is inside it, 60 that
  name a slot the archive leaves empty (a motion list it shares with another monster's archive),
  and 7 whose frame is outside: em066's and em067's motion 85 at frame 193 (its animation has 139
  frames) and em072's motion 34 at frame 53 (43 frames). The 7 are open: they may be a shared
  motion, or an entry of a kind that isn't an effect event in the same section.
- **FX6 (done, 2026-11-26).** A PSL descriptor's first word is the frame count of the animation in
  its slot: `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k psl_descriptor`. Procedure: read
  every PSL entry of MHXX's monster archives, find the motion list of the same name in the same
  archive, and compare each descriptor's first word with the frame count of the animation at the
  descriptor's slot. Result: 507 PSLs, 18,831 slots, 8,129 descriptors. 110 descriptors are in
  four PSLs whose motion list is not in the same archive; of the other 8,019, 7,980 equal their
  animation's frame count and 39 sit at a slot the archive leaves empty. No descriptor's frame
  count differs from the animation in its slot.

- **FX10 (done, 2026-11-26).** The spawn tables' shape and every MEF record's resolution:
  `MH4U_FORK=… python3 reference/spawn_tables.py --exheader <MH4U v1.3.0 exheader.bin> --code
  <code.bin> --romfs <romfs.bin> --records`, run under the workspace's heavy lock because the
  record pass reads every monster archive. Procedure: read the five tables at `0xeede7c`,
  `0xeede98`, `0xeed988` and `0xef895c` and the type 5/11/12 remap tables, walk each base's path
  array, then read all 150 MEF entries of MH4U's monster archives and resolve every record's
  `(type, time, bone)` through steps 1 to 4 of [MH4U's spawn tables](#mh4us-spawn-tables); then
  `--cross-check` runs the spawn's own code (`0x391c74` to `0x391d88`, with the real `0x390c48`,
  `0x390ef8` and `0xc0a2a8` and only the effect manager's method stubbed) under Unicorn on a
  sample and compares base, sub and path with the model. Result: 14 base entries; 15 type
  pointers, non-null for types 0, 1, 2, 5, 7, 11, 12 and 13, holding 174 (time, joint-segment)
  records; type 4's table 13 entries; the type 5/11/12 remaps 73, 63 and 13 records; 283 base
  entries, 2,899 path pointers, 73 non-null entries with no path; 6,216 records, 6,205 resolved
  to 842 distinct paths, 0 with a sub past its base array's length, and 11 with no effect
  (em020, em027, em031, em082, em096 and em103, failing the joint segment remap). The cross-check
  agrees with the model on 696 of 696 samples, types 0 to 14, including the types with no time
  table and the type-4 table's edge.
- **FX11 (done, 2026-11-26; the in-game half is the maintainer's).** The addition path runs on
  MH4U's own spawn: `MH4U_FORK=… python3 reference/spawn_tables.py --exheader … --code … --probe
  2 0 0 --add`. Procedure: write the port's path array, time table and segment table into the
  emulator's memory, patch `0xeede98 + 4*2` and `0xef895c + 4*2` to point at them, and run the
  spawn's code on a record with type 2, time 0 and bone 0. Result: the code computes base 2 and
  sub 0 and asks the effect manager for `effect\efl\em\em125\em125_000` — the port's own path —
  while the same probe without `--add` gives the `lb000_000` path base 2 held. Two `.data` writes,
  no code edit. What the check does not cover: that the manager resolves the port's path to its
  own arc (unverified, [above](#carrying-a-source-effect-into-the-tables)), and the visual watch
  ([docs/checks.md](../docs/checks.md#a-ported-effect-at-the-source-frame-e1)).
