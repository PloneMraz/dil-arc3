"""The whole thing, against a live game: daemon, gate, loop, host.

Not a replay. The self commits a move each cycle, the host executes it, and the
next cycle sees what the region did about it. INV-1 closing against a real
region.
"""
from _paths import SRC, STARTER  # noqa: E402 — see scripts/_paths.py
import sys
from pathlib import Path

ROOT = STARTER
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
sys.path.insert(0, str(SRC))

import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction

from arc3 import GAME_CHANNEL, game_transducer
from arc3.host import create_source, declaration
from arc3.respond import least_resolved
from arc3.model import create_model, predict_rule
from dil.loop.cycle import Layers
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.runtime.daemon import Daemon
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log

game_id = sys.argv[1] if len(sys.argv) > 1 else "ls20"
budget = int(sys.argv[2]) if len(sys.argv) > 2 else 120
span = float(sys.argv[3]) if len(sys.argv) > 3 else float("inf")
floor = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0

arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
model = create_model()
source = create_source(arc.make(game_id), GameAction, action_budget=budget, model=model)

clock = [1_800_000_000_000]
def now():
    clock[0] += 1000
    return clock[0]

layers = Layers(
    t1=create_t1(), t2=create_t2(),
    t3=create_t3({GAME_CHANNEL: game_transducer}),
    t4=create_t4(), t5=create_t5(predict=predict_rule(model)), t6=create_t6(),
    t7=create_t7(attention_span=span), t8=create_t8(),
)
daemon = Daemon(
    host=declaration(game_id),
    source=source,
    layers=layers,
    glob=create_glob_mod({"fitFloor": floor} if floor else None),
    initial_emission=Emission(action=None),
    now=now,
    data=create_data_store(),
    events=create_event_log(),
    respond=least_resolved(),
)

gate = daemon.start()
print("precondition gate:", type(gate).__name__, getattr(gate, "reason", ""))

cycles = 0
try:
    while daemon.step():
        cycles += 1
except Exception as exc:
    print("STOPPED at cycle", cycles, ":", type(exc).__name__, exc)
    print("last 5 moves:", [(m.action_id, m.x, m.y) for m in source.delivered[-5:]])
    print("state before :", source.frame.state if source.frame else None,
          "afforded:", source.frame.available_actions if source.frame else None)

from collections import Counter
recs = daemon._events.all()
kinds = Counter(type(r).__name__ for r in recs)
scar_sources = Counter(
    r.event.source_id for r in recs if type(r).__name__ == "EventRecord"
)
absences = sum(n for k, n in scar_sources.items() if k == "region")
gain = daemon._glob.current().params.get("attentionGain")
prov = collections.Counter((r.from_, r.to) for r in recs if type(r).__name__ == "ProvenanceActivity") if False else None
fwd = sum(1 for r in recs if type(r).__name__ == "ProvenanceActivity" and r.from_ == "running" and r.to == "simulated")
print(f"FLOOR={floor} SPAN={span} fwd-built={fwd}  scars={sum(scar_sources.values())}  absences={absences}  other={sum(scar_sources.values())-absences}")
print("scar sources :", dict(scar_sources))
daemon.stop()
print(f"game={game_id}  cycles={cycles}  actions spent={source.spent}")
print("final state:", source.frame.state, "levels:", source.frame.levels_completed)

from collections import Counter
print("moves committed:", dict(Counter(m.action_id for m in source.delivered)))
counts = dict(layers.t5.snapshot()["counts"])
print("affordances learned:", counts)
print("FIELD =", dict(daemon._glob.current().params))
print("model: mover =", model.mover, "| contexts =", model.contexts_known(),
      "| displacements =", {a: model.displacement(a) for a in sorted(counts)})
