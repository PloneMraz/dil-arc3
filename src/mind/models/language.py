"""A language model — the one mind's computing, with weights trained before the loop ran.

The model (served over an OpenAI-compatible HTTP endpoint: llama.cpp locally,
vLLM on Kaggle) writes a program — `predict(grid, action, x, y)`, `propose(grid,
steps)` and `GOAL` — kept as data in the store; the program is how this model
predicts and proposes. When the mind thinks, the model is shown what the mind
hands it and writes a better program; what it keeps of a revision is its own
rule, for now (Plone, 2026-09-27). It is not a second mind: the mind holds the
seams with the loop, asks and writes; this is how it computes (`base.py`).

WHAT IT IS TOLD. Its task and what it does with any aim are priors the mind
recalls (`prior:mind-task`, `prior:mind-aim`): the words it reads, its data.
The region's values it uses — the fields of the region's report a program may
predict, the acts and which of them take a place — come from the host's
declaration (`organs`). What still speaks of this region in its code is the
text it writes to its model: the game, ACTION{n}, RESET (0), grids of hex
colours. Kept word for word, so the prompts are those of the runs already made
and of the submission the paper describes; to move them into its priors would
change what the model reads (LOG.md, 2026-09-27).

The model is reached with the standard library only — `dependencies = []` holds.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import textwrap
import re
import signal
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Final

from ..mind import expected_report
from ..organs import Organs, Step
from .base import Context, Expectation, Thinking, Write
from .base import Proposal as Proposal_

Grid = list[list[int]]
Status = dict[str, Any]

HEX: Final = "0123456789abcdef"

# The program's own tags (§9 open layer, tag F): what it is, never how good.
PROGRAM_TAGS: Final = {
    "domain": "mind", "kind": "program", "object": "frame", "source": "mind",
}

# What each act of thinking answered, whole, kept as the mind's own data: what it
# read and weighed shows in `[data]`, not only what it kept (Plone, 2026-09-25).
THOUGHT_TAGS: Final = {"domain": "mind", "kind": "thought", "source": "mind"}

# DECLARED limits on what one act of thinking can hold, set by the model's
# context, not by the loop: how many steps the prompt shows, how many of the
# program's misses it lists, how many questions one answer may put to memory,
# how many recalled non-frame items it shows, and how long a program may take on
# one grid. None narrows WHAT may be asked.
MAX_SHOWN: Final = 24
# The evidence rendered must fit the model's context with room to answer: each
# chain opens with a full 64x64 grid (~4.2k characters), and recalled frames are
# rarely consecutive. The oldest evidence goes first when it does not fit.
MAX_EVIDENCE_CHARS: Final = 60_000
MAX_MISSES_SHOWN: Final = 3
MAX_ASKS: Final = 4
MAX_RECALLED_LINES: Final = 40
MAX_RECALLED_LINE_CHARS: Final = 4000
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


def describe_status(status: Status | None) -> str:
    if not status:
        return ""
    return (f" | game: {status.get('stateFrom')}->{status.get('stateTo')}, "
            f"levels {status.get('levelsDelta', 0):+}, depth {status.get('depthDelta', 0):+}")


def describe_report(status: Status | None) -> str:
    """What the game reported of itself, said only when it said something new: a
    level completed, or a change of state."""
    if not status:
        return ""
    said = []
    if status.get("levelsDelta"):
        said.append(f"levels {status['levelsDelta']:+}")
    if status.get("stateTo") != status.get("stateFrom"):
        said.append(f"state {status.get('stateTo')}")
    return f" (the game reported: {', '.join(said)})" if said else ""


def render_evidence(transitions: list[Transition], report: bool = False) -> str:
    """The transitions as the model reads them: chains, each from a full grid.

    A chain is a run in which each step starts from the grid the one before it
    produced; each chain opens with its first grid in full, then one line per
    step as the cells it changed — and, with `report`, what the game reported of
    itself when that was news.
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
            note = describe_report(t.status) if report else ""
            out.append(f"#{n} {_name(t)}: {describe_change(t.before, t.after)}{note}")
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


