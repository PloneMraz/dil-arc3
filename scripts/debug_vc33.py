from _paths import SRC, STARTER  # noqa: E402 — see scripts/_paths.py
import sys
from pathlib import Path
ROOT = STARTER
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
sys.path.insert(0, str(SRC))
import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction
from arc3.host import create_source
from arc3.action import Move
from arc3.observe import move_value
from dil.loop.layers.t2 import Emission

arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
src = create_source(arc.make("vc33"), GameAction, action_budget=10)
host_input = src.next()
print("cycle0 signal affords:", host_input.signals[0].raw_payload["affords"])
print("cycle0 afforded set  :", host_input.afforded)
for i in range(5):
    mv = Move(6, 4 + i * 8, 4)
    print(f"deliver {mv} ...", end=" ")
    try:
        src.deliver(Emission(action=move_value(mv)))
        print("ok, frame depth", src.frame.depth, "state", src.frame.state)
    except Exception as e:
        print("FAILED:", type(e).__name__, e)
        break
