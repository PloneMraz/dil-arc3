"""The one mind — neutral about the region it lives in.

It holds the seams with the loop and thinks with a model, which is the part of
it that computes (`models/`; Plone, 2026-09-27: not a second mind, not a second
brain). It knows no region: how its eye and body work is the host's declaration
(`organs.py`); what the region is, what it is for, how it behaves, it reads from
its priors and learns from what comes back.

WHAT IT DOES, whatever its model:

- **Expects.** For each step the eye delivers, it asks its model what will come
  back, from where the region stood and the act alone (INV-8); where the command
  that made the step said what it was for (its want), that too; and, when the
  aim it holds falls due, the aim reached. All are its expectation of the step,
  and the datum the model says that expectation is, is `held_by` (v0.3.5). Where
  the model says nothing, the standing expectation holds: nothing changes, and
  the region reports what it reported last.
- **Thinks when an expectation fails** — the step, the region's report, what a
  command was for, the aim — at most once a cycle; on a change of the onlooker's
  word in its own right; and while the body waits for a command. It hands the
  model what it has: short-term perception (as long as T5's window), what memory
  answered to what was asked, what the onlooker says, what the region offers,
  why it is thinking. A model that learns from every return is also shown each.
- **Commands.** When the region has said all it says in a cycle, it asks the
  model what to do next and, if the body can carry it out (the body's own rule),
  pushes it as T5's test (§6.4); the body carries it out. With no command it
  thinks again while the body waits, at most MAX_WAIT_THOUGHTS times; then the
  body stands still. It commands nothing while it holds no aim (Plone,
  2026-09-25) — once its model can propose at all.
- **Writes** what its model says to write — anew or as a revision — each with
  what it was built from, ids only (v0.3.4); it learns each datum's id when the
  datum comes back, and a write that comes back is an echo, not an answer.
- **Asks** its memory what its model asks, and hands the model only what answers
  a question asked (Plone, 2026-09-27): what T3 recalls by description is the
  protocol's recall, traced, and not poured in. Its priors — what its model says
  it reads — it recalls itself, at its first arrival, and waits for them.
- **Holds the aim.** A model may state an aim; one that states none leaves the
  mind the aim it held (Plone, 2026-09-25).
"""

from __future__ import annotations

import json
from typing import Any, Callable, Final

from dil.loop.decisions import BASELINE_WINDOW
from dil.loop.layers.t3 import STORE_CHANNEL
from dil.loop.layers.t5 import Expecting, WriteRequest, persistence
from dil.loop.types import InfoUnit

from .models.base import Context, Model, Write
from .organs import Act, Organs, Step

# How many more times the mind thinks, in the same cycle, when it has no command
# the body can carry out — while the body waits. DECLARED, not measured.
MAX_WAIT_THOUGHTS: Final = 2


def _content_value(unit: InfoUnit) -> Any:
    content = unit.content
    return content.get("value") if isinstance(content, dict) else None


def _fingerprint(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, default=str)


def expected_report(said: dict[str, Any] | None, standing: dict[str, Any] | None) -> dict[str, Any] | None:
    """What the region is expected to report: what was said, over what stands."""
    if standing is None:
        return None
    base = dict(standing)
    if said:
        base.update(said)
    return base


