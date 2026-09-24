"""The shipped Seeing, on the 316 real transitions — before it is wired in."""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys, collections, time
sys.path.insert(0, str(SRC))
from arc3.seeing import create_seeing
from arc3.interpret import change_value
import json

rows = pickle.loads(open(sys.argv[1], "rb").read())
for game in ("ls20", "vc33"):
    seq = [r for r in rows if r[0] == game]
    seeing = create_seeing()
    ents_overall, per_frame, groups = set(), [], set()
    votes, hit, n = {}, 0, 0
    per_ent = collections.defaultdict(lambda: [0, 0, set()])
    interactions = 0
    t0 = time.perf_counter()
    for _g, act, prev, now in seq:
        action = "action:6" if act.startswith("6@") else f"action:{act}"
        scene = seeing.look(prev, now)
        interactions += len(scene.interactions)
        per_frame.append(len(scene.present))
        for th in scene.things:
            ents_overall.add(th.entity)
            if "+" in th.entity:
                groups.add(th.entity)
            out = json.dumps(change_value(th.change), sort_keys=True)
            k = (th.entity, f"{action}#{th.ahead}")
            if k in votes:
                ok = votes[k].most_common(1)[0][0] == out
                n += 1; hit += ok
                if action == "action:1":
                    e = per_ent[th.entity]; e[0] += ok; e[1] += 1; e[2].add(tuple(th.change.moved) if th.change.moved else None)
            votes.setdefault(k, collections.Counter())[out] += 1
    dt = (time.perf_counter() - t0) / len(seq)
    print(f"=== {game} ===  ({dt*1000:.0f} ms per transition)")
    print(f"  entities overall {len(ents_overall)}, present per frame {sum(per_frame)/len(per_frame):.1f}, churn {len(ents_overall)/(sum(per_frame)/len(per_frame)):.1f}x")
    print(f"  prediction (entity, action + what lies ahead): {100*hit//max(n,1)}% ({n})")
    print(f"  grouped things (common fate): {sorted(groups)[:6]}")
    print(f"  Other-to-Other interactions: {interactions}")
    if game == "ls20":
        for e, (h, t, outs) in sorted(per_ent.items()):
            moving = [o for o in outs if o not in ((0, 0), None)]
            if moving:
                print(f"  MOVER {e:<18} under ACTION1: {100*h//max(t,1)}% ({t})  outcomes {sorted(map(str, outs))}")
