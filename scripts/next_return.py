"""How often the next return comes as expected, after a chain and otherwise: the
base rates a chain's count is read against (Plone, 2026-11-04). From the stores
alone, as `chains.py` reads them.

    python scripts/next_return.py STORE_DIR [STORE_DIR ...]

For each frame the region returned in cycle c, whether the frame of cycle c + 1
collided (`chains.py`'s "the next return met as expected" counts the same way,
a cycle with no frame as not collided; here only cycles with a frame count).
The frames are grouped by what c's frame was: a chain's scar (a thought and a
turned choice built from it in its cycle), another frame scar, or a frame that
came as expected; each group also by whether c + 1's expectation of the frame
was held by a datum of memory (`heldBy`: a hypothesis or experiences) or by none
(the region expected otherwise than it was).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chains import chains, load  # noqa: E402


def expected_of(records) -> dict[int, str]:
    """Whether each cycle's expectation of the frame was held by memory: `held` or `none`."""
    return {r["cycleMark"]: "held" if r.get("heldBy") else "none" for r in records
            if r.get("form") == "expectation" and r.get("entity") == "frame"}


def tally(records, data) -> Counter:
    frames = {r["cycleMark"] for r in records if r.get("form") == "cycle-seal"
              for a in r["activity"].get("admitted", []) if a["open"].get("kind") == "frame"}
    scarred = {r["cycleMark"] for r in records if r.get("form") == "scar"
               and str(r.get("datumId", "")).startswith("signal-") and r["datumId"].endswith("-0")}
    chained = {c["cycle"] for c in chains(records, data)}
    expected = expected_of(records)
    out: Counter = Counter()
    for c in sorted(frames):
        if c + 1 not in frames:
            out["no frame next"] += 1
            continue
        group = "chain" if c in chained else "other scar" if c in scarred else "as expected"
        nxt = expected.get(c + 1, "?")
        for g in (group, "all"):
            out[(g, "n")] += 1
            out[(g, "came as expected")] += c + 1 not in scarred
            out[(g, nxt, "n")] += 1
            out[(g, nxt, "came as expected")] += c + 1 not in scarred
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("stores", type=Path, nargs="+")
    a = ap.parse_args()
    total: Counter = Counter()
    for store in a.stores:
        check, records, data = load(store)
        if not check.ok:
            print(f"{store.name}: hash chain BROKEN, left out")
            continue
        found = tally(records, data)
        total += found
        print(f"{store.name}: chains {found[('chain', 'n')]}, next as expected {found[('chain', 'came as expected')]}",
              flush=True)
    print(f"cycles whose next cycle has no frame: {total['no frame next']}")
    for g in ("chain", "other scar", "as expected", "all"):
        n, ok = total[(g, "n")], total[(g, "came as expected")]
        parts = [f"{g}: {ok} of {n}" + (f" ({ok / n:.1%})" if n else "")]
        for e in ("held", "none"):
            en, eok = total[(g, e, "n")], total[(g, e, "came as expected")]
            if en:
                parts.append(f"next held by {'memory' if e == 'held' else 'none'}: {eok} of {en} ({eok / en:.1%})")
        print("; ".join(parts))


if __name__ == "__main__":
    main()
