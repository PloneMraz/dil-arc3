"""What an offline scorecard says, for one run or several side by side.

    python scripts/read_scorecard.py OUTPUT_DIR [OUTPUT_DIR ...]

Each OUTPUT_DIR is where `run_competition.py` wrote (`competition.json`), as a
Kaggle Save & Run hands it back. The offline scorecard is the toolkit's own,
scored as the competition scores: each level's score from the human baseline's
actions against the agent's, squared, capped; levels weighted by their number;
games averaged. Read only — what the toolkit computed, nothing recomputed here.

Printed: per run, the score and the levels completed of the levels there are;
per game, each run's score and levels completed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def card(out: Path) -> dict:
    return json.loads((out / "competition.json").read_text())["scorecard"]


def main(dirs: list[str]) -> None:
    runs = [(Path(d).name, card(Path(d))) for d in dirs]
    for name, sc in runs:
        print(f"{name:32} score {sc['score']:.5f}  levels {sc['total_levels_completed']}/{sc['total_levels']}  "
              f"games {sc['total_environments']}  actions {sc['total_actions']}")
    games = sorted({e["id"] for _, sc in runs for e in sc["environments"]})
    print()
    print(f"{'game':16}" + "".join(f"{name[:18]:>20}" for name, _ in runs))
    for g in games:
        cells = []
        for _, sc in runs:
            e = next((e for e in sc["environments"] if e["id"] == g), None)
            cells.append("—" if e is None else f"{e['score']:.4f} ({e['levels_completed']}/{e['level_count']})")
        print(f"{g:16}" + "".join(f"{c:>20}" for c in cells))


if __name__ == "__main__":
    main(sys.argv[1:])
