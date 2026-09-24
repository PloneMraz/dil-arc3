"""The thinking algorithm: what this Other will do, given what I just did.

It plugs into T5's `PredictRule` seam and supplies the **expectation**. It never
sees the afforded set and never reaches the committed action, so it cannot
choose. The model thinks; the self acts. What it may do is ask the store, through
the rule's `ask` — reading memory is thinking's, acting on the region is not.

WHAT IT IS NOT. It is not a downloaded network, for three reasons each sufficient
on its own: the scored games are unseen and their mechanics are the thing to be
discovered, so foreign weights predict the wrong world; the evaluation session has
no network; and INV-5 names the alternative outright — "refeeding the whole game
history into a context window each step is a load, not an accrual".

WHAT REPLACED THE EARLIER ONE, AND WHY IT IS SMALLER. The previous model did its
own perceiving: it reached past the loop into the raw grid and decided for itself
what was worth looking at — the square a move would land on. That was the body's
job done by the mind, and it collapsed a 64x64 world into nine situations, all of
them exhausted in fifteen cycles.

With `perceive.py` finding the pieces and `seeing.py` following each one across
frames, grouping the pieces that move together into one thing and reading what
lies ahead of it, none of that is needed here. No mover to discover, no
background to vote on, no rigidity filter, no translation invariance to
engineer: a thing is already a thing and its displacement is already its
displacement. What is left is the part that is actually thinking — associating a
situation with an outcome and answering for it.

Measured on the same 316 real transitions the old model was measured on:

    game    old (hand-coded feature)   stuff by value   tracked things + what lies ahead
    ls20                         94%              93%                              99%
    vc33                         69%              85%                              93%

The hand-coded feature is gone, and nothing was given up for it.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Final

from dil.loop.layers.t3 import STORE_CHANNEL
from dil.loop.types import InfoUnit

# The context for an observation that names none.
NO_CONTEXT: Final = ""

# Whether this situation is one the model has met before (INV-7, up-channel).
CONTEXT_NOVELTY: Final = "contextNovelty"
# How many distinct situations the model is holding (INV-7, up-channel).
CONTEXTS_KNOWN: Final = "contextsKnown"

# Per situation — per action, in this host — how well the mind now predicts what
# the Others do after it (INV-7, up-channel). One key per action: `resolved:action:3`.
RESOLVED_PREFIX: Final = "resolved:"
# Per situation, how the REGION has answered it (INV-7, up-channel):
# `valence:action:3`. This is where want lives. See `region_valence`.
VALENCE_PREFIX: Final = "valence:"
# Per situation, how fast the mind is LEARNING it (INV-7, up-channel):
# `progress:action:3`. This is what curiosity reads. See `Mind.progress`.
PROGRESS_PREFIX: Final = "progress:"

# How many uses of an action make one window of learning progress (DECLARED,
# tunable). Progress compares the last window's accuracy with the one before it,
# so an action needs twice this many uses before it has a progress at all; until
# then it counts as still being learned.
PROGRESS_WINDOW: Final = 4


def region_valence(status: object, directive: dict[str, Any] | None) -> float:
    """How the region answered, read against the directive the mind recalled.

    The signs are not in this code. They were, until 2026-09-23: +1 for a level
    or a win and -1 for game over, written here and admitted by nobody. That was
    a directive smuggled in as code — no `prior` tag, no tagging-gate, invisible
    to anyone reading the store. It now arrives the way the protocol has for it:
    the host's published rules, admitted as `prior`, recalled by T3 on a cue, run
    up the layers, and read here.

    What stays in the code is the interpretation — what an objective and a run
    ended without it MEAN to something that has been told to reach one. What
    comes from the directive is which of the region's states those are, and what
    the region counts on the way. With no directive recalled there is nothing to
    read against, and every answer reads 0: a character with no problem to solve
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
    # The count the directive names as the way there. The region reports its
    # change as `levelsDelta` (interpret.region_status).
    toward = (directive.get("toward") or {}).get("count")
    if toward == "levels_completed" and (status.get("levelsDelta") or 0) > 0:
        return 1.0
    return 0.0


def _key(value: object) -> str:
    """A hashable form of an observation, for counting.

    `json.dumps(sort_keys=True)` is the same comparison T5 uses to decide whether
    an expectation matched, so what this counts as "the same outcome" and what T5
    counts as "predicted correctly" cannot drift apart.
    """
    return json.dumps(value, sort_keys=True, default=str)


