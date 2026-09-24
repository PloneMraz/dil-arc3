"""Export the recorded transitions as plain JSON, readable without this code.

frames.pkl holds arc3 Frame objects, so reading it needs this repository on the
path. The JSON holds only what the world-model probe uses — the game, the action
id and the last grid of the frame before and after — so the probe can run on its
own, on a Kaggle GPU for one.

    python scripts/export_transitions.py [OUT.json]    # default: data/transitions.json
"""
from __future__ import annotations
from _paths import SRC, DATA  # noqa: E402 — see scripts/_paths.py

import json
import pickle
import sys

sys.path.insert(0, str(SRC))

out = DATA / "transitions.json" if len(sys.argv) < 2 else sys.argv[1]
rows = pickle.loads((DATA / "frames.pkl").read_bytes())
records = [
    {
        "game": gid.split("-")[0],
        "action": int(str(act).split("@")[0]),
        "coords": str(act).split("@")[1] if "@" in str(act) else None,
        "before": [list(r) for r in prev.grids[-1]],
        "after": [list(r) for r in now.grids[-1]],
    }
    for gid, act, prev, now in rows
]
with open(out, "w", encoding="utf-8") as f:
    json.dump(records, f, separators=(",", ":"))
print(f"{len(records)} transitions -> {out}")
