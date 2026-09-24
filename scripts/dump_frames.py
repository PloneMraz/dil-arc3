"""Save real (prev, action, now) triples so the representation can be
iterated on offline instead of re-hitting the engine each time."""
from _paths import SRC, STARTER  # noqa: E402 — see scripts/_paths.py
import pickle, sys
from pathlib import Path

ROOT = STARTER
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
sys.path.insert(0, str(SRC))

import arc_agi
from arc_agi import OperationMode
from agents.agent import Agent
from arcengine import GameAction, GameState
from arc3 import read_frame

OUT = Path(sys.argv[1])
rows = []


class Dumper(Agent):
    MAX_ACTIONS = 160

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.prev = None; self.pending = None; self.n = 0

    def is_done(self, frames, latest_frame): return latest_frame.state is GameState.WIN

    def choose_action(self, frames, latest_frame):
        cur = None if latest_frame.is_empty() else read_frame(latest_frame)
        if cur and self.prev and self.pending is not None:
            rows.append((self.game_id, self.pending, self.prev, cur))
        self.prev = cur
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            self.pending = None
            return GameAction.RESET
        avail = sorted(latest_frame.available_actions)
        self.n += 1
        if avail == [6]:
            spot = [(32, 32), (10, 10), (50, 20), (20, 44)][(self.n // 6) % 4]
            act = GameAction.from_id(6); act.set_data({"x": spot[0], "y": spot[1]})
            self.pending = f"6@{spot[0]},{spot[1]}"
            return act
        aid = avail[(self.n // 6) % len(avail)]
        self.pending = str(aid)
        return GameAction.from_id(aid)


if __name__ == "__main__":
    arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
    for game_id in ("ls20", "vc33"):
        Dumper(card_id="d", game_id=game_id, agent_name=f"d.{game_id}",
               ROOT_URL="http://localhost", record=False,
               arc_env=arc.make(game_id), tags=["d"]).main()
    OUT.write_bytes(pickle.dumps(rows))
    print("saved", len(rows), "transitions ->", OUT)
