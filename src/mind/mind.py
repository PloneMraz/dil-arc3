"""The one mind — neutral about the region it lives in.

It holds the seams with the loop, and its learning (`learning.py`), which is its
own whatever its model: the model's seat takes an inducer, the part of it that
computes (`models/`; Plone, 2026-09-27: not a second mind, not a second brain;
2026-09-28: another model, and learning is not defined again). It knows no
region: how its sensory organs and effectors work is the host's declaration
(`organs.py`); what
the region is, what it is for, how it behaves, it reads from its priors and
learns from what comes back.

WHAT IT DOES:

- **Expects.** For each step the eye delivers, it asks its learning what will
  come back, from where the region stood and the act alone (INV-8): its
  expectation of the step, and the datum its learning says that expectation is,
  is `held_by` (v0.3.5). Where nothing its learning knows says what will come,
  it expects the region to be otherwise than it was (`organs.Otherwise`): to act
  is to expect it to tell, and silence collides (Plone, 2026-10-11). The report,
  where its learning says nothing, it expects as reported last.
- **Has its learning think when an expectation fails** — the step, or the
  region's report — as often a cycle as alertness allows; on a change of the
  onlooker's word in its own right; and while the host waits for a command. It
  hands its learning what it has: the recent steps (as many as T5's
  window), what memory answered to what was asked, what the onlooker says, what
  the region offers, why it is thinking. Its learning is also shown every
  return, and learns from it there; it thinks further on a collision of a
  step or of the region's report (what collided turns its next choice) and on
  the onlooker's word (`learning.Learning.think`); while the host waits, it thinks
  once in a situation (`consider`).
- **Commands.** When the region has said all it says in a cycle, it asks its
  learning what to do next and, if the host can carry it out (the host's own
  rule), pushes it as T5's test (§6.4); the host's effectors carry it out. With no
  command it has its learning think again while the host waits, at most
  MAX_WAIT_THOUGHTS times, and stops asking as soon as its learning does not; then
  the host stands still. It commands nothing while it holds no aim (Plone,
  2026-09-25) — and it always comes to hold one (below).
- **Writes** what its learning says to write — anew or as a revision — each with
  what it was built from, ids only (v0.3.4); it learns each datum's id when the
  datum comes back, and a write that comes back is an echo, not an answer.
- **Asks** its memory what its learning asks, and hands it only what answers a
  question asked (Plone, 2026-09-27): what T3 recalls by description is the
  protocol's recall, traced, and not poured in. Its priors — what its learning
  says it reads — it recalls itself, at its first arrival; it waits for those its
  learning says it cannot think without (`required`: none, as it stands).
- **Holds the aim** (Plone, 2026-09-28). A goal is an instruction from
  outside: a prior it reads, which says what will come back when it is met
  (`goal`, with `reached_when`). The aim is the mind's own: it takes the goal's
  value when there is one; when none comes back with what it asked its memory
  for — it waits one cycle for the answer — it holds its own, OWN_AIM: that the
  region reports something other than what it reports most, and has not ended. Its
  learning holds the same aim (`hold_aim`), and tells its model what it is for.
  No model has an aim.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Final

from dil.loop.decisions import BASELINE_WINDOW
from dil.loop.field import ALERTNESS, EXPLORATION, TRUST, axis, cast_votes, falling, rising, shifted_count
from dil.loop.layers.t3 import STORE_CHANNEL
from dil.loop.layers.t5 import Expecting, WriteRequest, persistence
from dil.loop.types import InfoUnit

from .learning import CURIOSITY, Learning
from .models.base import Context, Inducer, Learner, Write
from .organs import Act, AsRead, Organs, Otherwise, Step

# How many more times the mind thinks, in the same cycle, when it has no command
# the host can carry out — while the host waits. DECLARED, not measured.
MAX_WAIT_THOUGHTS: Final = 2
# The aim the mind holds when no goal is given (Plone, 2026-09-28): the region
# reports something other than what it reports most — a report seen before, but
# seldom, reaches it too — in a state it has not ended in (`Organs.ended`) — seeking the end of a run would be no aim. Grounded
# in what comes back, as every aim must be (the regress rule, 2026-09-25).
# DECLARED, a law of the mind.
OWN_AIM: Final = {"aim": "the region reports something other than what it reports most, and has not ended",
                  "source": "own", "reached_when": {"new": True}}
# How many cycles past the one it asked its memory in the mind waits for a goal
# before it holds its own aim: the answer comes back the next cycle. DECLARED.
GOAL_WAIT: Final = 1
# How many times a cycle the mind thinks on a failed expectation, at NEUTRAL
# alertness; the field's alertness shifts it (½–1½, rounded: 1 to 2). DECLARED,
# not measured — dil-core's MIND_THOUGHTS_PER_CYCLE.
MIND_THOUGHTS_PER_CYCLE: Final = 1


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
    """The one mind: it reads, expects, learns, and commands the host."""

    def __init__(self, inducer: Inducer, organs: Organs, priors: dict[str, dict[str, str]],
                 curiosity: str = CURIOSITY[0], attention: bool = False, turn: bool = True) -> None:
        # Its learning is its own, whatever its model: the model's seat takes the
        # inducer, and the learning computes with it (Plone, 2026-09-28). Its law of
        # curiosity is the learning's (`learning.CURIOSITY`), and so is whether it
        # attends to the experiences most like where it stands (`learning.ATTENTION_K`).
        self.learning: Learner = Learning(inducer, organs, priors, curiosity=curiosity, attention=attention,
                                           turn=turn)
        self.organs = organs
        self.steps_seen = 0
        # For the run's report only, never the field: whether each expectation of
        # a step held, and each command given (the trace is `[event]`).
        self.holds: list[int] = []
        self.commands: list[tuple[int, Act | None]] = []
        self._priors: dict[str, tuple[Any, str | None]] = {}
        self._priors_asked = False
        self._pending: str | None = None
        self._command_due = False
        # The recent steps: [step, unit, report or None, the report's unit or
        # None], as long as T5's window.
        self._seen: list[list[Any]] = []
        self._report_seen_at: int | None = None
        self._said: dict[str, Any] | None = None
        self._said_by_model = False
        self._held: tuple[object, ...] = ()
        self._offers: tuple = ()
        # The one aim it holds, and the cycle it asked its memory for its priors.
        self._aim: dict[str, Any] | None = None
        self._asked_at: int | None = None
        self._report_this_cycle = False
        self._remark: dict[str, Any] | None = None
        self._remark_unit: InfoUnit | None = None
        # Its answer to what an Other said, while it stands: the data it is. The
        # mind expects the Other to stop saying it (`Organs.quiet`).
        self._answer: tuple[object, ...] = ()
        self._thought_at: int | None = None
        self._thoughts_this_cycle = 0
        # The cycle's field, as it reached the mind at T5 (INV-7).
        self._field: Any = None
        # Questions put to memory, with when; answers arrive the next cycle.
        self._asks_open: list[tuple[int, dict[str, str]]] = []
        self._recalled: dict[str, tuple[Step | None, dict[str, str], Any]] = {}
        self._recalled_at: int | None = None
        # What it wrote, by fingerprint, until each comes back; its learning's handle
        # for each, and the datum id each became; revisions owed until then.
        self._echoes: list[str] = []
        self._handle_of: dict[str, object] = {}
        self._ids: dict[object, str] = {}
        self._owed: dict[object, tuple[Any, tuple[object, ...]]] = {}
        # Data written before the ids of some handles they were built from came
        # back (`Write.relinks`): their handle, payload as written, and the
        # handles still awaited.
        self._relinks: list[tuple[object, dict[str, Any], list[object]]] = []

    # ── what the run's report reads ──

    @property
    def thoughts(self) -> list[Any]:
        return self.learning.thoughts

    def __getattr__(self, name: str) -> Any:
        # What a report or a test reads of the learning through the mind: its
        # version, its counts — the learning's, not the seams'.
        if name.startswith("__") or name == "learning":
            raise AttributeError(name)
        return getattr(self.learning, name)

    # ── priors, echoes, answers ──

    def _ready(self) -> bool:
        return self.learning.required() <= set(self._priors)

    def _ask_priors(self, ask) -> None:
        if self._priors_asked or ask is None:
            return
        for name, cue in self.learning.cues().items():
            if name not in self._priors:
                ask(dict(cue))
        self._priors_asked = True
        self._asked_at = self.steps_seen

    def receive(self, name: str, payload: Any, datum_id: str | None) -> None:
        """A prior it reads, as it came back from memory. A test may hand one in
        with no datum behind it: then nothing names it as built from."""
        self._priors[name] = (payload, datum_id)
        self.learning.receive_prior(name, payload, datum_id)
        goal = payload.get("goal") if isinstance(payload, dict) else None
        if isinstance(goal, dict) and isinstance(goal.get("reached_when"), dict) and \
                (self._aim is None or self._aim.get("source") == "own"):
            # The aim takes the goal's value; its own gives way to a goal.
            self._hold_aim({"aim": str(goal.get("aim") or ""), "source": "goal",
                            "reached_when": dict(goal["reached_when"])})

    def take_return(self, ret: dict[str, Any], write, ask=None, test=None) -> None:
        """A store return: a prior it reads, its own write back, or an answer."""
        open_tags = ret.get("open", {})
        payload = ret.get("payload")
        entity = str(ret.get("entity"))
        for name, cue in self.learning.cues().items():
            if isinstance(payload, dict) and all(open_tags.get(k) == v for k, v in cue.items()):
                first = name not in self._priors
                if first:
                    self.receive(name, payload, entity)
                if not self._ready():
                    return
                if self._pending is not None:
                    self.think(self._pending, ask, write)
                if self._command_due or (first and self._aim is not None and self.commands
                                         and self.commands[-1][1] is None):
                    # It waited for what it reads, or — on its first arrival — the
                    # host waits for want of an aim it now holds: command. Without
                    # this a mind that held no aim at its first step commanded only
                    # when something else arrived — the onlooker — and without one
                    # never did. A prior recalled again later, asked for, is not a
                    # reason to command.
                    self.command(ask, write, test)
                return
        mark = _fingerprint(payload)
        if mark in self._echoes:
            # Its own write, come back: not an answer, however its tags match.
            self._echoes.remove(mark)
            handle = self._handle_of.pop(mark, None)
            if handle is not None and handle not in self._ids:
                self._ids[handle] = entity
                self.learning.acknowledge(handle, entity)
                owed = self._owed.pop(handle, None)
                if owed is not None and write is not None:
                    self._request(write, WriteRequest(payload=owed[0], datum_id=entity, built_from=owed[1]))
                self._relink(write, handle)
            return
        if not self._answers(open_tags, ret.get("fixed")):
            return
        if self._recalled_at != self.steps_seen:
            self._recalled, self._recalled_at = {}, self.steps_seen
        step = self.organs.step(payload) if isinstance(payload, dict) else None
        self._recalled[entity] = (step, dict(open_tags), payload)

    def _answers(self, open_tags: dict[str, str], fixed: Any) -> bool:
        provenance = fixed.get("provenance") if isinstance(fixed, dict) else None
        return any(
            all((provenance == v) if k == "provenance" else (open_tags.get(k) == v) for k, v in cue.items())
            for _, cue in self._asks_open
        )

    # ── writing ──

    def _relink(self, write, handle: object) -> None:
        """A handle's id has come back: each datum written awaiting it, once it
        awaits nothing more, is revised to name the ids it was built from after
        (`built_after`); the revision waits for that datum's own id if need be."""
        still = []
        for owner, payload, awaited in self._relinks:
            awaited = [h for h in awaited if h is not handle]
            if awaited:
                still.append((owner, payload, awaited))
                continue
            after = sorted(self._ids[h] for h in payload["_awaited"])
            built = (*payload["_built"], *(i for i in after if i not in payload["_built"]))
            revised = {k: v for k, v in payload.items() if k not in ("_awaited", "_built")}
            revised["built_after"] = after
            # The revision is built from all the datum was: what it named, and now these.
            self._write(write, [Write(payload=revised, revises=owner, built_from=built)])
        self._relinks = still

    def _awaited(self, refs: tuple[object, ...]) -> list[object]:
        """The handles among what a datum was built from whose ids have not come back."""
        return [ref[1] for ref in refs if isinstance(ref, tuple) and len(ref) == 2 and ref[0] == "handle"
                and ref[1] not in self._ids]

    def _resolve(self, refs: tuple[object, ...]) -> tuple[object, ...]:
        """Units and datum ids as they are; handles and priors as the ids they became.
        A handle whose id has not come back is left out (a datum that asks for it is
        revised once it comes: `Write.relinks`)."""
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
                payload = w.payload
                awaited = self._awaited(w.built_from) if w.relinks and w.handle is not None else []
                if awaited and write is not None and isinstance(payload, dict):
                    payload = {**payload, "awaiting": len(awaited)}
                    self._relinks.append((w.handle, {**payload, "_awaited": list(awaited), "_built": built},
                                          list(awaited)))
                self._request(write, WriteRequest(payload=payload, open=dict(w.tags or {}), built_from=built),
                              w.handle)

    # ── the aim ──

    def _hold_aim(self, aim: dict[str, Any]) -> None:
        self._aim = aim
        self.learning.hold_aim(aim)

    def _own_aim_if_due(self) -> None:
        """No goal came back with what it asked its memory for: its own aim."""
        if self._aim is None and self._asked_at is not None and self.steps_seen > self._asked_at + GOAL_WAIT:
            self._hold_aim(dict(OWN_AIM))

    # ── arrivals, one rule per channel ──

    def on_step(self, step: Step, observed: InfoUnit, content: dict[str, Any], payload: dict[str, Any],
                 window, contribute, ask, write) -> InfoUnit | Expecting:
        self.steps_seen += 1
        self._report_this_cycle = False
        self._ask_priors(ask)
        o = self.organs
        # 1. Expect, from the situation alone.
        expectation = self.learning.expect(step)
        expected = expectation.state
        by_model = expectation.by_model
        self._said, self._said_by_model = expectation.fields, expectation.fields is not None
        self._held = expectation.held if expectation.held else (self.learning.held() if by_model else ())
        predicted = InfoUnit(content={**content, "value": o.expected_payload(payload, expected)},
                             ref_frame=observed.ref_frame, t=observed.t)
        # 2. Then this step joins the recent steps.
        # Kept as long as the longest window the field can ask of T5; read as long
        # as the one it asks now (`_recent`).
        self._seen = [*self._seen, [step, observed, None, None]][-2 * BASELINE_WINDOW:]
        hit = expected.differs(step.after) if isinstance(expected, Otherwise) else \
            expected.matches(step.after) if isinstance(expected, AsRead) else expected == step.after
        self.holds.append(int(hit))
        self._write(write, self.learning.observe(step, observed, None, (observed,), on_report=False,
                                                 seen=self._recent()))
        # Its votes on the field (INV-7: each layer from what it alone sees): how far
        # the loop leans to explore — whether the region came where it had not
        # stood; and how readily what it expects by is trusted — whether what its
        # memory named (an expectation held by a hypothesis or experiences) was
        # borne out; where it named nothing, no vote. The layers below see tags
        # and entities, never these.
        if contribute is not None:
            cast_votes(contribute, {EXPLORATION: 1.0 if self.learning.came_somewhere_new else 0.0,
                                    TRUST: (1.0 if hit else 0.0) if by_model else None})
        # 3. The expectation failed: think.
        if not hit:
            self.think("step", ask, write)
        held = self._resolve(self._held) if by_model else ()
        return Expecting(predicted=predicted, held_by=held) if held else predicted

    def on_report(self, observed: InfoUnit, content: dict[str, Any], payload: dict[str, Any],
                  window, contribute, ask, write, test) -> InfoUnit | Expecting:
        self._report_this_cycle = True
        o = self.organs
        standing_unit = window[-1] if window else observed
        standing = _content_value(standing_unit)
        report = payload.get(o.report_key) if isinstance(payload.get(o.report_key), dict) else None
        self._offers = o.read_offers(payload.get(o.offers_key))
        # The step just seen gets what the region reported of itself.
        if self._seen and self._report_seen_at != self.steps_seen and report is not None:
            self._seen[-1][2], self._seen[-1][3] = report, observed
            self._report_seen_at = self.steps_seen
        # The expectation: what the region reported last, the agent's own act as
        # it is — or, where its learning said the report, what it said, the fields it
        # left out staying as they were.
        base = standing if isinstance(standing, dict) else dict(payload)
        own_act = {k: payload[k] for k in o.own_keys if k in payload}
        base = {**base, **own_act} if own_act else base

        def expecting(*parts: dict[str, Any] | None) -> dict[str, Any]:
            said = {k: v for part in parts if part for k, v in part.items()}
            if not said or report is None:
                return base
            return {**base, o.report_key: expected_report(said, o.unchanged(report))}

        own = self._said if self._said_by_model else None
        value = expecting(own)
        by_model = self._said_by_model
        if value == standing:
            predicted = standing_unit
        else:
            base_content = standing_unit.content if isinstance(standing_unit.content, dict) else {}
            predicted = InfoUnit(content={**base_content, "value": value}, ref_frame=standing_unit.ref_frame,
                                 t=standing_unit.t)
        if self._seen and report is not None:
            step, unit, _, _ = self._seen[-1]
            self._write(write, self.learning.observe(step, unit, report, (unit, observed), on_report=True))
        # The expectation failed: think — once its learning has met the report.
        if value != payload:
            self.think("report", ask, write)
        # The region has said all it says this cycle: construct the next action.
        self.command(ask, write, test)
        held: tuple[object, ...] = (standing_unit,) if window else ()
        if by_model:
            held = (*held, *self._resolve(self._held))
        return Expecting(predicted=predicted, held_by=held)

    def on_remark(self, entity_id: str, observed: InfoUnit, payload: dict[str, Any], window, contribute, ask,
                  write, test=None) -> InfoUnit | Expecting:
        """What an Other says of the agent's behaviour reaches the mind at once, as a
        mismatch (§8.4: a collision read into coordinates by a third party).

        What the mind expects of it: that it says what it said — or, once the mind
        has answered it, that it stops (`Organs.quiet`), and that expectation is
        the answer's data. A remark that does not come as expected collides: a
        ResistEvent, the scar on the remark and on what the expectation was — the
        answer, when it was said again after it. The mind thinks on the collision
        there and then and, if it thought, commands again: the host has not yet
        acted this cycle and carries out the last command (Plone, 2026-09-27: a
        remark strikes the mind directly; the mind does not wait for it). In a
        cycle the region said nothing in, what is said is all that comes, and
        the mind commands after it."""
        standing = persistence(entity_id, window, observed, contribute, ask, write)
        said_before = _content_value(standing)
        answered = bool(self._answer) and self.organs.quiet is not None and isinstance(said_before, dict)
        if answered:
            content = observed.content if isinstance(observed.content, dict) else {}
            quiet = InfoUnit(content={**content, "value": self.organs.quiet(said_before)},
                             ref_frame=observed.ref_frame, t=observed.t)
            held = self._resolve(self._answer)
            expected: InfoUnit | Expecting = Expecting(predicted=quiet, held_by=held) if held else quiet
            predicted = quiet
        else:
            expected = predicted = standing
        self._remark = {k: v for k, v in payload.items() if k != "entity"}
        self._remark_unit = observed
        if _content_value(predicted) == payload:
            if answered:
                self._answer = ()  # it stopped: the answer did what it was for
        else:
            self._answer = ()
            if self.think("onlooker", ask, write, again=True) and self._report_this_cycle:
                self.command(ask, write, test, on="command again")  # before the host acts
        if not self._report_this_cycle:
            self.command(ask, write, test)
        self._report_this_cycle = False
        return expected

    # ── commanding ──

    def _recent(self) -> list[list[Any]]:
        """The recent steps: as many as T5's window this cycle — BASELINE_WINDOW,
        shifted by the field's exploration as T5 shifts it (½–1½, 8 to 24)."""
        n = int(shifted_count(BASELINE_WINDOW, falling(axis(self._field, EXPLORATION))))
        return self._seen[-n:]

    def _context(self, on: str) -> Context:
        report = self._seen[-1][2] if self._seen else None
        state = (report or {}).get(self.organs.state_field)
        return Context(
            on=on, steps_seen=self.steps_seen, seen=[(s, u, r) for s, u, r, _ in self._recent()],
            recalled=[(k, s, t, p) for k, (s, t, p) in self._recalled.items()],
            offers=self._offers, ended=state if state in self.organs.ended else None,
            remark=self._remark, remark_unit=self._remark_unit, aim=self._aim,
            priors=dict(self._priors), field=self._field,
        )

    def command(self, ask, write, test, on: str = "command") -> None:
        """Construct the next action, and command it: T5's test, carried out by
        the host if it can. With no command, think again while the host waits.
        `on` is "command again" when it commands a second time in a cycle, on
        what an Other said: the host carries out the last, and its learning is told
        so, so that what it writes can say which it replaces."""
        if not self._seen:
            return
        if not self._ready():
            self._command_due = True  # it waits for what it reads
            return
        self._command_due = False
        self._own_aim_if_due()
        report = self._seen[-1][2] or {}
        state = report.get(self.organs.state_field)
        for attempt in range(MAX_WAIT_THOUGHTS + 1):
            if self._aim is None:
                reason = "no aim"
            else:
                proposal, writes = self.learning.propose(self._context(on))
                self._write(write, writes)
                act = proposal.act
                if act is not None and self.organs.can_carry_out(act, state, self._offers):
                    self.commands.append((self.steps_seen, act))
                    if test is not None:
                        test(self.organs.command(act))
                    return
                reason = "no command"
            if attempt < MAX_WAIT_THOUGHTS and not self.think(reason, ask, write, again=True):
                break  # its learning does not think on this: asking again changes nothing
        self.commands.append((self.steps_seen, None))

    # ── thinking ──

    def think(self, on: str, ask, write, again: bool = False) -> bool:
        """An expectation met a mismatch, or no command came: have its learning think.
        Once a cycle for a mismatch; `again` is the host waiting. False when the
        learning does not think on this."""
        if self._thought_at != self.steps_seen:
            self._thoughts_this_cycle = 0
        allowed = shifted_count(MIND_THOUGHTS_PER_CYCLE, rising(axis(self._field, ALERTNESS)))
        if self._thought_at == self.steps_seen and not again and self._thoughts_this_cycle >= allowed:
            return True
        if not self._ready():
            self._pending = on  # what it reads has not come back from memory yet
            return True
        self._pending = None
        self._thought_at = self.steps_seen
        if not again:
            self._thoughts_this_cycle += 1
        result = self.learning.think(self._context(on))
        if result is None:
            return False
        if result.asks is not None:
            self._asks_open = [(at, cue) for at, cue in self._asks_open if at >= self.steps_seen - 1]
            self._asks_open += [(self.steps_seen, dict(cue)) for cue in result.asks]
            if ask is not None:
                for cue in result.asks:
                    ask(dict(cue))
        self._write(write, list(result.writes))
        if on == "onlooker":
            self._answer = tuple(result.answer)
        return True