def extract_asks(text: str, keys: frozenset[str]) -> list[dict[str, str]]:
    """The questions the model put to memory: `ASK {...}` lines, each a cue by tags.

    A cue must be a JSON object of string values on the store's tag keys; anything
    else is not a question the store can answer, and is left out.
    """
    asks: list[dict[str, str]] = []
    for m in re.finditer(r"^\s*ASK\s+(\{.*\})\s*$", text, re.M):
        try:
            cue = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if (isinstance(cue, dict) and cue and set(cue) <= keys | {"provenance"}
                and all(isinstance(v, str) for v in cue.values()) and cue not in asks):
            asks.append(cue)
    return asks[:MAX_ASKS]


# ── running a program ──────────────────────────────────────────────────────


class ProgramError(Exception):
    """The program would not load, raised, ran too long, or returned no grid."""


def compile_functions(code: str) -> tuple[Callable[..., Any], Callable[..., Any] | None]:
    """The program's `predict`, and its `propose` if it wrote one."""
    fn, propose, _goal = compile_all(code)
    return fn, propose


def compile_all(code: str) -> tuple[Callable[..., Any], Callable[..., Any] | None, Any]:
    """The program's `predict`, its `propose` if it wrote one, and its `GOAL` as written.

    A block indented as a whole is taken as written: the indentation is the
    model's layout, not its program (two thoughts in two runs were lost to it).
    """
    env: dict[str, Any] = {}
    try:
        exec(compile(textwrap.dedent(code), "<program>", "exec"), env)  # noqa: S102 — the model's own program
    except Exception as exc:  # noqa: BLE001
        raise ProgramError(f"does not load: {exc!r}") from exc
    fn = env.get("predict")
    if not callable(fn):
        raise ProgramError("defines no predict()")
    propose = env.get("propose")
    return fn, (propose if callable(propose) else None), env.get("GOAL")


def goal_of(raw: Any, grid: Grid, fields: tuple[str, ...]) -> dict[str, Any] | None:
    """The aim a program holds itself to, or None when it holds none it can be held to."""
    return goal_check(raw, grid, fields)[0]


def goal_check(raw: Any, grid: Grid, fields: tuple[str, ...]) -> tuple[dict[str, Any] | None, str | None]:
    """The aim a program holds itself to — or None, and why it is not one.

    It must say what will come back when it is reached — cells of the grid,
    fields of the region's report — and within how many actions: an aim nothing
    coming back could show is not taken (`aim.py`: where a regress stops). The
    reason goes back to the model, as a failed load does."""
    if raw is None:
        return None, "the program defines no GOAL"
    if not isinstance(raw, dict):
        return None, "GOAL is not a dict"
    reached = _want_of(raw.get("reached_when"), grid, fields)
    if reached is None:
        return None, ("GOAL's reached_when names nothing that comes back: it must be "
                      '{"cells": {"row,col": colour}} on the grid, or {"status": {...}} with the '
                      f"fields the game reports ({', '.join(fields)})")
    try:
        within = int(raw.get("within"))
    except (TypeError, ValueError):
        return None, "GOAL's within is not a number of actions"
    if within < 1:
        return None, "GOAL's within must be at least 1"
    source = raw.get("source") if raw.get("source") in ("stated", "inferred") else "inferred"
    return {"aim": str(raw.get("aim") or "")[:500], "source": source, "reached_when": reached,
            "within": within}, None


def _goal_shown(goal: dict[str, Any]) -> dict[str, Any]:
    reached = dict(goal["reached_when"])
    if "cells" in reached:
        reached["cells"] = {f"{r},{c}": v for (r, c), v in reached["cells"].items()}
    return {**goal, "reached_when": reached}


def compile_program(code: str) -> Callable[..., Any]:
    return compile_functions(code)[0]


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


def run_program(fn: Callable[..., Any], t: Transition, fields: tuple[str, ...] = ()) -> Grid:
    """The program's grid for a transition's situation; raises ProgramError."""
    return run_full(fn, t, fields)[0]


Proposal = tuple[int, "int | None", "int | None"]


def _takes_steps(fn: Callable[..., Any]) -> bool:
    """Whether a `propose` reads the steps as well as the grid: a second
    positional parameter, or `*args`. One written for the grid alone still runs."""
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        return False
    if any(p.kind is p.VAR_POSITIONAL for p in params):
        return True
    return len([p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]) >= 2


