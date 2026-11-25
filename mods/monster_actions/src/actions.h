/* Generated from the per-id action-id map by reference/monster_handlers.py table.
 * Do not edit: edit reference/README.md's map and the per-id table, then run the tool.
 * Licence: GPL-3.0-or-later. */
#ifndef MHUC_ACTIONS_H
#define MHUC_ACTIONS_H

#include <stdint.h>

/* One translation for a ported monster: when the source game's AI asks for action
 * `category`/`index`, MH4U runs `target_category`/`target_index` instead. The target's
 * MH4U handler has the same body as the source's (reference/README.md records the
 * proof). `index` is 0xff for a category-only action: any index byte matches it. */
typedef struct MhucAction {
    uint8_t category;
    uint8_t index;
    uint8_t target_category;
    uint8_t target_index;
} MhucAction;

/* One ported monster's translations, keyed by its MH4U id (data/ids/registry.csv). */
typedef struct MhucPortedActions {
    uint8_t id;
    uint16_t entry_count;
    const MhucAction *entries;
} MhucPortedActions;

/* The index byte a category-only action's entry holds: any index matches it. */
#define MHUC_ACTION_NO_INDEX 0xff

/* Rathian, ported from mhxx em001 (rathian-gu, id 124): no entry: every action id her port keeps is shared with MH4U and runs MH4U's handler as it is (check R2). */
static const MhucAction *const mhuc_actions_124 = NULL;

/* Rathian, ported from mh3u em001 (rathian-3u, id 125): 16 action ids MH4U lacks, each sent to the shared MH4U action whose handler has the same body (reference/README.md). */
static const MhucAction mhuc_actions_125[] = {
    {0, 4, 0, 0},
    {7, 64, 7, 35},
    {7, 87, 7, 92},
    {7, 93, 7, 92},
    {10, 0, 10, 7},
    {10, 1, 10, 7},
    {10, 2, 10, 7},
    {10, 3, 10, 7},
    {10, 4, 10, 7},
    {10, 5, 10, 7},
    {10, 6, 10, 7},
    {11, 5, 11, 0},
    {11, 15, 11, 0},
    {11, 26, 11, 0},
    {11, 28, 11, 0},
    {13, 9, 0, 3},
};

/* Giadrome, ported from mhxx em034 (giadrome-gu, id 126): no entry: no action-id map is recorded for it yet. */
static const MhucAction *const mhuc_actions_126 = NULL;

/* Great Wroggi, ported from mh3u em045 (great-wroggi-3u, id 127): no entry: no action-id map is recorded for it yet. */
static const MhucAction *const mhuc_actions_127 = NULL;

#define MHUC_PORTED_ACTIONS_COUNT 4
static const MhucPortedActions mhuc_ported_actions[MHUC_PORTED_ACTIONS_COUNT] = {
    {124, 0, mhuc_actions_124},
    {125, 16, mhuc_actions_125},
    {126, 0, mhuc_actions_126},
    {127, 0, mhuc_actions_127},
};

#endif
