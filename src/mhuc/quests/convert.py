"""Convert an MHXX (GU-era) quest into an MH4U `.mib` model (docs/architecture.md#quests).

Input: one quest as `mhuc quest dump mhxx` prints it (the `.mib` and its `.sem`, `.esl`, `.rem` and supply
parts). Output: the JSON model `mhuc mib import` builds (src/mhuc/mibwrite.py).

What isn't converted comes from an MH4U template quest given by the user, and is listed in the result's
`placeholders`, never silently: rule 2 allows authoring only where no source exists, and every placeholder is
to be recorded in docs/sources.md#authored-register before anything ships. Every id goes through an id table
(data/idmap/mhxx-mh4u/*.csv); a quest with an id the tables don't map is refused, with every missing id listed,
rather than guessed.
"""
from __future__ import annotations

import csv
import os
import re

from . import mibwrite
from .quest import MIB4_LANGS, MIB4_TEXTS, QuestError

TABLES = ("monster", "map", "area", "item", "objective")
SEM_NAME = re.compile(r"b_m(\d+)em(\d+)_(\d+)")


class ConvertError(QuestError):
    pass


def load_tables(folder: str) -> dict[str, dict[str, str]]:
    """Each table maps a source key (text) to an MH4U value (text, an integer unless noted in the README)."""
    out = {}
    for name in TABLES:
        path = os.path.join(folder, f"{name}.csv")
        rows = {}
        if os.path.exists(path):
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("source", "").strip():
                        rows[row["source"].strip()] = row["target"].strip()
        out[name] = rows
    return out


class _Mapper:
    def __init__(self, tables):
        self.t, self.missing = tables, []

    def get(self, table: str, key: str) -> int:
        if key not in self.t[table]:
            self.missing.append(f"{table}:{key}")
            return 0
        return int(self.t[table][key], 0)


def convert_mhxx(parts: dict, template: dict, tables: dict, quest_id: int, texts: dict) -> dict:
    """`template` is an MH4U model JSON (`mhuc mib export`); `texts` maps each MH4U language (eng, fre, spa, ger,
    ita) to the 7 MH4U strings (title, success, failure, summary, main_monsters, client, sub_quest), taken from
    the source game's text (English from MHGU, rule 2). Returns the new model JSON with `placeholders`."""
    mib = parts.get("mib")
    if not mib:
        raise ConvertError("no rQuestData in the quest")
    m = _Mapper(tables)
    out = {k: v for k, v in template.items() if k != "placeholders"}
    fields = dict(template["fields"])
    xx_map = mib["map"]
    fields.update({
        "quest_id": quest_id,
        "time_min": mib["time_min"],
        "fee": mib["fee"],
        "reward": mib["reward"],
        "sub_reward": mib["sub_reward"],
        "map": m.get("map", str(xx_map)),
    })
    out["fields"] = fields
    placeholders = ["header bytes other than quest id, time, fee, rewards and map (template)",
                    f"stars (template): MH4U counts 1-3 Low, 4-7 High, 8-10 G (specs/quest.md 0xC2); MHXX's "
                    f"{mib['stars']} stars at rank {mib.get('rank')} need a decision on the scale",
                    "faint penalty, HR points, carve table, gathering rank, AI level, flags (template)",
                    "objectives (template): MHXX's objective types have no table yet",
                    "equipment presets (template)", "intruders (template)"]

    for lang in MIB4_LANGS:
        if lang not in texts or any(t not in texts[lang] for t in MIB4_TEXTS):
            raise ConvertError(f"texts: {lang} needs all of {', '.join(MIB4_TEXTS)}")
    out["texts"] = {lang: {t: texts[lang][t] for t in MIB4_TEXTS} for lang in MIB4_LANGS}

    # large monsters: one .sem per boss, its monster in the file name; waves by the .sem's round
    model_def = (template["waves"][0][0] if template["waves"] and template["waves"][0] else
                 {"monster": 0, "count": 1, "condition": 0, "area": 0, "frenzy": 0, "pos": [0.0, 0.0, 0.0],
                  "raw": ""})
    waves: dict[int, list] = {}
    for name, sem in sorted(parts.get("sem", {}).items()):
        hit = SEM_NAME.search(name)
        if not hit:
            continue
        em = f"em{int(hit.group(2)):03d}"
        d = dict(model_def)
        d.update({"monster": m.get("monster", em), "count": max(sem["count"], 1),
                  "area": m.get("area", f"{xx_map}:{sem['area']}"), "pos": list(sem["pos"])})
        waves.setdefault(sem["round"], []).append(d)
    if not waves:
        raise ConvertError("no boss placement (.sem) in the quest")
    out["waves"] = [waves[r] for r in sorted(waves)]
    placeholders.append("large monsters' bytes other than id, count, area and position (template definition)")

    # small monsters: each .esl area becomes an MH4U area list
    small = []
    for _, esl in sorted(parts.get("esl", {}).items()):
        for i, area in enumerate(esl):
            defs = []
            for e in area:
                d = dict(model_def)
                d.update({"monster": m.get("monster", f"small:{e['monster']}"), "count": 1,
                          "area": m.get("area", f"{xx_map}:esl{i}"), "pos": list(e["pos"])})
                defs.append(d)
            small.append(defs)
    out["small_areas"] = small or template["small_areas"]
    if not small:
        placeholders.append("small monsters (template: the quest has none)")

    # rewards: the first three .rem tables as main, extra and sub; slots are (item, count, chance)
    rems = [r for _, r in sorted(parts.get("rem", {}).items())]
    rewards = {}
    for name, rem in zip(("main", "extra", "sub"), rems, strict=False):
        items = [[chance, m.get("item", str(item)), count] for item, count, chance in rem["slots"] if item]
        if items:
            head = template["rewards"].get(name, template["rewards"].get("main", {"head": "00800000"}))["head"]
            rewards[name] = {"head": head, "items": items}
    out["rewards"] = rewards or template["rewards"]
    placeholders.append("which .rem table is MH4U's main, extra and sub reward is assumed by order, and each "
                        "slot is read as (item, count, chance)")

    supply = parts.get("supply")
    if supply:
        items = [[m.get("item", str(item)), count] for item, count, _ in supply if item]
        head = template["supply"][0]["head"] if template["supply"] else "00000000"
        out["supply"] = [{"head": head, "items": items}]

    if m.missing:
        raise ConvertError("ids the tables don't map: " + ", ".join(sorted(set(m.missing))))
    out["placeholders"] = placeholders
    mibwrite.model_from_json(out)  # it must build
    return out
