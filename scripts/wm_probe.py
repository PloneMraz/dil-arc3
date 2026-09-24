"""Can a local open model write an executable world model of an ARC-AGI-3 game?

A probe, not part of the agent. The model is shown the opening grid and a set of
transitions (action + the cells that changed), and asked for a Python function
`predict(grid, action) -> grid`. The function is run against every recorded
transition and scored by EXACT grid match; the transitions it gets wrong are fed
back (counterexample-guided), for a few rounds. Train and held-out transitions
are kept apart, so what is measured is generalisation, not recall.

Model-agnostic: it talks to any OpenAI-compatible chat endpoint.

    python wm_probe.py --game ls20 --endpoint http://127.0.0.1:8080/v1 --rounds 3
    python wm_probe.py --game ls20 --baseline-only
"""

from __future__ import annotations
from _paths import SRC, DATA  # noqa: E402 — see scripts/_paths.py

import argparse
import json
import pickle
import re
import sys
import time
import traceback
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(SRC))

HEX = "0123456789abcdef"


def load(game: str):
    rows = pickle.loads((DATA / "frames.pkl").read_bytes())
    out = []
    for gid, act, prev, now in rows:
        if not gid.startswith(game):
            continue
        out.append((int(str(act).split("@")[0]), [list(r) for r in prev.grids[-1]],
                    [list(r) for r in now.grids[-1]]))
    return out


def show(grid) -> str:
    return "\n".join("".join(HEX[v] for v in row) for row in grid)


def diff(a, b) -> list[tuple[int, int, int, int]]:
    return [(r, c, a[r][c], b[r][c]) for r in range(len(a)) for c in range(len(a[0])) if a[r][c] != b[r][c]]


def describe(i: int, action: int, before, after) -> str:
    d = diff(before, after)
    if not d:
        return f"#{i} ACTION{action}: no change"
    cells = " ".join(f"({r},{c}):{HEX[x]}>{HEX[y]}" for r, c, x, y in d[:120])
    more = f" ...(+{len(d) - 120} more)" if len(d) > 120 else ""
    return f"#{i} ACTION{action}: {len(d)} cells changed (row,col):old>new {cells}{more}"


PROMPT = """You are looking at a turn-based game on a 64x64 grid. Each cell holds a colour 0-15, shown as one hex digit.
Actions are ACTION1..ACTION4. Nobody has told you the rules; infer them from the evidence.

The grid before the first transition (row 0 first):
{grid}

Recorded transitions, in order (each starts from the grid the previous one produced):
{transitions}

Write a Python function

    def predict(grid: list[list[int]], action: int) -> list[list[int]]:

that returns the next grid for ANY grid of this game and any action 1-4. Aim for the general
mechanism (what moves, how far, what blocks it, anything that changes on every step), not a
lookup of these particular transitions. Use only the Python standard library. Return only one
```python code block."""

FEEDBACK = """Your function was run on the recorded transitions. It got {ok}/{n} exactly right.
Some it got wrong (expected vs yours, as changed cells relative to the grid before):
{fails}

Revise `predict` so it explains all the evidence. Return only one ```python code block."""


def chat(endpoint: str, model: str, messages, max_tokens: int, timeout: int) -> tuple[str, dict]:
    body = json.dumps({"model": model, "messages": messages, "temperature": 0.2,
                       "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    usage = resp.get("usage", {})
    usage["seconds"] = round(time.time() - t0, 1)
    return resp["choices"][0]["message"]["content"], usage


def extract(text: str) -> str | None:
    m = re.findall(r"```(?:python)?\n(.*?)```", text, re.S)
    return m[-1] if m else None


def score(code: str | None, data):
    """(exact matches, per-transition results). A crash counts as wrong."""
    if code is None:
        return 0, [(False, "no code block")] * len(data)
    env: dict = {}
    try:
        exec(compile(code, "<predict>", "exec"), env)
        fn = env["predict"]
    except Exception as exc:  # noqa: BLE001
        return 0, [(False, f"does not load: {exc!r}")] * len(data)
    res = []
    for action, before, after in data:
        try:
            got = fn([row[:] for row in before], action)
            ok = [list(r) for r in got] == after
            res.append((ok, None if ok else got))
        except Exception as exc:  # noqa: BLE001
            res.append((False, f"raised {exc!r}"))
    return sum(1 for ok, _ in res if ok), res


def fail_text(data, res, k=3) -> str:
    out = []
    for (action, before, after), (ok, got) in zip(data, res):
        if ok:
            continue
        exp = describe(0, action, before, after).split(": ", 1)[1]
        mine = got if isinstance(got, str) else describe(0, action, before, got).split(": ", 1)[1]
        out.append(f"- ACTION{action}\n  expected: {exp}\n  yours:    {mine}")
        if len(out) == k:
            break
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--endpoint", default="http://127.0.0.1:8080/v1")
    ap.add_argument("--model", default="local")
    ap.add_argument("--shown", type=int, default=24, help="transitions shown in the prompt")
    ap.add_argument("--train", type=int, default=80, help="transitions used for feedback")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--baseline-only", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    data = load(a.game)
    train, held = data[: a.train], data[a.train:]
    ident = "def predict(grid, action):\n    return grid\n"
    b_tr, _ = score(ident, train)
    b_he, _ = score(ident, held)
    print(f"{a.game}: {len(data)} transitions, train {len(train)}, held-out {len(held)}")
    print(f"baseline 'nothing changes': train {b_tr}/{len(train)}  held-out {b_he}/{len(held)}")
    changed = [len(diff(b, c)) for _, b, c in data]
    print(f"cells changed per transition: min {min(changed)} max {max(changed)} "
          f"zero-change {sum(1 for x in changed if x == 0)}")
    if a.baseline_only:
        return

    if a.game != "ls20":
        sys.exit("only ls20 is supported: vc33's ACTION6 carries coordinates this probe does not pass")
    sample = train[: a.shown]
    # The prompt says the shown transitions form one unbroken chain; check it is so.
    breaks = [i for i in range(1, len(sample)) if sample[i][1] != sample[i - 1][2]]
    if breaks:
        sys.exit(f"shown transitions are not one chain (breaks at {breaks}); shorten --shown")
    shown = "\n".join(describe(i, act, b, c) for i, (act, b, c) in enumerate(sample))
    messages = [{"role": "user", "content": PROMPT.format(grid=show(train[0][1]), transitions=shown)}]
    log = {"game": a.game, "model": a.model, "rounds": []}
    for rnd in range(a.rounds):
        text, usage = chat(a.endpoint, a.model, messages, a.max_tokens, a.timeout)
        code = extract(text)
        ok_tr, res_tr = score(code, train)
        ok_he, _ = score(code, held)
        print(f"round {rnd}: train {ok_tr}/{len(train)}  held-out {ok_he}/{len(held)}  "
              f"tokens in {usage.get('prompt_tokens')} out {usage.get('completion_tokens')}  "
              f"{usage.get('seconds')}s")
        log["rounds"].append({"round": rnd, "train": ok_tr, "held": ok_he, "usage": usage, "code": code,
                              "reply": text})
        if ok_tr == len(train):
            break
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": FEEDBACK.format(ok=ok_tr, n=len(train),
                                                                 fails=fail_text(train, res_tr))}]
    if a.out:
        Path(a.out).write_text(json.dumps(log, indent=1), encoding="utf-8")
        print("log ->", a.out)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
