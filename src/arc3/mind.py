"""The mind — one, and it thinks with a language model.

The mind is the thinking: the model (Qwen3.6, served over HTTP) and the program
it writes, `predict(grid, action, x, y) -> grid`, kept as data in the store. It
supplies expectations and reports how its understanding stands; it never sees
the afforded set and never reaches the committed action. The self acts.

What it thinks about each arrival:

- **The frame.** Predicted from the situation alone (INV-8): the grid before the
  move and the move, run through the program; with no program yet, the standing
  expectation — nothing changes. When the expectation fails, the mind thinks. No
  trigger, no constant: it asks the store for the frames that collided
  (`{"kind": "frame", "provenance": "scar"}`) and has the model write a program
  for what it has — what the store answered last, what T5's window holds of the
  frame (§6.1 `Expectation.built_from: history_window`), and the transition in
  front of it. It keeps a new program only if it explains that evidence better.
  The first program is written anew (`nascent`), each later one revises that
  datum; every write records what it was built from (v0.3.4) — exactly the
  evidence the model was shown.
- **The region's status.** The program does not predict it, so the standing
  expectation holds: it stays as it was (dil-core's reference law). That is the
  absence of an understanding, not a second one. What the status says is read
  against the directive, once recalled.
- **What the store returns.** The directive (what the character was told it is
  for), scarred frames it asked for, its own program coming back.

What it reports upward into the field (INV-7), per action, from its one
understanding — the program:

- `resolved:action:k` — how often the program has predicted the frame after k;
- `progress:action:k` — how fast that is changing, which curiosity follows;
- `valence:action:k` — how the region has answered k, read against the directive.

The self's respond policy reads the field and nothing else.

WHAT THIS REPLACED, 2026-09-24. Until then the loop ran two minds at T5: this one
for the frame, and an older one — counting what each "thing" did after each
action, over things a computation of the grid had found — for everything else,
and only the older one reached the self. Two understandings of one world never
met, and nothing said which of them the self crystallized from. Settled with
Plone: one mind, and it is the model.

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
from dil.loop.layers.t5 import WriteRequest, persistence
from dil.loop.types import InfoUnit

from .observe import FRAME_CHANNEL, FRAME_KIND, STATUS_CHANNEL

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
# The field keys the mind reports under, per action (INV-7, up-channel).
RESOLVED_PREFIX: Final = "resolved:"
PROGRESS_PREFIX: Final = "progress:"
VALENCE_PREFIX: Final = "valence:"

# How many uses of an action make one window of learning progress (DECLARED,
# tunable, carried from the mind this replaced). Progress compares the last
# window's accuracy with the one before it, so an action needs twice this many
# uses before it has a progress at all; until then it counts as still being
# learned, which is also what makes an untried action come first.
PROGRESS_WINDOW: Final = 4

MAX_SHOWN: Final = 24
# The evidence rendered must fit the model's context with room to answer: each
# chain opens with a full 64x64 grid (~4.2k characters), and recalled scars are
# rarely consecutive. The oldest evidence goes first when it does not fit.
MAX_EVIDENCE_CHARS: Final = 60_000
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


def region_valence(status: object, directive: dict[str, Any] | None) -> float:
    """How the region answered, read against the directive the mind recalled.

    The signs are not in this code: which of the region's states is the
    objective, which ends the run without it, and what counts on the way come
    from the directive, admitted as `prior` and recalled on a cue. With no
    directive recalled every answer reads 0: a character with no problem to solve
    has nothing to prefer.
    """
    if not isinstance(status, dict) or not directive:
        return 0.0
    objective = (directive.get("objective") or {}).get("state")
    ended_without = (directive.get("ended_without") or {}).get("state")
    if ended_without is not None and status.get("stateTo") == ended_without:
        return -1.0
    if objective is not None and status.get("stateTo") == objective:
        return 1.0
    toward = (directive.get("toward") or {}).get("count")
    if toward == "levels_completed" and (status.get("levelsDelta") or 0) > 0:
        return 1.0
    return 0.0


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


class Mind:
    """The one mind: a program the model writes, tested, rewritten on mismatch."""

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
        # The directive, once recalled and run up the layers; None until then.
        self._directive: dict[str, Any] | None = None
        # Per action: whether the program predicted each frame after it (1/0),
        # in order, and every reading of how the region answered it. Accrued
        # (INV-5); the field only ever carries the current reading.
        self._uses: dict[str, list[int]] = {}
        self._valence: dict[str, list[float]] = {}

    # ── what arrives ──

    def take_return(self, ret: dict[str, Any], write: Callable[[WriteRequest], None] | None) -> None:
        """A store return: the directive, a scarred frame it asked for, or its own program back."""
        open_tags = ret.get("open", {})
        payload = ret.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("objective"), dict):
            self._directive = payload
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

    # ── what it knows so far ──

    def directive(self) -> dict[str, Any] | None:
        return self._directive

    def resolution(self, context: str) -> float | None:
        """How often the program has predicted the frame after this action, so far."""
        uses = self._uses.get(context)
        return sum(uses) / len(uses) if uses else None

    def progress(self, context: str) -> float:
        """How fast the program's hold on this action is changing.

        The size of the change in accuracy between the last window of uses and
        the one before. Curiosity follows it rather than ignorance: what cannot be
        learned shows no progress, and is left alone (the "noisy TV" failure the
        mind this replaced measured). A revision that suddenly explains an action
        — or a world that changed under it — shows as progress again. Fewer than
        two windows of uses counts as still being learned.
        """
        uses = self._uses.get(context, [])
        if len(uses) < 2 * PROGRESS_WINDOW:
            return 1.0
        recent = uses[-PROGRESS_WINDOW:]
        before = uses[-2 * PROGRESS_WINDOW:-PROGRESS_WINDOW]
        return abs(sum(recent) / PROGRESS_WINDOW - sum(before) / PROGRESS_WINDOW)

    def valence(self, context: str) -> float | None:
        """How the region has answered this action, so far, on average."""
        readings = self._valence.get(context)
        return sum(readings) / len(readings) if readings else None

    def report(self, context: str, contribute: Callable[[dict[str, float]], None] | None) -> None:
        """Report this action's reading upward into the field (INV-7)."""
        if contribute is None or not context:
            return
        reading: dict[str, float] = {PROGRESS_PREFIX + context: self.progress(context)}
        resolution = self.resolution(context)
        if resolution is not None:
            reading[RESOLVED_PREFIX + context] = resolution
        valence = self.valence(context)
        if valence is not None:
            reading[VALENCE_PREFIX + context] = valence
        contribute(reading)

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
        while len(chosen) > 1 and len(render_evidence([t for t, _ in chosen])) > MAX_EVIDENCE_CHARS:
            chosen = chosen[1:]
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