class Mind:
    """The one mind: it reads, expects, thinks with its model, and commands the body."""

    def __init__(self, model: Model, organs: Organs) -> None:
        self.model = model
        self.organs = organs
        self.frame_calls = 0
        # For the run's report only, never the field: whether each expectation of
        # a step held, and each command given (the trace is `[event]`).
        self.holds: list[int] = []
        self.commands: list[tuple[int, Act | None]] = []
        self._priors: dict[str, tuple[Any, str | None]] = {}
        self._priors_asked = False
        self._pending: str | None = None
        self._command_due = False
        # Short-term perception: [step, unit, report or None], as long as T5's window.
        self._seen: list[list[Any]] = []
        self._status_seen_at: int | None = None
        self._said: dict[str, Any] | None = None
        self._said_by_model = False
        self._held: tuple[object, ...] = ()
        self._offers: tuple[int, ...] = ()
        self._wanted: tuple[Act, dict[str, Any]] | None = None
        self._want_fields: dict[str, Any] | None = None
        self._goal_fields: dict[str, Any] | None = None
        self._goal: dict[str, Any] | None = None
        self._goal_due = 0
        self._missed: dict[str, Any] | None = None
        self._status_this_cycle = False
        self._remark: dict[str, Any] | None = None
        self._remark_unit: InfoUnit | None = None
        self._thought_at: int | None = None
        # Questions put to memory, with when; answers arrive the next cycle.
        self._asks_open: list[tuple[int, dict[str, str]]] = []
        self._recalled: dict[str, tuple[Step | None, dict[str, str], Any]] = {}
        self._recalled_at: int | None = None
        # What it wrote, by fingerprint, until each comes back; the model's handle
        # for each, and the datum id each became; revisions owed until then.
        self._echoes: list[str] = []
        self._handle_of: dict[str, object] = {}
        self._ids: dict[object, str] = {}
        self._owed: dict[object, tuple[Any, tuple[object, ...]]] = {}

    # ── what the run's report reads ──

    @property
    def thoughts(self) -> list[Any]:
        return self.model.thoughts

    def __getattr__(self, name: str) -> Any:
        # What a report or a test reads of the model through the mind: its code,
        # its version, its last note — the model's, not the mind's.
        if name.startswith("__") or name == "model":
            raise AttributeError(name)
        return getattr(self.model, name)

    # ── priors, echoes, answers ──

    def _ready(self) -> bool:
        return self.model.required() <= set(self._priors)

    def _ask_priors(self, ask) -> None:
        if self._priors_asked or ask is None:
            return
        for name, cue in self.model.cues().items():
            if name not in self._priors:
                ask(dict(cue))
        self._priors_asked = True

    def receive(self, name: str, payload: Any, datum_id: str | None) -> None:
        """A prior it reads, as it came back from memory. A test may hand one in
        with no datum behind it: then nothing names it as built from."""
        self._priors[name] = (payload, datum_id)
        self.model.receive_prior(name, payload, datum_id)
        aim = self.model.stated_aim()
        if aim is not None and self._goal is None:
            self._hold_aim(aim)

    def take_return(self, ret: dict[str, Any], write, ask=None, test=None) -> None:
        """A store return: a prior it reads, its own write back, or an answer."""
        open_tags = ret.get("open", {})
        payload = ret.get("payload")
        entity = str(ret.get("entity"))
        for name, cue in self.model.cues().items():
            if isinstance(payload, dict) and all(open_tags.get(k) == v for k, v in cue.items()):
                if name not in self._priors:
                    self.receive(name, payload, entity)
                if not self._ready():
                    return
                if self._pending is not None:
                    self.think(self._pending, ask, write)
                if self._command_due:
                    self.command(ask, write, test)
                return
        mark = _fingerprint(payload)
        if mark in self._echoes:
            # Its own write, come back: not an answer, however its tags match.
            self._echoes.remove(mark)
            handle = self._handle_of.pop(mark, None)
            if handle is not None and handle not in self._ids:
                self._ids[handle] = entity
                self.model.acknowledge(handle, entity)
                owed = self._owed.pop(handle, None)
                if owed is not None and write is not None:
                    self._request(write, WriteRequest(payload=owed[0], datum_id=entity, built_from=owed[1]))
            return
        if not self._answers(open_tags, ret.get("fixed")):
            return
        if self._recalled_at != self.frame_calls:
            self._recalled, self._recalled_at = {}, self.frame_calls
        step = self.organs.step(payload) if isinstance(payload, dict) else None
        self._recalled[entity] = (step, dict(open_tags), payload)

    def _answers(self, open_tags: dict[str, str], fixed: Any) -> bool:
        provenance = fixed.get("provenance") if isinstance(fixed, dict) else None
        return any(
            all((provenance == v) if k == "provenance" else (open_tags.get(k) == v) for k, v in cue.items())
            for _, cue in self._asks_open
        )

    # ── writing ──

    def _resolve(self, refs: tuple[object, ...]) -> tuple[object, ...]:
        """Units and datum ids as they are; handles and priors as the ids they became."""
        out: list[object] = []
        for ref in refs:
            if isinstance(ref, tuple) and len(ref) == 2 and ref[0] == "handle":
                if ref[1] in self._ids:
                    out.append(self._ids[ref[1]])
            elif isinstance(ref, tuple) and len(ref) == 2 and ref[0] == "prior":
                if ref[1] in self._priors and self._priors[ref[1]][1] is not None:
                    out.append(self._priors[ref[1]][1])
            else:
                out.append(ref)
        return tuple(out)

    def _request(self, write, request: WriteRequest, handle: object | None = None) -> None:
        mark = _fingerprint(request.payload)
        self._echoes.append(mark)
        if handle is not None:
            self._handle_of[mark] = handle
        write(request)

    def _write(self, write, writes: list[Write]) -> None:
        if write is None:
            return
        for w in writes:
            built = self._resolve(w.built_from)
            if w.revises is not None:
                datum_id = self._ids.get(w.revises)
                if datum_id is None:
                    self._owed[w.revises] = (w.payload, built)  # written once its id is known
                else:
                    self._request(write, WriteRequest(payload=w.payload, datum_id=datum_id, built_from=built))
            else:
                self._request(write, WriteRequest(payload=w.payload, open=dict(w.tags or {}), built_from=built),
                              w.handle)

    # ── the aim ──

    def _hold_aim(self, aim: dict[str, Any]) -> None:
        self._goal = aim
        if aim.get("within") is not None:
            self._goal_due = self.frame_calls + aim["within"]

    # ── arrivals, one rule per channel ──

    def on_frame(self, step: Step, observed: InfoUnit, content: dict[str, Any], payload: dict[str, Any],
                 window, contribute, ask, write) -> InfoUnit | Expecting:
        self.frame_calls += 1
        self._status_this_cycle = False
        self._ask_priors(ask)
        o = self.organs
        # 1. Expect, from the situation alone; what the command that made this
        #    step was for; and, when it falls due, the aim reached.
        expectation = self.model.expect(step)
        foreseen = expectation.state
        wanted = self._wanted if self._wanted and self._wanted[0] == step.act else None
        self._wanted = None
        want = wanted[1] if wanted else {}
        meant = o.overlay(foreseen, want.get("part")) if want.get("part") else foreseen
        due = (self._goal is not None and self._goal.get("within") is not None
               and self.frame_calls >= self._goal_due)
        reached = self._goal["reached_when"] if due else {}
        expected = o.overlay(meant, reached.get("part")) if reached.get("part") else meant
        self._want_fields = dict(want["fields"]) if want.get("fields") else None
        self._goal_fields = dict(reached["fields"]) if reached.get("fields") else None
        if due:
            self._goal_due = self.frame_calls + self._goal["within"]  # held again, from here
        by_model = expectation.by_model or bool(want) or bool(reached)
        self._said, self._said_by_model = expectation.fields, expectation.fields is not None
        self._held = expectation.held if expectation.held else (self.model.held() if by_model else ())
        predicted = InfoUnit(content={**content, "value": o.expected_payload(payload, expected)},
                             ref_frame=observed.ref_frame, t=observed.t)
        # 2. Then look: this step joins short-term perception.
        self._seen = [*self._seen, [step, observed, None]][-BASELINE_WINDOW:]
        hit = expected == step.after
        self.holds.append(int(hit))
        self._write(write, self.model.observe(step, observed, None, (observed,), on_report=False))
        # 3. The expectation failed: think, on the first part that failed.
        if not hit:
            if foreseen != step.after:
                self.think("frame", ask, write)
            elif meant != step.after:
                self._missed = {"what": "want", "part": want["part"], "came": step.after}
                self.think("want", ask, write)
            else:
                self._missed = {"what": "goal", "aim": self._goal["aim"], "part": reached["part"],
                                "came": step.after}
                self.think("goal", ask, write)
        held = self._resolve(self._held) if by_model else ()
        return Expecting(predicted=predicted, held_by=held) if held else predicted

    def on_status(self, observed: InfoUnit, content: dict[str, Any], payload: dict[str, Any],
                  window, contribute, ask, write, test) -> InfoUnit | Expecting:
        self._status_this_cycle = True
        o = self.organs
        standing_unit = window[-1] if window else observed
        standing = _content_value(standing_unit)
        report = payload.get(o.report_key) if isinstance(payload.get(o.report_key), dict) else None
        self._offers = tuple(int(a) for a in payload.get(o.offers_key) or ())
        # The step just seen gets what the region reported of itself.
        if self._seen and self._status_seen_at != self.frame_calls and report is not None:
            self._seen[-1][2] = report
            self._status_seen_at = self.frame_calls
        # The expectation: what the region reported last, the agent's own act as
        # it is — or, where the model said the report, what it said, the fields it
        # left out staying as they were; with the want, and the aim when due.
        base = standing if isinstance(standing, dict) else dict(payload)
        own_act = {k: payload[k] for k in o.own_keys if k in payload}
        base = {**base, **own_act} if own_act else base

        def expecting(*parts: dict[str, Any] | None) -> dict[str, Any]:
            said = {k: v for part in parts if part for k, v in part.items()}
            if not said or report is None:
                return base
            return {**base, o.report_key: expected_report(said, o.unchanged(report))}

        own = self._said if self._said_by_model else None
        value = expecting(own, self._want_fields, self._goal_fields)
        by_model = self._said_by_model or bool(self._want_fields) or bool(self._goal_fields)
        if value == standing:
            predicted = standing_unit
        else:
            base_content = standing_unit.content if isinstance(standing_unit.content, dict) else {}
            predicted = InfoUnit(content={**base_content, "value": value}, ref_frame=standing_unit.ref_frame,
                                 t=standing_unit.t)
        if value != payload:
            aim = self._goal["reached_when"].get("fields") if self._goal else None
            if expecting(own) != payload and aim and report is not None and all(
                    report.get(k) == v for k, v in aim.items()):
                # The aim came before it was due: the model's time for it was wrong.
                self._missed = {"what": "goal-sooner", "aim": self._goal["aim"]}
                if self._goal.get("within") is not None:
                    self._goal_due = self.frame_calls + self._goal["within"]
                self.think("goal", ask, write)
            elif expecting(own) != payload:
                self.think("status", ask, write)
            elif expecting(own, self._want_fields) != payload:
                self._missed = {"what": "want-fields", "wanted": self._want_fields,
                                "came": {k: report.get(k) for k in self._want_fields}}
                self.think("want", ask, write)
            else:
                self._missed = {"what": "goal-fields", "aim": self._goal["aim"],
                                "came": {k: report.get(k) for k in self._goal_fields}}
                self.think("goal", ask, write)
        self._want_fields = self._goal_fields = None
        if self._seen and report is not None:
            step, unit, _ = self._seen[-1]
            self._write(write, self.model.observe(step, unit, report, (unit, observed), on_report=True))
        # The region has said all it says this cycle: construct the next action.
        self.command(ask, write, test)
        held: tuple[object, ...] = (standing_unit,) if window else ()
        if by_model:
            held = (*held, *self._resolve(self._held))
        return Expecting(predicted=predicted, held_by=held)

    def on_remark(self, entity_id: str, observed: InfoUnit, payload: dict[str, Any], window, contribute, ask,
                  write, test=None) -> InfoUnit:
        """What an Other says of the agent's behaviour. The standing expectation
        holds — it says what it said — and a change of it is a mismatch the mind
        thinks on. In a cycle the region said nothing in, what is said is all
        that comes, and the mind commands after it."""
        predicted = persistence(entity_id, window, observed, contribute, ask, write)
        self._remark = {k: v for k, v in payload.items() if k != "entity"}
        self._remark_unit = observed
        if _content_value(predicted) != payload:
            self.think("onlooker", ask, write, again=True)
        if not self._status_this_cycle:
            self.command(ask, write, test)
        self._status_this_cycle = False
        return predicted

    # ── commanding ──

    def _context(self, on: str) -> Context:
        report = self._seen[-1][2] if self._seen else None
        state = (report or {}).get(self.organs.state_field)
        return Context(
            on=on, frame_calls=self.frame_calls, seen=[(s, u, r) for s, u, r in self._seen],
            recalled=[(k, s, t, p) for k, (s, t, p) in self._recalled.items()],
            offers=self._offers, ended=state if state in self.organs.ended else None,
            remark=self._remark, remark_unit=self._remark_unit, missed=self._missed, aim=self._goal,
            priors=dict(self._priors),
        )

    def command(self, ask, write, test) -> None:
        """Construct the next action, and command it: T5's test, carried out by
        the body if it can. With no command, think again while the body waits."""
        if not self._seen:
            return
        if not self._ready():
            self._command_due = True  # it waits for what it reads
            return
        self._command_due = False
        report = self._seen[-1][2] or {}
        state = report.get(self.organs.state_field)
        for attempt in range(MAX_WAIT_THOUGHTS + 1):
            if self.model.can_propose() and self._goal is None:
                reason = "no goal"
            else:
                proposal, writes = self.model.propose(self._context("command"))
                self._write(write, writes)
                act = proposal.act
                if act is not None and self.organs.can_carry_out(*act, state, self._offers):
                    self.commands.append((self.frame_calls, act))
                    self._wanted = (act, proposal.want) if proposal.want else None
                    if test is not None:
                        test(self.organs.command(act))
                    return
                reason = "no command"
            if attempt < MAX_WAIT_THOUGHTS and not self.think(reason, ask, write, again=True):
                break  # its model does not think on this: asking again changes nothing
        self.commands.append((self.frame_calls, None))

    # ── thinking ──

    def think(self, on: str, ask, write, again: bool = False) -> bool:
        """An expectation met a mismatch, or no command came: have the model think.
        Once a cycle for a mismatch; `again` is the body waiting. False when the
        model does not think on this."""
        if self._thought_at == self.frame_calls and not again:
            return True
        if not self._ready():
            self._pending = on  # what it reads has not come back from memory yet
            return True
        self._pending = None
        self._thought_at = self.frame_calls
        result = self.model.think(self._context(on))
        if result is None:
            return False
        if result.asks is not None:
            self._asks_open = [(at, cue) for at, cue in self._asks_open if at >= self.frame_calls - 1]
            self._asks_open += [(self.frame_calls, dict(cue)) for cue in result.asks]
            if ask is not None:
                for cue in result.asks:
                    ask(dict(cue))
        self._write(write, list(result.writes))
        if result.aim is not None:
            # The aim is the mind's: one stated replaces it; none leaves it held.
            self._hold_aim(result.aim)
        return True


