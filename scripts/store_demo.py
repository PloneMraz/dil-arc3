"""Write a real store to disk from a live run, then open it."""
from _paths import SRC, STARTER  # noqa: E402 — see scripts/_paths.py
import json, sys
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
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.runtime.daemon import Daemon
from dil.store.data_store import create_data_store
from dil.store.event_log import create_durable_event_log
from dil.store.event_sink import verify_jsonl_sink, list_segments
from dil.store.substrate import DIL_CLAIM, claim_substrate
from dil.store.display_name import display_name

root = Path(sys.argv[1])

layout = claim_substrate(str(root))
print("DIL-CLAIM written:", json.dumps(DIL_CLAIM))
print("layout:", {k: str(Path(v).relative_to(root)) for k, v in
                  (("memory", layout.memory), ("event-log", layout.event_log),
                   ("commits", layout.commits))})

arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
model = create_model()
source = create_source(arc.make("ls20"), GameAction, action_budget=15, model=model)
clock = [1_800_000_000_000]
def now():
    clock[0] += 1000
    return clock[0]

layers = Layers(t1=create_t1(), t2=create_t2(),
                t3=create_t3({GAME_CHANNEL: game_transducer}), t4=create_t4(),
                t5=create_t5(predict=predict_rule(model)), t6=create_t6(),
                t7=create_t7(), t8=create_t8())
events = create_durable_event_log(layout.event_log)
daemon = Daemon(host=declaration("ls20", store_root=str(root)), source=source,
                layers=layers, glob=create_glob_mod(),
                initial_emission=Emission(action=None), now=now,
                data=create_data_store(), events=events,
                respond=least_resolved())
daemon.start()
while daemon.step():
    pass
daemon.stop()

print("\nsegments:", [s.file for s in list_segments(layout.event_log)])
print("chain verify:", verify_jsonl_sink(layout.event_log))
recs = events.all()
print("records:", len(recs))

from collections import Counter
print("by kind:", dict(Counter(getattr(r, "activity_kind", getattr(r, "kind", "?")) for r in recs)))

seg = sorted(Path(layout.event_log).glob("*.jsonl"))[0]
lines = seg.read_text(encoding="utf-8").splitlines()
print("\n--- line 0 (the manifest / constitution) ---")
print(json.dumps(json.loads(lines[0]), indent=1)[:900])
print("\n--- a scar line, if any ---")
for ln in lines:
    o = json.loads(ln)
    if o["record"].get("form") == "scar":
        print(json.dumps(o, indent=1)[:1100]); break
