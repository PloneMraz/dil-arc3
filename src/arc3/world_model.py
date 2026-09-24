"""A mind that thinks with a language model: an executable world model of the game.

Direction C, placed in the loop (CLAUDE.md, "Direction C, placed in the loop").
The model sits at the mind — it is the thinking — and what it makes is a
program, `predict(grid, action, x, y) -> grid`, kept as data in the store. The
loop tests it against the region like any expectation:

- **Predict first, from the situation alone** (INV-8). For the `frame` entity
  the mind reads the grid before the move and the move, runs the program, and
  that is the expectation. With no program yet, the standing expectation holds:
  nothing changes.
- **Meeting a mismatch, it thinks.** No trigger, no constant: the expectation
  failed, so the mind goes to memory for what bears on it — it asks the store for
  the frames that collided, `{"kind": "frame", "provenance": "scar"}` — and has the
  model write a program that explains what it has: what the store returned, what
  it has just seen (T5's window of the frame, §6.1 `Expectation.built_from:
  history_window`), and the transition in front of it. It keeps a new program
  only if it explains that evidence better than the one it holds.
- **The program is data** (v0.3.3). The first one is written anew and enters at
  `nascent`; each later one revises that datum, a bare `revision` line in the log
  and its content in the commit snapshot. Every write records what it was built
  from (v0.3.4): the data behind exactly the evidence the model was shown. The
  mind learns the datum's id when it arrives back at T1.

What the mind keeps in hand is only what the store answered last; what it has
just seen is T5's window, which the loop keeps: memory is the store, asked by
cue, never poured in. Every other
entity is thought about by the mind it wraps (`arc3.mind`).

The model is reached over an OpenAI-compatible HTTP endpoint (llama.cpp locally,
vLLM on Kaggle) with the standard library only — `dependencies = []` holds.
"""

from __future__ import annotations

import json
import re
import signal
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Final

from dil.loop.layers.t3 import STORE_CHANNEL
from dil.loop.layers.t5 import WriteRequest
from dil.loop.types import InfoUnit

from .observe import FRAME_CHANNEL, FRAME_KIND

Grid = list[list[int]]

HEX: Final = "0123456789abcdef"

# The cue the mind asks with when its expectation of the frame fails.
SCARRED_FRAMES: Final = {"kind": FRAME_KIND, "provenance": "scar"}

# The program's own tags (§9 open layer, tag F): what it is, never how good.
PROGRAM_TAGS: Final = {
    "domain": "world-model", "kind": "program", "object": FRAME_KIND, "source": "mind",
}

# DECLARED limits on what one act of thinking can hold, set by the model's
# context, not by the loop: how many transitions the prompt shows, how many of
# the program's misses it lists, and how long a program may take on one grid.
MAX_SHOWN: Final = 24
MAX_MISSES_SHOWN: Final = 3
PROGRAM_SECONDS: Final = 2

PROMPT: Final = """You are looking at a turn-based game on a 64x64 grid. Each cell holds a colour 0-15, shown as one hex digit.
Actions are ACTION1..ACTION7; ACTION6 also carries a cell (x = column, y = row). Nobody has told you the rules; infer them from the evidence.

{evidence}

Write a Python function

    def predict(grid: list[list[int]], action: int, x: int | None = None, y: int | None = None) -> list[list[int]]:

that returns the next grid for ANY grid of this game and any action. Aim for the general
mechanism (what moves, how far, what blocks it, anything that changes on every step), not a
lookup of these particular transitions. Use only the Python standard library. Return only one
```python code block."""

FEEDBACK: Final = """Your function was run on those transitions. It got {ok}/{n} exactly right.
Some it got wrong (expected vs yours, as changed cells relative to the grid before):
{misses}

Revise `predict` so it explains all the evidence. Return only one ```python code block."""


@dataclass(frozen=True, slots=True)
class Transition:
    """One observed step: the grid before, the move, the grid after (the last of each stack)."""

    before: Grid
    action: int
    x: int | None
    y: int | None
    after: Grid

    def key(self) -> str:
        return json.dumps([self.before, self.action, self.x, self.y, self.after])


