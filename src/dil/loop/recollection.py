"""Recollection — a law a mind may think by, over the record it reads.

§9 makes the store the seat of experience: "The self accrues from scars." §10
requires a private store to carry the resistance-retrieval channel, "otherwise
drift is certain". The channel is the record's view (v0.3.9, `record_view.py`):
an open link, handed to every predict rule every cycle. This is one law built on
it, not the link itself, and a rule takes it only by being it.

Note what §10 names: retrieval of RESISTANCE, not retrieval of data. So what
this law takes from the log is an expectation — what the region gave, last time,
in this same situation — held by the datum that collided then. Nothing else
crosses:

    read [event] ──► an expectation ──► the region answers ──► mismatch ──► scar

The scar it recalls is the datum the expectation is (`held_by`, v0.3.5): used
again, it returns to `running` (§9 `scar → running`), and if the region
contradicts it, it is scarred again — the driver does both, as for any held
datum. Measured as a predictor, it loses to persistence (LOG.md): the record
holds the region's exceptions, faithfully.

THE LOG IS HISTORY, READ BACK AS AN OTHER (protocol v0.3.8; Plone, 2026-10-25).
The whole store is the agent's history, `[data]` its memory and the log the
record that is only appended to and read: the agent reads it, and what it takes
from it is held in its memory. That record is the real past of what happened: a
trace that can be followed and inspected as any program's trace can. It asserts
nothing about a self that continues — §7 still forbids an implementation to
"claim self-continuity as an internal measurement". Reading it back is a meeting
with an Other in Mode-A, not the agent meeting itself: the record returns, being
immutable it "says no in a way the agent cannot re-interpret away" (§8.4), and the
agent may collide with it. It may not conclude that the record was itself.

ONLY SCARS ARE RECALLABLE, and that is not a shortcut. §10 names retrieval of
RESISTANCE: what returns here is what collided. An activity record is trace, not
experience (§9), and this law does not take one.

WHAT IT DOES NOT REACH, declared. The record was written under the same lens
that now reads it. A standing bias is recorded and returned and agrees with
itself, so recollection catches drift ACROSS time and not bias that never moved.
Its resistance is Mode-A, the agent's own record through its own lens, and §8
asks that Mode-A never run pure: it stands beside a live Mode-B source, never in
its place. §8.4's reflection — a third party's own view, pointed at a place in
the trace — is a different mechanism and is not replaced by this.

Ported from dil-core (c258f43).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final

from ..store.resist_event import EventRecord
from .layers.t5 import Expecting, RecordView, persistence
from .types import InfoUnit, RefFrame

# The reference frame a recalled unit is referred to (INV-4: non-null).
RECOLLECTION_LAYER: Final = 5

# The purpose its reads of the record are recorded under.
RECOLLECTION_PURPOSE: Final = "recollection"

# Derives the situation key an observation names (DECIDE@IMPL).
SituationKey = Callable[[InfoUnit], str]


def entity_only(unit: InfoUnit) -> str:
    """Default situation key: every situation is the same one — the weakest
    useful reading, "the last time this entity resisted". A host that can say
    WHERE it is supplies a sharper key."""
    return ""


def recall(
    record: RecordView,
    entity_id: str,
    observed: InfoUnit,
    key: SituationKey = entity_only,
) -> Expecting | None:
    """What the region gave, last time, in the situation this observation names —
    held by the datum that collided then — or None when the record, as far as
    the view reaches, holds nothing about it.

    `observed` is read to identify WHICH situation is being asked about. Its
    content is never used as the answer: that would be the prediction scoring
    itself (INV-8). Each scar the view returns is a record read, recorded under
    `recollection`."""
    wanted = key(observed)
    for found in record.scars(entity_id, RECOLLECTION_PURPOSE):
        r = found.record
        if not isinstance(r, EventRecord):
            continue
        # An absence scar records that nothing came back. There is no
        # observation in it to recall, and inventing one would fabricate a
        # return the region never made.
        if r.event.received is None or r.datum_id is None:
            continue
        past = InfoUnit(
            content=r.event.received,
            ref_frame=RefFrame(bound_layer=RECOLLECTION_LAYER, ref=f"recollection:{entity_id}"),
            t=r.event.t,
        )
        if key(past) == wanted:
            return Expecting(predicted=past, held_by=(r.datum_id,))
    return None


def recollecting(
    fallback: Callable[..., Any] = persistence,
    key: SituationKey = entity_only,
) -> Callable[..., Any]:
    """A predict rule that reads the record first and falls back when it is silent.

    The record answers only about a situation it holds within the view's reach;
    a situation it has never met leaves the fallback in charge, so this is never
    worse-informed than the law it extends. With no view — a rule run outside a
    cycle — the fallback answers."""

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None, *, record=None):
        recalled = recall(record, entity_id, observed, key) if record is not None else None
        if recalled is not None:
            return recalled
        return fallback(entity_id, window, observed, contribute, ask, write)

    return rule
