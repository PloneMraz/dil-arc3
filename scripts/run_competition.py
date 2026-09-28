"""Play every game the arcade offers, several at once, on one scorecard — as scoring does.

    $PY scripts/run_competition.py --mode competition --base-url http://gateway:8001/ \\
        --endpoint URL --model NAME --out /kaggle/working [--concurrency 4] [--cycles 60]
        [--deadline EPOCH] [--games a,b]
    $PY scripts/run_competition.py --mode offline --offline-dir DIR ... --games ls20,vc33
    $PY scripts/run_competition.py ... --player random_game.py     (the path, with the random agent)

The official harness opens one scorecard, makes every game on it once, plays them
in threads of one process, and closes the scorecard at the end; the gateway
records each action and writes the submission. This does the same, except that
each game is played by `run_game.py` in a process of its own (the mind bounds
the programs it runs with SIGALRM, which needs a main thread), reaching its game
through `world/remote.py`. Each game keeps its own store — its `[event]` log —
and its report, `run-<game>.txt`.

With `--drop-stores` a game's store is removed once it has played (`--stores`
says where they go): a scored rerun's outputs cannot be read back, and a store
of the learning mind is ~0.4 GB a game against Kaggle's 20 GiB. A Save & Run
keeps every store.

The deadline is a wall-clock instant: no game starts after it, and a game still
playing at it is stopped (its process, by the PID this script started). The
scorecard is closed either way.

Nothing here decides a move, and nothing here reads a game.
"""
from _paths import SRC, STARTER  # noqa: E402 — see scripts/_paths.py
import argparse, json, os, secrets, shutil, subprocess, sys, threading, time
from pathlib import Path

sys.path.insert(0, str(STARTER)); sys.path.insert(0, str(SRC))

import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction

from world.remote import Regions, serve

HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=("competition", "offline"), required=True)
ap.add_argument("--base-url", default="http://gateway:8001/")
ap.add_argument("--offline-dir", default=None)
ap.add_argument("--games", default=None, help="comma list; default: every game the arcade offers")
ap.add_argument("--cycles", type=int, default=60)
ap.add_argument("--concurrency", type=int, default=4)
ap.add_argument("--deadline", type=float, default=None, help="epoch seconds: start nothing after, stop what runs")
ap.add_argument("--endpoint", default="")
ap.add_argument("--model", default="")
ap.add_argument("--mind", choices=("learning", "language"), default="learning",
                help="learning: the one mind with its learning; language: the language model's earlier form, "
                     "not run (LOG.md, 2026-09-28)")
ap.add_argument("--inducer", choices=("exact", "grid", "language"), default="exact",
                help="the mind's model, what its learning computes with; language: a model served at "
                     "--endpoint")
ap.add_argument("--curiosity", default="new",
                help="the mind's law of curiosity, passed to run_game.py (mind/learning.py: CURIOSITY)")
ap.add_argument("--player", default="run_game.py",
                help="the script that plays each game, in scripts/: run_game.py, the agent; "
                     "random_game.py, the starter's random agent, to probe this path (LOG.md, 2026-09-27)")
ap.add_argument("--max-tokens", type=int, default=12288)
ap.add_argument("--out", required=True)
ap.add_argument("--stores", default=None, help="where each game's store goes (default: --out)")
ap.add_argument("--drop-stores", action="store_true",
                help="remove a game's store once it has played: a scored rerun's outputs cannot be read, "
                     "and 110 stores do not fit Kaggle's 20 GiB (LOG.md, 2026-09-27)")
a = ap.parse_args()
if a.mind == "language" and a.player == "run_game.py":
    # Its games would each stop before they start (run_game.py).
    sys.exit("--mind language: the language model's earlier form is kept and not run (LOG.md, 2026-09-28)")
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
stores = Path(a.stores) if a.stores else out
stores.mkdir(parents=True, exist_ok=True)
t0 = time.time()


def say(line: str) -> None:
    print(f"[competition {time.time() - t0:6.0f}s] {line}", flush=True)


if a.mode == "competition":
    arc = arc_agi.Arcade(operation_mode=OperationMode.COMPETITION, arc_base_url=a.base_url, environments_dir="")
else:
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=a.offline_dir)
offered = [e.game_id for e in arc.available_environments]
wanted = [g.strip() for g in a.games.split(",")] if a.games else offered
games = [g for g in offered if g in wanted or g.split("-", 1)[0] in wanted]
say(f"{len(offered)} games offered, {len(games)} to play")

card = arc.open_scorecard(tags=["dil-arc3"])
envs = {}
for g in games:
    env = arc.make(g, scorecard_id=card)
    if env is None:
        say(f"{g}: could not be made")
    else:
        envs[g] = env
say(f"scorecard {card}; {len(envs)} games made")

key = secrets.token_hex(16)
host, port = serve(Regions(envs, GameAction), key.encode())
env = dict(os.environ, DIL_REGIONS_KEY=key)

queue = list(envs)
running: dict[str, tuple[subprocess.Popen, float]] = {}
done: dict[str, int | str] = {}


def pump(game: str, proc: subprocess.Popen) -> None:
    started = time.time()
    with open(out / f"run-{game}.txt", "w") as log:
        for line in proc.stdout:
            log.write(line)
            log.flush()
            if " INFO " not in line and (line.startswith("===") or "final state" in line or "Traceback" in line):
                print(f"[{game} {time.time() - started:6.0f}s] {line}", end="", flush=True)


while queue or running:
    for g, (proc, _) in list(running.items()):
        if proc.poll() is not None:
            done[g] = proc.returncode
            del running[g]
            if a.drop_stores:
                shutil.rmtree(stores / f"store-{g}", ignore_errors=True)
            say(f"{g}: exit {proc.returncode}; {len(done)} done, {len(queue)} waiting")
    late = a.deadline is not None and time.time() >= a.deadline
    if late:
        for g, (proc, _) in running.items():
            proc.terminate()  # the PID this script started, and nothing else
            done[g] = "stopped at the deadline"
        for g in queue:
            done[g] = "not started: the deadline"
        say(f"deadline: {len(running)} stopped, {len(queue)} not started")
        for g, (proc, _) in running.items():
            proc.wait(timeout=60)
            if a.drop_stores:
                shutil.rmtree(stores / f"store-{g}", ignore_errors=True)
        running.clear()
        queue.clear()
        break
    while queue and len(running) < a.concurrency:
        g = queue.pop(0)
        proc = subprocess.Popen(
            [sys.executable, "-u", str(HERE / a.player), g, str(a.cycles),
             "--endpoint", a.endpoint, "--model", a.model, "--max-tokens", str(a.max_tokens),
             "--remote", f"{host}:{port}", "--out", str(stores / f"store-{g}"), "--mind", a.mind,
             *(["--inducer", a.inducer, "--curiosity", a.curiosity] if a.mind == "learning" else [])],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=str(HERE.parent), env=env)
        running[g] = (proc, time.time())
        threading.Thread(target=pump, args=(g, proc), daemon=True).start()
    time.sleep(2)

scorecard = arc.close_scorecard(card)
summary = scorecard.model_dump() if scorecard is not None and hasattr(scorecard, "model_dump") else None
(out / "competition.json").write_text(json.dumps(
    {"scorecard_id": card, "games": games, "exits": done, "scorecard": summary,
     "seconds": time.time() - t0}, indent=1, default=str))
say(f"scorecard closed; {sum(1 for v in done.values() if v == 0)} of {len(games)} games played through")