def transition_of(payload: dict[str, Any]) -> Transition | None:
    """The transition a frame payload records, or None if it is not one.

    The mind reads the last grid of each stack. Which grid of a stack is "the"
    view is not settled by the host; this is the mind's reading, declared: of the
    159 recorded `ls20` transitions 157 are single grids.
    """
    try:
        move = payload["move"]
        return Transition(
            before=[list(r) for r in payload["before"][-1]],
            action=int(move["actionId"]),
            x=move.get("x"),
            y=move.get("y"),
            after=[list(r) for r in payload["grids"][-1]],
        )
    except (KeyError, IndexError, TypeError, ValueError):
        return None


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


def render_evidence(transitions: list[Transition]) -> str:
    """The transitions as the model reads them: chains, each from a full grid.

    A chain is a run in which each step starts from the grid the one before it
    produced; each chain opens with its first grid in full, then one line per
    step as the cells it changed.
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
            out.append(f"#{n} {_name(t)}: {describe_change(t.before, t.after)}")
            n += 1
    return "\n".join(out)


def extract_code(text: str) -> str | None:
    m = re.findall(r"```(?:python)?\n(.*?)```", text, re.S)
    return m[-1] if m else None


# ── running a program ──────────────────────────────────────────────────────


class ProgramError(Exception):
    """The program would not load, raised, ran too long, or returned no grid."""


def compile_program(code: str) -> Callable[..., Any]:
    env: dict[str, Any] = {}
    try:
        exec(compile(code, "<world-model>", "exec"), env)  # noqa: S102 — the model's own program
    except Exception as exc:  # noqa: BLE001
        raise ProgramError(f"does not load: {exc!r}") from exc
    fn = env.get("predict")
    if not callable(fn):
        raise ProgramError("defines no predict()")
    return fn


def _alarm(_signum: int, _frame: Any) -> None:
    raise ProgramError(f"ran longer than {PROGRAM_SECONDS}s")


def run_program(fn: Callable[..., Any], t: Transition) -> Grid:
    """The program's grid for a transition's situation; raises ProgramError."""
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
        if not isinstance(out, list) or not all(isinstance(r, list) for r in out):
            raise ProgramError("did not return a grid")
        return [list(r) for r in out]
    except ProgramError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ProgramError(f"raised {exc!r}") from exc
    finally:
        if guarded:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)


def score(fn: Callable[..., Any] | None, evidence: list[Transition]) -> tuple[int, list[tuple[Transition, Grid | str]]]:
    """Exact matches over the evidence, and each miss with what the program gave."""
    if fn is None:
        return 0, [(t, "no program") for t in evidence]
    ok, misses = 0, []
    for t in evidence:
        try:
            got = run_program(fn, t)
        except ProgramError as exc:
            misses.append((t, str(exc)))
            continue
        if got == t.after:
            ok += 1
        else:
            misses.append((t, got))
    return ok, misses


# ── the model ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ModelEndpoint:
    """Where the thinking model is served, and how it is asked."""

    url: str = "http://127.0.0.1:8080/v1"
    model: str = "local"
    max_tokens: int = 12288
    # Measured: 0.2 with thinking off wrote the 95% program on Kaggle (CLAUDE.md,
    # run 2). Qwen's card recommends 0.7/0.8/20 for non-thinking; declared.
    temperature: float = 0.2
    think: bool = False
    timeout: int = 3600


def chat(endpoint: ModelEndpoint, messages: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": endpoint.model, "messages": messages,
        "temperature": endpoint.temperature, "max_tokens": endpoint.max_tokens,
    }
    if not endpoint.think:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(
        endpoint.url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=endpoint.timeout) as r:  # noqa: S310 — the operator's endpoint
        resp = json.loads(r.read())
    usage = dict(resp.get("usage", {}))
    usage["seconds"] = round(time.time() - t0, 1)
    usage["finish_reason"] = resp["choices"][0].get("finish_reason")
    return resp["choices"][0]["message"].get("content") or "", usage


# ── the mind ───────────────────────────────────────────────────────────────


@dataclass
class Thought:
    """One act of thinking, for the run's report (not the trace: the trace is `[event]`)."""

    frame_call: int
    evidence: int
    held_score: int
    candidate_score: int | None
    adopted: bool
    usage: dict[str, Any] = field(default_factory=dict)
    note: str = ""


