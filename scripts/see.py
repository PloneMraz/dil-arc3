"""What does segmentation actually see? Measured before anything is wired to it."""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys, collections, time
sys.path.insert(0, str(SRC))
from arc3.perceive import segment, background_of

rows = pickle.loads(open(sys.argv[1], "rb").read())

for game in ("ls20", "vc33"):
    seq = [r for r in rows if r[0] == game]
    t0 = time.perf_counter()
    per_frame, kinds, kind_counts = [], collections.Counter(), []
    moved = collections.Counter()
    for _g, _act, prev, now in seq[:60]:
        rp = segment(prev)
        rn = segment(now)
        per_frame.append(len(rp))
        for r in rp:
            kinds[r.kind] += 1
        kind_counts.append(len({r.kind for r in rp}))
        # which kinds changed centroid between the two frames?
        bp = {r.kind: r.centroid for r in rp}
        bn = {r.kind: r.centroid for r in rn}
        for k in bp.keys() & bn.keys():
            if bp[k] != bn[k]:
                moved[k] += 1
    dt = (time.perf_counter() - t0) / max(1, len(per_frame))

    print(f"\n=== {game} ===  ({len(per_frame)} frames, {dt*1000:.1f} ms/frame to segment both)")
    print(f"  regions per frame : min={min(per_frame)} max={max(per_frame)} mean={sum(per_frame)/len(per_frame):.1f}")
    print(f"  distinct kinds per frame: mean={sum(kind_counts)/len(kind_counts):.1f}")
    print(f"  distinct kinds overall  : {len(kinds)}")
    print("  most common kinds:")
    for k, n in kinds.most_common(6):
        print(f"     {k:<22} seen in {n} frames" + ("   <- MOVES" if moved.get(k) else ""))
    print(f"  kinds that ever moved: {len(moved)}  {dict(moved.most_common(4))}")
