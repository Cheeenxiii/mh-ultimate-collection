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

/* The kinds of file a ported id's resource record names. The record the plugin builds
 * rewrites the id token only in the paths of the kinds a port ships; the rest keep the
 * stand-in's path, because MH4U does not tolerate a missing file. */
#define MHUC_FILES_MODEL 0x0001u
#define MHUC_FILES_MOTIONS 0x0002u
#define MHUC_FILES_CAMERA 0x0004u
#define MHUC_FILES_TAIL 0x0008u
#define MHUC_FILES_MEF 0x0010u
#define MHUC_FILES_SOUND 0x0020u
#define MHUC_FILES_CMD 0x0040u
#define MHUC_FILES_EFL 0x0080u

#define MHUC_MOTION_SLOTS 6u
#define MHUC_MOTION_SLOT(slot) (1u << (slot))

/* One ported monster: the id it takes, the MH4U monster id whose rows the reader
 * hooks answer with until the port ships this monster's own rows, the motion-list slots
 * it ships (MHUC_MOTION_SLOT bits), and the kinds of file it ships (MHUC_FILES_* bits).
 * A slot or kind it does not ship keeps the stand-in's path. */
typedef struct MhucMonsterId {
    uint32_t id;
    unsigned char stand_in;
    unsigned char motion_mask;
    unsigned short files;
} MhucMonsterId;

/* The permanent ids, consecutive from 124. */
#define MHUC_MONSTER_COUNT 4
static const MhucMonsterId mhuc_monster_ids[MHUC_MONSTER_COUNT] = {
    {124, 1, 0x1fu, /* slots 0, 1, 2, 3, 4 */ MHUC_FILES_MODEL | MHUC_FILES_MOTIONS | MHUC_FILES_TAIL | MHUC_FILES_CMD},
    {125, 1, 0x07u, /* slots 0, 1, 2 */ MHUC_FILES_MODEL | MHUC_FILES_MOTIONS | MHUC_FILES_TAIL | MHUC_FILES_SOUND},
    {126, 15, 0x1du, /* slots 0, 2, 3, 4 */ MHUC_FILES_MODEL | MHUC_FILES_MOTIONS},
    {127, 15, 0x07u, /* slots 0, 1, 2 */ MHUC_FILES_MODEL | MHUC_FILES_MOTIONS},
};

/* The pooled ids: each is lent one byte of 224 to 255 for a quest that names it. */
#define MHUC_POOLED_MONSTER_COUNT 0
/* Empty: a dummy entry keeps the array valid C. */
static const MhucMonsterId mhuc_pooled_monster_ids[1] = {{0, 0, 0, 0}};

/* Rathian, mhxx em001 */
#define MHUC_MONSTER_ID_RATHIAN_GU 124
/* Rathian, mh3u em001 */
#define MHUC_MONSTER_ID_RATHIAN_3U 125
/* Giadrome, mhxx em034 */
#define MHUC_MONSTER_ID_GIADROME_GU 126
/* Great Wroggi, mh3u em045 */
#define MHUC_MONSTER_ID_GREAT_WROGGI_3U 127

#endif
