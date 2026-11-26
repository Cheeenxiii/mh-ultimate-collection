---
class: none (in-image data, no file)
extension: none (in-image)
games: MH3U (USA) and MH4U (USA v1.3.0)
status: verified
---

# In-image action data: the action-start record, the command list and the value curve

Some of a monster's action handlers do not start their move themselves. They pass the engine a
pointer into the game's image, and the engine reads what the move needs from it. Three such
tables matter for the port:

- the **action-start record**, 44 bytes, which the two readers start two animations from, pick
  a turn animation by the sign of the heading difference, and apply two floats to the speed;
- the **command list**, a run of 8-byte commands, which the shared category-10/11 handler keeps
  in the work block for its interpreter;
- the **value curve**, 8 bytes per key, which an action's sub-handlers evaluate to scale the
  monster's speed over the move.

None is a file: all live in the image's `.data`, next to the class's code. MH3U's Rathian
class `uEm002` keeps the action-start records at 0x00B0B168 and 0x00B0B194; MH4U's `uEm001`
keeps four at 0x00E09558, 0x00E09584, 0x00E095B0 and 0x00E095DC. The handlers and readers that
use them are named in [reference/README.md](../reference/README.md#the-tables-the-missing-ids-pass);
the conversion between the two games' records is [below](#conversion).

## Action-start record (44 bytes)

The readers are paired: MH3U 0x0084704C with MH4U 0x00938748, and MH3U 0x00847134 with MH4U
0x00938834 (reference/README.md's MH3U↔MH4U map). Each game's first reader starts the "b"
quartet, its second the "a" quartet, and the second reader reads the rest.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u16 | motion a: the animation the second reader starts | verified | ours, readers 0x00847134 / 0x00938834 (`ldrh r1,[record]`) |
| +0x04 | s32 | argument a1: the start's first integer argument; MH4U converts it to a float | verified | ours, reader's r2 (MH4U `vcvt.f32.s32` before 0x0091908C) |
| +0x08 | s32 | argument a2: the start's second integer argument; MH4U converts it to a float | verified | ours, reader's r3 (MH3U) / s1 (MH4U) |
| +0x0C | u32 | flags a: in MH4U the flag word the start takes in r2; MH3U passes it as a float argument its callee never reads | verified | ours, readers; MH4U 0x0091908C (sets mask 2 for a negative angle), 0x00B0549C (tests masks 1, 8, 0x10, 0x20); MH3U 0x0083771C → 0x00198688, which reads only the first two of the three words 0x0083771C passes on the stack |
| +0x10 | u16 | motion b: the animation the first reader starts | verified | ours, readers 0x0084704C / 0x00938748 (`ldrh r1,[record,#0x10]`) |
| +0x14 | s32 | argument b1: the start's first integer argument; MH4U converts it to a float | verified | ours, reader's r2 (MH3U) / s0 (MH4U) |
| +0x18 | s32 | argument b2: the start's second integer argument; MH4U converts it to a float | verified | ours, reader's r3 (MH3U) / s1 (MH4U) |
| +0x1C | u32 | flags b: as +0x0C, for the first reader | verified | ours, readers; MH4U 0x0091908C, 0x00B0549C; MH3U 0x0083771C → 0x00198688, which reads only the first two of the three words it is passed on the stack |
| +0x20 | u16 | turn motion a: started by the second reader when the heading difference has one sign | verified | ours, readers (`ldrh r1,[record,#0x20]`, chosen by the sign) |
| +0x22 | u16 | turn motion b: started for the other sign | verified | ours, readers (`ldrh r3,[record,#0x22]`, the other branch) |
| +0x24 | f32 | threshold: the second reader compares it with the speed at `work+0x168` to choose the turn | verified | ours, reader 0x00847134 / 0x00938834 (`vldr s1,[record,#0x24]`) |
| +0x28 | f32 | clamp: the first reader raises the speed at `work+0x168` to it | verified | ours, reader 0x0084704C / 0x00938748 (`vldr s1,[record,#0x28]`) |

The record is not a copy between the games: four fields are numbered differently and two
changed meaning. A field's status is about the offset the readers read, not about a meaning
it may have outside them.

## Conversion

| MH3U field | MH4U field | How |
|---|---|---|
| motion a, motion b, turn motion a, turn motion b | the same offsets | the same animation at another index. MH3U numbers a motion `file*100+slot` and MH4U `file<<8\|slot`, and the LMT files group the animations differently, so the pair is found by the animation's signature (frame count and loop frame, the R1 comparison), check N2. Both games' readers start the motion at the same offset for the same quartet, so the offset pairs them; the signature confirms the animation. |
| argument a1, a2, b1, b2 | the same offsets | carried unchanged (s32). |
| flags a, flags b | the same offsets | **not** from MH3U: its copies reach 0x00198688, which does not read them. MH4U's readers pass them to 0x0091908C as a flag word, so the rebuilt record takes the word MH4U's own records all hold, check N1. |
| threshold, clamp | the same offsets | carried unchanged (f32). |

`reference/monster_attack_records.py rebuild` is that conversion; `check` is the procedure
below. The rebuilt record is not committed: it is derived from the player's dumps at build
time, like the monster data (`mhuc monsterdata`).

## Command list (8-byte commands)

The category-10 and category-11 case blocks pass a list pointer in r1 to the shared handler
(MH3U 0x008326E0 and 0x008326DC; MH4U 0x00919788), which keeps it in the work block at
`work+0x98C` and hands it to the interpreter 0x0083E4B0. MH4U has its own handler and its own
interpreter; MH3U's list bytes are the ones the port's handler passes, and the two games' list
formats correspond (check N3).

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u8 | command: the interpreter dispatches on this byte; 0xFF ends the list | verified | ours, 0x0083E4B0 (`ldrb r0,[r4]`, `cmp r0,#0xFF`) |
| +0x04 | u32 | parameter: read as an integer, as a float, or as a pointer to another list, by the command | verified | ours, 0x0083E4B0 (`ldr r0,[r4,#4]`; `ldr r4,[r4,#4]` into a sub-list) |

The records are a run of eight-byte commands: 0x0083E4B0 indexes them with `add r4,r6,r2,lsl
#3` and advances its own index after each. What each command means is the interpreter's, not
this table's, and is unknown; the port does not need it (N3).

## Value curve (8 bytes per key)

Action 4's sub-handlers pass three more in-image tables: 0x00691CD8, 0x00691E68, 0x00691E80,
0x00692318 and 0x00692330 pass 0x00C4ED68, 0x00C4EEF0 and 0x00C4EF28 to 0x0083C6E0, which
evaluates the curve at `this+0x278` and scales the monster's speed by the result. MH3U's
evaluator 0x0058493C and MH4U's 0x00AAC8DC are a map pair ("same body"), so MH4U reads the same
records. The curve holds the move's own values, so the port carries the 3U table; there is no
MH4U record to compare it with (MH4U has no action 4).

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | f32 | key time | verified | ours, evaluator 0x0058493C / 0x00AAC8DC (`vldr s1,[r0]`) |
| +0x04 | f32 | key value | verified | ours, evaluator (`vldr s0,[r0,#4]`, interpolated with `[r0,#0xC]`) |

The keys are an eight-byte-stride run: the evaluator reads `[r0]` and `[r0+4]` for the key and
`[r0+8]` and `[r0+0xC]` for the next one, and advances by eight bytes. A key whose time is
negative ends the list, and its value is the constant after the last key (0x0058493C returns
`[r0+4]` without interpolating when `[r0]` is negative).

## Checks

- **N1 (done, MH3U USA's `code.bin` and MH4U USA v1.3.0's):** `reference/monster_attack_records.py
  check` reads 3/5's record at 0x00B0B168 and action 4's at 0x00B0B194 from MH3U, and MH4U's
  four `uEm001` records from 0x00E09558. It pairs the four motions by offset, carries the four
  arguments and two floats, takes the flag word MH4U's records all hold, rebuilds 3/5's record
  and compares it with MH4U's own. Results: the four arguments are equal (4 of 4) and the two
  floats are equal (2 of 2); the four motions pair to the same animation (N2); MH4U's four
  records all hold one flag word; and the rebuilt record equals MH4U's own on all 12 fields.
  Action 4 has no MH4U record to compare against (MH4U's `uEm001` has no action 4), so the check
  reports its rebuilt counterpart only. The values are printed, never written to the repository.
- **N2 (done, MH3U USA's and MH4U USA's RomFS):** the same command with `--mh3u-romfs` and
  `--mh4u-romfs` reads `em001`'s LMT files in file order from both games and compares the four
  paired motions' signatures (frame count and loop frame). Results: all four pairs are the same
  animation. Three of the four signatures occur at more than one index (the two turn animations
  share theirs with each other), so the signature confirms the animation but not the left/right
  order; the second reader's sign test, the same in both games, is what pairs the turn fields.
- **N3 (done, MH3U USA's image):** read the category-10 and -11 case blocks and the interpreter.
  Each 3U case block loads its list pointer from a literal and passes it to the shared handler
  0x008326E0 or its other entry 0x008326DC; the lists end with a 0xFF command; 0x0083E4B0 walks
  them eight bytes at a time. MH4U's 10/7 and 11/0 case blocks pass MH4U's own lists to the same
  handler's MH4U counterpart 0x00919788, which is evidence that the two games' formats
  correspond. Under decision 0002's 2026-11-26 second amendment the port reimplements the base
  handler too, so it reads MH3U's lists: the port needs those in-image bytes from the player's
  dump, converted at build time from the dump and never committed, and
  [#226](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/226) names them.
- **N4 (done, MH3U USA's `code.bin`):** `reference/monster_attack_records.py curve` reads each
  of action 4's three curves, and the evaluator 0x0058493C is the map pair of MH4U's 0x00AAC8DC
  ("same body", reference/README.md's 73). Results: 0x00C4ED68 has 2 keys, 0x00C4EEF0 has 6 and
  0x00C4EF28 has 9, and each ends with a negative-time key, its value the constant past the last
  key. No MH4U record exists for action 4, so the curves are carried rather than converted.
