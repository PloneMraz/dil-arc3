"""Which reading of identity makes a thing stay the same thing?

A kind that changes when the thing changes shape is not an identity. Measured
rather than argued: for each candidate, how many kinds exist overall against how
many are present in a frame. A stable identity keeps those two close.
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys, collections
sys.path.insert(0, str(SRC))
from arc3.perceive import segment

rows = pickle.loads(open(sys.argv[1], "rb").read())

variants = {
    "value+bbox (current)": lambda r: f"{r.value}:{r.height}x{r.width}",
    "value+size":           lambda r: f"{r.value}:{r.size}",
    "value only":           lambda r: f"{r.value}",
    "value+channel":        lambda r: f"{r.value}@{r.channel}",
}

for game in ("ls20", "vc33"):
    seq = [r for r in rows if r[0] == game][:60]
    print(f"\n=== {game} ===")
    print(f"  {'identity':<22} {'overall':>8} {'per-frame':>10} {'churn':>7} {'moving':>7}")
    for name, key in variants.items():
        overall, per_frame, moving = set(), [], collections.Counter()
        for _g, _a, prev, now in seq:
            rp, rn = segment(prev), segment(now)
            ks = {key(r) for r in rp}
            overall |= ks
            per_frame.append(len(ks))
            bp = {key(r): r.centroid for r in rp}
            bn = {key(r): r.centroid for r in rn}
            for k in bp.keys() & bn.keys():
                if bp[k] != bn[k]:
                    moving[k] += 1
        mean_pf = sum(per_frame) / len(per_frame)
        churn = len(overall) / mean_pf
        print(f"  {name:<22} {len(overall):>8} {mean_pf:>10.1f} {churn:>7.1f}x {len(moving):>7}")
