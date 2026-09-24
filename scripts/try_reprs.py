"""Try candidate effect representations against 316 real transitions.

The question is not "does it repeat" but "does it repeat AND tell the actions
apart". A representation that collapses everything to one signature repeats
perfectly and is worthless.
"""
from _paths import SRC  # noqa: E402 — see scripts/_paths.py
import pickle, sys
from collections import Counter, defaultdict
sys.path.insert(0, str(SRC))

rows = pickle.loads(open(sys.argv[1], "rb").read())


def cell_deltas(prev, now):
    van, app = defaultdict(list), defaultdict(list)
    trans = Counter()
    n = 0
    for gi in range(min(prev.depth, now.depth)):
        for r, (pr, nr) in enumerate(zip(prev.grids[gi], now.grids[gi])):
            for c, (pv, nv) in enumerate(zip(pr, nr)):
                if pv != nv:
                    n += 1; trans[(pv, nv)] += 1
                    van[pv].append((r, c)); app[nv].append((r, c))
    return n, trans, van, app


def centroid(cs):
    return (sum(r for r, _ in cs) / len(cs), sum(c for _, c in cs) / len(cs))


def disp(van, app, rigid: bool, min_cells: int):
    out = []
    for v in sorted(set(van) & set(app)):
        g, a = van[v], app[v]
        if len(g) < min_cells or len(a) < min_cells:
            continue
        if rigid and len(g) != len(a):
            continue
        gr, gc = centroid(g); ar, ac = centroid(a)
        out.append((v, round(ar - gr), round(ac - gc)))
    return tuple(out)


def v0(p, n_):
    n, tr, van, app = cell_deltas(p, n_)
    return (n, tuple(sorted((a, b, k) for (a, b), k in tr.items())), disp(van, app, False, 1))

def v1(p, n_):
    n, tr, van, app = cell_deltas(p, n_)
    return (n, tuple(sorted((a, b, k) for (a, b), k in tr.items())), disp(van, app, True, 1))

def v2(p, n_):
    n, tr, van, app = cell_deltas(p, n_)
    return (disp(van, app, True, 1),)

def v3(p, n_):
    n, tr, van, app = cell_deltas(p, n_)
    d = disp(van, app, True, 1)
    return (d, 0 if n == 0 else 1)

def v4(p, n_):
    """Displacements of rigid values with at least 2 cells — drop single-cell
    noise — plus whether anything changed at all."""
    n, tr, van, app = cell_deltas(p, n_)
    return (disp(van, app, True, 2), 0 if n == 0 else 1)


def score(fn, name):
    by_game = defaultdict(lambda: defaultdict(Counter))
    for game, act, p, n_ in rows:
        by_game[game][fn(p, n_)][act] += 1
    print(f"\n--- {name} ---")
    for game, table in sorted(by_game.items()):
        total = sum(sum(c.values()) for c in table.values())
        pure = sum(sum(c.values()) for c in table.values() if len(c) == 1)
        acts = sorted({a for c in table.values() for a in c})
        # how many signatures does each single action get split across?
        per_act = defaultdict(set)
        for sig, c in table.items():
            for a in c:
                per_act[a].add(sig)
        spread = ", ".join(f"{a}:{len(s)}" for a, s in sorted(per_act.items()))
        print(f"  {game:6} sigs={len(table):>3}  action-pure={pure}/{total} "
              f"({100*pure//total}%)  sigs-per-action[{spread}]")


for fn, name in ((v0, "v0 current"), (v1, "v1 rigid only"),
                 (v2, "v2 rigid disp only"), (v3, "v3 disp + changed-flag"),
                 (v4, "v4 disp>=2 cells + changed-flag")):
    score(fn, name)
