"""A live game with the one mind in the loop: the mind learns, DIL runs.

    $PY scripts/run_game.py GAME CYCLES [--inducer grid] [--alone] [--offline-dir DIR]
        [--remote HOST:PORT] [--out DIR]
    $PY scripts/run_game.py GAME CYCLES --inducer language --endpoint URL [--model NAME]
        [--max-tokens N] [--think] [...]      (a served language model the mind learns with)

The host carries the whole frame; the mind expects it from the hypotheses its
learning holds, computed by its model — the inducer — and thinks when an
expectation meets a mismatch — the frame, the status, the onlooker — or while
the body waits. Each hypothesis, each choice and each thought is kept as data.
What is printed is read back from the run's own `[event]` log, `[data]` and
commits — the same ones a third party would read.

`--inducer language` is a served language model the mind learns with; ARC-AGI-3
is not played with it for now (Plone, 2026-09-28).

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
from arc3.decisions import situation_fit
from arc3.organs import ARC_ORGANS
from arc3.task import TASK_CUE
from mind.learning import ATTENTION_K, CURIOSITY, MAX_IMAGINED_STEPS
from mind.mind import Mind, mind_rule as seat_rule
from mind.models.objects import ObjectsInducer
from mind.models.grid import GridInducer
from mind.models.language import ModelEndpoint
from mind.models.language_inducer import LanguageInducer
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

# This host's commit cadence, declared by the run: every 12 scars (Plone,
# 2026-09-28). dil-core declares 9 (dil/store/decisions.py, COMMIT_EVERY).
COMMIT_EVERY_HERE = 12

ap = argparse.ArgumentParser()
ap.add_argument("game", nargs="?", default="ls20")
ap.add_argument("cycles", nargs="?", type=int, default=10)
ap.add_argument("--endpoint", default="http://127.0.0.1:8080/v1")
ap.add_argument("--model", default="local")
ap.add_argument("--max-tokens", type=int, default=12288)
ap.add_argument("--think", action="store_true")
ap.add_argument("--inducer", choices=("grid", "objects", "language"), default="grid",
                help="the mind's model, what its learning computes with: hypotheses that reach past where they "
                     "were met (mind/models/grid.py), moves of things (mind/models/objects.py, on trial), or "
                     "programs a served language model writes "
                     "(mind/models/language_inducer.py, at --endpoint)")
ap.add_argument("--curiosity", choices=CURIOSITY, default=CURIOSITY[0],
                help="what the mind counts as worth trying: new (S2b, the default), changed (S2), "
                     "new-then-changed (S2c), new-plus-changed (S2d) — mind/learning.py")
ap.add_argument("--attention", action="store_true",
                help="weigh how much an act is wanted by what it did in the situations most like where it "
                     "stands, not everywhere (idea (a), mind/learning.py: ATTENTION_K)")
ap.add_argument("--look-ahead", type=int, default=MAX_IMAGINED_STEPS,
                help="how many steps the mind looks ahead past where it has stood, on what its hypotheses "
                     "predict (mind/learning.py: MAX_IMAGINED_STEPS)")
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
# The one mind, neutral, with its learning; its model's seat takes the inducer.
# The host declares its organs, and the mind reads the task for its goal.
if a.inducer == "language":
    inducer = LanguageInducer(ARC_ORGANS, ModelEndpoint(url=a.endpoint, model=a.model,
                                                        max_tokens=a.max_tokens, extra=extra))
elif a.inducer == "objects":
    inducer = ObjectsInducer(ARC_ORGANS)
else:
    inducer = GridInducer(ARC_ORGANS)
mind = Mind(inducer, ARC_ORGANS, priors={"task": TASK_CUE}, curiosity=a.curiosity,
            attention=a.attention, look_ahead=a.look_ahead)
seat = seat_rule(mind)
layers = Layers(
    t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
    t5=create_t5(predict=seat, fit=situation_fit), t6=create_t6(),
    t7=create_t7(attention_span=4.0), t8=create_t8(),
)
store_root = a.out or tempfile.mkdtemp(prefix=f"run-{a.game}-", dir=str(DATA))
daemon = Daemon(
    host=declaration(a.game, store_root=store_root, onlooker=not a.alone), source=host_source, layers=layers,
    glob=create_glob_mod(), initial_emission=Emission(action=None), respond=carrying_out(source),
    admit=admit,
    # The scar rhythm alone (Plone, 2026-09-27; decisions.COMMIT_CADENCE): the
    # learning revises data in place (2026-10-04), and what a datum holds is in
    # `[data]`; a commit's snapshot is for recovery, not reading (v0.3.6 §9).
    commit_on_write=False,
    # `[data]` and `[event]` synced to disk once a cycle, not each write (Plone,
    # 2026-10-04: a machine's crash loses at most the cycle running; recovery is
    # the commits'). The syncs of each were about 60% of a run (LOG.md).
    sync_each_cycle=True,
    # A commit every 12 scars, not dil-core's 9 (Plone, 2026-09-28): a commit is
    # the costliest thing a cycle does (decisions.COMMIT_EVERY; LOG.md).
    commit_every=COMMIT_EVERY_HERE,
)
gate = daemon.start()
print("gate:", type(gate).__name__, " store:", store_root, flush=True)

t0 = time.time()
n = 0
while daemon.step():
    n += 1
    last = mind.thoughts[-1] if mind.thoughts else None
    print(f"cycle {n - 1:3d}  learned {mind.version}  "
          + (f"chose {last.act} — {last.why}" + (f" (odds {last.odds:.2f})" if last.odds is not None else "")
             if last else ""), flush=True)
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
read_lines = kind("read")
print(f"  read of [data]        : by purpose, lines and data named "
      f"{ {p: (sum(1 for r in read_lines if r.purpose == p), sum(len(r.read) for r in read_lines if r.purpose == p)) for p in sorted({r.purpose for r in read_lines})} }")
learned = [d for _, d in daemon._data.entries() if d.open.get("kind") == "hypothesis"]
why = collections.Counter(t.why.split(" (")[0] for t in mind.thoughts)
print(f"  hypotheses written    : {len(learned)}  not holding now: {sum(1 for d in learned if not d.payload.get('holds'))}; "
      f"experiences {len([d for _, d in daemon._data.entries() if d.open.get('kind') == 'experience'])}")
print(f"  states met            : {len(mind.learning._raw_of)} (grids {len(mind.learning._raw)}; clock rows {sorted(mind.learning.inducer.clock)}, columns {sorted(mind.learning.inducer.clock_columns)})")
print(f"  held off the clock    : {sum(mind.learning.holds_by_situation)} of {len(mind.learning.holds_by_situation)}")
held = sum(1 for h in mind.learning._hypotheses if h.holds)
print(f"  inducer               : {mind.learning.inducer.kind}  hypotheses {len(mind.learning._hypotheses)} (held {held})")
print(f"  unseen (situation, act): {mind.learning.unseen[0]}  expected {mind.learning.unseen[1]}  right {mind.learning.unseen[2]}")
print(f"  why it chose          : {dict(why)}")
if a.curiosity != CURIOSITY[0]:
    print(f"  curiosity             : {a.curiosity}  changes by kind "
          f"{sorted(mind.learning._kind_changes.items(), key=lambda kv: -kv[1])[:6]}")
if a.look_ahead != MAX_IMAGINED_STEPS:
    print(f"  look-ahead            : {a.look_ahead} steps past where it stood")
if a.attention:
    print(f"  attention             : the {ATTENTION_K} experiences most alike")
if a.inducer == "language":
    answers = mind.learning.inducer.answers
    why_not = collections.Counter((t["why_not"] or "")[:60] for t in answers if not t["program"])
    print(f"  the model's answers   : {len(answers)}  programs {sum(1 for t in answers if t['program'])}  "
          f"seconds {sum(t['seconds'] or 0 for t in answers):.0f}  not a hypothesis {dict(why_not)}")
    print(f"  its readings          : {len([1 for _, d in daemon._data.entries() if d.open.get('kind') == 'reading'])}")
print(f"  kinds of act          : {len(mind.learning._kinds)}  (tried, somewhere new, levels) most tried "
      f"{sorted(mind.learning._kinds.items(), key=lambda kv: -kv[1][0])[:6]}")
print(f"  the mind's commands   : {[(c, p[0] if p else None) for c, p in mind.commands]}")
print(f"  frame expectation held: {sum(mind.holds)} of {len(mind.holds)}")
print(f"  the body stood still  : {source.waits} cycles")
print(f"  the aim held          : {mind._aim and {k: v for k, v in mind._aim.items() if k != 'reached_when'}}")
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
