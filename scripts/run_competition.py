"""Play every game the arcade offers, several at once, on one scorecard — as scoring does.

    $PY scripts/run_competition.py --mode competition --base-url http://gateway:8001/ \\
        --endpoint URL --model NAME --out /kaggle/working [--concurrency 4] [--cycles 60]
        [--deadline EPOCH] [--games a,b]
    $PY scripts/run_competition.py --mode offline --offline-dir DIR ... --games ls20,vc33

The official harness opens one scorecard, makes every game on it once, plays them
in threads of one process, and closes the scorecard at the end; the gateway
records each action and writes the submission. This does the same, except that
each game is played by `run_game.py` in a process of its own (the mind bounds
the programs it runs with SIGALRM, which needs a main thread), reaching its game
through `world/remote.py`. Each game keeps its own store — its `[event]` log —
and its report, `run-<game>.txt`.

The deadline is a wall-clock instant: no game starts after it, and a game still
playing at it is stopped (its process, by the PID this script started). The
scorecard is closed either way.

Nothing here decides a move, and nothing here reads a game.
"""
from _paths import SRC, STARTER  # noqa: E402 — see scripts/_paths.py
import argparse, json, os, secrets, subprocess, sys, threading, time
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
ap.add_argument("--endpoint", required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--max-tokens", type=int, default=12288)
ap.add_argument("--out", required=True)
a = ap.parse_args()
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
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
            say(f"{g}: exit {proc.returncode}; {len(done)} done, {len(queue)} waiting")
    late = a.deadline is not None and time.time() >= a.deadline
    if late:
        for g, (proc, _) in running.items():
            proc.terminate()  # the PID this script started, and nothing else
            done[g] = "stopped at the deadline"
        for g in queue:
            done[g] = "not started: the deadline"
        say(f"deadline: {len(running)} stopped, {len(queue)} not started")
        for proc, _ in running.values():
            proc.wait(timeout=60)
        running.clear()
        queue.clear()
        break
    while queue and len(running) < a.concurrency:
        g = queue.pop(0)
        proc = subprocess.Popen(
            [sys.executable, "-u", str(HERE / "run_game.py"), g, str(a.cycles),
             "--endpoint", a.endpoint, "--model", a.model, "--max-tokens", str(a.max_tokens),
             "--remote", f"{host}:{port}", "--out", str(out / f"store-{g}")],
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
