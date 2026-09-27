"""A live game with the one mind in the loop: the mind thinks, DIL runs.

    $PY scripts/run_game.py GAME CYCLES --endpoint URL [--model NAME]
        [--max-tokens N] [--think] [--alone] [--offline-dir DIR] [--remote HOST:PORT] [--out DIR]
    $PY scripts/run_game.py GAME CYCLES --mind learning [...]      (the mind that learns from nothing)

The host carries the whole frame; the mind predicts it with the program the
model wrote, and thinks when an expectation meets a mismatch — the frame, the
status, what a command or the aim was for, the onlooker — or while the body
waits; the model asks its memory for what it wants to read. The program is kept
as data (`nascent`, then revisions), each answer too, and every cycle in which
the mind wrote is committed. What is printed is read back from the run's
own `[event]` log, `[data]` and commits — the same ones a third party would read.

The game is played in a world (`world/`) with an onlooker in it (tag E): an Other
outside the agent and outside its host, who sees the agent's acts, or the lack
of one, and says what it sees; the host hears it. `--alone` leaves it out.

Nothing here submits to the competition.
"""
from _paths import SRC, STARTER, DATA  # noqa: E402 — see scripts/_paths.py
import argparse, collections, json, os, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(STARTER)); sys.path.insert(0, str(STARTER / "vendor" / "ARC-AGI-3-Agents"))
sys.path.insert(0, str(SRC))

import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction

from arc3 import transducers
from arc3.host import create_source, declaration
from arc3.mind import ModelEndpoint, create_mind, mind_rule
from arc3.learning_mind import create_learning_mind, learning_rule
from arc3.observe import admit
from world import Onlooker, World
from arc3.command import carrying_out
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
ap.add_argument("--mind", choices=("language", "learning"), default="language",
                help="which mind sits in the one seat: the language model's (mind.py), or the one that "
                     "learns from nothing (learning_mind.py)")
ap.add_argument("--offline-dir", default=None,
                help="play the environment files in this directory (Kaggle), not the starter kit's")
ap.add_argument("--alone", action="store_true", help="no onlooker: the agent meets only the region")
ap.add_argument("--out", default=None, help="where the store goes (default: a fresh dir under scripts/data)")
ap.add_argument("--remote", default=None,
                help="HOST:PORT of the regions served by run_competition.py; the key is in DIL_REGIONS_KEY")
a = ap.parse_args()

if a.remote:
    # The game was made in another process, on the one arcade and scorecard
    # a scored run allows (`world/remote.py`).
    from world.remote import RemoteRegion
    host, port = a.remote.rsplit(":", 1)
    region = RemoteRegion((host, int(port)), os.environ["DIL_REGIONS_KEY"].encode(), a.game)
else:
    if a.offline_dir:
        arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=a.offline_dir)
    else:
        arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
    region = arc.make(a.game)
world = region if a.alone else World(region, others={"onlooker": Onlooker()})
source = create_source(world, GameAction, action_budget=a.cycles)
host_source = source
# What this served model needs beyond the standard request: Qwen3 thinks unless
# told not to. The mind itself knows no model.
extra = {} if a.think else {"chat_template_kwargs": {"enable_thinking": False}}
LEARNING = a.mind == "learning"
if LEARNING:
    mind = create_learning_mind()
    seat = learning_rule(mind)
else:
    mind = create_mind(ModelEndpoint(url=a.endpoint, model=a.model, max_tokens=a.max_tokens, extra=extra))
    seat = mind_rule(mind)
layers = Layers(
    t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
    t5=create_t5(predict=seat), t6=create_t6(),
    t7=create_t7(attention_span=4.0), t8=create_t8(),
)
store_root = a.out or tempfile.mkdtemp(prefix=f"run-{a.game}-", dir=str(DATA))
daemon = Daemon(
    host=declaration(a.game, store_root=store_root, onlooker=not a.alone), source=host_source, layers=layers,
    glob=create_glob_mod(), initial_emission=Emission(action=None), respond=carrying_out(source),
    admit=admit,
)
gate = daemon.start()
print("gate:", type(gate).__name__, " store:", store_root, flush=True)

