"""The mind — one, and it thinks with a language model.

The mind is the thinking: the model (Qwen3.6, served over HTTP) and the program
it writes — `predict(grid, action, x, y)` and `propose(grid, steps)` — kept as data in
the store. It reads what the body took in, expects, is curious and wants — in
its thinking, not in a formula — and constructs the next action, commanding it
as T5's test (§6.4); the body carries it out (`command.py`). It acts on nothing
(Plone, 2026-09-25). What it is told its thinking is for is a prior in its store
(`task.py`), recalled like anything else. The model is replaceable: another
model is another endpoint, and changes how well the mind thinks, not what it
is.

The program is its understanding of the region. It predicts what the region
returns for a move: the next grid, and — when it says so — what the region will
report of itself (its state, its level count, its stack depth). Where it says
nothing about the status, the standing expectation holds: the region reports
what it reported last.

WHEN IT THINKS. When an expectation it holds meets a mismatch — the frame, the
region's status, or the onlooker's remark on its behaviour (tag E) — and only
then; at most once a cycle. No trigger, no constant: rewriting is the
consequence of mismatch. It thinks from what it has: what the store answered to
what it asked, the steps it has just seen (short-term perception, as long as
T5's window, `BASELINE_WINDOW`), and what the onlooker says now. It keeps a new
program only if it explains that evidence better — or as well, when the body is
waiting for a command, or when the onlooker objected: that objection is to how
it acts, and is met by acting otherwise. The first program is written
anew (`nascent`), each later one revises that datum; every write records what it
was built from (v0.3.4) — exactly the evidence the model was shown.

WHAT IT READS. The store, by asking — anything in it, by its tags; the model
chooses what (`ASK` lines in its answer: frames, statuses, the onlooker's
remarks, the rules it was told, scars or not). Nothing is poured in, and nothing
is asked for it: until the model asks, it thinks from what it has seen. The
answers arrive the next cycle (memory is what the store held before the cycle
that asks) and are the evidence of its next thought. Settled with Plone: the
mind may read the whole store and chooses what to read (2026-09-24); a fixed cue
written into this code had narrowed that to one kind of datum (LOG.md,
2026-09-25).

WHAT ITS EXPECTATIONS ARE (v0.3.5 `held_by`). An expectation the program made is
the program's: when it mismatches, the program's datum is scarred as the return
is, and when the program is used again it returns to `running` — so the program
circulates between the two for as long as its expectations meet the region, and
a third party reads each turn. A standing expectation is the observation it
repeats.

WHAT IT COMMANDS. When the region has said all it says in a cycle, the mind
runs `propose` on where the game stands and the steps it has just seen (its
short-term perception, each with what the region said of itself) and, if the
region affords the action (RESET always is), pushes it as T5's test: recorded from T5 in `[event]`, and
carried out by the body in the same cycle. With no such command it thinks
again while the body waits, at most MAX_WAIT_THOUGHTS times; then the body
stands still. Until 2026-09-25 the mind reported `resolved`, `progress` and
`valence` per action to the field and a policy weighed them: curiosity and want
written as a formula, and a proposal read one cycle late (INV-7). Both are gone
(LOG.md).

The model is reached over an OpenAI-compatible HTTP endpoint (llama.cpp locally,
vLLM on Kaggle) with the standard library only — `dependencies = []` holds.
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

from dil.loop.decisions import BASELINE_WINDOW
from dil.loop.layers.t3 import STORE_CHANNEL
from dil.loop.layers.t5 import Expecting, WriteRequest, persistence
from dil.loop.types import InfoUnit

from .action import COMPLEX_ACTION
from .observe import FRAME_CHANNEL, FRAME_KIND, ONLOOKER_CHANNEL, REMARK_KIND, STATUS_CHANNEL, STATUS_KIND
from .task import TASK_CUE, TASK_DOMAIN

Grid = list[list[int]]
Status = dict[str, Any]

HEX: Final = "0123456789abcdef"

# The program's own tags (§9 open layer, tag F): what it is, never how good.
PROGRAM_TAGS: Final = {
    "domain": "world-model", "kind": "program", "object": FRAME_KIND, "source": "mind",
}

# The status fields the region reports of itself, which the program may predict.
STATUS_FIELDS: Final = ("stateTo", "levelsDelta", "depthDelta")

# The keys a cue may carry: the open-tag dimensions (tag F) and provenance.
CUE_KEYS: Final = frozenset({"domain", "kind", "source", "object", "sense", "provenance"})

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
PROGRAM_SECONDS: Final = 2
# How many more times the mind thinks, in the same cycle, when it has no command
# the body can carry out — while the body waits. DECLARED, not measured: a model
# that fails this often leaves the body standing still, and the run ends.
MAX_WAIT_THOUGHTS: Final = 2

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
    m = re.findall(r"```(?:python)?\n(.*?)```", text, re.S)
    return m[-1] if m else None


def extract_asks(text: str) -> list[dict[str, str]]:
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
        if (isinstance(cue, dict) and cue and set(cue) <= CUE_KEYS
                and all(isinstance(v, str) for v in cue.values()) and cue not in asks):
            asks.append(cue)
    return asks[:MAX_ASKS]


# ── running a program ──────────────────────────────────────────────────────


class ProgramError(Exception):
    """The program would not load, raised, ran too long, or returned no grid."""


def compile_functions(code: str) -> tuple[Callable[..., Any], Callable[..., Any] | None]:
    """The program's `predict`, and its `propose` if it wrote one.

    A block indented as a whole is taken as written: the indentation is the
    model's layout, not its program (two thoughts in two runs were lost to it).
    """
    env: dict[str, Any] = {}
    try:
        exec(compile(textwrap.dedent(code), "<world-model>", "exec"), env)  # noqa: S102 — the model's own program
    except Exception as exc:  # noqa: BLE001
        raise ProgramError(f"does not load: {exc!r}") from exc
    fn = env.get("predict")
    if not callable(fn):
        raise ProgramError("defines no predict()")
    propose = env.get("propose")
    return fn, (propose if callable(propose) else None)


def compile_program(code: str) -> Callable[..., Any]:
    return compile_functions(code)[0]


def _alarm(_signum: int, _frame: Any) -> None:
    raise ProgramError(f"ran longer than {PROGRAM_SECONDS}s")


def _as_grid(out: Any) -> Grid:
    if not isinstance(out, list) or not all(isinstance(r, list) for r in out):
        raise ProgramError("did not return a grid")
    return [list(r) for r in out]


def run_full(fn: Callable[..., Any], t: Transition) -> tuple[Grid, Status | None]:
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
            said = {k: status[k] for k in STATUS_FIELDS if isinstance(status, dict) and k in status}
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


def run_program(fn: Callable[..., Any], t: Transition) -> Grid:
    """The program's grid for a transition's situation; raises ProgramError."""
    return run_full(fn, t)[0]


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


def run_propose(fn: Callable[..., Any], grid: Grid, steps: list[dict[str, Any]] | None = None) -> Proposal:
    """What the program proposes to do next from this state: (action, x, y).

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
        if isinstance(out, (int, str)):
            out = (out,)
        if not isinstance(out, (tuple, list)) or not out:
            raise ProgramError("proposed no action")
        action = out[0]
        x = out[1] if len(out) > 1 else None
        y = out[2] if len(out) > 2 else None
        if isinstance(action, str) and action.upper() == "RESET":
            action = 0
        elif isinstance(action, str) and action.upper().startswith("ACTION"):
            action = action[6:]
        action = int(action)
        if not 0 <= action <= 7:
            raise ProgramError(f"proposed ACTION{action}, which is no action")
        if action != COMPLEX_ACTION:
            return action, None, None
        if x is not None or y is not None:
            x, y = int(x), int(y)
            if not (0 <= y < len(grid) and 0 <= x < len(grid[0])):
                raise ProgramError(f"proposed a cell off the grid: ({x}, {y})")
        return action, x, y
    except ProgramError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ProgramError(f"propose raised {exc!r}") from exc
    finally:
        if guarded:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)


