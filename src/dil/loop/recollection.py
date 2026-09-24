"""Recollection — the store answering, as an expectation and as nothing else.

§9 makes the store the seat of experience: "The self accrues from scars." §10
requires a private store to carry the resistance-retrieval channel, "otherwise
drift is certain". Neither clause was satisfied anywhere: scars were written and
never returned, and the three edges §9 defines for their return —
`scar → running`, `scar → simulated`, `scar → projected` — could not fire,
because nothing in the loop read the store at all.

This is that channel. Note what §10 actually names: retrieval of RESISTANCE, not
retrieval of data. So the log's only output here is an expectation — what the
region gave, last time, in this same situation. Nothing else crosses:

    read [event] ──► an expectation ──► the region answers ──► mismatch ──► scar

WHY THE LOG IS AN OTHER AND NOT A MEMORY. §7 forbids the alternative outright:
"Continuity is not measurable from within... An implementation MUST NOT claim
self-continuity as an internal measurement." An agent treating the log as *its
own past* would be asserting exactly that continuity. It may only treat the log
as something that RETURNS — and a returning record satisfies §8.4's B-source
rule better than most live sources do, being immutable: it "says no in a way the
agent cannot re-interpret away". The agent may collide with the record. It may
not conclude that the record was itself.

ONLY SCARS ARE RECALLABLE, and that is not a shortcut. §9 admits activity
records as "trace, not experience: no layer learns from it", which "keeps the
audit trail complete across quiet stretches without letting uncontested
information into the agent's memory". Recalling only collided material keeps
that line exactly where §9 draws it.

WHAT IT DOES NOT REACH, declared. The record was written under the same lens
that now reads it. A standing bias is recorded and returned and agrees with
itself, so recollection catches drift ACROSS time and not bias that never moved.
It is a genuine Mode-B channel and it is weaker than a foreign one; §8.4's
reflection — a third party's own view, pointed at a place in the trace — is a
different mechanism and is not replaced by this.

Ported from dil-core.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, Protocol

from ..store.event_log import ReadableEventLog
from ..store.resist_event import EventRecord
from .types import InfoUnit, RefFrame

# The reference frame a recalled unit is referred to (INV-4: non-null).
RECOLLECTION_LAYER: Final = 5

# How many of an entity's records to scan back through, newest first. A bound,
# not a policy: the log is unbounded by §9 and a per-cycle read must not grow
# with it.
DEFAULT_MAX_SCAN: Final = 64

# Derives the situation key an observation names (DECIDE@IMPL).
SituationKey = Callable[[InfoUnit], str]


def entity_only(unit: InfoUnit) -> str:
    """The weakest useful key: every situation is the same one."""
    return ""


@dataclass(frozen=True, slots=True)
class RecalledFrom:
    """Where a recalled expectation came from — a scar, named by the datum key
    it takes in `[data]` and the cycle it was recorded at."""

    entity_id: str
    cycle: int
    t: int
    # The `[data]` key of the recalled scar: the datum the record names — the
    # region's return that collided — or, where it names none (an absence), the
    # cycle datum `cycle-N` that stood for it. Ported from dil-core dc7a9a7.
    datum_id: str = ""


class Recollection(Protocol):
    def recall(self, entity_id: str, observed: InfoUnit) -> InfoUnit | None:
        """What the region gave, last time, in the situation this observation
        names — or None when the record holds nothing about it.

        `observed` is read to identify WHICH situation is being asked about. Its
        content is never used as the answer: that would be the prediction
        scoring itself (INV-8).
        """
        ...

    def drain(self) -> tuple[RecalledFrom, ...]:
        """The scars recalled since the last drain, for the driver to record.

        A recalled scar has returned "to the store as data in use" (§9,
        `scar → running`), and §9 requires every such transition to be recorded
        in `[event]` as it occurs. A layer MUST NOT write to the log, so the
        recollection reports and the DRIVER writes.
        """
        ...


class LogRecollection:
    """A Recollection over an `[event]` log.

    Takes a `ReadableEventLog` and nothing more, so §8.4's "Mode-B returns; it
    does not write" holds by construction — this channel cannot append to
    `[event]`, reach into `[data]`, or correct the store.
    """

    __slots__ = ("_log", "_key", "_max_scan", "_recalled")

    def __init__(
        self,
        log: ReadableEventLog,
        key: SituationKey | None = None,
        max_scan: int = DEFAULT_MAX_SCAN,
    ) -> None:
        self._log = log
        self._key = key if key is not None else entity_only
        self._max_scan = max_scan
        self._recalled: list[RecalledFrom] = []

    def drain(self) -> tuple[RecalledFrom, ...]:
        out = tuple(self._recalled)
        self._recalled.clear()
        return out

    def recall(self, entity_id: str, observed: InfoUnit) -> InfoUnit | None:
        wanted = self._key(observed)
        records = self._log.by_source_id(entity_id)
        start = max(0, len(records) - self._max_scan)

        for i in range(len(records) - 1, start - 1, -1):
            record = records[i]
            if not isinstance(record, EventRecord):
                continue
            event = record.event
            # An absence scar records that nothing came back. There is no
            # observation in it to recall, and inventing one would fabricate a
            # return the region never made.
            if event.received is None:
                continue

            past = InfoUnit(
                content=event.received,
                ref_frame=RefFrame(
                    bound_layer=RECOLLECTION_LAYER, ref=f"recollection:{entity_id}"
                ),
                t=event.t,
            )
            if self._key(past) == wanted:
                self._recalled.append(
                    RecalledFrom(
                        entity_id=entity_id,
                        cycle=record.anchor.cycle,
                        t=event.t,
                        datum_id=record.datum_id or f"cycle-{record.anchor.cycle}",
                    )
                )
                return past
        return None


def create_log_recollection(
    log: ReadableEventLog,
    key: SituationKey | None = None,
    max_scan: int = DEFAULT_MAX_SCAN,
) -> LogRecollection:
    return LogRecollection(log, key, max_scan)
