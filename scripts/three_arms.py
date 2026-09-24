"""Separate the two things the model does.

It changed TWO things at once: it votes by majority over accrued evidence
instead of taking the most recent, and it conditions on context. Reporting the
combined number would credit context with wins that majority alone produces.
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys
from collections import Counter
sys.path.insert(0, str(SRC))
from arc3 import Move, affordance_key, diff
from arc3.model import create_model

rows = pickle.loads(open(sys.argv[1], "rb").read())

def as_move(act):
    return Move(6, *map(int, act[2:].split(","))) if act.startswith("6@") else Move(int(act))

for game in ("ls20", "vc33"):
    seq = [r for r in rows if r[0] == game]
    model = create_model()
    last = {}
    votes = {}            # entity -> Counter[effect], no context
    hit_p = hit_v = hit_m = n = 0

    for _g, act, prev, now in seq:
        entity = affordance_key(as_move(act))
        effect = diff(prev, now)
        context = model.context(prev, entity)

        p_pred = last.get(entity)
        v_pred = votes[entity].most_common(1)[0][0] if entity in votes else None
        m_pred = model.predict(entity, context)

        if p_pred is not None:
            n += 1
            hit_p += int(p_pred == effect)
            hit_v += int(v_pred == effect)
            hit_m += int(m_pred == effect)

        model.observe(entity, context, effect)
        last[entity] = effect
        votes.setdefault(entity, Counter())[effect] += 1

    pc = lambda h: f"{h:>4}/{n} ({100*h//max(n,1):>3}%)"
    print(f"\n=== {game} ===")
    print(f"  most-recent  (dil-core persistence) : {pc(hit_p)}")
    print(f"  majority     (accrued, no context)  : {pc(hit_v)}")
    print(f"  majority + context (the model)      : {pc(hit_m)}")
    print(f"  mover={model.mover}  contexts={model.contexts_known()}")
    for a in sorted({affordance_key(as_move(x[1])) for x in seq}):
        print(f"    {a}: displacement={model.displacement(a)}")