def expected_status(said: Status | None, standing: Status | None) -> Status | None:
    """What the region is expected to report: what the program said, over what it
    reported last. With nothing standing, the fields the program did not say stay
    as they were: the state it was in, and no change in levels or depth."""
    if standing is None:
        return None
    base = dict(standing)
    if said:
        base.update(said)
    return base


def _no_change(status: Status) -> Status:
    return {**status, "stateTo": status.get("stateFrom"), "levelsDelta": 0, "depthDelta": 0}


def score(fn: Callable[..., Any] | None, evidence: list[Transition]) -> tuple[int, list[tuple[Transition, Any]]]:
    """Exact matches over the evidence, and each miss with what the program gave.

    A step holds when the grid is exact and, where the region's report is known,
    the report is too — the program's status fields over "nothing changed".
    """
    if fn is None:
        return 0, [(t, "no program") for t in evidence]
    ok, misses = 0, []
    for t in evidence:
        try:
            grid, said = run_full(fn, t)
        except ProgramError as exc:
            misses.append((t, str(exc)))
            continue
        status_ok = t.status is None or expected_status(said, _no_change(t.status)) == t.status
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
    # What met the mismatch that set it thinking, and what it asked memory for.
    on: str = "frame"
    asked: list[dict[str, str]] = field(default_factory=list)


