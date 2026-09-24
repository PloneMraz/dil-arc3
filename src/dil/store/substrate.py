"""Substrate & DIL-CLAIM — DIL imposes its store law on the host's physical memory.

The host supplies only a *raw durable substrate* (a directory or partition on its
native storage). DIL does NOT conform to any store abstraction the host might
carry; it *requisitions* the raw substrate and imposes its ENTIRE law on it — the
layout, the tag schema, the tagging-gate, the append-only [event] log, the
provenance lifecycle, the commit DAG. "The granary still stores, but stores by a
new method."

This module fixes the two lowest pieces of that imposition:
  - the canonical on-substrate LAYOUT (store/{memory,event-log,commits}); and
  - the DIL-CLAIM: a marker DIL writes into the substrate declaring that this
    space is now ruled by DIL's law, at a stated version. On resume, a claim that
    is absent is written; a claim that is present but foreign or incompatible is
    refused — DIL owns the format, so it will not run a store it did not stamp, or
    one stamped under a different law.

The physical operations sit behind a small injectable `Substrate` seam so a
non-filesystem host (a partition, an object store) can back it differently; the
default is the local filesystem.

Ported from dil-core against DIL protocol v0.3.3.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Protocol

from .decisions import SCHEMA_VERSION, SCHEMA_VERSIONED_SINCE

# The law DIL stamps onto a substrate. A resume whose stored claim does not match
# these versions is refused (the substrate is not this DIL's, or is under a
# different law). Bump a version only on a real, intended change to that facet.
DIL_CLAIM: Final[dict[str, Any]] = {
    # The protocol version whose law governs this store.
    "protocol": "0.3.5",
    # The fixed-tag + open-tag schema version.
    "tagSchema": SCHEMA_VERSION,
    # The on-substrate layout version (the three store kinds below).
    "layout": 1,
}


class SubstrateClaimError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"DIL cannot claim the substrate: {detail}")


@dataclass(frozen=True, slots=True)
class StoreLayout:
    """The canonical on-substrate layout DIL imposes under a root."""

    root: str
    # `[data]` — mutable present (the SQLite store).
    memory: str
    # `[event]` — append-only, hash-chained JSONL segments.
    event_log: str
    # Snapshot DAG — content-addressed commit markers.
    commits: str
    # The DIL-CLAIM marker file.
    claim_file: str


class Substrate(Protocol):
    """The physical operations DIL needs of a substrate.

    Default: the local filesystem. A different host may inject its own backing.
    """

    def join(self, *parts: str) -> str: ...
    def mkdirp(self, dir_: str) -> None: ...
    def exists(self, path: str) -> bool: ...
    def read_text(self, path: str) -> str: ...
    def write_text(self, path: str, text: str) -> None: ...


class FsSubstrate:
    """The default filesystem substrate — this host's disk."""

    __slots__ = ()

    def join(self, *parts: str) -> str:
        return os.path.join(*parts)

    def mkdirp(self, dir_: str) -> None:
        Path(dir_).mkdir(parents=True, exist_ok=True)

    def exists(self, path: str) -> bool:
        return Path(path).exists()

    def read_text(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def write_text(self, path: str, text: str) -> None:
        Path(path).write_text(text, encoding="utf-8")


def fs_substrate() -> Substrate:
    return FsSubstrate()


def layout_for(root: str, sub: Substrate | None = None) -> StoreLayout:
    """Resolve the canonical layout paths under a root (no I/O)."""
    s = sub if sub is not None else fs_substrate()
    return StoreLayout(
        root=root,
        memory=s.join(root, "store", "memory"),
        event_log=s.join(root, "store", "event-log"),
        commits=s.join(root, "store", "commits"),
        claim_file=s.join(root, "store", "DIL-CLAIM.json"),
    )


def _write_claim(sub: Substrate, claim_file: str) -> None:
    payload = {**DIL_CLAIM, "claimedAt": int(time.time() * 1000)}
    sub.write_text(claim_file, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def claim_substrate(root: str, sub: Substrate | None = None) -> StoreLayout:
    """Claim the substrate and impose DIL's layout on it. Idempotent.

    - creates the three store directories if absent;
    - fresh substrate → writes the DIL-CLAIM marker;
    - already-claimed substrate → verifies the stored claim matches DIL_CLAIM; a
      foreign or incompatible claim raises (DIL will not run a store it did not
      stamp, or one stamped under a different law).

    Returns the resolved layout the rest of the store binds onto. This is the
    concrete act of "the king sits down" — run once at startup, after the gate.
    """
    s = sub if sub is not None else fs_substrate()
    layout = layout_for(root, s)
    s.mkdirp(layout.memory)
    s.mkdirp(layout.event_log)
    s.mkdirp(layout.commits)

    if not s.exists(layout.claim_file):
        _write_claim(s, layout.claim_file)
        return layout

    try:
        stored = json.loads(s.read_text(layout.claim_file))
    except (ValueError, OSError) as exc:
        raise SubstrateClaimError(
            f"existing {layout.claim_file} is not readable JSON; "
            "refusing to run a store whose claim is corrupt"
        ) from exc

    if not isinstance(stored, dict):
        raise SubstrateClaimError(
            f"existing {layout.claim_file} is not readable JSON; "
            "refusing to run a store whose claim is corrupt"
        )

    # `protocol` and `layout` must match exactly — a different law is not this store.
    for key in ("protocol", "layout"):
        if stored.get(key) != DIL_CLAIM[key]:
            raise SubstrateClaimError(
                f"substrate at {root} carries a foreign/incompatible claim "
                f"({key}={stored.get(key)}, expected {DIL_CLAIM[key]}); "
                "DIL will not rule a store stamped under a different law"
            )

    # `tagSchema` evolves forward within the VERSIONED era (policy B):
    #   - a stored schema in [SCHEMA_VERSIONED_SINCE, current) is fine — its lines
    #     are stamped per-line and hash under the versioned formula, so this DIL
    #     reads them and writes new ones under the current schema; the claim is
    #     advanced.
    #   - a NEWER stored schema is refused: an older DIL must not write a store it
    #     cannot fully interpret.
    #   - a PRE-VERSIONING stored schema is refused: its `[event]` lines carry no
    #     per-line stamp and were hashed under the old version-less formula, so the
    #     chain will not verify. Accepting it would advance the claim over a store
    #     whose trust-root log is unverifiable — the exact incoherence policy B
    #     exists to avoid. Clean non-start instead.
    raw_schema = stored.get("tagSchema")
    stored_schema = raw_schema if isinstance(raw_schema, int) and not isinstance(raw_schema, bool) else None

    if stored_schema is None or stored_schema > DIL_CLAIM["tagSchema"]:
        raise SubstrateClaimError(
            f"substrate at {root} is stamped under tag-schema {raw_schema}, newer "
            f"than this DIL's {DIL_CLAIM['tagSchema']}; it cannot safely write a "
            "store it does not fully interpret — upgrade DIL"
        )

    if stored_schema < SCHEMA_VERSIONED_SINCE:
        raise SubstrateClaimError(
            f"substrate at {root} is stamped under pre-versioning tag-schema "
            f"{raw_schema} (< {SCHEMA_VERSIONED_SINCE}); its [event] lines predate "
            "the self-describing chain and cannot be verified under the versioned "
            "hash formula. DIL will not run a store whose trust-root log it cannot "
            "verify"
        )

    if stored_schema < DIL_CLAIM["tagSchema"]:
        # advance the claim: new writes are under the current schema
        _write_claim(s, layout.claim_file)

    return layout
