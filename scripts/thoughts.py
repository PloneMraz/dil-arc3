"""Whether what turned a choice can be read back, from one game's store alone
(`[event]` and `[data]`; nothing from the run's report).

    python scripts/thoughts.py STORE_DIR

STORE_DIR is a game's store (the folder holding `store/event-log` and
`store/memory/data.sqlite`). It counts:

- the thoughts written, by what they were on and what they did;
- the choices whose `why` says a collision turned them, and of those how many
  have a turning thought written before them, how many are built from the return
  that thought was built from, and how many name the thought's own id;
- the turned choices built from neither, with the choice and thought around them;
- the choices whose `why` names an objection, and whether an objecting thought
  came before;
- the returns scarred, and how many a thought was built from.
"""

from __future__ import annotations

import glob
import json
import re
import sqlite3
import sys
from collections import Counter


def main(root: str) -> None:
    store = root.rstrip("/") + "/store"
    built: dict[str, list] = {}
    scars: set[str] = set()
    for f in sorted(glob.glob(store + "/event-log/*.jsonl")):
        for line in open(f):
            r = json.loads(line)["record"]
            if r.get("form") == "scar" and r.get("datumId", "").startswith("signal-"):
                scars.add(r["datumId"])
            for w in (r.get("activity") or {}).get("written", []):
                built[w["datumId"]] = w.get("builtFrom", [])
    con = sqlite3.connect(store + "/memory/data.sqlite")
    data = {k: json.loads(v) for k, v in con.execute("SELECT k, v FROM data")}

    def kind(k: str) -> str | None:
        return (data[k].get("open") or {}).get("kind")

    def num(k: str) -> tuple[int, int]:
        m = re.match(r"written-(\d+)-(\d+)", k)
        return (int(m[1]), int(m[2])) if m else (10 ** 9, 0)

    def what(p: dict) -> str:
        return p.get("collided") or next((w for w in ("objected", "kept_on", "lifted") if p.get(w)), "other")

    thoughts = sorted((k for k in data if kind(k) == "thought"), key=num)
    choices = sorted((k for k in data if kind(k) == "choice"), key=num)
    print("thoughts:", len(thoughts), dict(Counter((data[k]["payload"].get("on"), what(data[k]["payload"])) for k in thoughts)))

    turning = [k for k in thoughts if data[k]["payload"].get("turns", "").startswith(("from", "to"))]
    turned = [k for k in choices if "; turned " in data[k]["payload"].get("why", "")]
    before = by_source = by_id = 0
    unnamed = []
    for c in turned:
        prior = [t for t in turning if num(t) <= num(c)]
        if not prior:
            continue
        before += 1
        t = prior[-1]
        source = bool(set(built.get(t, [])) & set(built.get(c, [])))
        by_source += source
        by_id += t in built.get(c, [])
        if not source and t not in built.get(c, []):
            unnamed.append((c, t, sum(1 for x in choices if num(t) < num(x) < num(c))))
    print(f"turned choices: {len(turned)}; a turning thought before: {before}; "
          f"built from the return it was built from: {by_source}; naming the thought's id: {by_id}")
    for c, t, between in unnamed:
        print(f"  built from neither: {c} (step {data[c]['payload']['step']}), thought {t}, "
              f"{between} choice(s) between them")

    objecting = [k for k in thoughts if data[k]["payload"].get("objected")]
    named = [k for k in choices if "objected" in data[k]["payload"].get("why", "")]
    print(f"choices naming an objection: {len(named)}; an objecting thought before: "
          f"{sum(1 for c in named if any(num(t) <= num(c) for t in objecting))}")
    sources = {s for t in thoughts for s in built.get(t, [])}
    print(f"returns scarred: {len(scars)}; a thought built from them: {len(scars & sources)}")


if __name__ == "__main__":
    main(sys.argv[1])
