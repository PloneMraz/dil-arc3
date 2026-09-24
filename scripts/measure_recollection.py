"""Two sources of expectation, and who the region sides with.

The model says what it has learned; the record says what the region actually did
last time in this same situation. Where they disagree, §6.4 says do not
arbitrate — collide it against the region. This counts what the region then says.
"""
from _paths import SRC, STARTER  # noqa: E402 — see scripts/_paths.py
import sys, collections
from pathlib import Path
ROOT = STARTER
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
sys.path.insert(0, str(SRC))

import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction

from arc3 import GAME_CHANNEL, game_transducer
from arc3.host import create_source, declaration
from arc3.model import create_model, predict_rule, situation_key
from arc3.respond import least_resolved
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
from dil.loop.recollection import create_log_recollection
from dil.runtime.daemon import Daemon
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.resist_event import ProvenanceActivity

game = sys.argv[1] if len(sys.argv) > 1 else "ls20"
budget = int(sys.argv[2]) if len(sys.argv) > 2 else 120
with_record = sys.argv[3] != "off" if len(sys.argv) > 3 else True

tally = collections.Counter()

def watch(entity, context, from_model, from_record, actual):
    tally["calls"] += 1
    if from_record is None:
        tally["record silent"] += 1
        if from_model is not None:
            tally["model right" if from_model == actual else "model wrong"] += 1
        return
    tally["record spoke"] += 1
    if from_model == from_record:
        tally["agreed"] += 1
        tally["agreed+right" if from_record == actual else "agreed+wrong"] += 1
        return
    tally["DISAGREED"] += 1
    if from_record == actual:
        tally["  region sided with RECORD"] += 1
    elif from_model == actual:
        tally["  region sided with MODEL"] += 1
    else:
        tally["  region sided with NEITHER"] += 1

arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
model = create_model()
events = create_event_log()
rec = create_log_recollection(events, key=situation_key) if with_record else None
source = create_source(arc.make(game), GameAction, action_budget=budget, model=model)
clock = [1_800_000_000_000]
def now():
    clock[0] += 1000
    return clock[0]

layers = Layers(
    t1=create_t1(), t2=create_t2(), t3=create_t3({GAME_CHANNEL: game_transducer}),
    t4=create_t4(), t5=create_t5(predict=predict_rule(model, rec, watch)),
    t6=create_t6(), t7=create_t7(attention_span=4.0), t8=create_t8(),
)
daemon = Daemon(
    host=declaration(game), source=source, layers=layers, glob=create_glob_mod(),
    initial_emission=Emission(action=None), now=now, data=create_data_store(),
    events=events, respond=least_resolved(), recollection=rec,
)
daemon.start()
while daemon.step():
    pass
daemon.stop()

recs = events.all()
scar_src = collections.Counter(
    r.event.source_id for r in recs if type(r).__name__ == "EventRecord"
)
returns = sum(
    1 for r in recs
    if isinstance(r, ProvenanceActivity) and r.from_ == "scar" and r.to == "running"
)
print()
print(f"=== {game}  record={'ON' if with_record else 'OFF'}  cycles={source.spent} ===")
for k in ("calls", "record silent", "record spoke", "agreed", "agreed+right",
          "agreed+wrong", "DISAGREED", "  region sided with RECORD",
          "  region sided with MODEL", "  region sided with NEITHER",
          "model right", "model wrong"):
    if tally[k]:
        print(f"  {k:<28} {tally[k]}")
print(f"  {'scar -> running edges':<28} {returns}")
print(f"  scar sources: {dict(scar_src)}")