class Mind:
    """Associates (Other, situation) with what the Other then did."""

    __slots__ = (
        "_table", "_last", "_seen_values", "_hits", "_trials", "_valence", "_uses",
        "_directive",
    )

    def __init__(self) -> None:
        # The accrued evidence: per (entity, context), how often each outcome.
        # Counted by key, with one exemplar kept, so the outcome can be returned.
        self._table: dict[tuple[str, str], Counter[str]] = {}
        self._seen_values: dict[str, object] = {}
        # Persistence fallback, per entity: the last thing it did.
        self._last: dict[str, object] = {}
        # Per situation: how often a prediction about an Other came true. Accrued
        # (INV-5); the field only ever carries the current reading of it.
        self._hits: Counter[str] = Counter()
        self._trials: Counter[str] = Counter()
        # Per situation: every reading of how the region answered it.
        self._valence: dict[str, list[float]] = {}
        # Per situation, per use (one cycle in which the action was taken): how
        # many predictions about Others came true, out of how many. Keyed by the
        # cycle's time, so one use is every Other seen after one action.
        self._uses: dict[str, dict[int, list[int]]] = {}
        # The directive, once recalled from the store and run up the layers.
        # None until then: nothing has told this character what it is for.
        self._directive: dict[str, Any] | None = None

    # ── what it knows so far (read-only, for reporting) ──

    def contexts_known(self) -> int:
        return len(self._table)

    def entities_known(self) -> int:
        return len({entity for entity, _ in self._table})

    def has_seen(self, entity: str, context: str) -> bool:
        return (entity, context) in self._table

    def resolution(self, context: str) -> float | None:
        """How well the mind predicts what happens in this situation, so far."""
        trials = self._trials.get(context, 0)
        return self._hits[context] / trials if trials else None

    def valence(self, context: str) -> float | None:
        """How the region has answered this situation, so far, on average."""
        readings = self._valence.get(context)
        return sum(readings) / len(readings) if readings else None

    def progress(self, context: str) -> float:
        """How fast the mind is learning this situation — the size of the change
        in its accuracy between the last window of uses and the one before.

        WHY CURIOSITY READS THIS AND NOT HOW RESOLVED A SITUATION IS. Going for
        whatever is least resolved sticks to irreducible noise: measured on a
        live ls20 run, the agent took one action 103 times out of 120 because its
        outcome turned on something the mind could not see, so it never became
        resolved and curiosity never left it — the "noisy TV" failure. Noise that
        cannot be learned shows no progress, so curiosity that follows progress
        leaves it on its own. The absolute size is used, so an action whose
        accuracy starts FALLING — the world changed under it — is worth attention
        again too.

        A situation with fewer than two windows of uses counts as still being
        learned (1.0), which is also what makes an untried action come first.
        """
        uses = self._uses.get(context, {})
        accuracies = [h / t for _, (h, t) in sorted(uses.items()) if t]
        if len(accuracies) < 2 * PROGRESS_WINDOW:
            return 1.0
        recent = accuracies[-PROGRESS_WINDOW:]
        before = accuracies[-2 * PROGRESS_WINDOW : -PROGRESS_WINDOW]
        return abs(sum(recent) / PROGRESS_WINDOW - sum(before) / PROGRESS_WINDOW)

    def score(self, context: str, predicted: object, outcome: object, t: int = 0) -> None:
        """Record whether a prediction made in this situation came true.

        Called AFTER the prediction was formed, never before — comparing an
        expectation with what happened is what T5 does anyway, and it is not
        INV-8's concern, which is forming the expectation FROM the answer.
        """
        self._trials[context] += 1
        hit = _key(predicted) == _key(outcome)
        if hit:
            self._hits[context] += 1
        use = self._uses.setdefault(context, {}).setdefault(t, [0, 0])
        use[0] += int(hit)
        use[1] += 1

    def answered(self, context: str, status: object) -> None:
        """Record how the region answered this situation."""
        self._valence.setdefault(context, []).append(
            region_valence(status, self._directive)
        )

    def recall(self, returned: dict[str, Any]) -> None:
        """Take up what the store returned, if it is something the mind can read.

        Only a directive is read, today: a payload naming an objective. The rest
        of what may come back is left as it arrived. The return still carries
        the provenance the store held it at — `prior`, not the character's own
        and not yet tested — and nothing here changes that; only a collision
        does (§9).
        """
        payload = returned.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("objective"), dict):
            self._directive = payload

    def directive(self) -> dict[str, Any] | None:
        return self._directive

    # ── accrual and prediction ──

    def observe(self, entity: str, context: str, outcome: object) -> None:
        """Accrue one observation. Sequential, never reloaded (INV-5)."""
        key = _key(outcome)
        self._seen_values.setdefault(key, outcome)
        self._table.setdefault((entity, context), Counter())[key] += 1
        self._last[entity] = outcome

    def predict(self, entity: str, context: str) -> object | None:
        """What this Other is expected to do here, or None with nothing to say.

        A situation met before answers from that situation's evidence, by
        majority — which is the whole of the thinking, and is what beat reciting
        the most recent outcome by 5 points on one measured game and 1 on the
        other. A situation not met before falls back to what this Other last did.
        """
        seen = self._table.get((entity, context))
        if seen:
            return self._seen_values[seen.most_common(1)[0][0]]
        return self._last.get(entity)


def create_mind() -> Mind:
    return Mind()


def _payload_of(unit: InfoUnit) -> dict[str, Any] | None:
    content = unit.content
    if isinstance(content, dict):
        value = content.get("value")
        if isinstance(value, dict):
            return value
    return None


def observed_outcome(unit: InfoUnit) -> object | None:
    """What the region did, as this observation reports it.

    A thing reports a `change`; the region reports its `status`. Both are the
    outcome for their own entity, and the model does not need to know which kind
    of Other it is looking at to count them.
    """
    payload = _payload_of(unit)
    if payload is None:
        return None
    for field in ("change", "status"):
        if field in payload:
            return payload[field]
    return None


