"""A live game with the prior admitted: is the directive recalled, and does want change?"""
from _paths import SRC, STARTER, DATA  # noqa: E402 — see scripts/_paths.py
import sys, collections, tempfile
from pathlib import Path
ROOT = STARTER
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
sys.path.insert(0, str(SRC))

import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction

from arc3 import transducers
from arc3.host import create_source, declaration
from arc3.mind import create_mind, predict_rule
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
from dil.store.event_log import create_event_log

game = sys.argv[1] if len(sys.argv) > 1 else "ls20"
budget = int(sys.argv[2]) if len(sys.argv) > 2 else 60

arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
mind = create_mind()
source = create_source(arc.make(game), GameAction, action_budget=budget)
clock = [1_800_000_000_000]
def now():
    clock[0] += 1000
    return clock[0]

t8 = create_t8()
_orig = t8.process
tally = collections.Counter()
others_seen = []
def wrapped(inp, field, emit, contribute):
    out = _orig(inp, field, emit, contribute)
    tally["RelValue"] += len(out.rel_values)
    tally["SocialEdge"] += len(out.social_edges)
    others_seen.append(len(inp.others))
    return out
t8.process = wrapped

t2 = create_t2()
_t2p = t2.process
agency = collections.Counter()
def t2spy(inp, field, emit, contribute):
    out = _t2p(inp, field, emit, contribute)
    for tc in out.tagged:
        kind = "self:move" if tc.change.id == "self:move" else ("store" if tc.change.id.startswith("prior:") else "other")
        agency[(kind, tc.agency)] += 1
    return out
t2.process = t2spy
glob = create_glob_mod()
layers = Layers(
    t1=create_t1(), t2=t2, t3=create_t3(transducers()), t4=create_t4(),
    t5=create_t5(predict=predict_rule(mind)), t6=create_t6(),
    t7=create_t7(attention_span=4.0), t8=t8,
)
store_root = tempfile.mkdtemp(prefix=f"prior-{game}-", dir=str(DATA))
daemon = Daemon(
    host=declaration(game, store_root=store_root), source=source, layers=layers, glob=glob,
    initial_emission=Emission(action=None), now=now, respond=least_resolved(),
)
gate = daemon.start()
rep = daemon._requisitioned
print("gate:", type(gate).__name__, " admitted:", rep.admitted, " rejected:", rep.rejected)
n = 0
directive_at = None
positions = []
def _mover_pos(frame):
    cells = [(r, c) for g in frame.grids for r, row in enumerate(g) for c, v in enumerate(row) if v == 12]
    if not cells:
        return None
    return (round(sum(r for r, _ in cells) / len(cells)), round(sum(c for _, c in cells) / len(cells)))
while daemon.step():
    n += 1
    if directive_at is None and mind.directive() is not None:
        directive_at = n - 1
    if source.frame is not None:
        positions.append(_mover_pos(source.frame))
daemon.stop()

recs = daemon._events.all()
scars = collections.Counter(
    r.event.source_id for r in recs if type(r).__name__ == "EventRecord"
)
print(f"\n=== {game}  cycles={n}  actions={source.spent} ===")
print(f"  Others per cycle      : min={min(others_seen)} max={max(others_seen)} mean={sum(others_seen)/len(others_seen):.1f}")
print(f"  T8 RelValue           : {tally['RelValue']}")
print(f"  T8 SocialEdge         : {tally['SocialEdge']}")
print(f"  mind: entities={mind.entities_known()} situations={mind.contexts_known()}")
fp = glob.current().params
print(f"  field (per action)    : {({k: round(v,2) for k,v in sorted(fp.items()) if k.startswith(('progress:','valence:'))})}")
print(f"  field (facts)         : {({k: round(v,2) for k,v in sorted(fp.items()) if not k.startswith(('progress:','valence:'))})}")
print(f"  scars by source       : {dict(scars.most_common(8))}")
print(f"  total scars           : {sum(scars.values())}  (absences: {scars.get('region',0)})")
print(f"  moves committed       : {dict(collections.Counter((m.action_id, m.x, m.y) if m.action_id == 6 else m.action_id for m in source.delivered).most_common(6))}")
pos = [q for q in positions if q is not None]
print(f"  mover positions       : {len(set(pos))} distinct over {len(pos)} cycles; last 12: {pos[-12:]}")
prov = [r for r in recs if getattr(r, "activity_kind", None) == "provenance" and r.datum_id.startswith("prior:")]
qs = [r for r in recs if getattr(r, "activity_kind", None) == "emission" and r.issuing_layer == 3]
print(f"  store queries (T3)    : {[q.action['cue'] for q in qs]}")
print(f"  prior moves           : {[(p.datum_id, p.from_, p.to, p.cycle_mark) for p in prov]}")
print(f"  directive in mind at  : cycle {directive_at}")
print(f"  [data] priors now     : {[(k, d.fixed.provenance, d.fixed.cycle_mark) for k, d in daemon._data.entries() if k.startswith('prior:')]}")
print(f"  T2 agency             : {dict(sorted(agency.items()))}")
print(f"  final state           : {source.frame.state}  levels={source.frame.levels_completed}")
