"""Can individual pieces be tracked with a stable identity — and does it pay?

Kind-level identity (all cells of value 9 are one Other) held churn at 1.0x but
merged the moving piece with four static ones, so any reading of what surrounds
"thing:9" was swamped by the four that never move. This tracks each piece across
frames by nearest centroid within its value, measures whether the identity holds,
and measures whether the MOVING piece's own surroundings finally predict whether
it is blocked.

Prediction stays honest: surroundings are read off `prev` only, the outcome is
never used to choose which piece to look at.
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys, collections, math
sys.path.insert(0, str(SRC))
from arc3.perceive import segment, background_of

DIRS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


def ahead_of_piece(frame, piece):
    """First other stuff met on each side of ONE piece (any distance)."""
    grid = frame.grids[piece.channel]
    bg = background_of(grid)
    R, C = len(grid), len(grid[0])
    r0, c0, r1, c1 = piece.bbox
    out = {}
    for d, (dr, dc) in DIRS.items():
        met = set()
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if grid[r][c] != piece.value:
                    continue
                nr, nc = r + dr, c + dc
                while 0 <= nr < R and 0 <= nc < C and grid[nr][nc] in (bg, piece.value):
                    nr += dr; nc += dc
                met.add(f"{grid[nr][nc]}" if 0 <= nr < R and 0 <= nc < C else "edge")
        out[d] = ",".join(sorted(met))
    return "|".join(f"{d}:{out[d]}" for d in DIRS)


class Tracker:
    def __init__(self):
        self.next_id = 0
        self.tracked = []  # (id, value, centroid)

    def assign(self, pieces):
        free = list(self.tracked)
        ids = []
        for p in pieces:
            same = [t for t in free if t[1] == p.value]
            if same:
                best = min(same, key=lambda t: math.dist(t[2], p.centroid))
                free.remove(best)
                ids.append(best[0])
            else:
                ids.append(self.next_id); self.next_id += 1
        self.tracked = [(i, p.value, p.centroid) for i, p in zip(ids, pieces)]
        return ids


rows = pickle.loads(open(sys.argv[1], "rb").read())
for game in ("ls20", "vc33"):
    seq = [r for r in rows if r[0] == game]
    tr = Tracker()
    seen_ids, per_frame = set(), []
    votes, hit, n = {}, 0, 0
    mover_hit = mover_n = 0
    per_id = {}
    for _g, act, prev, now in seq:
        action = "action:6" if act.startswith("6@") else f"action:{act}"
        pp = segment(prev)
        pid = tr.assign(pp)
        seen_ids |= set(pid); per_frame.append(len(pid))
        # match now's pieces to prev's ids, to read each tracked piece's outcome
        now_pieces = segment(now)
        before = {i: p for i, p in zip(pid, pp)}
        free = list(now_pieces)
        for i, p in before.items():
            same = [q for q in free if q.value == p.value]
            if not same:
                outcome = "gone"
            else:
                q = min(same, key=lambda q: math.dist(q.centroid, p.centroid))
                free.remove(q)
                outcome = (round(q.centroid[0] - p.centroid[0]), round(q.centroid[1] - p.centroid[1]))
            ctx = f"{action}#{ahead_of_piece(prev, p)}"
            k = (f"{p.value}#{i}", ctx)
            if k in votes:
                ok = votes[k].most_common(1)[0][0] == outcome
                n += 1; hit += ok
                if game == "ls20" and action == "action:1":
                    per_id.setdefault(i, [0, 0, set()]); per_id[i][0] += ok; per_id[i][1] += 1; per_id[i][2].add(outcome)
                if False:
                    mover_n += 1; mover_hit += ok
            votes.setdefault(k, collections.Counter())[outcome] += 1
    churn = len(seen_ids) / (sum(per_frame) / len(per_frame))
    print(f"=== {game} ===")
    print(f"  tracked ids overall {len(seen_ids)}, pieces per frame {sum(per_frame)/len(per_frame):.1f}, churn {churn:.1f}x")
    print(f"  per-piece prediction (action + what lies ahead of THAT piece): {100*hit//max(n,1)}% ({n})")
    if game == "ls20":
        movers = {i: v for i, v in per_id.items() if any(o not in ((0, 0), "gone") for o in v[2])}
        for i, (h, t, outs) in sorted(movers.items()):
            print(f"  MOVING piece id {i}: under ACTION1 {100*h//max(t,1)}% ({t}), outcomes seen {sorted(map(str, outs))}")
        print(f"  value-9 pieces under ACTION1: {100*mover_hit//max(mover_n,1)}% ({mover_n})")
