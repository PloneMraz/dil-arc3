"""Is the effect signature stable under repetition of the same control?

The tag H declaration claims it is. This measures it. A control whose signature
never repeats would falsify the claim and force a different representation.
"""
from _paths import SRC, STARTER  # noqa: E402 — see scripts/_paths.py
import sys
from collections import Counter, defaultdict
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
from arc3.effect import diff

sigs = defaultdict(list)   # (game, action_key) -> [Effect, ...]


class MeasureAgent(Agent):
    MAX_ACTIONS = 96

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.prev = None
        self.pending = None
        self.n = 0

    def is_done(self, frames, latest_frame) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames, latest_frame) -> GameAction:
        cur = None
        if not latest_frame.is_empty():
            cur = read_frame(latest_frame)
        if cur and self.prev and self.pending is not None:
            sigs[(self.game_id, self.pending)].append(diff(self.prev, cur))
        self.prev = cur

        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            self.pending = None
            return GameAction.RESET

        avail = sorted(latest_frame.available_actions)
        self.n += 1
        if avail == [6]:
            # Repeat the SAME click, so repetition is genuinely repetition.
            spot = [(32, 32), (10, 10), (50, 20)][(self.n // 8) % 3]
            act = GameAction.from_id(6)
            act.set_data({"x": spot[0], "y": spot[1]})
            self.pending = f"6@{spot[0]},{spot[1]}"
            return act
        aid = avail[(self.n // 8) % len(avail)]
        self.pending = str(aid)
        return GameAction.from_id(aid)


if __name__ == "__main__":
    arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
    for game_id in ("ls20", "vc33"):
        MeasureAgent(
            card_id="m", game_id=game_id, agent_name=f"m.{game_id}",
            ROOT_URL="http://localhost", record=False,
            arc_env=arc.make(game_id), tags=["m"],
        ).main()

    # Which signatures discriminate? A signature seen under exactly one action
    # carries information about which action was taken; one seen under all of
    # them carries none.
    by_game = defaultdict(lambda: defaultdict(Counter))
    for (game, act), effs in sigs.items():
        for e in effs:
            by_game[game][e][act] += 1

    for game, table in sorted(by_game.items()):
        acts = sorted({a for c in table.values() for a in c})
        print()
        print(f"### {game} — {len(table)} distinct signatures over actions {acts}")
        print(f"{'n':>4} {'#acts':>5}  {'per-action':<34} signature")
        print("-" * 118)
        rows = sorted(table.items(), key=lambda kv: -sum(kv[1].values()))
        for eff, c in rows[:14]:
            total = sum(c.values())
            per = " ".join(f"{a}:{n}" for a, n in sorted(c.items()))
            mark = "  <-- DISCRIMINATES" if len(c) == 1 else ""
            desc = "NULL" if eff.is_null else (
                f"cells={eff.cells_changed} lv={eff.levels_delta} "
                f"disp={eff.displacements} trans={eff.transitions}"
            )
            print(f"{total:>4} {len(c):>5}  {per:<34} {desc[:60]}{mark}")
