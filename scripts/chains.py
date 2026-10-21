"""Find, in one game's store, the chains a reader can check (paper/OUTLINE.md):
a ResistEvent → the behaviour changed → the expectation revised → the next
ResistEvent otherwise. From the store alone: `[event]` (its hash chain verified
first) and `[data]`; nothing from the run's report.

    python scripts/chains.py STORE_DIR [--show N]

STORE_DIR is a game's store (the folder holding `store/event-log` and
`store/memory/data.sqlite`). Each link is a record the reader finds by its id:

1. the scar of a frame's return (`form: scar`, its `datumId`), and what was
   expected of it — that the region would be otherwise, or a state foreseen;
2. the thought the collision set off (`kind: thought`, built from that return);
3. the choice it turned (`kind: choice`, built from that return, its `why`
   saying how it turned);
4. what the mind expects of that act there from then on: the experience of it
   (`kind: experience`, from where, by what act), and each later cycle it was met
   again (its revisions) — whether the frame then collided or came as expected;
5. the next collision after it: which act, and what had been expected.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dil.store.event_sink import read_jsonl_sink, verify_jsonl_sink  # noqa: E402


def load(store: Path):
    log = store / "store" / "event-log"
    check = verify_jsonl_sink(log)
    records = read_jsonl_sink(log)
    con = sqlite3.connect(store / "store" / "memory" / "data.sqlite")
    data = {k: json.loads(v) for k, v in con.execute("SELECT k, v FROM data")}
    return check, records, data


def frame_of(cycle: int) -> str:
    return f"signal-{cycle}-0"


def chains(records, data):
    """Every chain that starts at a frame's scar and has a thought and a turned
    choice built from it, with the links it has."""
    scars = {r["datumId"]: r for r in records if r.get("form") == "scar" and r.get("datumId", "").endswith("-0")
             and str(r.get("datumId", "")).startswith("signal-")}
    # Each datum by the cycle it entered in, and all it was built from: a datum the
    # mind relinked (`built_after`) is written again, cycles later, built from what
    # it was and the ids that came back since.
    written: dict[str, dict] = {}
    for r in records:
        if r.get("form") == "cycle-seal":
            for w in r["activity"].get("written", []):
                entry = written.setdefault(w["datumId"], {"cycle": r["cycleMark"], "kind": w["open"].get("kind"),
                                                          "built": []})
                entry["built"] += [b for b in (w.get("builtFrom") or []) if b not in entry["built"]]
    by_source: dict[str, list[str]] = {}
    for d, w in written.items():
        for b in w["built"]:
            by_source.setdefault(b, []).append(d)
    revisions: dict[str, list[int]] = {}
    for r in records:
        if r.get("form") == "revision":
            revisions.setdefault(r["datumId"], []).append(r["cycleMark"])
    out = []
    for sid, scar in sorted(scars.items(), key=lambda kv: kv[1]["cycleMark"]):
        cycle = scar["cycleMark"]
        # What the collision set off is written in its own cycle (a later choice
        # may name the return too, among all it read).
        made = [d for d in by_source.get(sid, []) if written[d]["cycle"] == scar["cycleMark"]]
        thought = next((d for d in made if written[d]["kind"] == "thought"), None)
        choice = next((d for d in made if written[d]["kind"] == "choice"
                       and "turned" in str((data.get(d) or {}).get("payload", {}).get("why", ""))), None)
        if thought is None or choice is None:
            continue
        experience = next((d for d in made if written[d]["kind"] == "experience"), None)
        said = (data.get(thought) or {}).get("payload", {})
        if experience is None:
            # Written later (once the step's report came): found by where and by what act.
            experience = next((d for d, w in written.items() if w["kind"] == "experience"
                               and (data.get(d) or {}).get("payload", {}).get("from") == said.get("here")
                               and (data.get(d) or {}).get("payload", {}).get("act") == said.get("act")), None)
        met_again = [r for r in revisions.get(experience, []) if r > cycle + 1] if experience else []
        expected = (scar.get("event") or {}).get("expected") or {}
        otherwise = isinstance(expected.get("value"), dict) and bool(expected["value"].get("otherwise"))
        nxt = frame_of(cycle + 1)
        later = next((s for s in sorted(scars.values(), key=lambda r: r["cycleMark"]) if s["cycleMark"] > cycle), None)
        out.append({
            "scar": sid, "cycle": cycle, "expected": "otherwise" if otherwise else "a state foreseen",
            "thought": thought, "thought_says": (data.get(thought) or {}).get("payload", {}),
            "choice": choice, "choice_says": {k: (data.get(choice) or {}).get("payload", {}).get(k)
                                              for k in ("chose", "why")},
            "experience": experience,
            "experience_says": {k: (data.get(experience) or {}).get("payload", {}).get(k)
                                for k in ("act", "seen", "changed", "supports", "fails")} if experience else None,
            "experience_met_again_at": met_again,
            "met_again_collided": [r for r in met_again if frame_of(r) in scars],
            "next": nxt, "next_collided": nxt in scars,
            "next_expected": ("otherwise" if isinstance(((scars.get(nxt) or {}).get("event") or {}).get("expected", {})
                                                       .get("value"), dict)
                              and scars[nxt]["event"]["expected"]["value"].get("otherwise") else
                              "a state foreseen") if nxt in scars else None,
            "next_collision": later["datumId"] if later else None,
            "next_collision_act": ((later.get("event") or {}).get("received") or {}).get("value", {}).get("move")
            if later else None,
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("store", type=Path)
    ap.add_argument("--show", type=int, default=1)
    a = ap.parse_args()
    check, records, data = load(a.store)
    print(f"[event]: {check.count} records, hash chain {'verified' if check.ok else 'BROKEN'}")
    scars = sum(1 for r in records if r.get("form") == "scar" and str(r.get("datumId", "")).startswith("signal-")
                and r["datumId"].endswith("-0"))
    found = chains(records, data)
    print(f"frame scars: {scars}; chains (scar → thought → turned choice): {len(found)}; "
          f"of them the next return met as expected: {sum(not c['next_collided'] for c in found)}; "
          f"with the act met again where it collided: {sum(bool(c['experience_met_again_at']) for c in found)}, "
          f"then met as expected every time: "
          f"{sum(bool(c['experience_met_again_at']) and not c['met_again_collided'] for c in found)}")
    for c in found[:a.show]:
        print(json.dumps(c, indent=1, default=str))


if __name__ == "__main__":
    main()
