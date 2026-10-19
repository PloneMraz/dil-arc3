"""Run the host's boundary gate against real frames.

Tests use fakes. This proves the declaration in arc3/decisions.py survives what
the engine actually sends.
"""
from _paths import SRC, STARTER  # noqa: E402 — see scripts/_paths.py
import sys

ROOT = STARTER
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
sys.path.insert(0, str(SRC))

import arc_agi
from arc_agi import OperationMode
from agents.agent import Agent
from arcengine import GameAction, GameState

from arc3 import FrameViolation, read_frame

tally = {"accepted": 0, "refused": [], "depths": set(), "empty_skipped": 0}


class GateAgent(Agent):
    MAX_ACTIONS = 25

    def is_done(self, frames, latest_frame) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames, latest_frame) -> GameAction:
        if latest_frame.is_empty():
            tally["empty_skipped"] += 1
        else:
            try:
                f = read_frame(latest_frame)
                tally["accepted"] += 1
                tally["depths"].add(f.depth)
            except FrameViolation as exc:
                tally["refused"].append(str(exc))
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            return GameAction.RESET
        avail = sorted(latest_frame.available_actions)
        return GameAction.from_id(avail[0]) if avail else GameAction.RESET


if __name__ == "__main__":
    arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
    for game_id in ("ls20", "vc33"):
        agent = GateAgent(
            card_id="gate", game_id=game_id, agent_name=f"gate.{game_id}",
            ROOT_URL="http://localhost", record=False,
            arc_env=arc.make(game_id), tags=["gate"],
        )
        agent.main()

    print()
    print("accepted      :", tally["accepted"])
    print("stack depths  :", sorted(tally["depths"]))
    print("empty skipped :", tally["empty_skipped"])
    print("REFUSED       :", len(tally["refused"]))
    for r in tally["refused"][:5]:
        print("   ", r)
