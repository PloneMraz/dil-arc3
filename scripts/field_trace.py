"""What GLOB-MOD actually holds, cycle by cycle, on a live game.

Printed rather than described, so the claim that attention is composed from
context and environment can be read off a real run instead of taken on trust.
"""
from _paths import SRC, STARTER  # noqa: E402 — see scripts/_paths.py
import sys
from pathlib import Path
ROOT = STARTER
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
sys.path.insert(0, str(SRC))

import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction

from arc3 import GAME_CHANNEL, game_transducer
from arc3.host import create_source, declaration
from arc3.model import create_model, predict_rule
from arc3.respond import least_resolved
from dil.loop.cycle import Layers
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import attention_width, create_t7
from dil.loop.layers.t8 import create_t8
from dil.runtime.daemon import Daemon
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log

game = sys.argv[1] if len(sys.argv) > 1 else "ls20"
budget = int(sys.argv[2]) if len(sys.argv) > 2 else 40

arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
model = create_model()
source = create_source(arc.make(game), GameAction, action_budget=budget, model=model)
clock = [1_800_000_000_000]
def now():
    clock[0] += 1000
    return clock[0]

glob = create_glob_mod()
layers = Layers(
    t1=create_t1(), t2=create_t2(), t3=create_t3({GAME_CHANNEL: game_transducer}),
    t4=create_t4(), t5=create_t5(predict=predict_rule(model)), t6=create_t6(),
    t7=create_t7(attention_span=4.0), t8=create_t8(),
)
daemon = Daemon(
    host=declaration(game), source=source, layers=layers, glob=glob,
    initial_emission=Emission(action=None), now=now, data=create_data_store(),
    events=create_event_log(), respond=least_resolved(),
)
daemon.start()

keys = ["contextNovelty", "contextsKnown", "surprise", "otherCount", "silence", "strangeness"]
print(f"{'cyc':>3} " + " ".join(f"{k[:9]:>9}" for k in keys) + f" {'->width':>8} {'->span':>7}")
print("-" * 82)
n = 0
while daemon.step():
    n += 1
    p = dict(glob.current().params)
    if n <= 10 or n % 8 == 0:
        row = " ".join(f"{p.get(k, float('nan')):>9.3f}" for k in keys)
        w = attention_width(p)
        print(f"{n:>3} {row} {w:>8.3f} {4.0 * w:>7.3f}")
daemon.stop()
print()
print("final field:", {k: round(v, 3) for k, v in glob.current().params.items()})
