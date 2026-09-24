"""Is T5 performing as well as its rule ALLOWS, or is something broken?

T5's declared update law is persistence: predict the affordance's most recent
observed effect. The best that rule can possibly score on a given sequence is
the fraction of consecutive pairs that are equal. Comparing T5's actual match
rate against that ceiling separates "the rule is weak here" from "the wiring is
wrong".
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys
from collections import defaultdict
sys.path.insert(0, str(SRC))
from arc3 import Move, affordance_key, diff

rows = pickle.loads(open(sys.argv[1], "rb").read())
for game in ("ls20", "vc33"):
    seqs = defaultdict(list)
    for g, act, prev, now in rows:
        if g != game:
            continue
        move = Move(6, *map(int, act[2:].split(","))) if act.startswith("6@") else Move(int(act))
        seqs[affordance_key(move)].append(diff(prev, now))

    print(f"\n=== {game} ===")
    print(f"{'affordance':<12} {'n':>4} {'distinct':>9} {'persistence ceiling':>20} {'most common share':>18}")
    for k in sorted(seqs):
        s = seqs[k]
        pairs = sum(1 for a, b in zip(s, s[1:]) if a == b)
        ceiling = pairs / max(1, len(s) - 1)
        from collections import Counter
        top = Counter(s).most_common(1)[0][1] / len(s)
        print(f"{k:<12} {len(s):>4} {len(set(s)):>9} {ceiling:>19.0%} {top:>17.0%}")

    # What does the variation consist of?
    for k in sorted(seqs):
        c = Counter(seqs[k])
        nulls = sum(n for e, n in c.items() if e.is_null)
        print(f"  {k}: {nulls}/{len(seqs[k])} were NULL (blocked / nothing happened)")