def situation_of(unit: InfoUnit) -> str:
    """What the agent just did, as this observation reports it."""
    payload = _payload_of(unit)
    if payload is None:
        return NO_CONTEXT
    context = payload.get("context")
    return context if isinstance(context, str) else NO_CONTEXT


def surroundings_of(unit: InfoUnit) -> str:
    """What the Other faced when the agent acted — what lay ahead of it."""
    payload = _payload_of(unit)
    if payload is None:
        return ""
    situation = payload.get("situation")
    return situation if isinstance(situation, str) else ""


def predict_rule(mind: Mind, recollection: Any = None):
    """Adapt a `Mind` to T5's `PredictRule`.

    Order is load-bearing and is INV-8 in code: **predict first, from the
    situation alone, and accrue the outcome only afterwards**. Reading the
    observation's outcome before predicting would let the expectation be built
    from the answer, and the prediction error would be scoring itself.

    Where a `recollection` is given, §6.4 settles what to do when two internal
    sources disagree — "the opposition is not resolved by an internal rule but
    collided against the region" — so where the record speaks it is what gets
    tested. Measured, the record is a worse predictor than the model, for a
    structural reason: §9 admits only mismatches to the store, so what it holds
    is the region's surprises, and asked what will happen an exception loses to a
    distribution. It is off by default for that reason.

    The predicted unit is the observed one with only its outcome replaced, so
    T5's content comparison reduces to the outcome. A recalled unit is spliced
    the same way: its own context and channel are from another cycle and would
    make an identical outcome read as a mismatch.
    """

    def rule(entity_id: str, window, observed, contribute=None, ask=None):
        payload = _payload_of(observed)
        if payload is None:
            return observed
        # Something the character recalled from its own store, arriving like any
        # other return. The mind reads it; it is not an Other to predict.
        if isinstance(observed.content, dict) and observed.content.get("channel") == STORE_CHANNEL:
            mind.recall(payload)
            return observed
        # Two readings of where the agent is, kept apart. `context` is the action
        # — what the mind reports on, per action, to the self. `where` is the
        # action together with what this Other faced — what the mind predicts
        # from. Measured, reading what lay ahead of each tracked thing took
        # prediction from 93% to 99% on ls20 and from 85% to 93% on vc33, and
        # resolved the moving object's blocked-or-not outcome completely.
        context = situation_of(observed)
        surroundings = surroundings_of(observed)
        where = f"{context}#{surroundings}" if surroundings else context

        # 1. Both sources answer, from the situation alone.
        from_mind = mind.predict(entity_id, where)
        from_record = (
            recollection.recall(entity_id, observed)
            if recollection is not None
            else None
        )

        # The model's reading of its own situation, reported upward into the
        # field (INV-7) BEFORE it accrues — otherwise every situation would look
        # familiar the instant it was met. This is the interpretation the field
        # had no way of getting: T4's `strangeness` measures whether an arrival
        # could be attributed at all, which is a different question.
        if contribute is not None:
            contribute(
                {
                    CONTEXT_NOVELTY: 0.0 if mind.has_seen(entity_id, where) else 1.0,
                    CONTEXTS_KNOWN: float(mind.contexts_known()),
                }
            )

        # 2. Then accrue what actually happened.
        outcome = observed_outcome(observed)
        if outcome is not None:
            if from_mind is not None:
                mind.score(context, from_mind, outcome, observed.t)
            if "status" in payload:
                mind.answered(context, outcome)
            mind.observe(entity_id, where, outcome)

        # The mind's reading of this situation, reported upward (INV-7). Accrued
        # in the mind, carried by the field: the field's blend averages only the
        # contributions made THIS cycle and keeps no memory of its own, so the
        # memory has to be the contributor's. Each key names one situation, so
        # the field comes to hold a picture of every action the agent has taken,
        # updated as each is taken again.
        if contribute is not None and context:
            reading: dict[str, float] = {}
            resolution = mind.resolution(context)
            if resolution is not None:
                reading[RESOLVED_PREFIX + context] = resolution
            reading[PROGRESS_PREFIX + context] = mind.progress(context)
            valence = mind.valence(context)
            if valence is not None:
                reading[VALENCE_PREFIX + context] = valence
            if reading:
                contribute(reading)

        # 3. No arbiter (§6.4). The record, where it speaks, is what is tested.
        chosen = _outcome_of(from_record)
        if chosen is None:
            chosen = from_mind
        if chosen is None:
            # First sighting of this Other, and the record is silent: predict the
            # observation itself, as the reference rule does.
            return observed

        field = "status" if "status" in payload else "change"
        content = {**observed.content, "value": {**payload, field: chosen}}
        return InfoUnit(content=content, ref_frame=observed.ref_frame, t=observed.t)

    return rule


def _outcome_of(unit: InfoUnit | None) -> object | None:
    """The outcome inside a recalled unit, if it carries one."""
    return None if unit is None else observed_outcome(unit)
