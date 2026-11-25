/* Generated from data/ids/registry.csv by tools/check_ids.py --write.
 * Do not edit: edit the registry and run the tool. Licence: GPL-3.0-or-later. */
#ifndef MHUC_IDS_H
#define MHUC_IDS_H

/* MH4U's own monster ids are 0 to 123; a ported monster takes
 * 124 and up. 255 is the most a guild quest card's
 * one-byte id can hold (docs/decisions.md#0003-id-allocation-and-mod-saves). */
#define MHUC_MONSTER_FIRST 124
#define MHUC_MONSTER_LAST 255

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

/* One ported monster: the id it takes, the MH4U monster id whose rows the reader
 * hooks answer with until the port ships this monster's own rows, the number of
 * motion-list slots it ships from slot 0, and the kinds of file it ships
 * (MHUC_FILES_* bits). */
typedef struct MhucMonsterId {
    unsigned char id;
    unsigned char stand_in;
    unsigned char motions;
    unsigned short files;
} MhucMonsterId;

#define MHUC_MONSTER_COUNT 2
static const MhucMonsterId mhuc_monster_ids[MHUC_MONSTER_COUNT] = {
    {124, 1, 5, MHUC_FILES_MODEL | MHUC_FILES_MOTIONS | MHUC_FILES_TAIL | MHUC_FILES_CMD},
    {125, 1, 3, MHUC_FILES_MODEL | MHUC_FILES_MOTIONS | MHUC_FILES_TAIL | MHUC_FILES_CMD},
};

/* Rathian, mhxx em001 */
#define MHUC_MONSTER_ID_RATHIAN_GU 124
/* Rathian, mh3u em001 */
#define MHUC_MONSTER_ID_RATHIAN_3U 125

#endif
