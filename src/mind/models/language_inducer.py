"""The language inducer — a language model the mind learns with (Plone, 2026-09-28).

It computes for the mind's learning (`../learning.py`) as the other inducers do:
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

Its perception is that of the latest program it wrote that is a hypothesis and
defines `where` or `targets` (declared): what it reads into a grid changes as its
thinking does, and the learning reads every situation again when it does. Before
any, a situation is the grid as it came, and no cell is a target. What code keeps
beside it are records, never a reading of the grid: a state's identity (its
hash), and the exact hypothesis — "from here, this act gave that" (`exact.py`).

WHEN IT THINKS. Only when no hypothesis the mind holds foresaw a step (the
learning says so: `foreseen`): each answer costs seconds of a served model. It is
shown the steps of short-term perception (`evidence`), the last of them the step
not foreseen, and the program it wrote last with how it did on those steps.

WHAT IT IS TOLD is data the mind read, never code (Plone, 2026-09-25: a prompt is
a prior): the words of `prior:mind-task`, which the learning hands on once the
mind has recalled it (`induce`, `induce_feedback`, `unforeseen`) — the language
model's earlier words, kept word for word where they still hold (`arc3/task.py`
says what changed; Plone, 2026-09-28: S5). Until they come it is asked nothing.
Each answer names the prior among what it was built from. A program is a hypothesis only if it
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
from dataclasses import dataclass
from typing import Any, Callable, Final

from ..organs import Act, Organs, Step
from .exact import ExactForm, ExactInducer, Grid, Perceived, Prediction, grid_key
from .language import (
    MAX_EVIDENCE_CHARS, MAX_SHOWN, PROGRAM_SECONDS, THOUGHT_TAGS, ModelEndpoint, ProgramError, Transition, chat,
    extract_code, misses_text, render_evidence, score,
)

PERCEPTION_TAGS: Final = {"domain": "mind", "kind": "perception", "object": "frame", "source": "mind"}


@dataclass(eq=False)
class ProgramForm:
    """A program the model wrote: its code, as data, and its functions."""

    code: str
    digest: str
    predict: Callable[..., Any]
    where: Callable[..., Any] | None
    targets: Callable[..., Any] | None


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


class LanguageInducer(ExactInducer):
    """Programs a language model writes, and its reading of the grid."""

    kind = "language"
    # Its programs apply wherever the region stands: the learning looks ahead with them.
    general = True

    def __init__(self, organs: Organs, endpoint: ModelEndpoint | None = None,
                 chat_fn: Callable[..., tuple[str, dict[str, Any]]] = chat) -> None:
        super().__init__(organs)
        self.endpoint = endpoint or ModelEndpoint()
        self._chat = chat_fn
        self._seeing: ProgramForm | None = None      # whose where/targets it reads the grid with
        self._perceived = False                      # its reading changed since the learning last asked
        self._last: ProgramForm | None = None        # the last program that was a hypothesis
        self._said: list[Perceived] = []
        self._words: dict[str, str] | None = None      # what it is told, as the mind recalled it
        self._situations: dict[str, str] = {}        # a state's identity -> its situation, under its reading
        self._targets: dict[str, list[tuple[Act, tuple]]] = {}
        # For the run's report: each answer, with what came of it.
        self.answers: list[dict[str, Any]] = []

    # ── perception: the program's ──

    def situation(self, state: Grid) -> str:
        raw = grid_key(state)
        known = self._situations.get(raw)
        if known is not None:
            return known
        situation = self._read(self._seeing, state) if self._seeing is not None else raw
        self._situations[raw] = situation
        return situation

    @staticmethod
    def _read(form: ProgramForm | None, state: Grid) -> str:
        """Where the region stands in a state, as a program's `where` reads it; the
        state as it came where it reads nothing, or fails."""
        if form is None or form.where is None:
            return grid_key(state)
        try:
            read = _bounded(form.where, [row[:] for row in state])
            return "w" + hashlib.blake2b(json.dumps(read).encode(), digest_size=12).hexdigest()
        except (ProgramError, TypeError, ValueError):
            return grid_key(state)

    def perceive(self, step: Step, kind: tuple) -> Perceived | None:
        """Its reading changed with the program it wrote: the learning reads every
        situation again."""
        if not self._perceived:
            return None
        self._perceived = False
        form = self._seeing
        return Perceived(payload={"program": form.digest, "where": form.where is not None,
                                  "targets": form.targets is not None}, tags=dict(PERCEPTION_TAGS))

    def candidates(self, situation: str, state: Grid, offers: tuple[int, ...]) -> list[tuple[Act, tuple]]:
        """The acts it can take in a state: every act the region offers that takes
        no cell, and an act that takes one at each cell its program names."""
        out: list[tuple[Act, tuple]] = []
        for a in sorted(offers):
            if a == self.organs.reset[0]:
                continue
            if a in self.organs.placed:
                out += [((a, x, y), kind) for (_, x, y), kind in self._cells(situation, state, a)]
            else:
                out.append(((a, None, None), ("act", a)))
        return out

    def _cells(self, situation: str, state: Grid, a: int) -> list[tuple[Act, tuple]]:
        if situation not in self._targets:
            cells: list[tuple[Act, tuple]] = []
            form = self._seeing
            if form is not None and form.targets is not None:
                try:
                    named = _bounded(form.targets, [row[:] for row in state])
                    taken: set[tuple[int, int]] = set()
                    for cell in list(named or []):
                        x, y = int(cell[0]), int(cell[1])
                        if 0 <= y < len(state) and 0 <= x < len(state[y]) and (x, y) not in taken:
                            taken.add((x, y))
                            cells.append(((a, x, y), ("click", state[y][x])))
                except (ProgramError, TypeError, ValueError, IndexError):
                    cells = []
            self._targets[situation] = cells
        return [((a, x, y), kind) for (_, x, y), kind in self._targets[situation]]

    # ── hypotheses ──

    def induce(self, source: str, act: Act, before: Grid, after: Grid, *, foreseen: bool = False,
               evidence: tuple = (), report: dict | None = None, expected: Grid | None = None) -> list[Any]:
        if report is not None:
            return []   # its programs predict no report of the region (declared, for now)
        forms: list[Any] = [ExactForm(source=source, act=act, to=after)]
        if not foreseen:
            program = self._think(act, before, after, evidence)
            if program is not None:
                forms.append(program)
        return forms

    def receive_prior(self, name: str, payload: Any) -> None:
        if name == "task" and isinstance(payload, dict) and all(
                isinstance(payload.get(k), str) for k in ("induce", "induce_feedback", "unforeseen")):
            self._words = {k: payload[k] for k in ("induce", "induce_feedback", "unforeseen")}

    def _think(self, act: Act, before: Grid, after: Grid, evidence: tuple) -> ProgramForm | None:
        """Have the model write a program from what the mind has seen; the program,
        if it is a hypothesis: it gives, from the step, where the region came to.
        Not asked before it has been told what it is asked (its prior)."""
        if self._words is None:
            return None
        steps = [Transition(before=s.before, action=s.act[0], x=s.act[1], y=s.act[2], after=s.after, status=r)
                 for s, r in (evidence or ((Step(before, act, after), None),))][-MAX_SHOWN:]
        text, usage, why, form = "", {}, None, None
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
                    got = _grid_of(_bounded(form.predict, [row[:] for row in before], act[0], act[1], act[2]))
                    # Read as it would be read with this program held: by its own
                    # `where`, or else by the reading it has now.
                    reader = form if form.where is not None else self._seeing
                    if self._read(reader, got) != self._read(reader, after):
                        why = "its predict does not give, from the step it was asked on, where the region came to"
                        form = None
                except ProgramError as exc:
                    why = str(exc)
                    form = None
        if form is not None:
            self._last = form
            if form.where is not None or form.targets is not None:
                self._seeing, self._perceived = form, True
                self._situations, self._targets = {}, {}
        answer = {"on": "not foreseen", "steps": len(steps), "text": text, "program": form.digest if form else None,
                  "why_not": why, "tokens": usage.get("completion_tokens"), "seconds": usage.get("seconds")}
        if usage.get("reasoning"):
            answer["reasoning"] = usage["reasoning"]
        self._said.append(Perceived(payload=answer, tags=dict(THOUGHT_TAGS)))
        self.answers.append({k: v for k, v in answer.items() if k not in ("text", "reasoning")})
        return form

    def _messages(self, steps: list[Transition]) -> list[dict[str, str]]:
        """What the model is shown, in the words it was told, as its earlier form
        was: the steps seen (the oldest left out while they do not fit) and why it
        is asked; then the program it wrote last and how it did on those steps."""
        words = self._words or {}
        shown = list(steps)
        while len(shown) > 1 and len(render_evidence(shown)) > MAX_EVIDENCE_CHARS:
            shown = shown[1:]
        grid = shown[-1].after if shown else [[]]
        first = words["induce"].format(rows=len(grid), cols=len(grid[0]) if grid else 0,
                                       evidence=render_evidence(shown, report=True), also=words["unforeseen"],
                                       seconds=PROGRAM_SECONDS)
        messages = [{"role": "user", "content": first}]
        if self._last is not None:
            # Scored on the grid alone, as it is asked to predict it.
            evidence = [Transition(t.before, t.action, t.x, t.y, t.after) for t in shown]
            ok, misses = score(self._last.predict, evidence, (), lambda status: status)
            messages.append({"role": "assistant", "content": f"```python\n{self._last.code}```"})
            messages.append({"role": "user", "content": words["induce_feedback"].format(
                ok=ok, n=len(evidence), misses=misses_text(misses))})
        return messages

    def said(self) -> list[Perceived]:
        out, self._said = self._said, []
        return out

    def key(self, form: Any) -> tuple:
        if isinstance(form, ProgramForm):
            return ("program", form.digest)
        return super().key(form)

    def scope(self, form: Any, situation_of) -> tuple:
        if isinstance(form, ProgramForm):
            return ("program",)
        return super().scope(form, situation_of)

    def scopes(self, situation: str, act: Act) -> list[tuple]:
        return [("at", situation, act), ("program",)]

    def predict(self, form: Any, situation: str, state: Grid, act: Act, situation_of) -> Prediction | None:
        if not isinstance(form, ProgramForm):
            return super().predict(form, situation, state, act, situation_of)
        try:
            return Prediction(state=_grid_of(_bounded(form.predict, [row[:] for row in state], act[0], act[1],
                                                      act[2])))
        except ProgramError:
            return None   # it says nothing there

    def fields(self, form: Any) -> dict[str, Any] | None:
        return form.status if isinstance(form, ExactForm) else None

    def describe(self, form: Any, situation_of) -> dict[str, Any]:
        if isinstance(form, ProgramForm):
            return {"form": "program", "program": form.digest, "code": form.code,
                    "where": form.where is not None, "targets": form.targets is not None}
        return {"form": "exact", **super().describe(form, situation_of)}


__all__ = ["PERCEPTION_TAGS", "LanguageInducer", "ProgramForm", "compile_program"]