def steps_of(seen: list[Transition]) -> list[dict[str, Any]]:
    """The steps the mind has just seen, as its program reads them, oldest first:
    each the grid before, the action, the grid after, and what the region said
    of itself (its state, levels gained) when it said it. Copies: the program
    may not change what was seen."""
    return [
        {"before": [r[:] for r in t.before], "action": t.action, "x": t.x, "y": t.y,
         "after": [r[:] for r in t.after],
         "state": (t.status or {}).get("stateTo"), "levels": (t.status or {}).get("levelsDelta")}
        for t in seen
    ]


Want = dict[str, Any]


def _want_of(raw: Any, grid: Grid, fields: tuple[str, ...]) -> Want | None:
    """What a proposal says its action will bring about, in terms the region's
    return can refute: cells of the next grid, and fields of the region's next
    report. Anything else in it is not a claim the region can meet, and is left
    out; nothing left is no claim."""
    if not isinstance(raw, dict):
        return None
    want: Want = {}
    cells = raw.get("cells")
    if isinstance(cells, dict):
        got: dict[tuple[int, int], int] = {}
        for key, value in cells.items():
            try:
                r, c = (int(v) for v in (key.split(",") if isinstance(key, str) else key))
                v = int(value)
            except (TypeError, ValueError, AttributeError):
                continue
            if 0 <= r < len(grid) and 0 <= c < len(grid[0]) and 0 <= v <= 15:
                got[(r, c)] = v
        if got:
            want["cells"] = got
    status = raw.get("status")
    if isinstance(status, dict):
        said = {k: status[k] for k in fields if k in status}
        if said:
            want["status"] = said
    return want or None


def run_propose(fn: Callable[..., Any], grid: Grid, steps: list[dict[str, Any]] | None,
                acts: dict[int, str], placed: frozenset[int], fields: tuple[str, ...]) -> Proposal:
    """What the program proposes to do next from this state: (action, x, y)."""
    return run_propose_full(fn, grid, steps, acts, placed, fields)[0]


def run_propose_full(fn: Callable[..., Any], grid: Grid, steps: list[dict[str, Any]] | None,
                     acts: dict[int, str], placed: frozenset[int],
                     fields: tuple[str, ...]) -> tuple[Proposal, Want | None]:
    """What the program proposes to do next from this state: (action, x, y),
    and what it says that action will bring about, when it says so.

    A proposal is `(action, x, y)`, or `(action, x, y, want)` where `want` is
    `{"cells": {"row,col": colour}, "status": {...}}` — what the next grid and
    the region's next report will show if the action does what it is for.

    `propose(grid, steps)` reads where the game stands and the steps just seen;
    a `propose(grid)` reads the grid alone. An action is RESET (0) or
    ACTION1..ACTION7; a cell, for ACTION6, must lie on the grid — any other
    action carries none, and a cell given with one is not the action's. Anything
    else is not a proposal, and raises ProgramError."""
    guarded = threading.current_thread() is threading.main_thread()
    if guarded:
        old = signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(PROGRAM_SECONDS)
    try:
        board = [row[:] for row in grid]
        out = fn(board, list(steps or ())) if _takes_steps(fn) else fn(board)
        want_raw = None
        if isinstance(out, dict):
            want_raw = out.get("expect")
            out = out.get("action")
        if isinstance(out, (int, str)):
            out = (out,)
        if isinstance(out, (tuple, list)) and len(out) > 3 and isinstance(out[3], dict):
            want_raw = out[3]
        if not isinstance(out, (tuple, list)) or not out:
            raise ProgramError("proposed no action")
        action = out[0]
        x = out[1] if len(out) > 1 else None
        y = out[2] if len(out) > 2 else None
        named = {name.upper(): a for a, name in acts.items()}
        if isinstance(action, str) and action.upper() in named:
            action = named[action.upper()]
        elif isinstance(action, str) and action.upper().startswith("ACTION"):
            action = action[6:]
        action = int(action)
        if action not in acts:
            raise ProgramError(f"proposed ACTION{action}, which is no action")
        want = _want_of(want_raw, grid, fields)
        if action not in placed:
            return (action, None, None), want
        if x is not None or y is not None:
            x, y = int(x), int(y)
            if not (0 <= y < len(grid) and 0 <= x < len(grid[0])):
                raise ProgramError(f"proposed a cell off the grid: ({x}, {y})")
        return (action, x, y), want
    except ProgramError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ProgramError(f"propose raised {exc!r}") from exc
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


