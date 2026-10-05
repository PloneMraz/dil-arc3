"""Why the situations a run met grew as they did, read from its stores.

    python scripts/situations.py STORES_DIR RUN_DIR [GAME ...]

STORES_DIR holds `store-<game>-*/store/memory/data.sqlite` (a Save & Run's
`stores.tar.gz`, unpacked); RUN_DIR its `run-<game>-*.txt` reports, which say the
clock the mind found. For each game, the grids it reached in order (the last of
each frame's stack), read off that clock:

- situations: how many grids were met that differ off the clock;
- one line more: the row or column whose masking as well cuts them most — a
  counter the clock rules did not take, if it cuts many;
- hottest cells: masking the 8 / 32 / 128 cells most often among those that
  made a grid new (against the nearest grid met before) — what the acts move,
  where no line does it;
- steady cells: cells changing in a quarter of the steps that changed anything,
  under every act taken ten times or more — a counter or animation by the cell,
  as against what one act moves (a bar that moves on is not one: each of its
  cells changes once).

Reads only; needs numpy (the starter kit's interpreter has it).
"""
from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import sys

import numpy as np


def clock_of(run_dir: str, game: str) -> tuple[list[int], list[int]]:
    text = open(glob.glob(f"{run_dir}/run-{game}-*.txt")[0]).read()
    m = re.search(r"clock rows \[([^\]]*)\], columns \[([^\]]*)\]", text)
    return ([int(x) for x in m.group(1).split(",") if x.strip()],
            [int(x) for x in m.group(2).split(",") if x.strip()])


def frames(db: str) -> list[dict]:
    con = sqlite3.connect(db)
    out = []
    for k, v in con.execute("SELECT k, v FROM data WHERE k LIKE 'signal-%'"):
        p = json.loads(v)["payload"]
        if isinstance(p, dict) and p.get("grids") and "before" in p:
            out.append((int(k.split("-")[1]), p))
    return [p for _, p in sorted(out, key=lambda kp: kp[0])]


def game_report(db: str, run_dir: str, game: str) -> str:
    rows, cols = clock_of(run_dir, game)
    fs = frames(db)
    H, W = np.array(fs[0]["grids"][-1]).shape
    grids = np.stack([g for g in (np.array(p["grids"][-1]) for p in fs) if g.shape == (H, W)])
    mask = np.ones((H, W), bool)
    mask[rows, :] = False
    for c in cols:
        mask[:, c] = False

    def count(m: np.ndarray) -> int:
        return len({(g * m).tobytes() for g in grids})

    n = count(mask)
    lines = []
    for r in set(range(H)) - set(rows):
        m = mask.copy(); m[r, :] = False; lines.append((count(m), f"row {r}"))
    for c in set(range(W)) - set(cols):
        m = mask.copy(); m[:, c] = False; lines.append((count(m), f"col {c}"))
    k, line = min(lines)

    seen, keys, hot = [], set(), np.zeros((H, W), int)
    for g in grids:
        key = (g * mask).tobytes()
        if key not in keys:
            if seen:
                stack = np.stack(seen)
                hot += (stack[int(((stack != g) & mask).sum(axis=(1, 2)).argmin())] != g) & mask
            keys.add(key); seen.append(g)
    order = np.argsort(-hot, axis=None)
    hottest = []
    for K in (8, 32, 128):
        m = mask.copy(); m.flat[order[:K]] = False; hottest.append(count(m))

    changed, acts = [], []
    for p in fs:
        if p["before"]:
            b, g = np.array(p["before"][-1]), np.array(p["grids"][-1])
            if b.shape == g.shape == (H, W):
                changed.append((b != g) & mask); acts.append(p["move"]["actionId"])
    changed, acts = np.stack(changed), np.array(acts)
    moved = changed.any(axis=(1, 2))
    kinds = [a for a in np.unique(acts) if a != 0 and ((acts == a) & moved).sum() >= 10]
    steady = (np.stack([changed[(acts == a) & moved].mean(axis=0) for a in kinds]).min(axis=0) >= 0.25).sum() \
        if kinds else 0
    return (f"{game}: {n} situations (clock rows {rows}, columns {cols}); one line more: {line} -> {k} "
            f"({100 * (n - k) // max(n, 1)}%); hottest 8/32/128 cells -> {'/'.join(map(str, hottest))}; "
            f"steady cells {int(steady)} (acts {[int(a) for a in kinds]})")


def main() -> None:
    stores, run_dir, games = sys.argv[1], sys.argv[2], set(sys.argv[3:])
    for db in sorted(glob.glob(f"{stores}/store-*/store/memory/data.sqlite")):
        game = os.path.basename(db.split("/store/memory")[0])[len("store-"):].split("-")[0]
        if not games or game in games:
            print(game_report(db, run_dir, game), flush=True)


if __name__ == "__main__":
    main()
