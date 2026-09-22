"""display_name — a derived human-readable projection of a datum's tags.

This DISPLAYS tags as a name; it does NOT store tags in the name. The
authoritative tags remain the structured properties on the datum (tags.py):
fixed (with the updatable floor-tag) and open (≥3, keyed). A name is computed
from those on demand, never the source of truth — so the mutable parts
(floor-tag, provenance) never force a rename, and keyed open tags are never
flattened into lossy positions.

The store-kind prefix (`[data]`/`[event]`) is intentionally omitted: kind is
carried by storage *location* (the `store/{memory,event-log,commits}/` layout),
not by the name.

Example:
    [20260630]_[10:00:00]_[c2]_[running]_[T6]_[domain:financial]_[currency:VND]_[object:revenue]

Ported from dil-core against DIL protocol v0.3.2.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .tags import OpenTags, TaggedDatum

if TYPE_CHECKING:
    from .resist_event import EventRecord


def _yyyymmdd(ts: int) -> str:
    """Format an epoch-millisecond timestamp as YYYYMMDD in UTC (deterministic)."""
    d = datetime.fromtimestamp(ts / 1000, tz=UTC)
    return f"{d.year:04d}{d.month:02d}{d.day:02d}"


def _hhmmss(ts: int) -> str:
    """Format an epoch-millisecond timestamp as HH:mm:ss in UTC (deterministic)."""
    d = datetime.fromtimestamp(ts / 1000, tz=UTC)
    return f"{d.hour:02d}:{d.minute:02d}:{d.second:02d}"


def _ordered_open(open_tags: OpenTags) -> list[tuple[str, str]]:
    """Open-tag entries with `domain` first, then the rest sorted by key.

    The reference sorts the remainder with `String.localeCompare`, which is
    locale-sensitive; this sorts by code point, which is not. For the ASCII keys
    a tag registry actually uses the two agree, and a deterministic order is the
    property the name needs.
    """
    return sorted(open_tags.items(), key=lambda kv: (kv[0] != "domain", kv[0]))


def display_name(datum: TaggedDatum) -> str:
    """Project a datum's tags into a display name.

    Renders the fixed layer (date, cycle-mark, provenance, floor-tag) then every
    open tag as `key:value` (keys preserved, so the name stays filterable). The
    cycle-mark of a `prior` (None) renders as `c-`.
    """
    f = datum.fixed
    cycle = f.cycle_mark if f.cycle_mark is not None else "-"
    parts = [
        f"[{_yyyymmdd(f.timestamp)}]",
        f"[{_hhmmss(f.timestamp)}]",
        f"[c{cycle}]",
        f"[{f.provenance}]",
        f"[T{f.floor_tag}]",
        *(f"[{k}:{v}]" for k, v in _ordered_open(datum.open)),
    ]
    return "_".join(parts)


def event_display_name(record: EventRecord) -> str:
    """Project an [event] record into a display name.

    Since the event inherits the scar's tags, the name is the scar's display name
    plus the mismatch kind.
    """
    return f"{display_name(record.scar)}_[{record.event.mismatch_kind}]"
