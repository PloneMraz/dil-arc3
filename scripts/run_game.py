"""A live game with the one mind in the loop: the model thinks, DIL runs.

    $PY scripts/run_game.py GAME CYCLES --endpoint URL [--model NAME]
        [--max-tokens N] [--think] [--out DIR]

The host carries the whole frame; the mind predicts it with the program the
model wrote, thinks when the expectation fails (asking the store for the frames
that collided), keeps the program as data (`nascent`, then revisions), and every
cycle in which it wrote is committed. What is printed is read back from the run's
own `[event]` log, `[data]` and commits — the same ones a third party would read.

Nothing here submits to the competition.
"""
from _paths import SRC, STARTER, DATA  # noqa: E402 — see scripts/_paths.py
import argparse, collections, json, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(STARTER)); sys.path.insert(0, str(STARTER / "vendor" / "ARC-AGI-3-Agents"))
sys.path.insert(0, str(SRC))

import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction

from arc3 import transducers
from arc3.host import create_source, declaration
from arc3.mind import ModelEndpoint, create_mind, mind_rule
from arc3.observe import admit
from arc3.respond import least_resolved
from dil.conformance.checker import check_conformance
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

ap = argparse.ArgumentParser()
ap.add_argument("game", nargs="?", default="ls20")
ap.add_argument("cycles", nargs="?", type=int, default=10)
ap.add_argument("--endpoint", default="http://127.0.0.1:8080/v1")
ap.add_argument("--model", default="local")
ap.add_argument("--max-tokens", type=int, default=12288)
ap.add_argument("--think", action="store_true")
ap.add_argument("--offline-dir", default=None,
                help="play the environment files in this directory (Kaggle), not the starter kit's")
ap.add_argument("--out", default=None, help="where the store goes (default: a fresh dir under scripts/data)")
a = ap.parse_args()

if a.offline_dir:
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=a.offline_dir)
else:
    arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
source = create_source(arc.make(a.game), GameAction, action_budget=a.cycles)
wm = create_mind(ModelEndpoint(url=a.endpoint, model=a.model, max_tokens=a.max_tokens, think=a.think))
layers = Layers(
    t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
    t5=create_t5(predict=mind_rule(wm)), t6=create_t6(),
    t7=create_t7(attention_span=4.0), t8=create_t8(),
)
store_root = a.out or tempfile.mkdtemp(prefix=f"run-{a.game}-", dir=str(DATA))
daemon = Daemon(
    host=declaration(a.game, store_root=store_root), source=source, layers=layers,
    glob=create_glob_mod(), initial_emission=Emission(action=None), respond=least_resolved(),
    admit=admit,
)
gate = daemon.start()
print("gate:", type(gate).__name__, " store:", store_root, flush=True)

t0 = time.time()
n = 0
while daemon.step():
    n += 1
    last = wm.thoughts[-1] if wm.thoughts else None
    print(f"cycle {n - 1:3d}  frame calls {wm.frame_calls}  program v{wm.version}  "
          f"thoughts {len(wm.thoughts)}"
          + (f"  last: held {last.held_score}/{last.evidence} cand {last.candidate_score} "
             f"adopted {last.adopted} {last.usage.get('completion_tokens')} tok "
             f"{last.usage.get('seconds')}s {last.note}" if last else ""), flush=True)
daemon.stop()

recs = daemon._events.all()
kind = lambda k: [r for r in recs if getattr(r, "activity_kind", None) == k]  # noqa: E731
frame_ids = {k for k, d in daemon._data.entries() if d.open.get("kind") == "frame"}
frame_scars = [r for r in recs if type(r).__name__ == "EventRecord" and r.datum_id in frame_ids]
frames = sorted(frame_ids, key=lambda k: int(k.split("-")[1]))
by_prov = collections.Counter(daemon._data.get(k).fixed.provenance for k in frames)
queries = [r for r in kind("emission") if r.issuing_layer == 5]
programs = [(k, d) for k, d in daemon._data.entries() if d.open.get("kind") == "program"]
commits = daemon._commits.list() if daemon._commits is not None else []
report = check_conformance(daemon._events)

print(f"\n=== {a.game}  cycles={n}  wall={time.time() - t0:.0f}s ===")
print(f"  frames                : {len(frames)}  by provenance {dict(by_prov)}")
print(f"  frame scars by cycle  : {[r.anchor.cycle for r in frame_scars]}")
print(f"  mind asked the store  : {len(queries)} times  cues {sorted({json.dumps(q.action['cue']) for q in queries})}")
print(f"  programs in [data]    : {[(k, d.fixed.provenance, d.payload.get('version')) for k, d in programs]}")
print(f"  program moves         : {[(r.datum_id, r.from_, r.to, r.cycle_mark) for r in kind('provenance') if r.datum_id.startswith('written-')]}")
print(f"  revisions             : {[(r.datum_id, r.cycle_mark) for r in kind('revision')]}")
print(f"  commits               : {len(commits)}")
print(f"  thoughts              : {[(t.frame_call, t.evidence, t.held_score, t.candidate_score, t.adopted, t.usage.get('completion_tokens'), t.usage.get('seconds'), t.note) for t in wm.thoughts]}")
print(f"  [event] records       : {len(recs)}")
print(f"  conformance           : {[(r.id, r.verdict) for r in report.results]}")
print(f"  moves committed       : {dict(collections.Counter(m.action_id for m in source.delivered))}")
print(f"  field, per action     : {({k: round(v, 3) for k, v in sorted(daemon._glob.current().params.items()) if k.startswith(('resolved:', 'progress:', 'valence:'))})}")
print(f"  final state           : {source.frame.state}  levels={source.frame.levels_completed}")
if wm.code:
    print("\n--- the program the mind holds ---\n" + wm.code)
