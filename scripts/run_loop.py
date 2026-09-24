"""Run the real DIL loop over 316 real transitions.

The claim behind the affordance reading is that T5's expectation per affordance
STABILISES — confidence ramps, prediction error falls — which is the agent
learning what its controls do. This runs the actual cycle driver, not a mock of
it, and reports whether that happens.
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys
from collections import defaultdict
sys.path.insert(0, str(SRC))

from arc3 import GAME_CHANNEL, Move, affordance_key, diff, game_transducer, observe
from dil.loop.cycle import Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log

rows = pickle.loads(open(sys.argv[1], "rb").read())
game = sys.argv[2] if len(sys.argv) > 2 else "ls20"
rows = [r for r in rows if r[0] == game]

layers = Layers(
    t1=create_t1(),
    t2=create_t2(),
    t3=create_t3({GAME_CHANNEL: game_transducer}),
    t4=create_t4(),
    t5=create_t5(),
    t6=create_t6(),
    t7=create_t7(),
    t8=create_t8(),
)
clock = [0]
cycle = create_cycle(
    layers=layers, glob=create_glob_mod(), data=create_data_store(),
    events=create_event_log(), initial_emission=Emission(action=None),
    now=lambda: clock[0],
)

t5 = layers.t5
seen = defaultdict(int)
scars_total = 0
absences_total = 0
history = []

for i, (g, act, prev, now) in enumerate(rows):
    if act.startswith("6@"):
        x, y = act[2:].split(",")
        move = Move(6, int(x), int(y))
    else:
        move = Move(int(act))
    clock[0] = 1_800_000_000_000 + i * 1000
    eff = diff(prev, now)
    result = cycle.run(observe(prev, move, now, eff, t=i))
    scars_total += result.scars
    absences_total = absences_total + result.absences
    key = affordance_key(move)
    seen[key] += 1
    snap = t5.snapshot()
    counts = dict(snap["counts"])
    history.append((i, key, result.scars, counts.get(key, 0)))

print(f"game={game}  cycles={len(rows)}  scars={scars_total}  absences={absences_total}")
print("scars per cycle:", round(scars_total / len(rows), 2))
from collections import Counter
print("scar counts per cycle:", dict(Counter(h[2] for h in history)))
print()
print("Per affordance, as T5 accrued it:")
print(f"{'affordance':<12} {'observations':>12} {'confidence':>11}")
counts = dict(t5.snapshot()["counts"])
from dil.loop.decisions import SUFFICIENT_RECURRENCE
for k in sorted(counts):
    conf = min(1.0, counts[k] / SUFFICIENT_RECURRENCE)
    print(f"{k:<12} {counts[k]:>12} {conf:>11.2f}")

print()
print("Did resistance fall as observations accrued? Scars per 40-cycle block:")
block = 40
for start in range(0, len(history), block):
    chunk = history[start:start + block]
    s = sum(c[2] for c in chunk)
    print(f"  cycles {start:>3}-{start+len(chunk)-1:>3}: {s:>3} scars")