class WorldModel:
    """The thinking about the frame: a program, tested, rewritten on mismatch."""

    def __init__(self, endpoint: ModelEndpoint, chat_fn: Callable[..., tuple[str, dict[str, Any]]] = chat) -> None:
        self.endpoint = endpoint
        self._chat = chat_fn
        self.code: str | None = None
        self._fn: Callable[..., Any] | None = None
        self.version = 0
        # The program's datum in `[data]`, learned when it arrives back at T1.
        self.datum_id: str | None = None
        # A revision made before the datum's id was known, written on arrival,
        # with what it was built from.
        self._unwritten: tuple[dict[str, Any], tuple[object, ...]] | None = None
        # What the store answered last: the scarred frames it returned. An answer
        # arrives in one cycle, after that cycle's frame; a new one replaces it.
        self._recalled: dict[str, Transition] = {}
        self._recalled_at: int | None = None
        self.frame_calls = 0
        self.thoughts: list[Thought] = []

    # ── what arrives ──

    def take_return(self, ret: dict[str, Any], write: Callable[[WriteRequest], None] | None) -> None:
        """A store return: a scarred frame the mind asked for, or its own program coming back."""
        open_tags = ret.get("open", {})
        if open_tags.get("kind") == FRAME_KIND:
            t = transition_of(ret.get("payload") or {})
            if t is not None:
                if self._recalled_at != self.frame_calls:
                    self._recalled = {}
                    self._recalled_at = self.frame_calls
                self._recalled[str(ret.get("entity"))] = t
        elif open_tags.get("kind") == PROGRAM_TAGS["kind"] and self.datum_id is None:
            payload = ret.get("payload") or {}
            if isinstance(payload, dict) and payload.get("code") is not None:
                self.datum_id = str(ret.get("entity"))
                if self._unwritten is not None and write is not None:
                    payload, built_from = self._unwritten
                    write(WriteRequest(payload=payload, datum_id=self.datum_id, built_from=built_from))
                    self._unwritten = None

    # ── the expectation ──

    def expect(self, t: Transition) -> Grid:
        """The grid the mind expects, from the situation alone (INV-8)."""
        if self._fn is not None:
            try:
                return run_program(self._fn, t)
            except ProgramError:
                pass
        return [row[:] for row in t.before]  # the standing expectation: nothing changes

    # ── thinking ──

    def think(self, seen: Transition, source: InfoUnit,
              window: tuple[InfoUnit, ...] | list[InfoUnit],
              ask: Callable[[dict[str, str]], None] | None,
              write: Callable[[WriteRequest], None] | None) -> None:
        """The expectation failed: go to memory, and have the model write a better program.

        The evidence is what the store answered last (oldest), what T5's window
        holds of the frame, and the transition in front of it — each with the
        datum it came from, so a write records exactly what it was built from.
        """
        if ask is not None:
            ask(dict(SCARRED_FRAMES))
        sourced: list[tuple[Transition, object]] = [
            *((t, datum_id) for datum_id, t in self._recalled.items()),
            *((t, unit) for unit in window
              if (t := transition_of(_content_value(unit) or {})) is not None),
            (seen, source),
        ]
        by_key: dict[str, tuple[Transition, object]] = {}
        for t, src in sourced:
            by_key.pop(t.key(), None)
            by_key[t.key()] = (t, src)
        chosen = list(by_key.values())[-MAX_SHOWN:]
        evidence = [t for t, _ in chosen]
        built_from = tuple(src for _, src in chosen)
        held_ok, held_misses = score(self._fn, evidence)
        messages = [{"role": "user", "content": PROMPT.format(evidence=render_evidence(evidence))}]
        if self.code is not None:
            messages.append({"role": "assistant", "content": f"```python\n{self.code}```"})
            messages.append({"role": "user", "content": FEEDBACK.format(
                ok=held_ok, n=len(evidence), misses=self._misses_text(held_misses))})
        try:
            text, usage = self._chat(self.endpoint, messages)
        except Exception as exc:  # noqa: BLE001 — a model that fails leaves the program as it is
            self.thoughts.append(Thought(self.frame_calls, len(evidence), held_ok, None, False, note=f"model failed: {exc!r}"))
            return
        code = extract_code(text)
        if code is None:
            self.thoughts.append(Thought(self.frame_calls, len(evidence), held_ok, None, False, usage, "no code block"))
            return
        try:
            fn = compile_program(code)
        except ProgramError as exc:
            self.thoughts.append(Thought(self.frame_calls, len(evidence), held_ok, None, False, usage, str(exc)))
            return
        cand_ok, _ = score(fn, evidence)
        adopted = self._fn is None or cand_ok > held_ok
        self.thoughts.append(Thought(self.frame_calls, len(evidence), held_ok, cand_ok, adopted, usage))
        if not adopted:
            return
        self.code, self._fn = code, fn
        self.version += 1
        payload = {"code": code, "version": self.version}
        if write is None:
            return
        if self.version == 1:
            write(WriteRequest(payload=payload, open=dict(PROGRAM_TAGS), built_from=built_from))
        elif self.datum_id is not None:
            write(WriteRequest(payload=payload, datum_id=self.datum_id, built_from=built_from))
        else:
            # Written as a revision once the datum's id is known.
            self._unwritten = (payload, built_from)

    def _misses_text(self, misses: list[tuple[Transition, Grid | str]]) -> str:
        out = []
        for t, got in misses[:MAX_MISSES_SHOWN]:
            mine = got if isinstance(got, str) else describe_change(t.before, got)
            out.append(f"- {_name(t)}\n  expected: {describe_change(t.before, t.after)}\n  yours:    {mine}")
        return "\n".join(out)


