"""The starter kit's random agent, played through the path dil-arc3's agent is played.

    $PY scripts/random_game.py GAME CYCLES --remote HOST:PORT [--out DIR]

A probe, not an agent: v12, the first scored run, scored 0.00 against the random
agent's 0.02, and the score alone cannot say whether the agent played and got
nowhere, or the path its games go through lost their actions — one scorecard,
one arcade, each game in a process of its own reaching its game through
`world/remote.py` (Plone, 2026-09-27). This keeps that path and changes only
what chooses the move, to the random agent's rule, as the starter kit writes it
(`agent/my_agent.py`, run by `ARC-AGI-3-Agents/agents/agent.py`):

  - RESET when the game is not yet played or is over;
  - otherwise one of ACTION1..ACTION7 at random — not read from the actions the
    game offers — ACTION4 twice as likely in ls20; ACTION6 at a random cell;
  - stop at WIN, or once the count of actions passes MAX_ACTIONS = 80 (the
    harness loops while the count is <= 80, so up to 81).

Launched by `run_competition.py --player random_game.py`, which passes the
arguments `run_game.py` takes; those it has no use for are ignored. It uses no
model and no DIL.
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import argparse, os, random, sys, time

sys.path.insert(0, str(SRC))

from world.remote import RemoteRegion

MAX_ACTIONS = 80
RESET, COMPLEX = 0, 6

ap = argparse.ArgumentParser()
ap.add_argument("game")
ap.add_argument("cycles", nargs="?", type=int, default=None, help="ignored: the random agent counts its own")
ap.add_argument("--remote", required=True)
ap.add_argument("--out", default=None, help="ignored: the random agent keeps no store")
a, _ignored = ap.parse_known_args()

# As the starter seeds it: per game, from the clock.
random.seed(int(time.time() * 1_000_000) + hash(a.game) % 1_000_000)

host, port = a.remote.rsplit(":", 1)
region = RemoteRegion((host, int(port)), os.environ["DIL_REGIONS_KEY"].encode(), a.game)

state, levels, count = "NOT_PLAYED", 0, 0
moves: dict[int, int] = {}
t0 = time.time()
while state != "WIN" and count <= MAX_ACTIONS:
    data = None
    if state in ("NOT_PLAYED", "GAME_OVER"):
        action = RESET
    else:
        candidates = list(range(1, 8))
        weights = [2 if c == 4 else 1 for c in candidates] if a.game.split("-")[0] == "ls20" else None
        action = random.choices(candidates, weights=weights, k=1)[0]
        if action == COMPLEX:
            data = {"x": random.randint(0, 63), "y": random.randint(0, 63)}
    frame = region.step(action, data)
    if frame is not None:
        state, levels = frame.state, frame.levels_completed
    moves[action] = moves.get(action, 0) + 1
    count += 1

print(f"=== {a.game}  random agent  actions={count}  wall={time.time() - t0:.0f}s ===")
print(f"  moves                 : {dict(sorted(moves.items()))}")
print(f"  final state           : {state}  levels={levels}", flush=True)
