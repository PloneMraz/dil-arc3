"""Does conditioning on where the move lands beat predicting last-time?

Same transitions, same order, same fallback. The only difference is whether the
expectation is conditioned on the context. Accrual is sequential in both, so
neither sees anything the other could not have.
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys
from collections import Counter
sys.path.insert(0, str(SRC))
from arc3 import Move, affordance_key, diff
from arc3.model import create_model

rows = pickle.loads(open(sys.argv[1], "rb").read())

for game in ("ls20", "vc33"):
    seq = [r for r in rows if r[0] == game]
    model = create_model()
    last: dict[str, object] = {}
    hit_m = hit_p = n = 0
    ctx_used = 0

    for _g, act, prev, now in seq:
        move = Move(6, *map(int, act[2:].split(","))) if act.startswith("6@") else Move(int(act))
        entity = affordance_key(move)
        effect = diff(prev, now)

        context = model.context(prev, entity)
        if context:
            ctx_used += 1

        p_pred = last.get(entity)
        m_pred = model.predict(entity, context)

        if p_pred is not None:
            n += 1
            hit_p += int(p_pred == effect)
            hit_m += int(m_pred == effect)

        model.observe(entity, context, effect)
        last[entity] = effect

    print(f"\n=== {game} ===  predictions scored: {n}")
    print(f"  persistence      : {hit_p:>4}/{n}  ({100*hit_p//max(n,1)}%)")
    print(f"  context-conditioned: {hit_m:>4}/{n}  ({100*hit_m//max(n,1)}%)")
    print(f"  mover learned    : {model.mover}   contexts known: {model.contexts_known()}")
    print(f"  cycles with a non-empty context: {ctx_used}/{len(seq)}")
    for e in sorted({affordance_key(Move(6, *map(int, a[2:].split(',')))) if a.startswith('6@') else affordance_key(Move(int(a))) for _g, a, _p, _n in seq}):
        print(f"    {e}: displacement learned = {model.displacement(e)}")