def _content_value(unit: InfoUnit) -> Any:
    content = unit.content
    return content.get("value") if isinstance(content, dict) else None


def world_model_rule(base_rule: Callable[..., InfoUnit], wm: WorldModel) -> Callable[..., InfoUnit]:
    """Wrap a mind's rule: the frame is the world model's to think about; the rest is the base mind's."""

    def rule(entity_id: str, window, observed: InfoUnit, contribute=None, ask=None, write=None) -> InfoUnit:
        content = observed.content if isinstance(observed.content, dict) else {}
        channel = content.get("channel")
        if channel == STORE_CHANNEL:
            value = _content_value(observed)
            if isinstance(value, dict):
                wm.take_return(value, write)
            return base_rule(entity_id, window, observed, contribute, ask, write)
        if channel != FRAME_CHANNEL:
            return base_rule(entity_id, window, observed, contribute, ask, write)

        payload = _content_value(observed)
        t = transition_of(payload) if isinstance(payload, dict) else None
        if t is None:
            return base_rule(entity_id, window, observed, contribute, ask, write)
        wm.frame_calls += 1
        # 1. Predict, from the situation alone.
        expected = wm.expect(t)
        predicted = InfoUnit(
            content={**content, "value": {**payload, "grids": [expected]}},
            ref_frame=observed.ref_frame, t=observed.t,
        )
        # 2. Then look. A mismatch is the loop's to register; thinking is the mind's.
        if expected != t.after:
            wm.think(t, observed, tuple(window or ()), ask, write)
        return predicted

    return rule


__all__ = [
    "MAX_MISSES_SHOWN", "MAX_SHOWN", "PROGRAM_SECONDS", "PROGRAM_TAGS", "SCARRED_FRAMES",
    "ModelEndpoint", "ProgramError", "Thought", "Transition", "WorldModel",
    "chat", "compile_program", "render_evidence", "run_program", "score",
    "transition_of", "world_model_rule",
]
