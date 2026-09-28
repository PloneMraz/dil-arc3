"""A series of Save & Run versions of the learning notebook, one after another.

    python scripts/kaggle/run_series.py SERIES [--first-pushed] [--start I] [--stop J] [--games a,b,...]

For each configuration in turn: build the notebook (`build_dil_run.py`), push
it — the kernel only: the dataset the series runs on is pushed once, before,
with `push_dil_run.py` — wait until Kaggle has run it, and download its outputs
to `scripts/data/kaggle/dil-run/<series>-<name>/` (git-ignored), with the
notebook as it was built. `--first-pushed`: the first configuration's version
is already running; wait for it, and push the rest. `--start`/`--stop` run the
configurations from I up to J (0-based, J not included); `--games` plays those
games in place of the 25 (Plone, 2026-09-28: the laws of curiosity on 6 games).

A version that does not end COMPLETE stops the series, its outputs downloaded:
what came of it is looked at before anything else runs. Each line goes to the
series' log as well as out. Nothing here submits to the competition.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KAGGLE = REPO.parent / "ARC-AGI-3-Kaggle-Starter" / ".venv" / "bin" / "kaggle"
OUT = REPO / "scripts" / "data" / "kaggle" / "dil-run"
KERNEL = "plonemraz/dil-arc3-learning"

# The 25 games of the competition's environment_files (LOG.md, 2026-09-28).
GAMES = ("ar25,bp35,cd82,cn04,dc22,ft09,g50t,ka59,lf52,lp85,ls20,m0r0,r11l,re86,s5i5,sb26,sc25,sk48,"
         "sp80,su15,tn36,tr87,tu93,vc33,wa30")

# (name, inducer, curiosity): the 25-game measurement settled with Plone.
SERIES = {
    "m25": [
        ("exact-new", "exact", "new"),
        ("grid-new", "grid", "new"),
        ("grid-changed", "grid", "changed"),
        ("grid-new-then-changed", "grid", "new-then-changed"),
        ("grid-new-plus-changed", "grid", "new-plus-changed"),
    ],
}


def say(log: Path, text: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {text}"
    print(line, flush=True)
    with log.open("a") as f:
        f.write(line + "\n")


def kaggle(*args: str, timeout: int = 600) -> str:
    done = subprocess.run([str(KAGGLE), *args], capture_output=True, text=True, timeout=timeout)
    return (done.stdout + done.stderr).strip()


def status() -> str:
    try:
        return kaggle("kernels", "status", KERNEL, timeout=120).splitlines()[-1]
    except (subprocess.TimeoutExpired, IndexError) as exc:
        return f"status unknown: {exc!r}"


def finished(text: str) -> bool:
    return any(word in text.upper() for word in ("COMPLETE", "ERROR", "CANCEL"))


def wait(log: Path, pushed_at: float | None) -> str:
    """Until the version runs to an end; the end it came to. Right after a push the
    status may still be the last version's end: wait first for it to leave it."""
    if pushed_at is not None:
        while finished(status()) and time.time() - pushed_at < 900:
            time.sleep(30)
    while True:
        text = status()
        if finished(text):
            return text
        say(log, text)
        time.sleep(300)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("series", choices=sorted(SERIES))
    ap.add_argument("--first-pushed", action="store_true")
    ap.add_argument("--cycles", type=int, default=600)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--stop", type=int, default=None)
    ap.add_argument("--games", default=GAMES)
    a = ap.parse_args()
    log = OUT / f"{a.series}-series.log"
    chosen = SERIES[a.series][a.start:a.stop]
    say(log, f"series {a.series}: {[c[0] for c in chosen]} on {a.games}")
    for i, (name, inducer, curiosity) in enumerate(chosen):
        dest = OUT / f"{a.series}-{name}"
        dest.mkdir(parents=True, exist_ok=True)
        pushed_at = None
        if not (i == 0 and a.first_pushed):
            built = subprocess.run(
                [sys.executable, str(HERE / "build_dil_run.py"), "--mind", "learning", "--inducer", inducer,
                 "--curiosity", curiosity, "--game", a.games, "--cycles", str(a.cycles),
                 "--concurrency", str(a.concurrency)], capture_output=True, text=True, cwd=str(REPO))
            if built.returncode != 0:
                say(log, f"{name}: build failed: {built.stderr.strip()[-500:]}")
                sys.exit(1)
            shutil.copytree(OUT / "kernel", dest / "kernel", dirs_exist_ok=True)
            say(log, f"{name}: {kaggle('kernels', 'push', '-p', str(OUT / 'kernel')).splitlines()[-1]}")
            pushed_at = time.time()
        else:
            shutil.copytree(OUT / "kernel", dest / "kernel", dirs_exist_ok=True)   # as it was built and pushed
            say(log, f"{name}: already pushed; waiting for it")
        end = wait(log, pushed_at)
        say(log, f"{name}: {end}")
        got = kaggle("kernels", "output", KERNEL, "-p", str(dest), timeout=3600)
        say(log, f"{name}: outputs -> {dest} ({len(list(dest.iterdir()))} entries) {got.splitlines()[-1] if got else ''}")
        if "COMPLETE" not in end.upper():
            say(log, f"{name}: did not complete; the series stops here")
            sys.exit(2)
    say(log, f"series {a.series}: {[c[0] for c in chosen]} done")


if __name__ == "__main__":
    main()
