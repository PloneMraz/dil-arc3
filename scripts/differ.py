"""Two individuals of the same DIL on the same game, read from their stores alone:
where they first chose otherwise, what each read of the field there and why it
chose, and how far apart they went — the field each lived in, what it expected,
what it thought on, what it did.

    python scripts/differ.py STORE_A STORE_B [--around N]

Each STORE is a game's store folder (holding `store/event-log` and
`store/memory/data.sqlite`). Every number is read from `[data]` (the choices,
thoughts and experiences the mind wrote) and `[event]` (the scars), each log's
hash chain verified first.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dil.store.event_sink import read_jsonl_sink, verify_jsonl_sink  # noqa: E402

AXES = ("trust", "alertness", "exploration")


def read(store: Path) -> dict:
    log = store / "store" / "event-log"
    check = verify_jsonl_sink(log)
    records = read_jsonl_sink(log)
    con = sqlite3.connect(store / "store" / "memory" / "data.sqlite")
    data = [json.loads(v) for (v,) in con.execute("SELECT v FROM data")]
    of = lambda kind: [d.get("payload") or {} for d in data if (d.get("open") or {}).get("kind") == kind]
    choices = {}
    for c in sorted(of("choice"), key=lambda c: c.get("step", 0)):
        choices[c.get("step")] = c                    # the last of a step is the one carried out
    return {
        "chain": check.ok, "records": check.count, "choices": choices, "thoughts": of("thought"),
        "experiences": of("experience"),
        "frame_scars": sum(1 for r in records if r.get("form") == "scar"
                           and str(r.get("datumId", "")).startswith("signal-") and r["datumId"].endswith("-0")),
    }


def why(c: dict) -> str:
    return (c.get("why") or "").split(" (")[0]


def summary(name: str, s: dict) -> None:
    cs = list(s["choices"].values())
    fields = [c["field"] for c in cs if c.get("field")]
    mean = {a: round(sum(f[a] for f in fields) / len(fields), 3) for a in AXES} if fields else {}
    levels = sum(e.get("reached", 0) for e in s["experiences"])
    whys = Counter(why(c).split(";")[0] for c in cs)
    turns = sum(1 for c in cs if "turned" in (c.get("why") or ""))
    print(f"{name}: [event] {s['records']} records, chain {'verified' if s['chain'] else 'BROKEN'}")
    print(f"  field (mean read)   : {mean}")
    print(f"  choices {len(cs)}, turned by a collision {turns}; thoughts {len(s['thoughts'])}; "
          f"frame scars {s['frame_scars']}; aim reached {levels}")
    print(f"  why it chose        : {dict(whys.most_common(5))}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--around", type=int, default=2, help="choices shown before the first difference")
    o = ap.parse_args()
    a, b = read(o.a), read(o.b)
    summary("A", a)
    summary("B", b)
    steps = sorted(set(a["choices"]) & set(b["choices"]))
    first = next((t for t in steps if a["choices"][t].get("chose") != b["choices"][t].get("chose")), None)
    if first is None:
        print("\nthe same choice at every step both made")
        return
    same = sum(1 for t in steps if a["choices"][t].get("chose") == b["choices"][t].get("chose"))
    print(f"\nfirst chose otherwise at step {first}; the same choice at {same} of {len(steps)} steps")
    for t in [s for s in steps if first - o.around <= s <= first]:
        for name, s in (("A", a), ("B", b)):
            c = s["choices"][t]
            print(f"  step {t:4} {name}: chose {c.get('chose')}  field {c.get('field')}  — {c.get('why')}")
            for key in ("onlooker", "supersedes", "lifted"):
                if c.get(key):
                    print(f"             {key}: {json.dumps(c[key])}")


if __name__ == "__main__":
    main()
