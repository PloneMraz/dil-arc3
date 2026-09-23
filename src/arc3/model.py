"""The thinking organ: what an action is expected to do, given the situation.

It plugs into T5's `PredictRule` seam and supplies the **expectation**. It never
sees the afforded set and never reaches the emission, so it cannot choose. The
model thinks; the self acts.

**Why it is not a downloaded network.** The games scored are ones the agent has
never seen, and their mechanics are the thing to be discovered, so weights
trained on other games predict the wrong world. Kaggle's evaluation session has
no network, and INV-5 forbids the alternative outright: "refeeding the whole
game history into a context window each step is a load, not an accrual", which
rules out a large model re-read of its own history every step. What is left —
and what the protocol actually asks for — is a predictor that **accrues within
the episode**, one observation at a time. It starts knowing nothing about the
game it is in, which is the honest starting position.

**What it conditions on.** Persistence predicts that a control does what it did
last time, and measured on real `ls20` frames that is right 66–86% of the time.
The residual is position: whether a move is blocked depends on what is in the
way. So the context is **what lies where the move would take you** — the cells
the mover would land on. Nothing else about the frame is used, because nothing
else was shown to matter, and a wider context would only spread the same
evidence thinner.

Both the mover and each action's displacement are **learned from the agent's own
effects**, not configured: the mover is whichever value has displaced rigidly
most often, and an action's displacement is the one most often seen under it.
Before either is known the context is empty and the model falls back to
persistence, so it is never worse-informed than the rule it replaces.
"""

from __future__ import annotations

from collections import Counter
from typing import Final

from dil.loop.types import InfoUnit

from .effect import Effect
from .frame import Frame

# The context for an action whose displacement or mover is not yet known.
NO_CONTEXT: Final = ""
# Stands for a destination cell that falls outside the grid — a wall of a kind,
# and distinguishable from any real cell value.
OFF_GRID: Final = -1
# A value must have displaced rigidly at least this often before it is trusted
# as the mover. One observation is a coincidence.
MIN_MOVER_VOTES: Final = 2


class EffectModel:
    """Predicts an affordance's effect, conditioned on where it would land."""

    __slots__ = (
        "_mover_votes", "_bg_votes", "_disp", "_table", "_last", "_rows", "_cols",
    )

    def __init__(self, rows: int = 64, cols: int = 64) -> None:
        self._rows = rows
        self._cols = cols
        # How often each value has displaced rigidly — the vote for "mover".
        self._mover_votes: Counter[int] = Counter()
        # How often each value was the commonest in a frame — the vote for
        # "background". The background mirrors every move: when a thing steps
        # into empty space, the hole it leaves steps the other way, so the
        # background collects displacement votes it has not earned and can tie
        # with, or beat, the thing that actually moved. Excluding it is not a
        # tie-break convention; the background is not an object.
        self._bg_votes: Counter[int] = Counter()
        # Per action, how often each (value, d_row, d_col) was seen. Keyed by
        # VALUE and filtered to the mover at query time, because which value is
        # the mover is not settled when the observation arrives — and the
        # background's mirrored displacement would otherwise outvote the real
        # one, being equally frequent and opposite.
        self._disp: dict[str, Counter[tuple[int, int, int]]] = {}
        # The accrued evidence: what each affordance did from each situation.
        self._table: dict[tuple[str, str], Counter[Effect]] = {}
        # Persistence fallback, per affordance.
        self._last: dict[str, Effect] = {}

    # ── what the model knows so far (read-only, for reporting) ──

    @property
    def background(self) -> int | None:
        for value, _ in self._bg_votes.most_common(1):
            return value
        return None

    @property
    def mover(self) -> int | None:
        background = self.background
        for value, votes in self._mover_votes.most_common():
            if value == background:
                continue
            return value if votes >= MIN_MOVER_VOTES else None
        return None

    def displacement(self, entity: str) -> tuple[int, int] | None:
        """How far this affordance moves the mover, as most often observed."""
        counter = self._disp.get(entity)
        mover = self.mover
        if not counter or mover is None:
            return None
        for (value, dr, dc), _ in counter.most_common():
            if value == mover:
                return (dr, dc)
        return None

    def contexts_known(self) -> int:
        return len(self._table)

    # ── perception for prediction ──

    def context(self, frame: Frame, entity: str) -> str:
        """Name the situation this affordance would act into.

        The key is the multiset of values the mover would land on. It is a
        multiset rather than a list of positions so that the same obstruction
        met at two places reads as the same situation — the translation
        invariance the effect signature already rests on.
        """
        # Note what the frame is mostly made of, every time one is seen. This
        # runs before the early returns: the background has to be known before
        # the mover can be told apart from it.
        self._note_background(frame)

        mover = self.mover
        if mover is None:
            return NO_CONTEXT
        step = self.displacement(entity)
        if step is None:
            return NO_CONTEXT

        dr, dc = step
        landing: Counter[int] = Counter()
        for grid in frame.grids:
            for r, row in enumerate(grid):
                for c, value in enumerate(row):
                    if value != mover:
                        continue
                    tr, tc = r + dr, c + dc
                    if 0 <= tr < self._rows and 0 <= tc < self._cols:
                        landing[grid[tr][tc]] += 1
                    else:
                        landing[OFF_GRID] += 1
        if not landing:
            return NO_CONTEXT
        return ";".join(f"{v}:{n}" for v, n in sorted(landing.items()))

    def _note_background(self, frame: Frame) -> None:
        counts: Counter[int] = Counter()
        for grid in frame.grids:
            for row in grid:
                counts.update(row)
        for value, _ in counts.most_common(1):
            self._bg_votes[value] += 1

    # ── accrual and prediction ──

    def observe(self, entity: str, context: str, effect: Effect) -> None:
        """Accrue one observation. Sequential, never reloaded (INV-5)."""
        for value, dr, dc in effect.displacements:
            self._mover_votes[value] += 1
            self._disp.setdefault(entity, Counter())[(value, dr, dc)] += 1
        self._table.setdefault((entity, context), Counter())[effect] += 1
        self._last[entity] = effect

    def predict(self, entity: str, context: str) -> Effect | None:
        """The expected effect, or None when the model has nothing to say.

        A situation seen before answers from that situation's evidence. One not
        seen before falls back to persistence, which is what this replaces and
        never does worse than.
        """
        seen = self._table.get((entity, context))
        if seen:
            return seen.most_common(1)[0][0]
        return self._last.get(entity)


