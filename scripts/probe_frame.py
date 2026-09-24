"""Read real ARC-AGI-3 frames and report their actual shape and value range.

Declaring tag A from the SDK's type hints alone would be declaring from a
signature; this reads what the engine actually returns.
"""
from _paths import STARTER  # noqa: E402 — see scripts/_paths.py
import sys
from pathlib import Path

ROOT = STARTER
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))

import arc_agi
from arc_agi import OperationMode
from agents.agent import Agent
from arcengine import GameAction, GameState

seen = {
    "frames": 0,
    "shapes": set(),
    "values": set(),
    "actions": set(),
    "states": set(),
    "sample": None,
}


class ProbeAgent(Agent):
    MAX_ACTIONS = 20

    def is_done(self, frames, latest_frame) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames, latest_frame) -> GameAction:
        f = latest_frame
        seen["frames"] += 1
        seen["states"].add(f.state.name)
        seen["actions"].add(tuple(sorted(f.available_actions)))
        if f.frame:
            seen["shapes"].add(
                (len(f.frame), len(f.frame[0]), len(f.frame[0][0]) if f.frame[0] else 0)
            )
            for grid in f.frame:
                for row in grid:
                    seen["values"].update(row)
            if seen["sample"] is None:
                seen["sample"] = [row[:12] for row in f.frame[0][:4]]
        if f.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            return GameAction.RESET
        return GameAction.ACTION1


if __name__ == "__main__":
    arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
    for game_id in ("ls20", "vc33"):
        env = arc.make(game_id)
        agent = ProbeAgent(
            card_id="probe", game_id=game_id, agent_name=f"probe.{game_id}",
            ROOT_URL="http://localhost", record=False, arc_env=env, tags=["probe"],
        )
        agent.main()

    print()
    print("frames observed :", seen["frames"])
    print("frame shapes    :", sorted(seen["shapes"]), "  (grids, rows, cols)")
    vals = sorted(seen["values"])
    print("cell values     :", f"min={min(vals)} max={max(vals)}", "| distinct:", len(vals), "|", vals)
    print("available_actions sets:", sorted(seen["actions"]))
    print("states seen     :", sorted(seen["states"]))
    print("sample rows     :")
    for row in seen["sample"] or []:
        print("   ", row)
