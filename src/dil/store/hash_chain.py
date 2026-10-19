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

CANONICALIZATION. The reference implementation hashes `JSON.stringify(record)`,
and `_canonical_json` below gives the same text: JavaScript's separators,
non-ASCII left unescaped, and numbers as JavaScript writes them — a float with
no fraction as an integer (`1.0` → `1`, `-0.0` → `0`), and the exponent where
JavaScript puts it (below 1e-6 and from 1e21: `1e-7`, `1e+21`; Python writes
`1e-07`, and `1e-05` where JavaScript writes `0.00001`). So a log written by
dil-core verifies under this verifier and one written here verifies under
dil-core's (`dil verify`). The records carry floats — an expectation's
`confidence` and `delta`, the field in a seal, a scar's error — and until
2026-10-19 this port hashed them as Python writes them, so `0.0` and `1.0` hashed
otherwise than in dil-core and every log written here broke under dil-core's
verifier at its first expectation (LOG.md, 2026-10-19). A line written so is
still verified here, by the form it was written in (`ChainOk.legacy` counts
them): either form binds the line's content, and nothing else is accepted.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from __future__ import annotations

import hashlib
import json
import re
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


def _js_number(x: float) -> str:
    """A finite float as ECMAScript's Number::toString writes it: the shortest digits
    that read back to it (Python's `repr` gives the same digits), placed by its rules."""
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    digits, exponent = _shortest(abs(x))
    k, n = len(digits), exponent + len(digits)  # value = 0.d1…dk × 10^n
    if k <= n <= 21:
        return sign + digits + "0" * (n - k)
    if 0 < n <= 21:
        return sign + digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * -n + digits
    e = n - 1
    mantissa = digits if k == 1 else digits[0] + "." + digits[1:]
    return f"{sign}{mantissa}e{'+' if e >= 0 else '-'}{abs(e)}"


def _shortest(x: float) -> tuple[str, int]:
    """The shortest digits of a positive float and the power of ten of the last."""
    mantissa, _, exp = repr(x).partition("e")
    whole, _, frac = mantissa.partition(".")
    digits = (whole + frac).lstrip("0")
    exponent = int(exp or 0) - len(frac)
    stripped = digits.rstrip("0")
    return stripped, exponent + len(digits) - len(stripped)


# In a text Python's `json` wrote, a string, or a float as Python writes it (a
# point, an exponent, or both); integers are not matched, and stand as they are.
_STRING_OR_FLOAT: Final = re.compile(r'"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+(?:e[-+]\d+)?|e[-+]\d+)')
_DIGITS: Final = frozenset("0123456789")


def _js_token(match: re.Match[str]) -> str:
    token = match.group()
    return token if token[0] == '"' else _js_number(float(token))


def _float_spans(text: str) -> list[tuple[int, int]]:
    """Where each float lies in a text Python's `json` wrote with no backslash in it:
    found at its point or its exponent (`str.find`, not a scan of every character —
    a frame's grids are hundreds of kilobytes of integers), and outside a string,
    which an even count of quotes before it says when no quote is escaped."""
    spans: list[tuple[int, int]] = []
    size = len(text)
    for mark in ".e":
        p = text.find(mark)
        while p != -1:
            if (p and text[p - 1] in _DIGITS and (mark == "." or text[p + 1] in "-+")
                    and not any(s <= p < e for s, e in spans) and text.count('"', 0, p) % 2 == 0):
                start = p
                while start and text[start - 1] in _DIGITS:
                    start -= 1
                if start and text[start - 1] == "-":
                    start -= 1
                end = p + 1
                if mark == ".":
                    while end < size and text[end] in _DIGITS:
                        end += 1
                    if end < size and text[end] == "e":
                        end += 2  # past the exponent's sign
                else:
                    end += 1
                while end < size and text[end] in _DIGITS:
                    end += 1
                spans.append((start, end))
            p = text.find(mark, p + 1)
    spans.sort()
    return spans


def _canonical_json(value: Any) -> str:
    """Serialize exactly as `JSON.stringify` does — see the note in the module docstring:
    Python's text, each float in it written again as JavaScript writes it."""
    text = _python_json(value)
    if "\\" in text:  # a quote may be escaped: tell strings apart the longer way
        return _STRING_OR_FLOAT.sub(_js_token, text)
    spans = _float_spans(text)
    if not spans:
        return text
    parts, last = [], 0
    for start, end in spans:
        parts += (text[last:start], _js_number(float(text[start:end])))
        last = end
    parts.append(text[last:])
    return "".join(parts)


def _python_json(value: Any) -> str:
    """How this port serialized a record before 2026-10-19: floats as Python writes them."""
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


def _python_hash(seq: int, prev: str, schema_version: int, record: SerializedEventRecord) -> str:
    """The hash this port gave a line before 2026-10-19 (floats as Python writes them)."""
    return _sha256(f"{seq}\n{prev}\n{schema_version}\n{_python_json(record)}")


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
    # Lines that verify only by the form this port wrote before 2026-10-19
    # (floats as Python writes them): dil-core's verifier does not take them.
    legacy: int = 0


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
    legacy = 0

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
            if line.hash != _python_hash(line.seq, line.prev, line.schema_version, line.record):
                return ChainBroken(
                    at_line=i,
                    reason="content break: hash does not match the record",
                )
            legacy += 1
        prev = line.hash

    return ChainOk(count=len(lines), head=prev, legacy=legacy)