def mind_rule(mind: Mind) -> Callable[..., InfoUnit | Expecting]:
    """The mind at T5's seam (`PredictRule`): one rule, one mind, every arrival."""
    channels = mind.organs.channels

    def rule(entity_id: str, window, observed: InfoUnit, contribute=None, ask=None, write=None, test=None,
             field=None, read=None, record=None):
        # The cycle's field reaches the mind as it reaches every layer (INV-7);
        # the store's view, what it reads its memory through (v0.3.7 §9); and the
        # record's, what it reads its history through (v0.3.9 §9).
        mind._field = field
        mind.learning.recall_from(read)
        mind.learning.read_record(record)
        mind.learning.read_field(field)
        content = observed.content if isinstance(observed.content, dict) else {}
        channel = content.get("channel")
        payload = _content_value(observed)
        window = tuple(window or ())
        if channel == STORE_CHANNEL:
            if isinstance(payload, dict):
                mind.take_return(payload, write, ask, test)
            return observed
        if channel == channels.get("step") and isinstance(payload, dict):
            step = mind.organs.step(payload)
            mind.learning.step_source = entity_id
            if step is not None:
                return mind.on_step(step, observed, content, payload, window, contribute, ask, write)
        if channel == channels.get("report") and isinstance(payload, dict):
            return mind.on_report(observed, content, payload, window, contribute, ask, write, test)
        if channel == channels.get("others") and isinstance(payload, dict):
            return mind.on_remark(entity_id, observed, payload, window, contribute, ask, write, test)
        return persistence(entity_id, window, observed, contribute, ask, write)

    return rule


__all__ = ["MAX_WAIT_THOUGHTS", "MIND_THOUGHTS_PER_CYCLE", "Mind", "expected_report", "mind_rule"]
