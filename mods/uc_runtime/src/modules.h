/* Generated from data/ids/registry.csv by tools/check_ids.py --write.
 * Do not edit: edit the registry and run the tool. Licence: GPL-3.0-or-later. */
#ifndef MHUC_MODULES_H
#define MHUC_MODULES_H

#include <stdint.h>

/* One ported monster in the runtime's table: the registry id, the registry key, and the
 * monster's C module (src/monsters/<key>.c, its interface in src/module.h).
 * tools/check_ids.py writes the row: `ops` is the module when that file exists, and 0
 * for a data-only port whose actions stay with the game. */
struct MhucModuleOps;
typedef struct MhucModule {
    uint32_t id;                      /* its registry id */
    const char *key;                  /* its registry key */
    const struct MhucModuleOps *ops;  /* its code, or 0 while it has none */
} MhucModule;

extern const struct MhucModuleOps mhuc_module_rathian_gu;
extern const struct MhucModuleOps mhuc_module_rathian_3u;

#define MHUC_MODULE_COUNT 4

static const MhucModule mhuc_modules[MHUC_MODULE_COUNT] = {
    {124, "rathian-gu", &mhuc_module_rathian_gu},  /* Rathian */
    {125, "rathian-3u", &mhuc_module_rathian_3u},  /* Rathian */
    {126, "giadrome-gu", 0},  /* Giadrome */
    {127, "great-wroggi-3u", 0},  /* Great Wroggi */
};

/* The module for `id`, or 0 when the id has none. */
static inline const MhucModule *mhuc_module_for(uint32_t id) {
    for (unsigned i = 0; i < MHUC_MODULE_COUNT; i++) {
        if (mhuc_modules[i].id == id) {
            return &mhuc_modules[i];
        }
    }
    return 0;
}

#endif
