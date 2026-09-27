"""The commit repo's snapshot payload as a tree of content-addressed objects
(protocol §9; choice 2-(b); ported from dil-core `1096476`).

A state reads back exactly as it was put; two snapshots that share a subtree
share its object, so a snapshot costs what changed; an object altered on disk is
caught on read; a value that looks like a reference reads back as itself; and a
snapshot written whole before the tree (choice 2-(a)) still reads.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from dil.store.commit_store import MIN_OBJECT_BYTES, create_dir_commit_store


def grid(fill: int) -> list[list[int]]:
    return [[fill] * 64 for _ in range(64)]


def objects(path) -> set[str]:
    return {p.name for p in (path / "objects").iterdir()}


def test_a_state_reads_back_exactly_as_it_was_put(tmp_path):
    store = create_dir_commit_store(tmp_path)
    state = {
        "layers": {"t5": {"windows": {"a": [grid(1), grid(2)]}}},
        "glob": {"params": {"appraisalGain": 1}, "cycle": 7},
        "data": [["signal-0-0", {"payload": {"grids": [grid(3)]}, "open": {"kind": "frame"}}]],
        "small": [1, "two", None, True],
    }
    h = store.put_state(state)
    assert store.get_state(h) == state
    assert objects(tmp_path), "the large subtrees are objects of their own"


def test_two_snapshots_that_share_a_subtree_share_its_object(tmp_path):
    store = create_dir_commit_store(tmp_path)
    first = {"data": [["a", {"g": grid(1)}], ["b", {"g": grid(2)}]]}
    second = {"data": [["a", {"g": grid(1)}], ["b", {"g": grid(2)}], ["c", {"g": grid(3)}]]}
    store.put_state(first)
    before = objects(tmp_path)
    h2 = store.put_state(second)
    added = objects(tmp_path) - before
    assert len(added) <= 3, f"only what changed is stored anew (added {len(added)})"
    assert store.get_state(h2) == second


def test_an_object_altered_on_disk_is_caught_when_the_state_is_read(tmp_path):
    store = create_dir_commit_store(tmp_path)
    h = store.put_state({"data": [["a", {"g": grid(5)}]]})
    file = next((tmp_path / "objects").iterdir())
    file.write_text(file.read_text(encoding="utf-8").replace("5", "6", 1), encoding="utf-8")
    with pytest.raises(RuntimeError, match="fails its content address"):
        store.get_state(h)


def test_a_value_that_looks_like_a_reference_reads_back_as_itself(tmp_path):
    store = create_dir_commit_store(tmp_path)
    state = {
        "looks": {"#dil-ref": "not a hash"},
        "escaped": {"#dil-esc": {"#dil-ref": "x"}},
        "big": {"#dil-ref": "y", "pad": "z" * MIN_OBJECT_BYTES},
    }
    assert store.get_state(store.put_state(state)) == state


def test_a_snapshot_written_whole_before_the_tree_still_reads(tmp_path):
    store = create_dir_commit_store(tmp_path)
    legacy = {"data": [["a", {"g": grid(9)}]], "glob": {"cycle": 3}}
    text = json.dumps(legacy, separators=(",", ":"))
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    (tmp_path / "state" / f"{h}.json").write_text(text, encoding="utf-8")
    assert store.get_state(h) == legacy
