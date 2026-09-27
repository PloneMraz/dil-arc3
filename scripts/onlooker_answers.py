"""How the learning mind answered the onlooker, read from a run's store and [event] log.

    python scripts/onlooker_answers.py scripts/data/<run>

Read back from the store alone, as a third party would. Works on stores written
before the remark struck the mind (objections as acts at `here`) and after (as
[state, act] pairs, lifted when the onlooker says something else).

  A  the move the body carried out in a cycle whose remark objected to an act at
     the state it stood in: was it that act?
  B  choices made while an objection stood, at a state it holds for: how many
     took the act objected to, and how many of those said there was no other way
  C  answers (the thoughts written on a remark) scarred: said again after them
  D  the onlooker's collisions, and cycles in which the mind commanded twice
"""

from __future__ import annotations

import glob
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path


def said_of(remark: dict | None) -> tuple | None:
    if not remark or not remark.get("remark"):
        return None
    named = [remark.get("act")] if remark.get("act") else list(remark.get("acts") or [])
    return (remark["remark"], *sorted(str(n.get("act")) for n in named if isinstance(n, dict)))


def main(run: Path) -> None:
    db = sqlite3.connect(run / "store" / "memory" / "data.sqlite")
    thoughts, choices = [], []
    for k, v in db.execute("select k, v from data"):
        d = json.loads(v)
        p, o = d.get("payload"), d.get("open", {})
        if not isinstance(p, dict):
            continue
        cycle = d["fixed"]["cycleMark"]
        if o.get("kind") == "thought" and p.get("on") == "onlooker":
            thoughts.append((cycle, k, p))
        elif o.get("kind") == "choice":
            choices.append((cycle, k, p))
    thoughts.sort(key=lambda x: x[0])
    choices.sort(key=lambda x: x[0])

    moves: dict[int, tuple] = {}
    tests_per_cycle: Counter = Counter()
    moved: dict[str, list[tuple[str, str]]] = defaultdict(list)
    onlooker_scars = 0
    for f in sorted(glob.glob(str(run / "store" / "event-log" / "*.jsonl"))):
        for line in open(f):
            r = json.loads(line)["record"]
            form = r.get("form")
            if form == "emission":
                a = r.get("action") or {}
                if r.get("issuingLayer") == 8 and a.get("kind") == "move":
                    moves[r["cycleMark"]] = (a.get("actionId"), a.get("x"), a.get("y"))
                if r.get("issuingLayer") == 5 and a.get("kind") == "test":
                    tests_per_cycle[r["cycleMark"]] += 1
            elif form == "provenance":
                moved[r["datumId"]].append((r["from"], r["to"]))
            elif form == "scar" and (r.get("open") or {}).get("source") == "onlooker":
                onlooker_scars += 1

    def pairs(p: dict) -> list[tuple[str, tuple]]:
        """Each objection as (state, act) — the act whole: an act that takes a
        place is objected to at that place, not everywhere."""
        out = []
        for item in p.get("objected") or []:
            if len(item) == 2 and isinstance(item[0], str):
                out.append((item[0], tuple(item[1])))      # [state, act]
            elif p.get("here") is not None:
                out.append((p["here"], tuple(item)))       # act, at here (before)
        return out

    # A
    a_total = a_same = 0
    for cycle, _, p in thoughts:
        objected_here = {act for state, act in pairs(p) if state == p.get("here")}
        if not objected_here or cycle not in moves:
            continue
        a_total += 1
        a_same += int(moves[cycle] in objected_here)

    # B: replay objections against choices, cycle by cycle
    live: dict[tuple, set[tuple[str, tuple]]] = {}
    lifting = any("lifted" in p for _, _, p in thoughts + choices) or any(
        len(i) == 2 and isinstance(i[0], str) for _, _, p in thoughts for i in p.get("objected") or [])
    ti = 0
    b_at = b_took = b_no_other = 0
    for cycle, _, c in choices:
        while ti < len(thoughts) and thoughts[ti][0] < cycle:
            p = thoughts[ti][2]
            s = said_of(p.get("remark"))
            if lifting:
                live = {k: v for k, v in live.items() if k == s}
            if s is not None:
                live.setdefault(s, set()).update(pairs(p))
            ti += 1
        if lifting:
            s = said_of(c.get("onlooker"))
            live = {k: v for k, v in live.items() if k == s}
        held = {(state, act) for v in live.values() for state, act in v}
        at_here = {act for state, act in held if state == c.get("here")}
        if not at_here or not c.get("chose"):
            continue
        b_at += 1
        if tuple(c["chose"]) in at_here:
            b_took += 1
            b_no_other += int("no other way" in (c.get("why") or "") or "objected" in (c.get("why") or ""))

    # C
    answers = [k for _, k, p in thoughts if p.get("objected")]
    scarred = sum(1 for k in answers if ("running", "scar") in moved.get(k, []))

    print(f"store: {run}")
    print(f"thoughts on the onlooker: {len(thoughts)}  (answers with an objection: {len(answers)})")
    print(f"A  body's move in the cycle of an objection was the act objected to: {a_same} of {a_total}")
    print(f"B  choices at a state an objection held for: {b_at}; took the objected act: {b_took}"
          f" (said so: {b_no_other})")
    print(f"C  answers scarred (said again after): {scarred} of {len(answers)}")
    print(f"D  onlooker collisions: {onlooker_scars}; cycles with two commands: "
          f"{sum(1 for n in tests_per_cycle.values() if n >= 2)}")
    why = Counter((c.get("why") or "").split(" (")[0] for _, _, c in choices)
    print("why it chose:", dict(why.most_common(8)))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
