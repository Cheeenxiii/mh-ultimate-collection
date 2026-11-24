"""Monster ids to names, inferred from quests and the wiki's quest pages (check Q22 in specs/quest.md).

Each quest gives a set of large-monster ids (its waves) and the wiki's page for it a set of monster names (its
"<game> <monster> Quests" categories). An id's candidates are the names common to every quest it appears in;
names already taken by other ids are then struck out until nothing changes. What comes out is the maintainer's
own working table, written outside the repository (CLAUDE.md, rule 1): it is derived from the game's files.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request

API = "https://monsterhunterwiki.org/api.php"


def infer(observations: list[tuple[set[int], set[str]]]) -> dict[int, list[str]]:
    """observations: (ids, names) per quest. Returns each id's remaining candidates, sorted."""
    cand: dict[int, set[str]] = {}
    for ids, names in observations:
        for i in ids:
            cand[i] = cand[i] & names if i in cand else set(names)
    changed = True
    while changed:
        changed = False
        fixed = {i: next(iter(c)) for i, c in cand.items() if len(c) == 1}
        for i, c in cand.items():
            if len(c) > 1:
                n = c - {v for j, v in fixed.items() if j != i}
                if n and n != c:
                    cand[i], changed = n, True
        for ids, names in observations:
            open_ids = [i for i in ids if len(cand[i]) != 1]
            rest = names - {next(iter(cand[i])) for i in ids if len(cand[i]) == 1}
            if len(open_ids) == 1 and len(rest) == 1 and cand[open_ids[0]] != rest:
                cand[open_ids[0]], changed = set(rest), True
    return {i: sorted(c) for i, c in sorted(cand.items())}


def categories(wikitext: str, game: str, known: set[str]) -> set[str]:
    """The monster names among a quest page's "<game> <name> Quests" categories."""
    return {c for c in re.findall(rf"\[\[Category:{re.escape(game)} (.+?) Quests\]\]", wikitext) if c in known}


def fetch_page(title: str, cache_dir: str, pause: float = 0.4) -> str:
    """A wiki page's wikitext, cached in cache_dir (outside the repository); '' if it doesn't exist."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, re.sub(r"[^A-Za-z0-9._-]", "_", title) + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)["text"]
    query = urllib.parse.urlencode({"action": "parse", "page": title, "prop": "wikitext", "format": "json",
                                    "redirects": 1})
    req = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": "mhuc/0.1 (format documentation)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    text = data["parse"]["wikitext"]["*"] if "parse" in data else ""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"text": text}, f)
    time.sleep(pause)
    return text