t0 = time.time()
n = 0
while daemon.step():
    n += 1
    last = mind.thoughts[-1] if mind.thoughts else None
    if LEARNING:
        print(f"cycle {n - 1:3d}  learned {mind.version}  "
              + (f"chose {last.act} — {last.why}" + (f" (odds {last.odds:.2f})" if last.odds is not None else "")
                 if last else ""), flush=True)
        continue
    print(f"cycle {n - 1:3d}  frame calls {mind.frame_calls}  program v{mind.version}  "
          f"thoughts {len(mind.thoughts)}"
          + (f" on {last.on}" if last else "")
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
queries = [r for r in kind("emission") if r.issuing_layer == 5 and r.action.get("kind") == "query"]
programs = [(k, d) for k, d in daemon._data.entries() if d.open.get("kind") == "program"]
commits = daemon._commits.list() if daemon._commits is not None else []
report = check_conformance(daemon._events)
scar_sources = collections.Counter(r.event.source_id for r in recs if type(r).__name__ == "EventRecord")
remarks = [(k, {x: v for x, v in d.payload.items() if x != "entity"}) for k, d in daemon._data.entries()
           if d.open.get("kind") == "remark" and d.payload.get("remark")]

print(f"\n=== {a.game}  cycles={n}  wall={time.time() - t0:.0f}s ===")
print(f"  frames                : {len(frames)}  by provenance {dict(by_prov)}")
print(f"  frame scars by cycle  : {[r.anchor.cycle for r in frame_scars]}")
print(f"  scars by source       : {dict(scar_sources)}")
print(f"  onlooker's remarks    : {len(remarks)} cycles  first {remarks[:3]}")
print(f"  mind asked the store  : {len(queries)} times  cues {sorted({json.dumps(q.action['cue']) for q in queries})}")
print(f"  programs in [data]    : {[(k, d.fixed.provenance, d.payload.get('version')) for k, d in programs]}")
program_ids = {k for k, _ in programs}
answers = [d for _, d in daemon._data.entries() if d.open.get("kind") == "thought"]
print(f"  program moves         : {[(r.datum_id, r.from_, r.to, r.cycle_mark) for r in kind('provenance') if r.datum_id in program_ids]}")
print(f"  answers kept          : {len(answers)}  program not taken: {sum(1 for d in answers if not d.payload.get('kept'))}")
print(f"  revisions             : {[(r.datum_id, r.cycle_mark) for r in kind('revision')]}")
print(f"  commits               : {len(commits)}")
if LEARNING:
    learned = [d for _, d in daemon._data.entries() if d.open.get("kind") == "transition"]
    why = collections.Counter(t.why.split(" (")[0] for t in mind.thoughts)
    print(f"  transitions learned   : {len(learned)}  no longer holding: {sum(1 for d in learned if not d.payload.get('holds'))}")
    print(f"  states met            : {len(mind._grid_of)} (grids {len(mind._raw)}; clock rows {sorted(mind.clock)})")
    print(f"  held off the clock    : {sum(mind.holds_off_clock)} of {len(mind.holds_off_clock)}")
    print(f"  why it chose          : {dict(why)}")
    print(f"  kinds of act          : {len(mind._kinds)}  (tried, changed, levels) most tried "
          f"{sorted(mind._kinds.items(), key=lambda kv: -kv[1][0])[:6]}")
else:
    print(f"  thoughts              : {[(t.frame_call, t.on, t.evidence, t.held_score, t.candidate_score, t.adopted, t.usage.get('completion_tokens'), t.usage.get('seconds'), t.note) for t in mind.thoughts]}")
    print(f"  what the model asked  : {[(t.frame_call, t.asked) for t in mind.thoughts if t.asked]}")
print(f"  the mind's commands   : {[(c, p[0] if p else None) for c, p in mind.commands]}")
print(f"  frame expectation held: {sum(mind.holds)} of {len(mind.holds)}")
print(f"  the body stood still  : {source.waits} cycles")
print(f"  the GOAL held         : {mind._goal and {k: v for k, v in mind._goal.items() if k != 'reached_when'}}")
held_scars = collections.Counter(r.datum_id.split('-')[0] for r in recs if type(r).__name__ == "EventRecord")
print(f"  scars by datum kind   : {dict(held_scars)}")
print(f"  [event] records       : {len(recs)}")
print(f"  conformance           : {[(r.id, r.verdict) for r in report.results]}")
for r in report.results:
    if r.id in ("5", "7"):
        print(f"    C{r.id}: {r.detail}")
print(f"  moves committed       : {dict(collections.Counter(m.action_id for m in source.delivered))}")
print(f"  final state           : {source.frame.state}  levels={source.frame.levels_completed}")
if mind.code:
    print("\n--- the program the mind holds ---\n" + mind.code)