def chat(endpoint: ModelEndpoint, messages: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": endpoint.model, "messages": messages,
        "temperature": endpoint.temperature, "max_tokens": endpoint.max_tokens,
    }
    payload.update(endpoint.extra)
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
    message = resp["choices"][0]["message"]
    reasoning = message.get("reasoning_content") or message.get("reasoning")
    if reasoning:
        usage["reasoning"] = reasoning  # kept with the answer, in the store
    return message.get("content") or "", usage


# ── the model's thinking ───────────────────────────────────────────────────


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
    # What met the mismatch that set it thinking, and what it asked memory for.
    on: str = "frame"
    asked: list[dict[str, str]] = field(default_factory=list)


def _transition(step: Step, report: Status | None) -> Transition:
    return Transition(before=step.before, action=step.act[0], x=step.act[1], y=step.act[2],
                      after=step.after, status=report)


def _missed_text(missed: dict[str, Any] | None, overlay_missed: Callable[[Any, Any], str]) -> str | None:
    """What did not come, as the model is told it."""
    if not missed:
        return None
    what = missed.get("what")
    if what == "want":
        return f"cells (row,col): (wanted, came) {overlay_missed(missed['part'], missed['came'])}"
    if what == "goal":
        return (f"your GOAL ({missed['aim']}) was not reached when you said: "
                f"cells (row,col): (expected, came) {overlay_missed(missed['part'], missed['came'])}")
    if what == "goal-sooner":
        return f"your GOAL ({missed['aim']}) came sooner than you said"
    if what == "want-fields":
        return f"the game's report: wanted {json.dumps(missed['wanted'])}, came {json.dumps(missed['came'])}"
    if what == "goal-fields":
        return f"your GOAL ({missed['aim']}) was not reached when you said: the report came {json.dumps(missed['came'])}"
    return None


