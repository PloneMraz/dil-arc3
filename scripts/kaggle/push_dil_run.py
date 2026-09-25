"""Upload the built dataset, wait until Kaggle serves THAT version, then push the notebook.

    python scripts/kaggle/push_dil_run.py -m "message" [--must-have src/arc3/task.py]

Why not `kaggle datasets status`: it answered "ready" at once, for the version
before, and a notebook pushed on that ran the old code (2026-09-25: four games
exited in a second on a flag the old `run_game.py` did not know). What is waited
for here is the thing itself: the dataset's file list showing a file created
after the upload began — and, with `--must-have`, a file the new build has.

Run from the repository root after `build_dil_run.py`. Nothing here submits to
the competition.
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KAGGLE = REPO.parent / "ARC-AGI-3-Kaggle-Starter" / ".venv" / "bin" / "kaggle"
OUT = REPO / "scripts" / "data" / "kaggle" / "dil-run"
DATASET = "plonemraz/dil-arc3-src"


def kaggle(*args: str, timeout: int = 600) -> str:
    done = subprocess.run([str(KAGGLE), *args], capture_output=True, text=True, timeout=timeout)
    return done.stdout + done.stderr


def served_files() -> list[tuple[str, dt.datetime]]:
    """Every file of the dataset's current version, with its creation time (UTC)."""
    files, token = [], None
    for _ in range(50):
        out = kaggle("datasets", "files", DATASET, *(["--page-token", token] if token else []), "--page-size", "200")
        token = None
        for line in out.splitlines():
            if line.startswith("Next Page Token = "):
                token = line.split("= ", 1)[1].strip()
                continue
            parts = line.split()
            if len(parts) >= 4 and parts[-2][:4].isdigit():
                stamp = dt.datetime.fromisoformat(f"{parts[-2]} {parts[-1]}").replace(tzinfo=dt.timezone.utc)
                files.append((parts[0], stamp))
        if token is None:
            break
    return files


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--message", required=True)
    ap.add_argument("--must-have", default=None, help="a path the new build has, e.g. src/arc3/task.py")
    ap.add_argument("--wait", type=int, default=1800, help="seconds to wait for the version to be served")
    a = ap.parse_args()

    began = dt.datetime.now(dt.timezone.utc)
    print(kaggle("datasets", "version", "-p", str(OUT / "dataset"), "-m", a.message).strip().splitlines()[-1])
    deadline = time.time() + a.wait
    while True:
        files = served_files()
        fresh = [name for name, stamp in files if stamp >= began - dt.timedelta(seconds=5)]
        has = a.must_have is None or any(name.endswith(a.must_have) for name in fresh)
        print(f"{dt.datetime.now():%H:%M:%S} served files {len(files)}, made since upload {len(fresh)}, "
              f"must-have {'yes' if has else 'no'}", flush=True)
        if fresh and has:
            break
        if time.time() > deadline:
            sys.exit("the new dataset version was not served in time; the notebook was NOT pushed")
        time.sleep(30)
    print(kaggle("kernels", "push", "-p", str(OUT / "kernel")).strip().splitlines()[-1])


if __name__ == "__main__":
    main()
