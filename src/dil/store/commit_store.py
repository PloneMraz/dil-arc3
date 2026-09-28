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


# One encoder for every canonical text: `json.dumps` with these arguments builds a
# new one per call — 2.8 million of them in 60 cycles of sb26. The text is the
# same (a port-side optimization, LOG.md, 2026-09-28).
_ENCODER = json.JSONEncoder(separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _canonical(value: Any) -> str:
    return _ENCODER.encode(value)


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
# What a subtree is made of beyond single values (read by type, in C, per row).
_CONTAINERS: Final = frozenset({list, tuple, dict})
_ESC: Final = "#dil-esc"


class DirCommitStore:
    """A commit repo backed by a directory."""

    __slots__ = ("_dir", "_state_dir", "_object_dir", "_head_file", "_texts", "_touched")

    def __init__(self, dir_: str | os.PathLike[str]) -> None:
        self._dir = Path(dir_)
        self._state_dir = self._dir / "state"
        self._object_dir = self._dir / "objects"
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._object_dir.mkdir(parents=True, exist_ok=True)
        self._head_file = self._dir / "HEAD"
        # The text of each container stored at the last commit, by the object it
        # was made from — held, so no other object takes its id — and what the
        # commit being put has asked for. A container a snapshot shares with the
        # last (a datum not changed since) is not made into text again; its
        # objects are on disk already (a port-side optimization, LOG.md,
        # 2026-09-28; the names and the text are those it would be given anew).
        self._texts: dict[int, tuple[Any, str]] = {}
        self._touched: dict[int, tuple[Any, str]] = {}

    def _text(self, value: Any) -> str:
        if type(value) in _CONTAINERS:
            kept = self._texts.get(id(value))
            if kept is not None and kept[0] is value:
                self._touched[id(value)] = kept
                return kept[1]
            text = self._made_text(value)
            self._touched[id(value)] = (value, text)
            return text
        return self._made_text(value)

    def _made_text(self, value: Any) -> str:
        """The canonical text of `value` as it stands in its parent: inline, or,
        when it is at least MIN_OBJECT_BYTES long, the reference to the object it
        is stored as. Built bottom-up, each node's text from its children's, so
        no part is serialized twice — the same text `_canonical` would give the
        node with its large subtrees replaced (the names do not change)."""
        node = self._node_text(value)
        if not isinstance(value, (list, tuple, dict)) or len(node) < MIN_OBJECT_BYTES:
            return node
        h = _sha256(node)
        _put_object(self._object_dir / f"{h}.json", node)
        return '{"' + _REF + '":"' + h + '"}'

    def _node_text(self, value: Any) -> str:
        """The canonical text of a node, its large subtrees replaced by references."""
        if isinstance(value, (list, tuple)):
            if _CONTAINERS.isdisjoint(set(map(type, value))):
                return _canonical(value)  # a row of values: one call, nothing to store in it
            return "[" + ",".join(self._text(v) for v in value) + "]"
        if isinstance(value, dict):
            if not all(isinstance(k, str) for k in value):
                return self._node_text(json.loads(_canonical(value)))  # keys as JSON writes them
            body = "{" + ",".join(_canonical(k) + ":" + self._text(v) for k, v in value.items()) + "}"
            # A value that looks like a reference is escaped, so it reads back as itself.
            return '{"' + _ESC + '":' + body + "}" if _REF in value or _ESC in value else body
        return _canonical(value)

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
        self._touched = {}
        text = self._node_text(state)
        h = _sha256(text)
        _put_object(self._state_dir / f"{h}.json", text)
        self._texts, self._touched = self._touched, {}
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
