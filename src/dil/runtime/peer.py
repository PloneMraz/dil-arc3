"""Peer reflection — the reader is another agent in the same run.

NOT USED BY THIS HOST. Tag E here is the onlooker (`arc3/onlooker.py`): a peer
that relays another agent's recorded collisions only retells them, and two peers
echo each other (LOG.md, 2026-09-25). Kept as ported, its plumbing fixed and
tested. What follows is the case as it was made for it.

**The problem this solves.** §8.4 puts reflection outside the agent: "a collision
read into coordinates by a third party … entering through T3 tagged ENV_PUSHED",
and the agent "cannot self-reflect on call". §10 then makes it an obligation: "A
private store serves one agent and MUST carry the resistance-retrieval channel,
otherwise drift is certain." A Kaggle evaluation session has no network and no
human, so the usual reader — a user, a critic service — cannot exist.

**The protocol's own second branch.** §10 continues: "A shared store serves many
agents, wherein multiplicity itself supplies other-resistance, linking T8 and
SocialEdge." The way out is not to invent a third party but to stop being one
agent. Several agents run in the same session, each playing its own game, and
each reads the others' recorded collisions. dil-core's tag E already names this
source: "WHO reads (a user, **another agent**, a critic service) stays
deliberately deployment-open".

**Why a peer is a legitimate reader, and where that stops.** The reading must not
come from the lens it is meant to correct. A peer has accrued different
collisions from different games, so its lens is not this agent's, and
`form_reading` still refuses any coordinate that names no real record — a
reflection cannot be fabricated about a collision that never happened.

What this does NOT catch, and the paper must say so: every peer runs the same
implementation, with the same update law and the same declared thresholds. A bias
in the *mechanism* is invisible to all of them equally. Peer reflection catches
**accrued** drift, not **structural** bias. It is a real Mode-B channel between
agents, and it is weaker than a genuinely foreign reader. Declaring it as
anything more would be the self-confirmation §8.4 calls "a sealed room".

Ported concepts from dil-core; the peer arrangement is this host's own choice.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ..loop.cycle import HostCycleInput
from ..loop.layers.t2 import Emission
from ..store.event_log import ReadableEventLog
from ..store.resist_event import EventRecord, LogRecord
from .host_source import HostSource
from .reflection import CollisionCoordinate, collision_coordinates, form_reading, reflection_signal

# The channel a peer's reading enters on. T3 must have the reflection transducer
# registered for this id, so the reading is typed `reflection` rather than raw.
PEER_REFLECTION_CHANNEL = "peer-reflection"


class ReadOnlyEventLog:
    """A view of another agent's [event] log that can be read and nothing else.

    `ReadableEventLog` is a Protocol, so handing a peer the log itself would give
    it `append` in fact if not in type. This view holds no reference a caller can
    write through: it reads, and it reads late — the log is looked up at each call,
    so a peer built before the other agent's store exists sees it once it does.
    """

    __slots__ = ("_get",)

    def __init__(self, log: ReadableEventLog | Callable[[], ReadableEventLog]) -> None:
        self._get = log if callable(log) and not hasattr(log, "all") else (lambda: log)

    def all(self) -> list[LogRecord]:
        return self._get().all()

    def size(self) -> int:
        return self._get().size()

    def by_source_id(self, source_id: str) -> list[EventRecord]:
        return self._get().by_source_id(source_id)


def read_only(log: ReadableEventLog | Callable[[], ReadableEventLog]) -> ReadOnlyEventLog:
    """A read-only view of `log`, or of whatever log `log()` returns when read."""
    return ReadOnlyEventLog(log)


@dataclass(frozen=True, slots=True)
class PeerLog:
    """One peer's identity and its read-only log.

    The log is a ReadableEventLog and nothing more: §8.4's "Mode-B returns; it
    does not write" is kept by the type. A peer can be read; it cannot be written
    to, and it holds no handle on this agent's store.
    """

    reader_id: str
    log: ReadableEventLog


class PeerReflectingSource:
    """Wraps a HostSource and folds peers' unread collisions into each cycle.

    Every cycle it asks each peer's log for collisions it has not yet passed on,
    forms a reading about each, and appends them to that cycle's signals. They
    enter through T3 like any other external input — no side door — and T2
    classifies them ENV_PUSHED, because this agent never emitted them.

    Only collisions recorded *before* this cycle are read: a peer's log is
    evidence already written, never a live channel into the running loop.
    """

    __slots__ = ("_inner", "_peers", "_seen", "_channel", "_max_per_cycle", "delivered")

    def __init__(
        self,
        inner: HostSource,
        peers: Sequence[PeerLog],
        channel: str = PEER_REFLECTION_CHANNEL,
        max_per_cycle: int = 2,
    ) -> None:
        self._inner = inner
        self._peers = list(peers)
        # Per peer, how many of its collisions have already been read on.
        self._seen: dict[str, int] = {p.reader_id: 0 for p in peers}
        self._channel = channel
        # A bound, so one noisy peer cannot flood the cycle: §11's single-source
        # domination is the same failure the diversity monitor watches for.
        self._max_per_cycle = max_per_cycle
        self.delivered: list[Emission] = []

    def _readings(self, t: int) -> list:
        signals = []
        for peer in self._peers:
            coordinates: list[CollisionCoordinate] = collision_coordinates(peer.log)
            already = self._seen[peer.reader_id]
            fresh = coordinates[already : already + self._max_per_cycle]
            for coordinate in fresh:
                reading = form_reading(
                    peer.log,
                    coordinate.index,
                    peer.reader_id,
                    {
                        "drifted_at": {
                            "cycle": coordinate.cycle,
                            "source_id": coordinate.source_id,
                            "mismatch_kind": coordinate.mismatch_kind,
                        }
                    },
                )
                signals.append(reflection_signal(reading, self._channel, t))
            self._seen[peer.reader_id] = already + len(fresh)
        return signals

    def next(self) -> HostCycleInput | None:
        host_input = self._inner.next()
        if host_input is None:
            return None

        t = max((s.t for s in host_input.signals), default=0)
        readings = self._readings(t)
        if not readings:
            return host_input

        # Everything the inner source said is kept, presence included: the
        # readings add signals and change nothing else about the cycle.
        return HostCycleInput(
            signals=(*host_input.signals, *readings),
            changes=host_input.changes,
            interactions=host_input.interactions,
            afforded=host_input.afforded,
        )

    def deliver(self, response: Emission) -> None:
        self.delivered.append(response)
        self._inner.deliver(response)

    @property
    def inner(self) -> HostSource:
        """The source this one wraps — the body that plays."""
        return self._inner


def peer_reflecting_source(
    inner: HostSource,
    peers: Sequence[PeerLog],
    channel: str = PEER_REFLECTION_CHANNEL,
    max_per_cycle: int = 2,
) -> PeerReflectingSource:
    return PeerReflectingSource(
        inner, peers, channel=channel, max_per_cycle=max_per_cycle
    )
