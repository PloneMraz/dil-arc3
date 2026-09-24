"""Where the world-model programs in probe logs go wrong, cell by cell.

    python scripts/compare_programs.py [--data scripts/data/transitions.json]
        [--game ls20] [--train 80] [--show LOG.json:ROUND] LOG.json ...

For every program in every round of each `wm_probe.py` log: exact matches on the
train and held-out split, crashes, and — over the transitions it got wrong — how
many cells were wrong, and whether they were wrong in the bar on rows 61–62 or
elsewhere. `--show` prints the wrong cells of one program's first misses.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from wm_probe import load, score
except ImportError:  # run from the repository root
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from wm_probe import load, score

BAR_ROWS = (61, 62)


def wrong_cells(got, after):
    return [(r, c) for r in range(len(after)) for c in range(len(after[0]))
            if got[r][c] != after[r][c]]


def profile(code, data):
    ok, res = score(code, data)
    crashes = sum(1 for good, got in res if not good and isinstance(got, str))
    cells, bar_only, off_bar = [], 0, 0
    for (_, _, after), (good, got) in zip(data, res):
        if good or isinstance(got, str):
            continue
        w = wrong_cells(got, after)
        cells.append(len(w))
        if all(r in BAR_ROWS for r, _ in w):
            bar_only += 1
        if any(r not in BAR_ROWS for r, _ in w):
            off_bar += 1
    mean = sum(cells) / len(cells) if cells else 0
    return ok, crashes, mean, bar_only, off_bar


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent / "data" / "transitions.json"))
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--train", type=int, default=80)
    ap.add_argument("--show", help="LOG.json:ROUND — print that program's first misses")
    a = ap.parse_args()

    data = load(a.game, a.data)
    train, held = data[: a.train], data[a.train:]
    print(f"{'log':<22}{'rnd':>4}{'train':>7}{'held':>6}{'crash':>7}"
          f"{'wrong cells/miss':>18}{'bar only':>10}{'off bar':>9}")
    for path in a.logs:
        log = json.loads(Path(path).read_text())
        for rnd in log["rounds"]:
            code = rnd.get("code")
            if not code:
                print(f"{Path(path).stem:<22}{rnd['round']:>4}   no program")
                continue
            ok_tr, cr_tr, mean, bar, off = profile(code, train)
            ok_he, cr_he, _, _, _ = profile(code, held)
            print(f"{Path(path).stem:<22}{rnd['round']:>4}{ok_tr:>7}{ok_he:>6}{cr_tr + cr_he:>7}"
                  f"{mean:>18.1f}{bar:>10}{off:>9}")

    if a.show:
        path, rnd = a.show.rsplit(":", 1)
        code = json.loads(Path(path).read_text())["rounds"][int(rnd)]["code"]
        _, res = score(code, train)
        shown = 0
        for i, ((action, before, after), (good, got)) in enumerate(zip(train, res)):
            if good:
                continue
            if isinstance(got, str):
                print(f"\ntransition {i}, ACTION{action}: {got}")
            else:
                w = wrong_cells(got, after)
                print(f"\ntransition {i}, ACTION{action}: {len(w)} wrong cells")
                for r, c in w[:12]:
                    print(f"  ({r},{c}) before {before[r][c]} expected {after[r][c]} got {got[r][c]}")
            shown += 1
            if shown == 3:
                break


if __name__ == "__main__":
    main()
