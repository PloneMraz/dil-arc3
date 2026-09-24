"""Does what happens to a thing repeat, given the action taken?

The new mapping is entity = thing, context = action. T5 can only learn if the
pair repeats. Measured against the same 316 real transitions the old mapping was
measured on, so the two are comparable.
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys, collections
sys.path.insert(0, str(SRC))
from arc3.interpret import changes_of

rows = pickle.loads(open(sys.argv[1], "rb").read())

for game in ("ls20", "vc33"):
    seq = [r for r in rows if r[0] == game]
    seqs = collections.defaultdict(list)
    for _g, act, prev, now in seq:
        action = "action:6" if act.startswith("6@") else f"action:{act}"
        for kind, ch in changes_of(prev, now).items():
            seqs[(kind, action)].append(ch)

    last, votes = {}, {}
    hit_p = hit_v = n = 0
    for _g, act, prev, now in seq:
        action = "action:6" if act.startswith("6@") else f"action:{act}"
        for kind, ch in changes_of(prev, now).items():
            key = (kind, action)
            if key in last:
                n += 1
                hit_p += int(last[key] == ch)
                hit_v += int(votes[key].most_common(1)[0][0] == ch)
            last[key] = ch
            votes.setdefault(key, collections.Counter())[ch] += 1

    entities = {k for k, _ in seqs}
    print(f"\n=== {game} ===")
    print(f"  entities (things)   : {len(entities)}  -> {sorted(entities)[:6]}")
    print(f"  (entity, action) keys: {len(seqs)}")
    print(f"  predictions scored  : {n}")
    print(f"  most-recent  : {hit_p}/{n} ({100*hit_p//max(n,1)}%)")
    print(f"  majority     : {hit_v}/{n} ({100*hit_v//max(n,1)}%)")
    interesting = [(k, len(set(v)), len(v)) for k, v in seqs.items() if len(set(v)) > 1]
    print(f"  keys with >1 outcome: {len(interesting)}/{len(seqs)}")
    for k, d, tot in sorted(interesting, key=lambda x: -x[2])[:4]:
        print(f"     {k[0]:<12} {k[1]:<10} {d} distinct over {tot}")
