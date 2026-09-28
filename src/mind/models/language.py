"""A served language model: what the language inducer needs to reach it and read it.

What is here is shared computing, naming no region: how a model is reached
(`ModelEndpoint`, `chat`: an OpenAI-compatible `/chat/completions` endpoint —
llama.cpp, vLLM, or a provider with a key), how a grid and what was seen of it
are shown to it (`render_evidence`, with the host's names for its acts and the
fields of its report), how the code in its answer is found (`extract_code`), and
how a program is run and scored on steps (`run_full`, `score`). The model has no
aim: the aim is the mind's, and the mind tells the model what to compute
(Plone, 2026-09-28; `language_inducer.py`).

The language model's earlier form — which wrote `predict`, `propose` and `GOAL`,
sat in the place of the mind's learning, and which submission `56588469` ran —
is gone; `3b31806` keeps it (LOG.md, 2026-09-29).

The model is reached with the standard library only — `dependencies = []` holds.
"""

from __future__ import annotations

import json
import os
import re
import signal
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Final

from ..mind import expected_report

Grid = list[list[int]]
Status = dict[str, Any]

HEX: Final = "0123456789abcdef"

# What each answer a model gives is kept as: the mind's own data (Plone, 2026-09-25).
THOUGHT_TAGS: Final = {"domain": "mind", "kind": "thought", "source": "mind"}

# DECLARED limits on what one answer can be asked from, set by the model's
# context, not by the loop: how many steps it is shown, how many characters they
# may take, how many of a program's misses it is told, and how long a program
# may take on one grid.
MAX_SHOWN: Final = 24
# Each chain of steps opens with a full 64x64 grid (~4.2k characters); the oldest
# steps go first when they do not fit.
MAX_EVIDENCE_CHARS: Final = 60_000
MAX_MISSES_SHOWN: Final = 3
PROGRAM_SECONDS: Final = 2

@dataclass(frozen=True, slots=True)
class Transition:
    """One observed step: the grid before, the move, the grid after (the last of
    each stack), and what the region reported of itself, when it is known."""

    before: Grid
    action: int
    x: int | None
    y: int | None
    after: Grid
    status: Status | None = None

    def key(self) -> str:
        return json.dumps([self.before, self.action, self.x, self.y, self.after])


# ── rendering what the model is shown ──────────────────────────────────────


def show(grid: Grid) -> str:
    return "\n".join("".join(HEX[v] for v in row) for row in grid)


def diff(a: Grid, b: Grid) -> list[tuple[int, int, int, int]]:
    return [
        (r, c, a[r][c], b[r][c])
        for r in range(min(len(a), len(b)))
        for c in range(min(len(a[r]), len(b[r])))
        if a[r][c] != b[r][c]
    ]


def _name(t: Transition) -> str:
    return f"ACTION{t.action}" + (f"(x={t.x},y={t.y})" if t.x is not None else "")


def describe_change(before: Grid, after: Grid) -> str:
    d = diff(before, after)
    if not d:
        return "no change"
    cells = " ".join(f"({r},{c}):{HEX[x]}>{HEX[y]}" for r, c, x, y in d[:120])
    more = f" ...(+{len(d) - 120} more)" if len(d) > 120 else ""
    return f"{len(d)} cells changed (row,col):old>new {cells}{more}"



def _named(t: Transition, name: Callable[[tuple], str] | None) -> str:
    act = (t.action, t.x, t.y)
    return name(act) if name is not None else _name(t)


def render_evidence(transitions: list[Transition], report: bool = False,
                    name: Callable[[tuple], str] | None = None,
                    news: Callable[[Status], str] | None = None) -> str:
    """The transitions as the model reads them: chains, each from a full grid.

    A chain is a run in which each step starts from the grid the one before it
    produced; each chain opens with its first grid in full, then one line per
    step as the cells it changed — and, with `report`, what the region reported
    of itself when that was news (`news`: the host's reading of its own report,
    through its organs). `name`: the host's name for an act.
    """
    chains: list[list[Transition]] = []
    for t in transitions:
        if chains and chains[-1][-1].after == t.before:
            chains[-1].append(t)
        else:
            chains.append([t])
    out: list[str] = []
    n = 0
    for chain in chains:
        out.append("Starting from this grid (row 0 first):\n" + show(chain[0].before))
        for t in chain:
            note = news(t.status) if report and news is not None and t.status else ""
            out.append(f"#{n} {_named(t, name)}: {describe_change(t.before, t.after)}{note}")
            n += 1
    return "\n".join(out)

def extract_code(text: str) -> str | None:
    """The last code block of an answer.

    A block opens and closes with a fence at the start of a line; a fence
    anywhere else — inside a docstring, say — does not close it. An answer whose
    fences are all indented is read the old way."""
    lines = text.splitlines(keepends=True)
    closers = [i for i, line in enumerate(lines) if re.fullmatch(r"```[ \t]*\n?", line)]
    openers = [i for i, line in enumerate(lines) if re.fullmatch(r"```(?:python|py)[ \t]*\n?", line)]
    # The last block that opens and closes: a model that abandons a block and
    # starts again leaves an open one before it — six answers in one run did,
    # each thinking inside a docstring it never closed (LOG.md, 2026-09-27).
    for start in reversed(openers):
        end = next((i for i in closers if i > start), None)
        if end is not None:
            return "".join(lines[start + 1:end])
    m = re.findall(r"```(?:python)?\n(.*?)```", text, re.S)
    return m[-1] if m else None


