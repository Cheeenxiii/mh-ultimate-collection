/* Generated from R1's comparison by reference/monster_motions.py table.
 * Do not edit: run the tool against the player's own dumps. Licence: GPL-3.0-or-later. */
#ifndef MHUC_MOTIONS_H
#define MHUC_MOTIONS_H

#include <stdint.h>

/* One translation for a ported monster: for `category`/`index` (its current action),
 * MH4U's handler asks `motion`; the source game's animation is at `source` in the
 * converted motion lists, in MH4U's packing (`file << 8 | slot`; the converted lists
 * keep the source game's grouping). `index` is 0x100 for a category-only action.
 */
typedef struct MhucMotion {
    uint8_t category;
    uint16_t index;
    uint16_t motion;
    uint16_t source;
} MhucMotion;

/* One ported monster's translations, keyed by its MH4U id (data/ids/registry.csv).
 * `unresolved` holds the action ids R1 cannot resolve yet, as
 * `category << 8 | index`: the plugin passes their motion numbers through unchanged.
 * The four counts are R1's for the pair this table was compared with;
 * tools/check_motion_tables.py checks them. */
typedef struct MhucPortedMotions {
    uint8_t id;
    uint16_t entry_count;
    uint16_t unresolved_count;
    uint16_t common;
    uint16_t compared;
    uint16_t same_index;
    uint16_t not_compared;
    const MhucMotion *entries;
    const uint16_t *unresolved;
} MhucPortedMotions;

/* Rathian, ported from mhxx em001 (rathian-gu, id 124): 0 of R1's 167 compared action ids translated, 0 left out (category 7's computed index), 167 start the same index in both games; 106 of the 273 common ids aren't compared. */
static const MhucMotion *const mhuc_motions_124 = NULL;
static const uint16_t *const mhuc_unresolved_124 = NULL;