def create_model(rows: int = 64, cols: int = 64) -> EffectModel:
    return EffectModel(rows=rows, cols=cols)


def situation_key(unit: InfoUnit) -> str:
    """The situation an observation names, for the recollection to key on.

    The same context the model conditions on, so the record answers about the
    same thing the model is predicting about.
    """
    content = unit.content
    if isinstance(content, dict):
        value = content.get("value")
        if isinstance(value, dict):
            context = value.get("context")
            if isinstance(context, str):
                return context
    return NO_CONTEXT


def predict_rule(
    model: EffectModel,
    recollection: Any = None,
    watch: Any = None,
):
    """Adapt an `EffectModel` to T5's `PredictRule`, optionally with the record.

    TWO SOURCES OF EXPECTATION, AND NO ARBITER BETWEEN THEM. The model says what
    it has learned; the record says what the region actually did, last time, in
    this same situation. They can disagree, and §6.4 already settles what to do
    about that: "the opposition is not resolved by an internal rule but collided
    against the region". So nothing here picks a winner on the merits. Where the
    record has something to say, it is what gets TESTED — and the region settles
    it. Where the record is silent, which is everywhere it has never collided,
    the model rules.

    That asymmetry is earned, not arbitrary. A record exists for a situation
    only because the region once contradicted the agent there. Testing the
    record again is testing exactly the point where the agent has already been
    wrong once, which is the point worth testing. And the record is the harder
    source to re-author: §8.4's B-source rule prefers "a source that says no in
    a way the agent cannot re-interpret away", and an immutable line in an
    append-only log is precisely that.

    Whichever source answers, the loser is corrected by the outcome: the model
    accrues the region's actual return either way, and a record that turns out
    wrong produces a fresh scar that supersedes it next time.

    Order is load-bearing and is INV-8 in code: the rule **predicts first, from
    the context alone, and accrues the observed effect only afterwards**. Reading
    the observation's effect before predicting would let the expectation be built
    from the answer, and the prediction error would be scoring itself.

    The predicted InfoUnit is the observed one with only its effect replaced, so
    T5's content comparison reduces to the effect — which is exactly what tag H
    declares fit to be. It also removes a latent fragility in plain persistence,
    which compared whole units and so would have counted a change in the afforded
    list as a failed prediction about the control.
    """
    from .observe import effect_from_value, effect_value

    def rule(entity_id: str, window, observed):
        value = observed.content["value"]
        context = value.get("context", NO_CONTEXT)

        # 1. Both sources answer, from the context alone — never from the effect
        #    being predicted, which is the answer (INV-8).
        from_model = model.predict(entity_id, context)
        from_record = (
            recollection.recall(entity_id, observed)
            if recollection is not None
            else None
        )

        # 2. Then accrue what actually happened. The model learns from the
        #    region whichever source was put up for testing.
        model.observe(entity_id, context, effect_from_value(value["effect"]))

        # 3. No arbiter (§6.4). The record, where it speaks, is what is tested.
        recalled_effect = _effect_of(from_record)
        if watch is not None:
            # An observability hook, off by default. It exists so a claim about
            # which source was right can be CHECKED on the real code path rather
            # than on a re-implementation of it. It reads; it never decides.
            watch(
                entity_id,
                context,
                effect_value(from_model) if from_model is not None else None,
                recalled_effect,
                value["effect"],
            )
        chosen = recalled_effect if recalled_effect is not None else (
            effect_value(from_model) if from_model is not None else None
        )
        if chosen is None:
            # First sighting of this affordance, and the record is silent:
            # predict the observation itself, as dil-core does.
            return observed

        # Only the effect is replaced, so T5's content comparison reduces to the
        # effect — which is what tag H declares fit to be. A recalled unit is
        # spliced the same way: its own `affords` and `game` are from another
        # cycle and would make an identical effect read as a mismatch.
        content = {**observed.content, "value": {**value, "effect": chosen}}
        return InfoUnit(content=content, ref_frame=observed.ref_frame, t=observed.t)

    return rule


def _effect_of(unit: InfoUnit | None) -> dict[str, object] | None:
    """The effect payload inside a recalled unit, if it carries one."""
    if unit is None or not isinstance(unit.content, dict):
        return None
    value = unit.content.get("value")
    if isinstance(value, dict) and isinstance(value.get("effect"), dict):
        return value["effect"]
    return None
