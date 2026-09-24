from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys, collections
sys.path.insert(0, str(SRC))
from arc3.interpret import contacts, interactions_of
rows = pickle.loads(open(sys.argv[1], "rb").read())
for game in ("ls20", "vc33"):
    seq = [r for r in rows if r[0] == game][:80]
    standing = [len(contacts(p)) for _g, _a, p, _n in seq]
    changes = [interactions_of(p, n) for _g, _a, p, n in seq]
    per = [len(c) for c in changes]
    kinds = collections.Counter(k for c in changes for (_a, _b, k) in c)
    pairs = collections.Counter((a, b) for c in changes for (a, b, _k) in c)
    print(f"=== {game} ({len(seq)} transitions) ===")
    print(f"  standing contacts per frame : mean {sum(standing)/len(standing):.1f}")
    print(f"  interactions per transition : mean {sum(per)/len(per):.2f}  max {max(per)}  zero in {per.count(0)}/{len(per)}")
    print(f"  by kind: {dict(kinds)}")
    print(f"  pairs  : {dict(pairs.most_common(5))}")
