"""What lies ahead, per side, at any distance — and does curiosity stop sticking?

Variant C casts a ray from every cell of a kind in each direction and records the
first other kind it meets (or the grid's edge). No distance constant, no
knowledge of what any action does: only what is there to be met on each side.

The real question is per-action resolution. Curiosity stuck on ACTION1 because it
was the uniquely least-resolved action; if a reading equalises resolution across
actions, the stickiness has its cause removed.
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys, collections
sys.path.insert(0, str(SRC))
from arc3.interpret import changes_of
from arc3.perceive import background_of

DIRS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


def touching(frame):
    out = collections.defaultdict(lambda: {d: set() for d in DIRS})
    for grid in frame.grids:
        bg = background_of(grid); R, C = len(grid), len(grid[0])
        for r in range(R):
            for c in range(C):
                v = grid[r][c]
                if v == bg:
                    continue
                for d, (dr, dc) in DIRS.items():
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < R and 0 <= nc < C:
                        w = grid[nr][nc]
                        if w != bg and w != v:
                            out[f"thing:{v}"][d].add(f"thing:{w}")
                    else:
                        out[f"thing:{v}"][d].add("edge")
    return out


def ahead(frame):
    out = collections.defaultdict(lambda: {d: set() for d in DIRS})
    for grid in frame.grids:
        bg = background_of(grid); R, C = len(grid), len(grid[0])
        for r in range(R):
            for c in range(C):
                v = grid[r][c]
                if v == bg:
                    continue
                for d, (dr, dc) in DIRS.items():
                    nr, nc = r + dr, c + dc
                    # skip over own stuff and background; stop at the first other
                    while 0 <= nr < R and 0 <= nc < C and grid[nr][nc] in (bg, v):
                        nr += dr; nc += dc
                    if 0 <= nr < R and 0 <= nc < C:
                        out[f"thing:{v}"][d].add(f"thing:{grid[nr][nc]}")
                    else:
                        out[f"thing:{v}"][d].add("edge")
    return out


def keyed(s):
    return "|".join(f"{d}:{','.join(sorted(s[d]))}" for d in DIRS) if s else ""


rows = pickle.loads(open(sys.argv[1], "rb").read())
for game in ("ls20", "vc33"):
    seq = [r for r in rows if r[0] == game]
    print(f"\n=== {game} ===")
    print(f"  {'context':<22} {'overall':>7} {'ctxs':>5} {'mover@1':>8}   per-action resolution")
    for name, read in (("action only", None), ("B: touching per side", touching),
                       ("C: ahead per side", ahead)):
        votes, hit, n, ctxs = {}, 0, 0, set()
        per = collections.defaultdict(lambda: [0, 0])
        m_hit = m_n = 0
        for _g, act, prev, now in seq:
            action = "action:6" if act.startswith("6@") else f"action:{act}"
            sur = read(prev) if read else None
            for kind, ch in changes_of(prev, now).items():
                ctx = action if read is None else f"{action}#{keyed(sur.get(kind, {}))}"
                ctxs.add(ctx)
                k = (kind, ctx)
                if k in votes:
                    ok = votes[k].most_common(1)[0][0] == ch
                    n += 1; hit += ok
                    per[action][0] += ok; per[action][1] += 1
                    if action == "action:1" and kind == "thing:9":
                        m_n += 1; m_hit += ok
                votes.setdefault(k, collections.Counter())[ch] += 1
        res = "  ".join(f"{a[-1]}:{h/t:.2f}" for a, (h, t) in sorted(per.items()) if t)
        spread = [h / t for h, t in per.values() if t]
        gap = max(spread) - min(spread) if len(spread) > 1 else 0
        print(f"  {name:<22} {100*hit//max(n,1):>6}% {len(ctxs):>5} "
              f"{(100*m_hit//m_n if m_n else 0):>7}%   {res}   (spread {gap:.2f})")
