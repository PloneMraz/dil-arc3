"""Does reading what surrounds a thing resolve what the action alone cannot?

Measured on the same 316 real transitions every earlier mapping was measured on.
Majority-over-accrued-evidence prediction, sequential (predict, then accrue), so
no variant sees anything another could not have.
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys, collections
sys.path.insert(0, str(SRC))
from arc3.interpret import changes_of
from arc3.perceive import background_of

DIRS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


def surrounds(frame):
    """Per kind: which other kinds lie directly against it, on each side."""
    out = collections.defaultdict(lambda: {d: set() for d in DIRS})
    for grid in frame.grids:
        bg = background_of(grid)
        rows, cols = len(grid), len(grid[0])
        for r in range(rows):
            for c in range(cols):
                v = grid[r][c]
                if v == bg:
                    continue
                for name, (dr, dc) in DIRS.items():
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        w = grid[nr][nc]
                        if w != bg and w != v:
                            out[f"thing:{v}"][name].add(f"thing:{w}")
                    else:
                        out[f"thing:{v}"][name].add("edge")
    return out


def key_undirected(s):
    return ",".join(sorted(set().union(*s.values()))) if s else ""


def key_directed(s):
    return "|".join(f"{d}:{','.join(sorted(s[d]))}" for d in DIRS) if s else ""


rows = pickle.loads(open(sys.argv[1], "rb").read())
for game in ("ls20", "vc33"):
    seq = [r for r in rows if r[0] == game]
    variants = {"action only": None, "A: touching (any side)": key_undirected,
                "B: touching, per side": key_directed}
    print(f"\n=== {game} ===")
    print(f"  {'context':<24} {'overall':>8} {'contexts':>9} {'action:1 all':>13} {'thing:9 @ action:1':>19}")
    for name, keyfn in variants.items():
        votes, hit, n, contexts = {}, 0, 0, set()
        a1_hit = a1_n = m_hit = m_n = 0
        for _g, act, prev, now in seq:
            action = "action:6" if act.startswith("6@") else f"action:{act}"
            sur = surrounds(prev) if keyfn else None
            for kind, ch in changes_of(prev, now).items():
                ctx = action if keyfn is None else f"{action}#{keyfn(sur.get(kind, {}))}"
                contexts.add(ctx)
                k = (kind, ctx)
                if k in votes:
                    ok = votes[k].most_common(1)[0][0] == ch
                    n += 1; hit += ok
                    if action == "action:1":
                        a1_n += 1; a1_hit += ok
                        if kind == "thing:9":
                            m_n += 1; m_hit += ok
                votes.setdefault(k, collections.Counter())[ch] += 1
        pct = lambda h, t: f"{100*h//max(t,1)}% ({t})"
        print(f"  {name:<24} {pct(hit,n):>8} {len(contexts):>9} {pct(a1_hit,a1_n):>13} {pct(m_hit,m_n):>19}")
