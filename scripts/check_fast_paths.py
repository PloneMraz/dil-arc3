"""The port's fast paths give what the code before them gave, call by call.

    python scripts/check_fast_paths.py GAME CYCLES [run_game.py options...]

Plays a game through `run_game.py` with the snapshot encoder and the event log's
freezing wrapped: at every call, the value the fast path returns is compared
with what the code it replaced returns (the encoder as it was before; the log's
`copy.deepcopy`), and the first difference stops the run with what it was. A
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

sys.argv = [str(Path(__file__).with_name("run_game.py")), *sys.argv[1:]]
runpy.run_path(sys.argv[0], run_name="__main__")
print(f"checked: encode {calls['encode']}, freeze {calls['freeze']}, canonical text {calls['canonical']} calls; "
      "no difference", flush=True)
