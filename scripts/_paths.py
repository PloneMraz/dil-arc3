"""Where the scripts find things, worked out from where this file sits.

The measurement scripts were written on Windows with absolute paths baked in.
They now locate the repository, the workspace and the ARC-AGI-3 starter kit
relative to this file, so they run wherever the workspace is mounted.

    REPO     this repository
    SRC      its source tree, put on sys.path by the scripts. Set DIL_ARC3_SRC
             to point a script at another checkout's src — how the scripts
             written against removed code are re-run (see scripts/README.md)
    STARTER  the ARC-AGI-3 Kaggle starter kit, a sibling in the workspace; it
             holds the game engine's vendored framework and cached games
    DATA     scripts/data/: measured transitions (frames.pkl) and the stores of
             live runs. Git-ignored: it is output, reproducible with the scripts.
"""

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = Path(os.environ.get("DIL_ARC3_SRC", REPO / "src")).resolve()
STARTER = REPO.parent / "ARC-AGI-3-Kaggle-Starter"
DATA = REPO / "scripts" / "data"
DATA.mkdir(parents=True, exist_ok=True)
