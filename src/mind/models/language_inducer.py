"""The language inducer — a language model the mind learns with (Plone, 2026-09-28).

It computes for the mind's learning (`../learning.py`) as any inducer does, and
stands on its own (Plone, 2026-10-06):
the learning holds the experiences and the hypotheses, weighs them against the
region, expects, is curious and chooses; the model does none of that. What it
does is think: shown what the mind has just seen, it works out how the region
behaves and writes it as one program — and that program is both a hypothesis and
how the grid is read (Plone, 2026-09-28: all that reads the grid is the language
model's, not code beside it):

- `predict(grid, action, x, y)` — the grid that follows (x and y the cell of an
  act that takes one, else None): a hypothesis, applying wherever the region
  stands, and what the mind looks ahead with;
- `where(grid)`, if it writes one — the grid as it bears on where the region
  stands, every cell that changes whatever is done (a counter, a timer) set to
  -1: the situation;
- `targets(grid)`, if it writes one — the cells worth putting an act that takes
  a cell on.

How it reads a state is the latest program it wrote that is a hypothesis and
defines `where` or `targets` (declared): what it reads into a grid changes as its
thinking does, and the learning reads every situation again when it does. That
program, and the last it wrote, it holds only while new: once the mind holds
them as hypotheses it has them back from the mind's memory (`keep`), read from
the store as every form is (Plone, 2026-10-05). Before any, a situation is the
grid as it came, and no cell is a target. What code keeps beside it is a record,
never a reading of the grid: a state's identity (its hash). What an experience
says — "from here, this act gave that" — is the mind's own (its learning's
experiences). Code reads no grid for it: how alike two states are it does not
say (0), what a step made is the state it came to, and a cell its program names
is of no kind but "click" (Plone, 2026-10-06: all that reads the grid is the
model's).

WHEN IT THINKS. Only when no hypothesis the mind holds foresaw a step (the
learning says so: `foreseen`): each answer costs seconds of a served model. It is
shown the recent steps (`evidence`), the last of them the step
not foreseen, and the program it wrote last with how it did on those steps.

WHAT IT IS TOLD is data the mind read, never code (Plone, 2026-09-25: a prompt is
a prior): the words of `prior:mind-task` (`induce`, `induce_feedback`,
`unforeseen`, `aimed`), which the learning hands on once the mind has recalled
them, filled in with what the host declares of the region (its acts, the fields
of its report) and with **the aim the mind holds**, which the mind tells it
(`hold_aim`) — no word of a game, and no aim of the model's own: the model only
computes, and what for is the mind's to say (Plone, 2026-09-28). Until the
words come it is asked nothing. Each answer names the prior among what it was
built from. A program is a hypothesis only if it
gives, from that step, where the region came to stand: what one experience
suggests must bear it out. Each answer is kept whole as the mind's datum
(`said`): its text, its reasoning when the model gives one, the program it
yielded or why none.

Declared, for now: it predicts no report of the region (its status), so the
standing expectation holds for it; it does not ask memory (`ASK`).
"""

from __future__ import annotations

import hashlib
import json
import signal
import textwrap
import threading
from dataclasses import dataclass, replace
from typing import Any, Callable, Final

from ..organs import Act, Organs, Step
from .base import Note, Prediction
from .language import (
    MAX_EVIDENCE_CHARS, MAX_SHOWN, PROGRAM_SECONDS, THOUGHT_TAGS, ModelEndpoint, ProgramError, Transition, chat,
    extract_code, misses_text, render_evidence, score, show,
)

Grid = list[list[int]]

# A change of how it reads states: the program it reads them with now.
READING_TAGS: Final = {"domain": "mind", "kind": "reading", "object": "frame", "source": "mind"}


def identity(grid: Grid) -> str:
    """A state's own identity: a hash of its cells, as they came — a record, no reading."""
    h = hashlib.blake2b(digest_size=12)
    for row in grid:
        h.update(json.dumps(row).encode())
    return h.hexdigest()


@dataclass(eq=False)
class ProgramForm:
    """A program the model wrote: its code, as data, and its functions."""

    code: str
    digest: str
    predict: Callable[..., Any]
    where: Callable[..., Any] | None
    targets: Callable[..., Any] | None
    # The cells its `where` may set to -1, where the steps bore out only part of
    # it: a -1 anywhere else is read as the cell it hides (None: all it says).
    where_cells: frozenset[tuple[int, int]] | None = None


def _alarm(_signum: int, _frame: Any) -> None:
    raise ProgramError(f"ran longer than {PROGRAM_SECONDS}s")


