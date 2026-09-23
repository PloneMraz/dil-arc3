"""The thinking algorithm: what this Other will do, given what I just did.

It plugs into T5's `PredictRule` seam and supplies the **expectation**. It never
sees the afforded set and never reaches the emission, so it cannot choose. The
model thinks; the self acts.

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

With `perceive.py` finding the things and `interpret.py` reading what became of
them, none of that is needed here. No mover to discover, no background to vote
on, no rigidity filter, no translation invariance to engineer: a thing is already
a thing and its displacement is already its displacement. What is left is the
part that is actually thinking — associating a situation with an outcome and
answering for it.

Measured on the same 316 real transitions the old model was measured on:

    game    old (hand-coded feature)   new (things)
    ls20                         94%            93%
    vc33                         69%            85%

One point given up where the hand-coded feature was doing the work, sixteen
gained where it was blind — and the feature is gone.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Final

from dil.loop.types import InfoUnit

# The context for an observation that names none.
NO_CONTEXT: Final = ""

# Whether this situation is one the model has met before (INV-7, up-channel).
CONTEXT_NOVELTY: Final = "contextNovelty"
# How many distinct situations the model is holding (INV-7, up-channel).
CONTEXTS_KNOWN: Final = "contextsKnown"


def _key(value: object) -> str:
    """A hashable form of an observation, for counting.

    `json.dumps(sort_keys=True)` is the same comparison T5 uses to decide whether
    an expectation matched, so what this counts as "the same outcome" and what T5
    counts as "predicted correctly" cannot drift apart.
    """
    return json.dumps(value, sort_keys=True, default=str)


class Mind:
    """Associates (Other, situation) with what the Other then did."""

    __slots__ = ("_table", "_last", "_seen_values")

    def __init__(self) -> None:
        # The accrued evidence: per (entity, context), how often each outcome.
        # Counted by key, with one exemplar kept, so the outcome can be returned.
        self._table: dict[tuple[str, str], Counter[str]] = {}
        self._seen_values: dict[str, object] = {}
        # Persistence fallback, per entity: the last thing it did.
        self._last: dict[str, object] = {}

    # ── what it knows so far (read-only, for reporting) ──

    def contexts_known(self) -> int:
        return len(self._table)

    def entities_known(self) -> int:
        return len({entity for entity, _ in self._table})

    def has_seen(self, entity: str, context: str) -> bool:
        return (entity, context) in self._table

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
    """The situation this observation was made in — what the agent just did."""
    payload = _payload_of(unit)
    if payload is None:
        return NO_CONTEXT
    context = payload.get("context")
    return context if isinstance(context, str) else NO_CONTEXT


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

    def rule(entity_id: str, window, observed, contribute=None):
        payload = _payload_of(observed)
        if payload is None:
            return observed
        context = situation_of(observed)

        # 1. Both sources answer, from the situation alone.
        from_mind = mind.predict(entity_id, context)
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
                    CONTEXT_NOVELTY: 0.0 if mind.has_seen(entity_id, context) else 1.0,
                    CONTEXTS_KNOWN: float(mind.contexts_known()),
                }
            )

        # 2. Then accrue what actually happened.
        outcome = observed_outcome(observed)
        if outcome is not None:
            mind.observe(entity_id, context, outcome)

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
