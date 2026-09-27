"""The commit repo (protocol §9) — git-style, at `store/commits/`.

A COMMIT MARKER is the tiny commit-object: parent-linked (the DAG), it points
INTO the [event] log via the hash-chain head and at its snapshot payload via a
content address. The PAYLOAD is the whole-system state, stored as a tree of
content-addressed objects, as git stores a commit's tree (choice 2-(b); Plone,
2026-09-27; dil-core `1096476`): every object or array in it whose JSON is at
least MIN_OBJECT_BYTES long is stored once, under `objects/`, by the sha256 of
its text, and stands in its parent as `{"#dil-ref": <hash>}`; the root is stored
under `state/`, and its hash is the snapshot's address. A subtree that did not
change since the last snapshot is the same object, stored once: a snapshot costs
what changed, not the whole store. Every object read is checked against its
name, so the root's hash still covers the whole state. A snapshot written whole
before the tree (choice 2-(a)) has no reference in it, and reads as it was.

Immutability is self-enforcing, like git objects: every file's NAME is the sha256
of its content — written once, exclusively (fail-if-exists; identical content is
deduplicated by construction), never rewritten; editing a file breaks its own
name. `HEAD` is the one movable pointer (a git ref): rollback moves it by writing
a NEW fork marker — no marker is ever deleted. Payload retention governs `state/`
files only and is a deployment concern; no pruning exists here.

Ported from dil-core against DIL protocol v0.3.3; the tree from dil-core `1096476`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

_OBJECT_RE: Final = re.compile(r"^[0-9a-f]{64}\.json$")


@dataclass(frozen=True, slots=True)
class CommitMarker:
    """The tiny commit object. All content beyond it lives behind hashes."""

    # Hash of the previous marker; None for the first commit.
    parent: str | None
    # The [event] hash-chain head at commit time (None when no durable sink).
    chain_head: str | None
    # Log volume at commit time.
    event_count: int
    # Scars digested so far (the §9 counter rhythm, COMMIT_EVERY).
    scar_count: int
    # The cycle the snapshot was taken at (a cycle boundary).
    cycle: int
    # Wall-clock stamp, informational for operators (the loop runs in cycle-time).
    at: int
    # Content address of the snapshot payload.
    state_hash: str
    # The declared decision values in force (loop configuration, §9).
    config: dict[str, Any]
    # Set on the fork marker written at recovery: the marker restored FROM.
    recovered_from: str | None = None


def _marker_dict(marker: CommitMarker) -> dict[str, Any]:
    """Serialize a marker in the reference's key order — the hash covers the text."""
    out: dict[str, Any] = {"parent": marker.parent}
    if marker.recovered_from is not None:
        out["recoveredFrom"] = marker.recovered_from
    out["chainHead"] = marker.chain_head
    out["eventCount"] = marker.event_count
    out["scarCount"] = marker.scar_count
    out["cycle"] = marker.cycle
    out["at"] = marker.at
    out["stateHash"] = marker.state_hash
    out["config"] = marker.config
    return out


def _marker_from_dict(obj: dict[str, Any]) -> CommitMarker:
    return CommitMarker(
        parent=obj["parent"],
        chain_head=obj["chainHead"],
        event_count=obj["eventCount"],
        scar_count=obj["scarCount"],
        cycle=obj["cycle"],
        at=obj["at"],
        state_hash=obj["stateHash"],
        config=obj["config"],
        recovered_from=obj.get("recoveredFrom"),
    )