class LanguageModel:
    """The one mind's computing, with a language model: it writes a program —
    `predict`, `propose` and `GOAL` — and revises it when an expectation fails.

    What it keeps of a revision is its own rule, for now (Plone, 2026-09-27): a
    new program is kept if it explains the evidence better; or as well, when the
    body waits for a command, or when what set the mind thinking was how it acts
    — the onlooker, a want, an aim — and then only if it acts otherwise.
    """

    def __init__(self, organs: Organs, endpoint: ModelEndpoint | None = None,
                 chat_fn: Callable[..., tuple[str, dict[str, Any]]] = chat,
                 priors: dict[str, dict[str, str]] | None = None,
                 kinds: dict[str, str] | None = None) -> None:
        self.organs = organs
        self.endpoint = endpoint if endpoint is not None else ModelEndpoint()
        self._chat = chat_fn
        self._cues = dict(priors or {})
        # The tag values by which recalled data are told apart: the host's.
        self._kinds = {"status": "status", "remark": "remark", **(kinds or {})}
        self._task: dict[str, str] | None = None
        self._aim_text: dict[str, str] | None = None
        self.code: str | None = None
        self._fn: Callable[..., Any] | None = None
        self._propose: Callable[..., Any] | None = None
        self.version = 0
        self.datum_id: str | None = None
        self._last_note: str | None = None
        self.thoughts: list[Thought] = []

    # ── what it reads ──

    def cues(self) -> dict[str, dict[str, str]]:
        return dict(self._cues)

    def required(self) -> frozenset[str]:
        return frozenset({"task", "aim"})

    def receive_prior(self, name: str, payload: Any, datum_id: str | None) -> None:
        if name == "task":
            self._task = payload
        elif name == "aim":
            self._aim_text = payload

    def stated_aim(self) -> dict[str, Any] | None:
        return None  # its aim is what its program states

    def can_propose(self) -> bool:
        return self._fn is not None

    def held(self) -> tuple[object, ...]:
        return (("handle", "program"),) if self._fn is not None else ()

    def acknowledge(self, handle: object, datum_id: str) -> None:
        if handle == "program":
            self.datum_id = datum_id

    def observe(self, step: Step, unit: Any, fields: Status | None, units: tuple[Any, ...],
                on_report: bool) -> list[Write]:
        return []  # it revises only when the mind thinks

    # ── the expectation ──

    def expect(self, step: Step) -> Expectation:
        """The state it expects, from the situation alone (INV-8): its program's,
        or — with none, or one that fails — the standing expectation."""
        t = _transition(step, None)
        if self._fn is not None:
            try:
                grid, said = run_full(self._fn, t, self.organs.report_fields)
                return Expectation(state=grid, fields=said, by_model=True)
            except ProgramError:
                pass
        return Expectation(state=[row[:] for row in t.before], fields=None, by_model=False)

    # ── what to do next ──

    def _proposal(self, fn: Callable[..., Any] | None, grid: Grid,
                  steps: list[dict[str, Any]]) -> tuple[Proposal | None, Want | None]:
        if fn is None:
            return None, None
        try:
            return run_propose_full(fn, grid, steps, self.organs.acts, self.organs.placed,
                                    self.organs.report_fields)
        except ProgramError:
            return None, None

    def propose(self, context: Context) -> tuple[Proposal_, list[Write]]:
        grid = context.seen[-1][0].after
        steps = steps_of([_transition(s, r) for s, _, r in context.seen])
        act, want = self._proposal(self._propose, grid, steps)
        return Proposal_(act, want=_want_parts(want)), []

    # ── thinking ──

    def think(self, context: Context) -> Thinking:
        """An expectation met a mismatch, or no command came: have the model think.
        The evidence is what the store answered to what was asked (oldest), and
        the steps just seen — each with the datum it came from, so a write records
        exactly what it was built from."""
        on = context.on
        o = self.organs
        seen = [(_transition(s, r), u) for s, u, r in context.seen]
        recalled_steps = [(k, s) for k, s, _, _ in context.recalled if s is not None]
        recalled_other = [(k, t, p) for k, s, t, p in context.recalled if s is None]
        sourced: list[tuple[Transition, object]] = [
            *((_transition(s, None), datum_id) for datum_id, s in recalled_steps),
            *seen,
        ]
        by_key: dict[str, tuple[Transition, object]] = {}
        for t, src in sourced:
            prior = by_key.pop(t.key(), None)
            if prior is not None and t.status is None and prior[0].status is not None:
                t = prior[0]
            by_key[t.key()] = (t, src)
        chosen = list(by_key.values())[-MAX_SHOWN:]
        while len(chosen) > 1 and len(render_evidence([t for t, _ in chosen])) > MAX_EVIDENCE_CHARS:
            chosen = chosen[1:]
        shown = [t for t, _ in chosen]
        # Programs are scored on the grid alone, as the model is asked to predict it.
        evidence = [dataclasses.replace(t, status=None) for t in shown]
        lines = [(k, _recalled_line(t.get("kind"), t, p, self._kinds)) for k, t, p in recalled_other]
        lines = [(k, line) for k, line in lines if line][-MAX_RECALLED_LINES:]
        built_from = (tuple(src for _, src in chosen) + tuple(datum_id for datum_id, _ in lines)
                      + (("prior", "task"), ("prior", "aim")))
        held_ok, held_misses = score(self._fn, evidence, o.report_fields, o.unchanged)
        also = ""
        if context.ended is not None:
            # What the body can carry out, said as it is: the game's own list of
            # actions still names some after it has ended (vc33 names ACTION6),
            # and a prompt that repeated it contradicted "no action the game can
            # take now" — 27 thoughts in a row answered ACTION6 (LOG.md).
            also += f"\nThe game has ended ({context.ended}): the only action that can be taken now is RESET (0).\n"
        elif context.offers:
            offered = ", ".join(o.acts.get(a, f"ACTION{a}") for a in context.offers)
            also += f"\nThe game now offers: {offered} (and RESET, 0).\n"
        if lines:
            also += "\nWhat you recalled from memory:\n" + "\n".join(line for _, line in lines) + "\n"
        if context.remark and context.remark.get("remark"):
            also += f"\nAn onlooker watching your moves says: {json.dumps(context.remark)}\n"
        missed = _missed_text(context.missed, o.missed)
        if on == "no command":
            also += "\nYour propose gave no action the game can take now.\n"
        if on == "want" and missed:
            also += f"\nYour last action did not bring about what your propose said it would: {missed}\n"
        if on == "goal" and missed:
            also += f"\n{missed[0].upper()}{missed[1:]}.\n"
        if context.aim is not None:
            also += f"\nThe GOAL your program holds: {json.dumps(context.aim.get('shown', context.aim))}\n"
        notes = ""
        if on == "no goal":
            notes += "\nYour program holds no GOAL that what comes back could show reached.\n"
        if self._last_note:
            notes += f"\n{self._last_note}\n"
        grid = shown[-1].after if shown else [[]]
        first = self._task["task"].format(rows=len(grid), cols=len(grid[0]) if grid else 0,
                                          evidence=render_evidence(shown, report=True), also=also,
                                          seconds=PROGRAM_SECONDS)
        first += "\n\n" + self._aim_text["aim"]
        # What was wrong goes where the model reads what to do: the last message.
        if self.code is None:
            first += notes
        messages = [{"role": "user", "content": first}]
        if self.code is not None:
            messages.append({"role": "assistant", "content": f"```python\n{self.code}```"})
            messages.append({"role": "user", "content": self._task["feedback"].format(
                ok=held_ok, n=len(evidence), misses=self._misses_text(held_misses)) + notes})
        try:
            text, usage = self._chat(self.endpoint, messages)
        except Exception as exc:  # noqa: BLE001 — a model that fails leaves the program as it is
            self.thoughts.append(Thought(context_frame(context), len(evidence), held_ok, None, False,
                                         note=f"model failed: {exc!r}", on=on))
            return Thinking()
        reasoning = usage.pop("reasoning", None)
        asks = extract_asks(text, o.tag_keys)
        code = extract_code(text)
        note, cand_ok, adopted, fn, propose, goal = "", None, False, None, None, None
        goal_note: str | None = None
        if code is None:
            note = "no code block"
        else:
            try:
                fn, propose, goal_raw = compile_all(code)
                goal, goal_note = goal_check(goal_raw, grid, o.report_fields)
            except ProgramError as exc:
                note = str(exc)
        if fn is not None:
            cand_ok, _ = score(fn, evidence, o.report_fields, o.unchanged)
            # Kept when it explains the evidence better. Also when it explains as
            # much and can give a command, if the body is waiting for one — or if
            # what set it thinking was about how it acts, not what it expects: the
            # onlooker's objection, or a command that did not bring about what it
            # was for. Those are met by acting otherwise, not by predicting better
            # (Plone, 2026-09-25).
            acting = on in ("no command", "onlooker", "want", "goal", "no goal")
            # When what set it thinking was how it acts — the onlooker, a want or
            # an aim the region refuted — a program that predicts as well is kept
            # only if it acts otherwise from where the game stands: the same
            # action again is no answer to it (Plone, 2026-09-27; in the aim run
            # every rethought program proposed the action it replaced).
            otherwise = True
            if on in ("onlooker", "want", "goal") and propose is not None and self._propose is not None \
                    and context.seen:
                g = context.seen[-1][0].after
                steps = steps_of([t for t, _ in seen])
                now_held = self._proposal(self._propose, g, steps)[0]
                now_cand = self._proposal(propose, g, steps)[0]
                otherwise = now_cand is not None and now_cand != now_held
                if now_cand is None:
                    note = "its propose gave no action from where the game stands now"
                elif not otherwise:
                    note = (f"it proposed {o.name(now_held)} again, the action the program you hold "
                            f"proposes now; what set you thinking was how you act, so a program that "
                            f"only predicts as well must act otherwise")
            adopted = (self._fn is None or cand_ok > held_ok
                       or (acting and cand_ok >= held_ok and propose is not None and otherwise
                           and (on != "no goal" or goal is not None))
                       or (context.aim is None and goal is not None and cand_ok >= held_ok))
        # Said to the model next time as what happened: not taken and why; or
        # kept, with its GOAL not taken and why.
        if not adopted:
            reason = note or goal_note or (
                "it did not explain the evidence better than the program you hold")
            self._last_note = f"Your last answer was not taken: {reason}."
            note = note or goal_note or ""
        elif goal_note and goal is None:
            self._last_note = f"Your last answer's program was kept; its GOAL was not taken: {goal_note}."
            note = f"kept; GOAL not taken: {goal_note}"
        else:
            self._last_note = None
        self.thoughts.append(Thought(context_frame(context), len(evidence), held_ok, cand_ok, adopted, usage,
                                     note, on, asks))
        # The answer, whole, as the mind's own datum, built from what it was shown;
        # written after the program it kept, if it kept one.
        answer: dict[str, Any] = {"on": on, "text": text, "kept": adopted, "note": note}
        if reasoning:
            answer["reasoning"] = reasoning
        writes: list[Write] = []
        aim = None
        if adopted:
            writes += self._keep(code, fn, propose, built_from)
            if goal is not None:
                # The aim is the mind's: a program that states one replaces it; one
                # that states none leaves the mind the aim it held.
                aim = {"aim": goal["aim"], "source": goal["source"],
                       "reached_when": {"part": goal["reached_when"].get("cells"),
                                        "fields": goal["reached_when"].get("status")},
                       "within": goal["within"], "shown": _goal_shown(goal)}
        writes.append(Write(payload=answer, tags=dict(THOUGHT_TAGS), built_from=built_from))
        return Thinking(writes=writes, asks=asks, aim=aim)

    def _keep(self, code, fn, propose, built_from) -> list[Write]:
        """The program kept: written anew the first time, a revision after."""
        self.code, self._fn, self._propose = code, fn, propose
        self.version += 1
        payload = {"code": code, "version": self.version}
        if self.version == 1:
            return [Write(payload=payload, tags=dict(PROGRAM_TAGS), handle="program", built_from=built_from)]
        return [Write(payload=payload, revises="program", built_from=built_from)]

    def _misses_text(self, misses: list[tuple[Transition, Any]]) -> str:
        out = []
        for t, got in misses[:MAX_MISSES_SHOWN]:
            mine = got if isinstance(got, str) else describe_change(t.before, got[0])
            out.append(f"- {_name(t)}\n  expected: {describe_change(t.before, t.after)}\n  yours:    {mine}")
        return "\n".join(out)