class Mind:
    """The one mind: it reads, expects, thinks, and commands the body's next action."""

    def __init__(self, endpoint: ModelEndpoint, chat_fn: Callable[..., tuple[str, dict[str, Any]]] = chat,
                 task: dict[str, str] | None = None) -> None:
        self.endpoint = endpoint
        self._chat = chat_fn
        # What it is told its thinking is for, once recalled (`task.py`), and the
        # datum it came from; a test may hand it in, as if recalled. A thought
        # that comes before it waits for it.
        self._task: dict[str, str] | None = task
        self._task_id: str | None = None
        self._task_asked = False
        self._pending: str | None = None
        self.code: str | None = None
        self._fn: Callable[..., Any] | None = None
        self._propose: Callable[..., Any] | None = None
        self.version = 0
        # The program's datum in `[data]`, learned when it arrives back at T1.
        self.datum_id: str | None = None
        # A revision made before the datum's id was known, written on arrival,
        # with what it was built from.
        self._unwritten: tuple[dict[str, Any], tuple[object, ...]] | None = None
        # What the store answered to what the model asked: frames as steps, the
        # rest as lines, each with the datum it came from. An answer arrives in
        # one cycle; a new batch replaces the last.
        self._recalled: dict[str, Transition] = {}
        self._recalled_lines: dict[str, str] = {}
        self._recalled_at: int | None = None
        # Short-term perception: the steps just seen, each with the unit it came
        # from and, once it arrives, what the region reported — as long as T5's
        # window, and no longer.
        self._seen: list[tuple[Transition, InfoUnit]] = []
        self._said: Status | None = None
        self._said_by_program = False
        self._status_seen_at: int | None = None
        # What the region says it offers next, from its own report.
        self._affords: tuple[int, ...] = ()
        # A command still owed this cycle, once what it is for comes back.
        self._command_due = False
        # The onlooker's current remark on its behaviour, as it last arrived.
        self._remark: dict[str, Any] | None = None
        self._thought_at: int | None = None
        self.frame_calls = 0
        self.thoughts: list[Thought] = []
        # For the run's report only, never the field: whether each frame
        # expectation held, and each command given (the trace is `[event]`).
        self.holds: list[int] = []
        self.commands: list[tuple[int, Proposal | None]] = []

    # ── what arrives ──

    def take_return(self, ret: dict[str, Any], write: Callable[[WriteRequest], None] | None,
                    ask: Callable[[dict[str, str]], None] | None = None,
                    test: Callable[[Any], None] | None = None) -> None:
        """A store return: its task, something it asked for, or its own program back."""
        open_tags = ret.get("open", {})
        payload = ret.get("payload")
        entity = str(ret.get("entity"))
        if open_tags.get("domain") == TASK_DOMAIN and isinstance(payload, dict) and "task" in payload:
            self._task, self._task_id = payload, entity
            if self._pending is not None:
                self.think(self._pending, ask, write)
            if self._command_due:
                self.command(ask, write, test)
            return
        kind = open_tags.get("kind")
        if kind == PROGRAM_TAGS["kind"]:
            if self.datum_id is None and isinstance(payload, dict) and payload.get("code") is not None:
                self.datum_id = entity
                if self._unwritten is not None and write is not None:
                    payload, built_from = self._unwritten
                    write(WriteRequest(payload=payload, datum_id=self.datum_id, built_from=built_from))
                    self._unwritten = None
            return
        # Anything else it asked for is evidence for its next thought.
        if self._recalled_at != self.frame_calls:
            self._recalled, self._recalled_lines = {}, {}
            self._recalled_at = self.frame_calls
        if kind == FRAME_KIND:
            t = transition_of(payload or {}) if isinstance(payload, dict) else None
            if t is not None:
                self._recalled[entity] = t
            return
        line = _recalled_line(kind, open_tags, payload)
        if line:
            self._recalled_lines[entity] = line

    def held_by(self) -> tuple[str, ...]:
        """The datum an expectation the program made is: the program's, once known."""
        return (self.datum_id,) if self._fn is not None and self.datum_id is not None else ()

    # ── the expectation ──

    def expect(self, t: Transition) -> Grid:
        """The grid the mind expects, from the situation alone (INV-8)."""
        return self._expect_full(t)[0]

    def _expect_full(self, t: Transition) -> tuple[Grid, Status | None, bool]:
        """The expected grid, the status fields said, and whether the program made
        them — a program that fails leaves the standing expectation, which is not
        the program's."""
        if self._fn is not None:
            try:
                grid, said = run_full(self._fn, t)
                return grid, said, True
            except ProgramError:
                pass
        return [row[:] for row in t.before], None, False  # the standing expectation: nothing changes

    # ── arrivals, one rule per channel ──

    def on_frame(self, t: Transition, observed: InfoUnit, content: dict[str, Any], payload: dict[str, Any],
                 window, contribute, ask, write) -> InfoUnit | Expecting:
        self.frame_calls += 1
        # What its thinking is for, read from its own memory, once: the answer
        # arrives next cycle, and a thought before it waits for it.
        if self._task is None and not self._task_asked and ask is not None:
            ask(dict(TASK_CUE))
            self._task_asked = True
        # 1. Expect, from the situation alone.
        expected, said, by_program = self._expect_full(t)
        self._said, self._said_by_program = said, said is not None
        predicted = InfoUnit(
            content={**content, "value": {**payload, "grids": [expected]}},
            ref_frame=observed.ref_frame, t=observed.t,
        )
        # 2. Then look: this step joins short-term perception.
        self._seen = [*self._seen, (t, observed)][-BASELINE_WINDOW:]
        hit = expected == t.after
        self.holds.append(int(hit))
        # 3. The expectation failed: think. A mismatch is the loop's to register;
        #    thinking is the mind's.
        if not hit:
            self.think("frame", ask, write)
        held = self.held_by() if by_program else ()
        return Expecting(predicted=predicted, held_by=held) if held else predicted

    def on_status(self, observed: InfoUnit, content: dict[str, Any], payload: dict[str, Any],
                  window, contribute, ask, write, test) -> InfoUnit | Expecting:
        standing_unit = window[-1] if window else observed
        standing = _content_value(standing_unit)
        status_now = payload.get("status") if isinstance(payload.get("status"), dict) else None
        # What the region says it offers next.
        self._affords = tuple(int(a) for a in payload.get("affords") or ())
        # The step just seen gets what the region reported of itself.
        if self._seen and self._status_seen_at != self.frame_calls and status_now is not None:
            t, unit = self._seen[-1]
            self._seen[-1] = (dataclasses.replace(t, status=status_now), unit)
            self._status_seen_at = self.frame_calls
        # The expectation: what the region reported last, under this action —
        # or, where the program said the status, what it said, the fields it
        # left out staying as they were.
        value = standing if isinstance(standing, dict) else dict(payload)
        value = {**value, "context": payload.get("context")} if "context" in payload else value
        if self._said_by_program and status_now is not None:
            value = {**value, "status": expected_status(self._said, _no_change(status_now))}
        if value == _content_value(standing_unit):
            predicted = standing_unit
        else:
            base = standing_unit.content if isinstance(standing_unit.content, dict) else {}
            predicted = InfoUnit(content={**base, "value": value}, ref_frame=standing_unit.ref_frame,
                                 t=standing_unit.t)
        if value != payload:
            self.think("status", ask, write)
        # The region has said all it says this cycle: construct the next action.
        self.command(ask, write, test)
        held: tuple[object, ...] = (standing_unit,) if window else ()
        if self._said_by_program:
            held = (*held, *self.held_by())
        return Expecting(predicted=predicted, held_by=held)

    def on_remark(self, observed: InfoUnit, payload: dict[str, Any], window, contribute, ask, write) -> InfoUnit:
        """What the onlooker says of the agent's behaviour. The standing
        expectation holds — it says what it said — and a change of stance is a
        mismatch the mind thinks on."""
        predicted = persistence("onlooker", window, observed, contribute, ask, write)
        self._remark = {k: v for k, v in payload.items() if k != "entity"}
        if _content_value(predicted) != payload:
            self.think("onlooker", ask, write)
        return predicted

    # ── commanding ──

    def command(self, ask, write, test) -> None:
        """Construct the next action from where the game stands, and command it.

        The mind acts on nothing: the command is T5's test (§6.4), recorded from
        T5, and the body carries it out if the region affords it. Curiosity,
        want and expectation are the mind's thinking, in the program it wrote;
        nothing here weighs them. With no command the body can carry out, the
        mind thinks again while the body waits — at most MAX_WAIT_THOUGHTS
        times; then the body stands still.
        """
        if not self._seen:
            return
        if self._task is None:
            self._command_due = True  # it waits for what it is for
            return
        self._command_due = False
        grid = self._seen[-1][0].after
        steps = steps_of([t for t, _ in self._seen])
        for attempt in range(MAX_WAIT_THOUGHTS + 1):
            proposal = self._proposal(grid, steps)
            if proposal is not None and (proposal[0] == 0 or proposal[0] in self._affords):
                self.commands.append((self.frame_calls, proposal))
                if test is not None:
                    action, x, y = proposal
                    test({"kind": "move", "actionId": action, "x": x, "y": y})
                return
            if attempt < MAX_WAIT_THOUGHTS:
                self.think("no command", ask, write, again=True)
        self.commands.append((self.frame_calls, None))

    def _proposal(self, grid: Grid, steps: list[dict[str, Any]]) -> Proposal | None:
        if self._propose is None:
            return None
        try:
            return run_propose(self._propose, grid, steps)
        except ProgramError:
            return None

    # ── thinking ──

    def think(self, on: str, ask: Callable[[dict[str, str]], None] | None,
              write: Callable[[WriteRequest], None] | None, again: bool = False) -> None:
        """An expectation met a mismatch, or no command came: have the model think.

        The evidence is what the store answered to what it asked (oldest), and
        the steps it has just seen — each with the datum it came from, so a write
        records exactly what it was built from. Once a cycle for a mismatch;
        `again` is the body waiting for a command.
        """
        if self._thought_at == self.frame_calls and not again:
            return
        if self._task is None:
            # What it is for has not come back from memory yet: the thought waits.
            self._pending = on
            return
        self._pending = None
        self._thought_at = self.frame_calls
        sourced: list[tuple[Transition, object]] = [
            *((t, datum_id) for datum_id, t in self._recalled.items()),
            *self._seen,
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
        lines = list(self._recalled_lines.items())[-MAX_RECALLED_LINES:]
        built_from = (tuple(src for _, src in chosen) + tuple(datum_id for datum_id, _ in lines)
                      + ((self._task_id,) if self._task_id is not None else ()))
        held_ok, held_misses = score(self._fn, evidence)
        also = ""
        if self._affords:
            offered = ", ".join(f"ACTION{a}" for a in self._affords)
            also += f"\nThe game now offers: {offered} (and RESET, 0).\n"
        if lines:
            also += "\nWhat you recalled from memory:\n" + "\n".join(line for _, line in lines) + "\n"
        if self._remark and self._remark.get("remark"):
            also += f"\nAn onlooker watching your moves says: {json.dumps(self._remark)}\n"
        if on == "no command":
            also += "\nYour propose gave no action the game offers now.\n"
        grid = shown[-1].after if shown else [[]]
        first = self._task["task"].format(rows=len(grid), cols=len(grid[0]) if grid else 0,
                                          evidence=render_evidence(shown, report=True), also=also)
        messages = [{"role": "user", "content": first}]
        if self.code is not None:
            messages.append({"role": "assistant", "content": f"```python\n{self.code}```"})
            messages.append({"role": "user", "content": self._task["feedback"].format(
                ok=held_ok, n=len(evidence), misses=self._misses_text(held_misses))})
        try:
            text, usage = self._chat(self.endpoint, messages)
        except Exception as exc:  # noqa: BLE001 — a model that fails leaves the program as it is
            self.thoughts.append(Thought(self.frame_calls, len(evidence), held_ok, None, False,
                                         note=f"model failed: {exc!r}", on=on))
            return
        # What it chose to read next: each question a store query from T5.
        asks = extract_asks(text)
        if ask is not None:
            for cue in asks:
                ask(dict(cue))
        code = extract_code(text)
        if code is None:
            self.thoughts.append(Thought(self.frame_calls, len(evidence), held_ok, None, False, usage,
                                         "no code block", on, asks))
            return
        try:
            fn, propose = compile_functions(code)
        except ProgramError as exc:
            self.thoughts.append(Thought(self.frame_calls, len(evidence), held_ok, None, False, usage, str(exc), on, asks))
            return
        cand_ok, _ = score(fn, evidence)
        # Kept when it explains the evidence better. Also when it explains as much
        # and can give a command, if the body is waiting for one — or if what set
        # it thinking was the onlooker: an Other's objection is to how it acts,
        # not to what it expects, and is answered by acting otherwise, not by
        # predicting better (Plone, 2026-09-25).
        adopted = (self._fn is None or cand_ok > held_ok
                   or (on in ("no command", "onlooker") and cand_ok >= held_ok and propose is not None))
        self.thoughts.append(Thought(self.frame_calls, len(evidence), held_ok, cand_ok, adopted, usage, "", on, asks))
        if not adopted:
            return
        self.code, self._fn, self._propose = code, fn, propose
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

    def _misses_text(self, misses: list[tuple[Transition, Any]]) -> str:
        out = []
        for t, got in misses[:MAX_MISSES_SHOWN]:
            mine = got if isinstance(got, str) else describe_change(t.before, got[0])
            out.append(f"- {_name(t)}\n  expected: {describe_change(t.before, t.after)}\n  yours:    {mine}")
        return "\n".join(out)


def _content_value(unit: InfoUnit) -> Any:
    content = unit.content
    return content.get("value") if isinstance(content, dict) else None


def _recalled_line(kind: str | None, open_tags: dict[str, str], payload: Any) -> str:
    """A recalled datum that is not a frame, as one line the model reads."""
    if not isinstance(payload, dict):
        return ""
    if kind == STATUS_KIND:
        return (f"- after {payload.get('context')}, the game reported "
                f"{json.dumps(payload.get('status'))}")
    if kind == REMARK_KIND:
        said = {k: v for k, v in payload.items() if k != "entity"}
        return f"- the onlooker said {json.dumps(said)}"
    text = json.dumps(payload)
    return f"- {open_tags.get('domain', 'datum')}/{kind}: {text[:600]}"


def standing_status(held: InfoUnit, payload: dict[str, Any]) -> InfoUnit:
    """What the region is expected to report: what it reported last, under this action.

    The status payload carries the action just taken as its `context`, and that
    is the agent's own act, not the region's word — T2 classifies it, and the
    mind knows it before the region answers. Expecting last cycle's action back would
    register every change of move as the region resisting: on the first Kaggle
    run, 42 of 45 status scars were that and nothing else (LOG.md, 2026-09-24).
    So the standing expectation holds what the region said, and takes the context
    as it is.
    """
    value = _content_value(held)
    if not isinstance(value, dict) or "context" not in payload or value.get("context") == payload["context"]:
        return held
    content = held.content if isinstance(held.content, dict) else {}
    return InfoUnit(content={**content, "value": {**value, "context": payload["context"]}},
                    ref_frame=held.ref_frame, t=held.t)


def mind_rule(mind: Mind) -> Callable[..., InfoUnit | Expecting]:
    """The mind at T5's seam (`PredictRule`): one rule, one mind, every arrival."""

    def rule(entity_id: str, window, observed: InfoUnit, contribute=None, ask=None, write=None, test=None):
        content = observed.content if isinstance(observed.content, dict) else {}
        channel = content.get("channel")
        payload = _content_value(observed)
        window = tuple(window or ())

        if channel == STORE_CHANNEL:
            # Something the character asked its store for, arriving like any
            # other return. The mind reads it; it is not an Other to predict.
            if isinstance(payload, dict):
                mind.take_return(payload, write, ask, test)
            return observed

        if channel == FRAME_CHANNEL and isinstance(payload, dict):
            t = transition_of(payload)
            if t is not None:
                return mind.on_frame(t, observed, content, payload, window, contribute, ask, write)

        if channel == STATUS_CHANNEL and isinstance(payload, dict):
            return mind.on_status(observed, content, payload, window, contribute, ask, write, test)

        if channel == ONLOOKER_CHANNEL and isinstance(payload, dict):
            return mind.on_remark(observed, payload, window, contribute, ask, write)

        return persistence(entity_id, window, observed, contribute, ask, write)

    return rule


def create_mind(endpoint: ModelEndpoint | None = None,
                chat_fn: Callable[..., tuple[str, dict[str, Any]]] = chat,
                task: dict[str, str] | None = None) -> Mind:
    return Mind(endpoint if endpoint is not None else ModelEndpoint(), chat_fn, task)


__all__ = [
    "CUE_KEYS", "MAX_ASKS", "MAX_EVIDENCE_CHARS", "MAX_MISSES_SHOWN", "MAX_SHOWN", "MAX_WAIT_THOUGHTS",
    "PROGRAM_SECONDS", "PROGRAM_TAGS", "STATUS_FIELDS",
    "Mind", "ModelEndpoint", "ProgramError", "Proposal", "Thought", "Transition",
    "chat", "compile_functions", "compile_program", "create_mind", "expected_status", "extract_asks",
    "mind_rule", "render_evidence", "run_full", "run_program", "run_propose", "score", "standing_status",
    "steps_of", "transition_of",
]