def _canonical(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _put_object(file: Path, text: str) -> None:
    """Write-once, content-addressed put. Identical content deduplicates."""
    try:
        with file.open("x", encoding="utf-8") as fh:
            fh.write(text)
    except FileExistsError:
        # same address ⇒ same content: already stored, nothing to do
        pass


def _get_object(file: Path, expected_hash: str, kind: str) -> str:
    """Read + verify a content-addressed object (tampering breaks its own name)."""
    text = file.read_text(encoding="utf-8")
    if _sha256(text) != expected_hash:
        raise RuntimeError(
            f"commit store: {kind} {expected_hash} fails its content address — "
            "the file was altered"
        )
    return text


# DECIDE@IMPL (declared, not measured): how large a subtree must be to be an
# object of its own. Smaller ones stay inline in their parent; a row of a grid
# does, a grid does not. A bound on the number of files, not on what is kept.
MIN_OBJECT_BYTES: Final = 1024

# The key of a reference to an object, and of an escaped value that has it.
_REF: Final = "#dil-ref"
_ESC: Final = "#dil-esc"


class DirCommitStore:
    """A commit repo backed by a directory."""

    __slots__ = ("_dir", "_state_dir", "_object_dir", "_head_file")

    def __init__(self, dir_: str | os.PathLike[str]) -> None:
        self._dir = Path(dir_)
        self._state_dir = self._dir / "state"
        self._object_dir = self._dir / "objects"
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._object_dir.mkdir(parents=True, exist_ok=True)
        self._head_file = self._dir / "HEAD"

    def _children(self, value: Any) -> Any:
        """A value whose large subtrees are stored and replaced by their references."""
        if isinstance(value, list):
            return [self._store(v) for v in value]
        if isinstance(value, dict):
            out = {k: self._store(v) for k, v in value.items()}
            # A value that looks like a reference is escaped, so it reads back as itself.
            return {_ESC: out} if _REF in out or _ESC in out else out
        return value

    def _store(self, value: Any) -> Any:
        """A value stored as an object of its own if it is large enough, else inline."""
        if not isinstance(value, (list, dict)):
            return value
        node = self._children(value)
        text = _canonical(node)
        if len(text) < MIN_OBJECT_BYTES:
            return node
        h = _sha256(text)
        _put_object(self._object_dir / f"{h}.json", text)
        return {_REF: h}

    def _load(self, value: Any) -> Any:
        """A value with every reference read back (and checked) and every escape undone."""
        if isinstance(value, list):
            return [self._load(v) for v in value]
        if not isinstance(value, dict):
            return value
        if len(value) == 1 and _REF in value and isinstance(value[_REF], str):
            h = value[_REF]
            return self._load(json.loads(_get_object(self._object_dir / f"{h}.json", h, "object")))
        if len(value) == 1 and _ESC in value:
            return {k: self._load(v) for k, v in value[_ESC].items()}
        return {k: self._load(v) for k, v in value.items()}

    def put_state(self, state: Any) -> str:
        """Store a snapshot payload; returns its content address (idempotent)."""
        # Plain JSON first: what a snapshot is, not how it is held in memory.
        plain = json.loads(_canonical(state))
        text = _canonical(self._children(plain))
        h = _sha256(text)
        _put_object(self._state_dir / f"{h}.json", text)
        return h

    def put_marker(self, marker: CommitMarker) -> str:
        """Store a marker; returns its content address and moves HEAD to it."""
        text = _canonical(_marker_dict(marker))
        h = _sha256(text)
        _put_object(self._dir / f"{h}.json", text)
        # the one movable pointer (a git ref)
        self._head_file.write_text(h, encoding="utf-8")
        return h

    def get_marker(self, hash_: str) -> CommitMarker:
        """Read a marker; raises if the content does not match its address."""
        text = _get_object(self._dir / f"{hash_}.json", hash_, "marker")
        return _marker_from_dict(json.loads(text))

    def get_state(self, state_hash: str) -> Any:
        """Read a snapshot payload; raises if the content does not match its address."""
        text = _get_object(self._state_dir / f"{state_hash}.json", state_hash, "state payload")
        return self._load(json.loads(text))

    def head(self) -> str | None:
        """The movable pointer to the current branch tip, or None before any commit."""
        if not self._head_file.exists():
            return None
        return self._head_file.read_text(encoding="utf-8").strip()

    def list(self) -> list[str]:
        """All marker hashes present (unordered; order lives in the parent links)."""
        return [e.name[:-5] for e in self._dir.iterdir() if _OBJECT_RE.match(e.name)]


def create_dir_commit_store(dir_: str | os.PathLike[str]) -> DirCommitStore:
    return DirCommitStore(dir_)
