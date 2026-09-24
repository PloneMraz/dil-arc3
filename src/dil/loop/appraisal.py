"""The appraisal step (protocol §6 link 4, §8.5, INV-8).

Between integration and response, the loop assigns direction and value. Two rules
bind it:

  - **INV-8**: it MUST NOT draw its criteria from the state the agent is editing,
    because self-scoring is hackable. Here the criteria come from the declared
    out-of-loop anchor (decisions.py, tag C) — external to the edited state.
  - **§8.5**: the standard is context, not a fixed scale. The appraisal reads the
    current ModField as the conditioning context, so the same information under a
    different field receives a different valence. The verdict is a ↔ — revisable
    — never a `=`.

Ported from dil-core against DIL protocol v0.3.3.
"""

from dataclasses import dataclass, field as dc_field

from ..invariants.guards import assert_appraisal_independence
from ..invariants.types import AppraisalCriteria
from .decisions import APPRAISAL_ANCHOR_ID
from .types import Appraisal, InfoUnit, ModField, PredErr


@dataclass(frozen=True, slots=True)
class AppraisalInput:
    # Reference to the information being appraised (e.g. a cycle id).
    info_ref: str
    # The cycle's prediction errors (resistance registered this cycle).
    pred_errs: tuple[PredErr, ...]
    # The cycle's modulatory field — the conditioning context (§8.5).
    field: ModField
    # Identifier of the state the agent is editing (for the INV-8 check).
    edited_state: str
    # Outcomes cast by forward-building this cycle (§6.2, §6.4), each entering
    # appraisal as an InfoUnit in its own right — but as a NOT-YET-COLLIDED
    # datum: a `projected` carries no resistance, having not met the region, so
    # it does not inflate the resistance-based valence. It is context the
    # appraisal has, the mechanism by which a new situation changes the command
    # (§6.4). Empty when the store afforded no material to build from.
    projected: tuple[InfoUnit, ...] = dc_field(default_factory=tuple)


def appraise(input: AppraisalInput) -> Appraisal:  # noqa: A002 — mirrors the reference
    """Appraise the cycle's integrated information.

    The valence reflects the resistance met, scaled by the field's appraisal gain
    so the same information under a different field lands differently.
    Goal-relevance reflects how much of the cycle was resistance. Both are a ↔.
    """
    # INV-8: criteria come from the external anchor, never the edited state.
    assert_appraisal_independence(
        AppraisalCriteria(
            criteria_source=APPRAISAL_ANCHOR_ID,
            edited_state=input.edited_state,
        )
    )

    # §8.5: read the current field as the conditioning context.
    gain = input.field.params.get("appraisalGain", 1.0)
    resistance = sum(e.delta for e in input.pred_errs)

    # Forward-cast outcomes are not-yet-collided: they carry no resistance, so
    # they do not change the valence — they only widen the set of information the
    # appraisal is made over (§6.4). Their presence is noted in the info_ref.
    projected = input.projected

    return Appraisal(
        info_ref=(
            f"{input.info_ref}+{len(projected)}proj" if projected else input.info_ref
        ),
        # Meeting resistance is informative but counts against the current
        # goal-fit; scaled by the context's gain.
        valence=-resistance * gain,
        goal_relevance=(
            min(1.0, resistance / len(input.pred_errs)) if input.pred_errs else 0.0
        ),
    )