# ── running a program ──────────────────────────────────────────────────────


class ProgramError(Exception):
    """The program would not load, raised, ran too long, or returned no grid."""

def _alarm(_signum: int, _frame: Any) -> None:
    raise ProgramError(f"ran longer than {PROGRAM_SECONDS}s")


def _as_grid(out: Any) -> Grid:
    if not isinstance(out, list) or not all(isinstance(r, list) for r in out):
        raise ProgramError("did not return a grid")
    return [list(r) for r in out]

def run_full(fn: Callable[..., Any], t: Transition, fields: tuple[str, ...]) -> tuple[Grid, Status | None]:
    """The program's grid for a transition's situation, and the status fields it
    predicts (None when it says nothing about the status); raises ProgramError."""
    guarded = threading.current_thread() is threading.main_thread()
    if guarded:
        old = signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(PROGRAM_SECONDS)
    try:
        grid = [row[:] for row in t.before]
        try:
            out = fn(grid, t.action, t.x, t.y)
        except TypeError:
            out = fn([row[:] for row in t.before], t.action)
        if isinstance(out, dict):
            status = out.get("status")
            said = {k: status[k] for k in fields if isinstance(status, dict) and k in status}
            return _as_grid(out.get("grid")), (said or None)
        return _as_grid(out), None
    except ProgramError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ProgramError(f"raised {exc!r}") from exc
    finally:
        if guarded:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)

def score(fn: Callable[..., Any] | None, evidence: list[Transition], fields: tuple[str, ...],
          unchanged: Callable[[Status], Status]) -> tuple[int, list[tuple[Transition, Any]]]:
    """Exact matches over the evidence, and each miss with what the program gave.

    A step holds when the grid is exact and, where the region's report is known,
    the report is too — the program's status fields over "nothing changed".
    """
    if fn is None:
        return 0, [(t, "no program") for t in evidence]
    ok, misses = 0, []
    for t in evidence:
        try:
            grid, said = run_full(fn, t, fields)
        except ProgramError as exc:
            misses.append((t, str(exc)))
            continue
        status_ok = t.status is None or expected_report(said, unchanged(t.status)) == t.status
        if grid == t.after and status_ok:
            ok += 1
        else:
            misses.append((t, (grid, said)))
    return ok, misses


# ── the model ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ModelEndpoint:
    """Where the thinking model is served, and how it is asked."""

    url: str = "http://127.0.0.1:8080/v1"
    model: str = "local"
    max_tokens: int = 12288
    # Measured: 0.2 with thinking off wrote the 95% program on Kaggle (LOG.md,
    # 2026-09-24, run 2). Qwen's card recommends 0.7/0.8/20 for non-thinking; declared.
    temperature: float = 0.2
    timeout: int = 3600
    # Anything the served model needs beyond the OpenAI-compatible request — for
    # Qwen with thinking off, {"chat_template_kwargs": {"enable_thinking": False}}.
    # The mind knows no model: another model is another endpoint, and changes how
    # well it thinks, not what the mind is.
    extra: dict[str, Any] = field(default_factory=dict)
    # The NAME of the environment variable that holds the endpoint's API key —
    # never the key. None for an endpoint that asks none (every run so far: no
    # network at evaluation). Kept for after the competition (Plone, 2026-09-27).
    # The key is read when a request is sent and goes nowhere but its header: not
    # into the store, `[event]`, a snapshot, a commit's config, a report or LOG.
    api_key_env: str | None = None


def chat(endpoint: ModelEndpoint, messages: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": endpoint.model, "messages": messages,
        "temperature": endpoint.temperature, "max_tokens": endpoint.max_tokens,
    }
    payload.update(endpoint.extra)
    headers = {"Content-Type": "application/json"}
    if endpoint.api_key_env is not None:
        key = os.environ.get(endpoint.api_key_env)
        if not key:
            # Named, not shown: the message carries the variable's name only.
            raise RuntimeError(f"no API key in the environment variable {endpoint.api_key_env}")
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(
        endpoint.url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(), headers=headers,
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=endpoint.timeout) as r:  # noqa: S310 — the operator's endpoint
        resp = json.loads(r.read())
    usage = dict(resp.get("usage", {}))
    usage["seconds"] = round(time.time() - t0, 1)
    usage["finish_reason"] = resp["choices"][0].get("finish_reason")
    message = resp["choices"][0]["message"]
    reasoning = message.get("reasoning_content") or message.get("reasoning")
    if reasoning:
        usage["reasoning"] = reasoning  # kept with the answer, in the store
    return message.get("content") or "", usage

def misses_text(misses: list[tuple[Transition, Any]], name: Callable[[tuple], str] | None = None) -> str:
    """A program's misses as the model is told them: the first MAX_MISSES_SHOWN."""
    out = []
    for t, got in misses[:MAX_MISSES_SHOWN]:
        mine = got if isinstance(got, str) else describe_change(t.before, got[0])
        out.append(f"- {_named(t, name)}\n  expected: {describe_change(t.before, t.after)}\n  yours:    {mine}")
    return "\n".join(out)


__all__ = ["HEX", "MAX_EVIDENCE_CHARS", "MAX_MISSES_SHOWN", "MAX_SHOWN", "PROGRAM_SECONDS", "THOUGHT_TAGS",
           "ModelEndpoint", "ProgramError", "Transition", "chat", "describe_change", "diff", "extract_code",
           "misses_text", "render_evidence", "run_full", "score", "show"]
