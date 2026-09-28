"""The port's fast paths give what the code before them gave, call by call.

    python scripts/check_fast_paths.py GAME CYCLES [run_game.py options...]

Plays a game through `run_game.py` with each fast path wrapped: at every call,
what it returns is compared with what the code it replaced returns — the
snapshot encoder as it was, the log's `copy.deepcopy`, `json.dumps`; the store's
reads against its table decoded afresh; the data's encodings kept across commits
against the data encoded anew; each snapshot's address against a commit store
that keeps no text — and the first difference stops the run with what it was. A
check of the optimization of 2026-09-28 (LOG.md), for the record; slow, since
each call is made twice.
"""
from __future__ import annotations

import copy
import runpy
import sys
from dataclasses import fields, is_dataclass
from pathlib import Path

from _paths import SRC  # noqa: E402 — see scripts/_paths.py

sys.path.insert(0, str(SRC))

import json  # noqa: E402

import dil.runtime.commit as commit  # noqa: E402
import dil.runtime.daemon as daemon  # noqa: E402
import dil.store.commit_store as commit_store  # noqa: E402
import dil.store.event_log as event_log  # noqa: E402

_TAG = "__dil__"


def encode_before(value):
    """`encode_snapshot_value` as it was before the fast path."""
    if is_dataclass(value) and not isinstance(value, type):
        return {_TAG: type(value).__name__,
                "fields": {f.name: encode_before(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, dict):
        return {k: encode_before(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode_before(v) for v in value]
    return value


calls = {"encode": 0, "freeze": 0, "canonical": 0}
fast_encode, fast_freeze = commit.encode_snapshot_value, event_log.deep_freeze
fast_canonical = commit_store._canonical


def canonical_checked(value):
    got = fast_canonical(value)
    want = json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    calls["canonical"] += 1
    if got != want:
        sys.exit(f"canonical text differs at call {calls['canonical']}")
    return got


def encode_checked(value):
    got, want = fast_encode(value), encode_before(value)
    calls["encode"] += 1
    if got != want or repr(got) != repr(want):
        sys.exit(f"encode differs at call {calls['encode']}")
    return got


def freeze_checked(value):
    got, want = fast_freeze(value), copy.deepcopy(value)
    calls["freeze"] += 1
    if got != want or repr(got) != repr(want) or type(got) is not type(want):
        sys.exit(f"freeze differs at call {calls['freeze']}: {type(value).__name__}")
    return got


daemon.encode_snapshot_value = encode_checked
event_log.deep_freeze = freeze_checked
commit_store._canonical = canonical_checked

# The store read from memory, against the table decoded afresh at every read.
import dil.store.sqlite_data_store as sqlite_store  # noqa: E402

calls.update({"read": 0, "data": 0, "state": 0})
held_entries, held_get = sqlite_store.SqliteDataStore.entries, sqlite_store.SqliteDataStore.get


def table(store):
    rows = store._db.execute("SELECT k, v FROM data ORDER BY rowid").fetchall()
    return [(k, sqlite_store._decode(v)) for k, v in rows]


def entries_checked(self):
    got = held_entries(self)
    calls["read"] += 1
    if got != table(self):
        sys.exit(f"the store read from memory differs from its table at read {calls['read']}")
    return got


def get_checked(self, id):
    got = held_get(self, id)
    calls["read"] += 1
    if got != dict(table(self)).get(id):
        sys.exit(f"the store's datum {id} differs from its table at read {calls['read']}")
    return got


sqlite_store.SqliteDataStore.entries = entries_checked
sqlite_store.SqliteDataStore.get = get_checked

# Each datum's encoding kept across commits, against encoding the data anew.
kept_data = daemon._encoded_data


def data_checked(data, held):
    got = kept_data(data, held)
    calls["data"] += 1
    if got != encode_before(data):
        sys.exit(f"the data kept encoded differs at commit {calls['data']}")
    return got


daemon._encoded_data = data_checked

# The commit store's kept texts, against a store with none (the same address).
kept_put = commit_store.DirCommitStore.put_state


def put_checked(self, state):
    h = kept_put(self, state)
    fresh = commit_store.DirCommitStore(self._dir)
    calls["state"] += 1
    if kept_put(fresh, state) != h:
        sys.exit(f"the snapshot's address differs at commit {calls['state']}")
    return h


commit_store.DirCommitStore.put_state = put_checked

sys.argv = [str(Path(__file__).with_name("run_game.py")), *sys.argv[1:]]
runpy.run_path(sys.argv[0], run_name="__main__")
print(f"checked: encode {calls['encode']}, freeze {calls['freeze']}, canonical text {calls['canonical']}, "
      f"store reads {calls['read']}, data kept {calls['data']}, snapshot addresses {calls['state']}; "
      "no difference", flush=True)