def mind_rule(mind: Mind) -> Callable[..., InfoUnit]:
    """The mind at T5's seam (`PredictRule`): one rule, one mind, every arrival."""

    def rule(entity_id: str, window, observed: InfoUnit, contribute=None, ask=None, write=None) -> InfoUnit:
        content = observed.content if isinstance(observed.content, dict) else {}
        channel = content.get("channel")
        payload = _content_value(observed)

        if channel == STORE_CHANNEL:
            # Something the character asked its store for, arriving like any
            # other return. The mind reads it; it is not an Other to predict.
            if isinstance(payload, dict):
                mind.take_return(payload, write)
            return observed

        if channel == FRAME_CHANNEL:
            t = transition_of(payload) if isinstance(payload, dict) else None
            if t is None:
                return persistence(entity_id, window, observed, contribute, ask, write)
            mind.frame_calls += 1
            # 1. Predict, from the situation alone.
            expected = mind.expect(t)
            predicted = InfoUnit(
                content={**content, "value": {**payload, "grids": [expected]}},
                ref_frame=observed.ref_frame, t=observed.t,
            )
            # 2. Then look, and accrue how the program did under this action.
            hit = expected == t.after
            context = str(payload.get("context") or "")
            if context:
                mind._uses.setdefault(context, []).append(int(hit))
            # 3. The expectation failed: think. A mismatch is the loop's to
            #    register; thinking is the mind's.
            if not hit:
                mind.think(t, observed, tuple(window or ()), ask, write)
            mind.report(context, contribute)
            return predicted

        if channel == STATUS_CHANNEL and isinstance(payload, dict):
            # The program does not predict the region's status: the standing
            # expectation holds. What the region said is read against the
            # directive — how it answered the action just taken.
            predicted = persistence(entity_id, window, observed, contribute, ask, write)
            context = str(payload.get("context") or "")
            if context and "status" in payload:
                mind._valence.setdefault(context, []).append(
                    region_valence(payload["status"], mind._directive)
                )
                mind.report(context, contribute)
            return predicted

        return persistence(entity_id, window, observed, contribute, ask, write)

    return rule


def create_mind(endpoint: ModelEndpoint | None = None,
                chat_fn: Callable[..., tuple[str, dict[str, Any]]] = chat) -> Mind:
    return Mind(endpoint if endpoint is not None else ModelEndpoint(), chat_fn)


__all__ = [
    "MAX_EVIDENCE_CHARS", "MAX_MISSES_SHOWN", "MAX_SHOWN", "PROGRAM_SECONDS", "PROGRAM_TAGS",
    "PROGRESS_PREFIX", "PROGRESS_WINDOW", "RESOLVED_PREFIX", "SCARRED_FRAMES", "VALENCE_PREFIX",
    "Mind", "ModelEndpoint", "ProgramError", "Thought", "Transition",
    "chat", "compile_program", "create_mind", "mind_rule", "region_valence", "render_evidence",
    "run_program", "score", "transition_of",
]
