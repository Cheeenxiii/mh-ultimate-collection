/* Generated from data/ids/registry.csv by tools/check_ids.py --write.
 * Do not edit: edit the registry and run the tool. Licence: GPL-3.0-or-later. */
#ifndef MHUC_IDS_H
#define MHUC_IDS_H

#include <stdint.h>

/* MH4U's own monster ids are 0 to 123. A ported monster takes
 * 124 and up: 124 to 223 are permanent, and a
 * monster registered from 256 up is lent a free byte from
 * 224 to 255 for each quest that names it
 * (docs/decisions.md#0003-id-allocation-and-mod-saves). */
#define MHUC_MONSTER_FIRST 124
#define MHUC_MONSTER_LAST 223
#define MHUC_MONSTER_POOL_FIRST 224
#define MHUC_MONSTER_POOL_LAST 255
#define MHUC_MONSTER_POOL_SIZE 32
#define MHUC_REGISTRY_POOL_FIRST 256

/* One ported monster: the id it takes, and the MH4U monster id whose rows the
 * reader hooks answer with until the port ships this monster's own rows. */
typedef struct MhucMonsterId {
    uint32_t id;
    unsigned char stand_in;
} MhucMonsterId;

/* The permanent ids, consecutive from 124. */
#define MHUC_MONSTER_COUNT 2
static const MhucMonsterId mhuc_monster_ids[MHUC_MONSTER_COUNT] = {
    {124, 1},
    {125, 1},
};

/* The pooled ids: each is lent one byte of 224 to 255 for a quest that names it. */
#define MHUC_POOLED_MONSTER_COUNT 0
/* Empty: a dummy entry keeps the array valid C. */
static const MhucMonsterId mhuc_pooled_monster_ids[1] = {{0, 0}};

/* Rathian, mhxx em001 */
#define MHUC_MONSTER_ID_RATHIAN_GU 124
/* Rathian, mh3u em001 */
#define MHUC_MONSTER_ID_RATHIAN_3U 125

#endif