def _bounded(fn: Callable[..., Any], *args: Any) -> Any:
    """A call of the model's program, within PROGRAM_SECONDS; raises ProgramError."""
    guarded = threading.current_thread() is threading.main_thread()
    if guarded:
        old = signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(PROGRAM_SECONDS)
    try:
        return fn(*args)
    except ProgramError:
        raise
    except Exception as exc:  # noqa: BLE001 — the model's program
        raise ProgramError(f"raised {exc!r}") from exc
    finally:
        if guarded:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)


def _grid_of(out: Any) -> Grid:
    if isinstance(out, dict):
        out = out.get("grid")
    if not isinstance(out, list) or not out or not all(isinstance(r, list) for r in out):
        raise ProgramError("did not return a grid")
    return [list(r) for r in out]


def _bear_out(form: ProgramForm, steps: list[Transition]) -> tuple[ProgramForm, str | None]:
    """A program with its `where` as far as the steps bear it out, and why not all.

    A cell it sets to -1 is one that "changes whatever is done" (its words): taken
    by regions of such cells side by side, each must change at every step at which
    a cell outside it changed, and at some step at which nothing outside it did. A
    block an act moves is still where no act moved it, and never changes alone; a
    clock that ticks at every step passes both (ls20, version 4, LOG.md
    2026-10-19). The regions borne out are kept and the others struck: its `where`
    then hides only the cells of the regions kept (`where_cells`) — the steps
    judging the model's reading, cell by cell, and code reading none of the grid
    for it (version 6: a `where` set aside whole for the block took the bar with
    it, and every grid read as new). None kept: set aside. Two clocks that only
    ever tick together are not borne out, and a clock slower than the steps not
    until the steps show it — declared, not measured beyond ls20."""
    if not steps:
        return replace(form, where=None), "no step has been seen to bear its where out"
    hidden: set[tuple[int, int]] = set()
    for t in steps:
        try:
            read = _bounded(form.where, [row[:] for row in t.before])
        except ProgramError as exc:
            return replace(form, where=None), f"its where {exc}"
        if not isinstance(read, list) or not all(isinstance(r, list) for r in read):
            return replace(form, where=None), "its where does not give a grid"
        hidden |= {(r, c) for r, row in enumerate(read) for c, v in enumerate(row) if v == -1}
    changes = [{(r, c) for r in range(min(len(t.before), len(t.after)))
                for c in range(min(len(t.before[r]), len(t.after[r]))) if t.before[r][c] != t.after[r][c]}
               for t in steps]
    changes = [ch for ch in changes if ch]
    kept: set[tuple[int, int]] = set()
    struck: list[str] = []
    while hidden:
        region, edge = set(), [next(iter(hidden))]
        while edge:
            cell = edge.pop()
            if cell in hidden:
                hidden.discard(cell)
                region.add(cell)
                r, c = cell
                edge += [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
        alone = any(ch <= region for ch in changes)
        always = all(ch & region for ch in changes if ch - region)
        if alone and always:
            kept |= region
        else:
            rows, cols = [r for r, _ in region], [c for _, c in region]
            struck.append(f"rows {min(rows)}-{max(rows)}, columns {min(cols)}-{max(cols)}")
    if not struck:
        return form, None
    why = ("its where sets to -1 cells at " + "; ".join(struck)
           + ", which the steps do not show changing whatever is done")
    if not kept:
        return replace(form, where=None), why
    return _hiding_only(form, frozenset(kept)), why + " (struck; the rest kept)"


def _hiding_only(form: ProgramForm, cells: frozenset[tuple[int, int]]) -> ProgramForm:
    """The program, its `where` hiding only these cells: any other it sets to -1 is
    read as the cell it hides."""
    where = form.where

    def read(grid: Grid) -> Grid:
        out = where(grid)
        return [[v if v != -1 or (r, c) in cells else grid[r][c] for c, v in enumerate(row)]
                for r, row in enumerate(out)]

    return replace(form, where=read, where_cells=cells)


def compile_program(code: str) -> ProgramForm:
    """The program an answer holds; raises ProgramError when it will not load or
    defines no predict()."""
    env: dict[str, Any] = {}
    try:
        exec(compile(textwrap.dedent(code), "<program>", "exec"), env)  # noqa: S102 — the model's own program
    except Exception as exc:  # noqa: BLE001
        raise ProgramError(f"does not load: {exc!r}") from exc
    fn = env.get("predict")
    if not callable(fn):
        raise ProgramError("defines no predict()")
    where, targets = env.get("where"), env.get("targets")
    return ProgramForm(code=code, digest=hashlib.sha256(code.encode()).hexdigest()[:16], predict=fn,
                       where=where if callable(where) else None, targets=targets if callable(targets) else None)


class LanguageInducer:
    """Programs a language model writes, and its reading of the grid."""

    kind = "language"
    # Its programs apply wherever the region stands: the learning looks ahead with them.
    general = True

    def __init__(self, organs: Organs, endpoint: ModelEndpoint | None = None,
                 chat_fn: Callable[..., tuple[str, dict[str, Any]]] = chat) -> None:
        self.organs = organs
        self.endpoint = endpoint or ModelEndpoint()
        self._chat = chat_fn
        # The program whose where/targets it reads the grid with, and the last
        # program that was a hypothesis: each in hand while new, then — once the
        # mind holds it (`keep`) — only how to have it back from the mind's memory.
        self._seeing: tuple[ProgramForm | None, Callable[[], Any] | None] | None = None
        self._reread = False                         # its reading changed since the learning last asked
        self._last: tuple[ProgramForm | None, Callable[[], Any] | None] | None = None
        self._said: list[Note] = []
        self._words: dict[str, str] | None = None      # what it is told, as the mind recalled it
        self._aim: dict[str, Any] | None = None        # the mind's aim, as the mind told it
        self._situations: dict[str, str] = {}        # a state's identity -> its situation, under its reading
        self._targets: dict[str, list[tuple[Act, tuple]]] = {}
        # For the run's report: each answer, with what came of it.
        self.answers: list[dict[str, Any]] = []

    # ── the programs it computes with again ──

    def keep(self, form: Any, recall: Callable[[], Any]) -> None:
        """A program it wrote is a hypothesis the mind holds: what it reads the
        grid with, and shows the model again, it has back from the mind's memory."""
        for name in ("_seeing", "_last"):
            held = getattr(self, name)
            if held is not None and held[0] is form:
                setattr(self, name, (None, recall))

    @staticmethod
    def _now(held: tuple[ProgramForm | None, Callable[[], Any] | None] | None) -> ProgramForm | None:
        if held is None:
            return None
        return held[0] if held[1] is None else held[1]()

    # ── reading a state: the program's ──

    def identity(self, state: Grid) -> str:
        """A state's own identity, as it came."""
        return identity(state)

    def situation(self, state: Grid) -> str:
        """Where the region stands in a state, as its program's `where` reads it."""
        raw = identity(state)
        known = self._situations.get(raw)
        if known is not None:
            return known
        situation = self._read(self._now(self._seeing), state) if self._seeing is not None else raw
        self._situations[raw] = situation
        return situation

    @staticmethod
    def _read(form: ProgramForm | None, state: Grid) -> str:
        """Where the region stands in a state, as a program's `where` reads it; the
        state as it came where it reads nothing, or fails."""
        if form is None or form.where is None:
            return identity(state)
        try:
            read = _bounded(form.where, [row[:] for row in state])
            return "w" + hashlib.blake2b(json.dumps(read).encode(), digest_size=12).hexdigest()
        except (ProgramError, TypeError, ValueError):
            return identity(state)

    def learn_reading(self, step: Step, kind: tuple) -> Note | None:
        """Its reading changed with the program it wrote: the learning reads every
        situation again."""
        if not self._reread:
            return None
        self._reread = False
        form = self._now(self._seeing)
        return Note(payload={"program": form.digest, "where": form.where is not None,
                             "targets": form.targets is not None}, tags=dict(READING_TAGS))

    def made(self, step: Step) -> frozenset:
        """What a step made: the state it came to, when it changed anything — a
        record, as code reads no grid here."""
        return frozenset((identity(step.after),)) if step.after != step.before else frozenset()

    def similarity(self, a: Grid, b: Grid) -> float:
        """How alike two states are it does not say: that would be code reading the grid."""
        return 0.0

    # ── what can be done ──

    def learnable(self, act: Act) -> Act:
        """An act as it is learned: the place kept only for an act that takes one."""
        return act if act[0] in self.organs.placed else (act[0], None, None)

    def default_kind(self, act: Act) -> tuple:
        return ("act", act[0])

    def copy(self, state: Grid) -> Grid:
        """A state of its own, as the learning keeps what it expects."""
        return [row[:] for row in state]

    def unlike(self, expected: Grid, came: Grid) -> None:
        """Where what came differs: it says nothing of it."""
        return None

    def at(self, act: Act, state: Grid, where: Any) -> bool:
        return False

    def as_read(self, state: Grid) -> Grid:
        """A grid as it reads it: as the `where` of the program it reads with sees it,
        a cell that `where` sets to -1 left out (None) — a `where` it holds only
        where the steps bore it out; all of the grid before it holds one, or where
        that `where` fails. Code reads no cell: which are left out is the program's."""
        form = self._now(self._seeing) if self._seeing is not None else None
        if form is None or form.where is None:
            return [row[:] for row in state]
        try:
            read = _bounded(form.where, [row[:] for row in state])
        except ProgramError:
            return [row[:] for row in state]
        if not isinstance(read, list) or len(read) != len(state):
            return [row[:] for row in state]
        out = []
        for row, seen_row in zip(state, read):
            if not isinstance(seen_row, list) or len(seen_row) != len(row):
                return [r[:] for r in state]
            out.append([None if v == -1 else cell for cell, v in zip(row, seen_row)])
        return out

    def coarse(self, kind: tuple) -> tuple | None:
        """No kind falls in a coarser one."""
        return None

    def candidates(self, situation: str, state: Grid, offers: tuple[int, ...]) -> list[tuple[Act, tuple]]:
        """The acts it can take in a state: every act the region offers that takes
        no cell, and an act that takes one at each cell its program names, in the
        order it names them — all of one kind: code reads nothing of the cell, so
        which to try first is the order the model gave."""
        out: list[tuple[Act, tuple]] = []
        for a in sorted(offers):
            if self.organs.restarts((a, None, None)):
                continue
            if a in self.organs.placed:
                out += [((a, x, y), kind) for (_, x, y), kind in self._cells(situation, state, a)]
            else:
                out.append(((a, None, None), ("act", a)))
        return out

    def _cells(self, situation: str, state: Grid, a: int) -> list[tuple[Act, tuple]]:
        if situation not in self._targets:
            cells: list[tuple[Act, tuple]] = []
            form = self._now(self._seeing)
            if form is not None and form.targets is not None:
                try:
                    named = _bounded(form.targets, [row[:] for row in state])
                    taken: set[tuple[int, int]] = set()
                    for cell in list(named or []):
                        x, y = int(cell[0]), int(cell[1])
                        if 0 <= y < len(state) and 0 <= x < len(state[y]) and (x, y) not in taken:
                            taken.add((x, y))
                            cells.append(((a, x, y), ("click",)))
                except (ProgramError, TypeError, ValueError, IndexError):
                    cells = []
            self._targets[situation] = cells
        return [((a, x, y), kind) for (_, x, y), kind in self._targets[situation]]

    # ── hypotheses ──

    def induce(self, source: str, act: Act, before: Grid, after: Grid, *, foreseen: bool = False,
               evidence: tuple = (), report: dict | None = None, expected: Grid | None = None,
               through: tuple = ()) -> list[Any]:
        if report is not None:
            return []   # its programs predict no report of the region (declared, for now)
        forms: list[Any] = []
        if not foreseen:
            program = self._think(act, before, after, evidence)
            if program is not None:
                forms.append(program)
        return forms

    def receive_prior(self, name: str, payload: Any) -> None:
        if name == "task" and isinstance(payload, dict) and all(
                isinstance(payload.get(k), str) for k in ("induce", "induce_feedback", "unforeseen", "aimed")):
            self._words = {k: payload[k] for k in ("induce", "induce_feedback", "unforeseen", "aimed", "nothing_seen")
                           if isinstance(payload.get(k), str)}

    def consider(self, situation: str, state: Grid) -> tuple[ProgramForm, Note] | None:
        """Asked while the body waits with nothing it can do: the model, shown the
        state alone, writes a program whose `targets` may name where an act that
        takes a cell can be put — as grid's reading of a state names things there
        (its `things`), here the model's. Asked only before it holds a reading.
        What it writes is no hypothesis: no step was met to build one from
        (INV-4), and the steps that follow judge it; its `where` is set aside, as
        no step bears it out. Its answer is kept whole; the reading, a datum the
        mind has it back from (`keep`). None where it writes nothing it can read
        a state with."""
        if self._words is None or "nothing_seen" not in self._words or self._seeing is not None:
            return None
        o, words = self.organs, self._words
        first = words["induce"].format(
            rows=len(state), cols=len(state[0]) if state else 0,
            acts=", ".join(n for a, n in sorted(o.acts.items())), placed=", ".join(o.acts[a] for a in sorted(o.placed)),
            numbers=", ".join(f"{n} is {a}" for a, n in sorted(o.acts.items())),
            evidence="Starting from this grid (row 0 first):\n" + show(state),
            also=words["nothing_seen"], aim=self._aim_said(), seconds=PROGRAM_SECONDS)
        text, usage, why, form, where_not = "", {}, None, None, None
        try:
            text, usage = self._chat(self.endpoint, [{"role": "user", "content": first}])
        except Exception as exc:  # noqa: BLE001 — the served model, not the mind
            why = f"the model did not answer: {exc!r}"
        if why is None:
            code = extract_code(text)
            if code is None:
                why = "the answer holds no code block"
            else:
                try:
                    form = compile_program(code)
                    if form.where is not None:
                        where_not = "no step has been seen to bear its where out"
                        form = replace(form, where=None)
                    if form.targets is None:
                        why, form = "it names no cell", None
                except ProgramError as exc:
                    why, form = str(exc), None
        answer = {"on": "nothing to do", "steps": 0, "text": text, "program": form.digest if form else None,
                  "why_not": why, "where_not": where_not,
                  "tokens": usage.get("completion_tokens"), "seconds": usage.get("seconds")}
        if usage.get("reasoning"):
            answer["reasoning"] = usage["reasoning"]
        self._said.append(Note(payload=answer, tags=dict(THOUGHT_TAGS)))
        self.answers.append({k: v for k, v in answer.items() if k not in ("text", "reasoning")})
        if form is None:
            return None
        self._seeing, self._reread = (form, None), False
        self._situations, self._targets = {}, {}
        return form, Note(payload={"program": form.digest, "code": form.code, "where": False, "targets": True,
                                   "on": "nothing to do"}, tags=dict(READING_TAGS))

    def hold_aim(self, aim: dict[str, Any]) -> None:
        """The aim the mind holds: what the mind tells its model the program is
        for. The model has none of its own (Plone, 2026-09-28)."""
        self._aim = dict(aim)

    def _aim_said(self) -> str:
        """The mind's aim, as the model is told it: the goal's fields the region is
        to report, or the words of the mind's own aim."""
        if self._aim is None:
            return ""
        fields = (self._aim.get("reached_when") or {}).get("fields")
        said = ("the region reports " + ", ".join(f"{k} {v}" for k, v in fields.items()) if fields
                else str(self._aim.get("aim") or ""))
        return self._words["aimed"].format(aim=said) if said else ""

    def _news(self, report: dict[str, Any] | None) -> str:
        """What the region reported of itself, when it was news: the fields of its
        report that are not what they would be had nothing changed (its organs)."""
        if not report:
            return ""
        unchanged = self.organs.unchanged(report)
        news = [f"{k} {report[k]}" for k in self.organs.report_fields if k in report and report[k] != unchanged.get(k)]
        return f" (it reported: {', '.join(news)})" if news else ""

    def _think(self, act: Act, before: Grid, after: Grid, evidence: tuple) -> ProgramForm | None:
        """Have the model write a program from what the mind has seen; the program,
        if it is a hypothesis: it gives, from the step, where the region came to.
        Not asked before it has been told what it is asked (its prior)."""
        if self._words is None:
            return None
        seen = [Transition(before=s.before, action=s.act[0], x=s.act[1], y=s.act[2], after=s.after, status=r)
                for s, r in (evidence or ((Step(before, act, after), None),))]
        steps = seen[-MAX_SHOWN:]
        text, usage, why, form, where_not = "", {}, None, None, None
        try:
            text, usage = self._chat(self.endpoint, self._messages(steps))
        except Exception as exc:  # noqa: BLE001 — the served model, not the mind
            why = f"the model did not answer: {exc!r}"
        if why is None:
            code = extract_code(text)
            if code is None:
                why = "the answer holds no code block"
            else:
                try:
                    form = compile_program(code)
                    # Its `where` is a reading only where the steps shown bear it
                    # out; else it is set aside, and the program is judged by the
                    # reading held before it. A program never judges itself by a
                    # reading the evidence does not hold (INV-8's shape: the
                    # criteria are not drawn from what is judged; Plone, 2026-10-19).
                    if form.where is not None:
                        # Borne out by every step the mind gave, not only those the
                        # model was shown: more steps, more chance of one at which a
                        # clock changed alone (version 5, LOG.md, 2026-10-19).
                        given = seen if seen and seen[-1].after == after else [*seen, Transition(
                            before=before, action=act[0], x=act[1], y=act[2], after=after)]
                        form, where_not = _bear_out(form, given)
                    got = _grid_of(_bounded(form.predict, [row[:] for row in before], act[0], act[1], act[2]))
                    reader = form if form.where is not None else self._now(self._seeing)
                    if self._read(reader, got) != self._read(reader, after):
                        why = "its predict does not give, from the step it was asked on, where the region came to"
                        form = None
                except ProgramError as exc:
                    why = str(exc)
                    form = None
        if form is not None:
            self._last = (form, None)
            if form.where is not None or form.targets is not None:
                self._seeing, self._reread = (form, None), True
                self._situations, self._targets = {}, {}
        answer = {"on": "not foreseen", "steps": len(steps), "text": text, "program": form.digest if form else None,
                  "why_not": why, "where_not": where_not,
                  "tokens": usage.get("completion_tokens"), "seconds": usage.get("seconds")}
        if usage.get("reasoning"):
            answer["reasoning"] = usage["reasoning"]
        self._said.append(Note(payload=answer, tags=dict(THOUGHT_TAGS)))
        self.answers.append({k: v for k, v in answer.items() if k not in ("text", "reasoning")})
        return form

    def _messages(self, steps: list[Transition]) -> list[dict[str, str]]:
        """What the model is shown, in the words it was told: the region as its host
        declares it, the steps seen (the oldest left out while they do not fit),
        why it is asked and what the mind is working toward; then the program it
        wrote last and how it did on those steps."""
        words = self._words or {}
        shown = list(steps)
        while len(shown) > 1 and len(render_evidence(shown)) > MAX_EVIDENCE_CHARS:
            shown = shown[1:]
        grid = shown[-1].after if shown else [[]]
        o = self.organs
        acts = ", ".join(n for a, n in sorted(o.acts.items()))
        placed = ", ".join(o.acts[a] for a in sorted(o.placed))
        numbers = ", ".join(f"{n} is {a}" for a, n in sorted(o.acts.items()))
        first = words["induce"].format(
            rows=len(grid), cols=len(grid[0]) if grid else 0, acts=acts, placed=placed, numbers=numbers,
            evidence=render_evidence(shown, report=True, name=o.name, news=self._news),
            also=words["unforeseen"], aim=self._aim_said(), seconds=PROGRAM_SECONDS)
        messages = [{"role": "user", "content": first}]
        last = self._now(self._last)
        if last is not None:
            # Scored on the grid alone, as it is asked to predict it.
            evidence = [Transition(t.before, t.action, t.x, t.y, t.after) for t in shown]
            ok, misses = score(last.predict, evidence, (), lambda status: status)
            messages.append({"role": "assistant", "content": f"```python\n{last.code}```"})
            messages.append({"role": "user", "content": words["induce_feedback"].format(
                ok=ok, n=len(evidence), misses=misses_text(misses, name=self.organs.name))})
        return messages

    def said(self) -> list[Note]:
        out, self._said = self._said, []
        return out

    def key(self, form: ProgramForm) -> tuple:
        """What a program says, as one value: its code."""
        return ("program", form.digest)

    def scope(self, form: ProgramForm, situation_of) -> tuple:
        """Where a program applies: wherever the region stands."""
        return ("program",)

    def scopes(self, situation: str, act: Act) -> list[tuple]:
        return [("program",)]

    def predict(self, form: ProgramForm, situation: str, state: Grid, act: Act, situation_of) -> Prediction | None:
        try:
            return Prediction(state=_grid_of(_bounded(form.predict, [row[:] for row in state], act[0], act[1],
                                                      act[2])))
        except ProgramError:
            return None   # it says nothing there

    def describe(self, form: ProgramForm, situation_of) -> dict[str, Any]:
        return {"form": "program", "program": form.digest, "code": form.code,
                "where": form.where is not None, "targets": form.targets is not None,
                "where_cells": sorted([r, c] for r, c in form.where_cells) if form.where_cells else None}

    def restore(self, payload: dict[str, Any]) -> ProgramForm:
        """A program from its datum, which holds its code: loaded again — its `where`
        set aside again where it was when the program was held."""
        form = compile_program(payload["code"])
        if payload.get("where") is False:
            return replace(form, where=None)
        cells = payload.get("where_cells")
        return _hiding_only(form, frozenset((r, c) for r, c in cells)) if cells and form.where is not None else form


__all__ = ["READING_TAGS", "LanguageInducer", "ProgramForm", "compile_program", "identity"]
