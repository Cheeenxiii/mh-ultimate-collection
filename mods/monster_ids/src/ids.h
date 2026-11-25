/* Generated from data/ids/registry.csv by tools/check_ids.py --write.
 * Do not edit: edit the registry and run the tool. Licence: GPL-3.0-or-later. */
#ifndef MHUC_IDS_H
#define MHUC_IDS_H

/* MH4U's own monster ids are 0 to 123; a ported monster takes
 * 124 and up. 255 is the most a guild quest card's
 * one-byte id can hold (docs/decisions.md#0003-id-allocation-and-mod-saves). */
#define MHUC_MONSTER_FIRST 124
#define MHUC_MONSTER_LAST 255

/* One ported monster: the id it takes, and the MH4U monster id whose rows the
 * reader hooks answer with until the port ships this monster's own rows. */
typedef struct MhucMonsterId {
    unsigned char id;
    unsigned char stand_in;
} MhucMonsterId;

#define MHUC_MONSTER_COUNT 2
static const MhucMonsterId mhuc_monster_ids[MHUC_MONSTER_COUNT] = {
    {124, 1},
    {125, 1},
};

/* Rathian, mhxx em001 */
#define MHUC_MONSTER_ID_RATHIAN_GU 124
/* Rathian, mh3u em001 */
#define MHUC_MONSTER_ID_RATHIAN_3U 125

#endif