def mind_rule(mind: Mind) -> Callable[..., InfoUnit | Expecting]:
    """The mind at T5's seam (`PredictRule`): one rule, one mind, every arrival."""
    channels = mind.organs.channels

    def rule(entity_id: str, window, observed: InfoUnit, contribute=None, ask=None, write=None, test=None):
        content = observed.content if isinstance(observed.content, dict) else {}
        channel = content.get("channel")
        payload = _content_value(observed)
        window = tuple(window or ())
        if channel == STORE_CHANNEL:
            if isinstance(payload, dict):
                mind.take_return(payload, write, ask, test)
            return observed
        if channel == channels.get("frame") and isinstance(payload, dict):
            step = mind.organs.step(payload)
            if step is not None:
                return mind.on_frame(step, observed, content, payload, window, contribute, ask, write)
        if channel == channels.get("report") and isinstance(payload, dict):
            return mind.on_status(observed, content, payload, window, contribute, ask, write, test)
        if channel == channels.get("others") and isinstance(payload, dict):
            return mind.on_remark(entity_id, observed, payload, window, contribute, ask, write, test)
        return persistence(entity_id, window, observed, contribute, ask, write)

    return rule


__all__ = ["MAX_WAIT_THOUGHTS", "Mind", "expected_report", "mind_rule"]
