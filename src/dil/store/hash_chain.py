"""Tamper-evidence for the [event] log at rest (toward protocol §9).

Each persisted record is chained: line N carries `prev` (the hash of line N−1)
and `hash` (sha256 over seq + prev + schema version + the serialized record). A
verifier walking the file detects ANY alteration, removal, insertion, or
reordering of a line: the chain breaks at that point and every later line
inherits the break.

HONEST SCOPE, declared not implied:
  - Detection is relative to a trusted head. An adversary with full write access
    to the file can rewrite the WHOLE chain consistently; detecting a total
    rewrite requires anchoring the chain head outside their reach — that
    anchoring is a deployment concern, deliberately left open.
  - This protects the log AT REST. In-process tampering defeats any in-process
    check by definition.
  - The §9 full-system commit/snapshot is the commit store's job; its markers
    pin this chain's head, and an external copy of a marker anchors the chain.

CANONICALIZATION, and a limit worth stating. The reference implementation hashes
`JSON.stringify(record)`. `_canonical_json` below reproduces that byte for byte
for the value kinds these records actually carry — objects, arrays, strings,
integers, booleans and null — by using JavaScript's separators and leaving
non-ASCII unescaped. The consequence is useful: a log written by dil-core
verifies under this verifier and vice versa. The limit is floats. JavaScript
renders 1.0 as `1` and Python renders it as `1.0`, so a record carrying a
non-integral float would hash differently in the two implementations. Nothing
this store writes does — timestamps, cycle marks, sequence numbers and layer
indices are all integers — but a payload supplied by a host could, and then
cross-implementation verification no longer holds for that line.

Ported from dil-core against DIL protocol v0.3.3.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, TypeAlias

from .decisions import SCHEMA_VERSION, SCHEMA_VERSIONED_SINCE

if TYPE_CHECKING:
    # Type-only, exactly as the reference's `import type`: the serialized forms
    # live beside the sink that builds them, and importing them at runtime would
    # make a cycle out of a dependency that only the type checker has.
    from .event_sink import SerializedEventRecord
else:
    SerializedEventRecord: TypeAlias = dict[str, Any]

# The `prev` of the first line — no predecessor.
CHAIN_GENESIS: Final = "0" * 64


@dataclass(frozen=True, slots=True)
class ChainedEventLine:
    """One persisted, chained line of the [event] file."""

    # Position in the chain, contiguous from 0.
    seq: int
    # Hash of the previous line (CHAIN_GENESIS for the first).
    prev: str
    # The store schema version this line was written under. Because `[event]` is
    # immutable, the line is self-describing: a reader interprets its record by
    # THIS version, and a log may hold lines of several versions after a schema
    # change. Stamped into the hash, so it is tamper-evident.
    schema_version: int | None
    # The record body, tags in fixed order.
    record: SerializedEventRecord
    # sha256 over seq + prev + schema_version + record.
    hash: str


def _canonical_json(value: Any) -> str:
    """Serialize exactly as `JSON.stringify` does — see the note in the module docstring."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_chain_entry(
    seq: int,
    prev: str,
    schema_version: int,
    record: SerializedEventRecord,
) -> str:
    """The hash a well-formed line must carry (covers the line's own schema version)."""
    return _sha256(f"{seq}\n{prev}\n{schema_version}\n{_canonical_json(record)}")


def chain_next(prev_hash: str, seq: int, record: SerializedEventRecord) -> ChainedEventLine:
    """Build the next chained line after `prev_hash`, stamped with the current schema."""
    return ChainedEventLine(
        seq=seq,
        prev=prev_hash,
        schema_version=SCHEMA_VERSION,
        record=record,
        hash=hash_chain_entry(seq, prev_hash, SCHEMA_VERSION, record),
    )


@dataclass(frozen=True, slots=True)
class ChainOk:
    count: int
    head: str
    ok: bool = True


@dataclass(frozen=True, slots=True)
class ChainBroken:
    at_line: int
    reason: str
    ok: bool = False


ChainVerification: TypeAlias = ChainOk | ChainBroken


def verify_chain(lines: list[ChainedEventLine]) -> ChainVerification:
    """Walk the chain and verify every link.

    Returns the head hash on success, or the first broken line and why. An empty
    chain is vacuously ok with the genesis head.
    """
    prev = CHAIN_GENESIS

    for i, line in enumerate(lines):
        if line.seq != i:
            return ChainBroken(
                at_line=i,
                reason=f"sequence break: expected seq {i}, found {line.seq}",
            )
        if line.prev != prev:
            return ChainBroken(
                at_line=i,
                reason="chain break: prev does not match the previous line's hash",
            )
        # Version boundary (decisions.SCHEMA_VERSIONED_SINCE, policy B): a line
        # with no numeric schema version is a pre-versioning line, written under
        # the old version-less hash formula. Reject it by VERSION, not as a vague
        # "content break": the current verifier cannot hash it the way it was
        # written, and pre-versioning logs are declared outside the versioned
        # chain. A store that old is refused earlier still, at the substrate claim.
        if not isinstance(line.schema_version, int) or isinstance(line.schema_version, bool):
            return ChainBroken(
                at_line=i,
                reason=(
                    "pre-versioning line: no schemaVersion, written under the "
                    f"version-less formula before schema {SCHEMA_VERSIONED_SINCE}; "
                    "it is outside the versioned [event] chain and cannot be "
                    "verified — a store from that era is refused at claim time"
                ),
            )
        if line.hash != hash_chain_entry(line.seq, line.prev, line.schema_version, line.record):
            return ChainBroken(
                at_line=i,
                reason="content break: hash does not match the record",
            )
        prev = line.hash

    return ChainOk(count=len(lines), head=prev)
