"""Does the SHIPPED arc3.effect.diff reproduce the v1 numbers?

The variant study used its own copy of the logic. This runs the module that will
actually be imported, over the same 316 transitions.
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys
from collections import Counter, defaultdict
sys.path.insert(0, str(SRC))
from arc3.effect import diff

rows = pickle.loads(open(sys.argv[1], "rb").read())
by_game = defaultdict(lambda: defaultdict(Counter))
for game, act, p, n in rows:
    by_game[game][diff(p, n)][act] += 1

for game, table in sorted(by_game.items()):
    total = sum(sum(c.values()) for c in table.values())
    pure = sum(sum(c.values()) for c in table.values() if len(c) == 1)
    per_act = defaultdict(set)
    for sig, c in table.items():
        for a in c:
            per_act[a].add(sig)
    spread = ", ".join(f"{a}:{len(s)}" for a, s in sorted(per_act.items()))
    print(f"{game:6} sigs={len(table):>3}  action-pure={pure}/{total} "
          f"({100*pure//total}%)  sigs-per-action[{spread}]")

print()
print("The control scheme, as the representation recovers it from ls20:")
seen = {}
for game, act, p, n in rows:
    if game != "ls20":
        continue
    e = diff(p, n)
    if e.displacements:
        seen.setdefault(act, Counter())[e.displacements] += 1
for act in sorted(seen):
    top, k = seen[act].most_common(1)[0]
    print(f"  ACTION{act}: {top}   (seen {k}x)")