/* Rathian, ported from mh3u em001 (rathian-3u, id 125): 96 of R1's 117 compared action ids translated, 19 left out (category 7's computed index), 2 start the same index in both games; 57 of the 174 common ids aren't compared. */
static const MhucMotion mhuc_motions_125[] = {
    {1, 4, 0x010, 0x013},
    {1, 5, 0x011, 0x014},
    {1, 6, 0x012, 0x017},
    {1, 7, 0x010, 0x013},
    {1, 8, 0x011, 0x014},
    {1, 13, 0x010, 0x013},
    {1, 14, 0x011, 0x014},
    {2, 4, 0x40c, 0x20e},
    {2, 5, 0x40c, 0x20e},
    {2, 6, 0x40c, 0x20e},
    {3, 0, 0x10d, 0x029},
    {3, 1, 0x10d, 0x029},
    {3, 2, 0x101, 0x01a},
    {3, 4, 0x106, 0x01f},
    {3, 6, 0x101, 0x01a},
    {3, 7, 0x101, 0x01a},
    {3, 8, 0x10f, 0x02d},
    {3, 12, 0x209, 0x03d},
    {3, 13, 0x101, 0x01a},
    {3, 16, 0x101, 0x01a},
    {3, 17, 0x101, 0x01a},
    {3, 18, 0x101, 0x01a},
    {3, 19, 0x101, 0x01a},
    {3, 20, 0x209, 0x03d},
    {3, 21, 0x209, 0x03d},
    {3, 24, 0x101, 0x01a},
    {3, 25, 0x209, 0x03d},
    {3, 27, 0x101, 0x01a},
    {3, 28, 0x101, 0x01a},
    {3, 29, 0x209, 0x03d},
    {7, 0, 0x201, 0x02f},
    {7, 1, 0x41a, 0x209},
    {7, 3, 0x203, 0x031},
    {7, 4, 0x203, 0x031},
    {7, 5, 0x406, 0x206},
    {7, 6, 0x007, 0x008},
    {7, 7, 0x007, 0x008},
    {7, 8, 0x408, 0x208},
    {7, 9, 0x405, 0x205},
    {7, 12, 0x203, 0x031},
    {7, 14, 0x405, 0x205},
    {7, 16, 0x007, 0x008},
    {7, 17, 0x20d, 0x036},
    {7, 18, 0x20e, 0x037},
    {7, 19, 0x007, 0x008},
    {7, 20, 0x41a, 0x209},
    {7, 21, 0x20e, 0x037},
    {7, 22, 0x20c, 0x045},
    {7, 23, 0x20c, 0x045},
    {7, 24, 0x20c, 0x045},
    {7, 25, 0x20c, 0x045},
    {7, 26, 0x20c, 0x045},
    {7, 27, 0x20c, 0x045},
    {7, 28, 0x20c, 0x045},
    {7, 29, 0x20c, 0x045},
    {7, 30, 0x405, 0x205},
    {7, 31, 0x401, 0x200},
    {7, 32, 0x007, 0x008},
    {7, 33, 0x409, 0x209},
    {7, 34, 0x408, 0x208},
    {7, 41, 0x203, 0x031},
    {7, 42, 0x41a, 0x209},
    {7, 43, 0x203, 0x031},
    {7, 44, 0x203, 0x031},
    {7, 45, 0x207, 0x038},
    {7, 53, 0x203, 0x031},
    {7, 54, 0x203, 0x031},
    {7, 55, 0x203, 0x031},
    {7, 56, 0x203, 0x031},
    {7, 57, 0x20c, 0x045},
    {7, 61, 0x406, 0x206},
    {7, 71, 0x410, 0x213},
    {7, 72, 0x203, 0x031},
    {7, 73, 0x203, 0x031},
    {7, 75, 0x209, 0x03d},
    {7, 76, 0x41a, 0x209},
    {7, 77, 0x201, 0x02f},
    {7, 78, 0x20d, 0x036},
    {7, 80, 0x405, 0x205},
    {7, 83, 0x405, 0x205},
    {7, 85, 0x007, 0x008},
    {7, 88, 0x405, 0x205},
    {7, 89, 0x405, 0x205},
    {7, 94, 0x209, 0x03d},
    {7, 95, 0x41a, 0x209},
    {8, 256, 0x403, 0x202},
    {9, 1, 0x404, 0x203},
    {9, 2, 0x405, 0x205},
    {12, 256, 0x101, 0x01a},
    {13, 0, 0x101, 0x01a},
    {13, 1, 0x209, 0x03d},
    {13, 2, 0x401, 0x200},
    {13, 4, 0x404, 0x203},
    {13, 5, 0x002, 0x013},
    {13, 6, 0x002, 0x01a},
    {13, 8, 0x013, 0x01a},
};
static const uint16_t mhuc_unresolved_125[] = {
    0x0724, /* 7/36 */
    0x0726, /* 7/38 */
    0x0727, /* 7/39 */
    0x0728, /* 7/40 */
    0x0731, /* 7/49 */
    0x0732, /* 7/50 */
    0x0733, /* 7/51 */
    0x0734, /* 7/52 */
    0x073b, /* 7/59 */
    0x073c, /* 7/60 */
    0x073e, /* 7/62 */
    0x0742, /* 7/66 */
    0x0743, /* 7/67 */
    0x0744, /* 7/68 */
    0x0745, /* 7/69 */
    0x0746, /* 7/70 */
    0x074a, /* 7/74 */
    0x075a, /* 7/90 */
    0x075b, /* 7/91 */
};

#define MHUC_PORTED_MOTIONS_COUNT 2
static const MhucPortedMotions mhuc_ported_motions[MHUC_PORTED_MOTIONS_COUNT] = {
    {124, 0, 0, 273, 167, 167, 106, mhuc_motions_124, mhuc_unresolved_124},
    {125, 96, 19, 174, 117, 2, 57, mhuc_motions_125, mhuc_unresolved_125},
};

#endif
