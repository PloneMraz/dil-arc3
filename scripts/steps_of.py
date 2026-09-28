"""The steps a run took, read back from its store: (cycle, grid before, act, grid after).

    from steps_of import steps_of
    for cycle, before, act, after in steps_of("scripts/data/<run>"): ...

Read from the frame signals in `[data]` alone, as a third party would: each frame
carries the grid stack before the move, the stack after, and the move. The last
grid of each stack is the one the mind sees.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def steps_of(run: str | Path):
    db = sqlite3.connect(Path(run) / "store" / "memory" / "data.sqlite")
    out = []
    for _, v in db.execute("select k, v from data"):
        d = json.loads(v)
        if d.get("open", {}).get("kind") != "frame":
            continue
        p = d["payload"]
        if not p.get("before") or not p.get("grids"):
            continue
        m = p.get("move") or {}
        out.append((d["fixed"]["cycleMark"], p["before"][-1], (m.get("actionId"), m.get("x"), m.get("y")),
                    p["grids"][-1]))
    out.sort(key=lambda s: s[0])
    return out