def context_frame(context: Context) -> int:
    """How many steps the mind has seen: the frame a thought belongs to."""
    return context.frame_calls


def _want_parts(want: Want | None) -> dict[str, Any] | None:
    """What a proposal is for, in the mind's terms: a part of the next state and
    fields of the next report."""
    if not want:
        return None
    return {k: v for k, v in (("part", want.get("cells")), ("fields", want.get("status"))) if v}


def _recalled_line(kind: str | None, open_tags: dict[str, str], payload: Any, kinds: dict[str, str]) -> str:
    """A recalled datum that is not a step, as one line the model reads."""
    if not isinstance(payload, dict):
        return ""
    if kind == kinds["status"]:
        return (f"- after {payload.get('context')}, the game reported "
                f"{json.dumps(payload.get('status'))}")
    if kind == kinds["remark"]:
        said = {k: v for k, v in payload.items() if k != "entity"}
        return f"- the onlooker said {json.dumps(said)}"
    if kind == PROGRAM_TAGS["kind"] and isinstance(payload.get("code"), str):
        return f"- a program (version {payload.get('version')}):\n{_cut(payload['code'])}"
    if kind == THOUGHT_TAGS["kind"] and isinstance(payload.get("text"), str):
        return f"- an answer you gave (on {payload.get('on')}, kept: {payload.get('kept')}):\n{_cut(payload['text'])}"
    return f"- {open_tags.get('domain', 'datum')}/{kind}: {_cut(json.dumps(payload, ensure_ascii=False))}"


def _cut(text: str) -> str:
    """A recalled item, whole up to MAX_RECALLED_LINE_CHARS, and said to be cut when it is."""
    if len(text) <= MAX_RECALLED_LINE_CHARS:
        return text
    return f"{text[:MAX_RECALLED_LINE_CHARS]} ... [cut at {MAX_RECALLED_LINE_CHARS} of {len(text)} characters]"


__all__ = [
    "MAX_ASKS", "MAX_EVIDENCE_CHARS", "MAX_MISSES_SHOWN", "MAX_SHOWN", "PROGRAM_SECONDS", "PROGRAM_TAGS",
    "THOUGHT_TAGS", "LanguageModel", "ModelEndpoint", "ProgramError", "Proposal", "Thought", "Transition",
    "chat", "compile_all", "compile_functions", "compile_program", "extract_asks", "extract_code", "goal_check",
    "goal_of", "render_evidence", "run_full", "run_program", "run_propose", "run_propose_full", "score", "steps_of",
]
