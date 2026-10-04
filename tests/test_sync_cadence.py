"""SYNC_CADENCE (a declared deviation, dil-arc3, 2026-10-04): the store synced to
disk once a cycle, not each write. The records and the data are the same; only
when they reach the disk changes. dil-core's sync of each write stays the default.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

from dil.store import create_durable_event_log, record_layer_exit
from dil.store.sqlite_data_store import create_sqlite_data_store
from dil.store.tags import FixedTags, TaggedDatum


def _count_fsyncs(monkeypatch) -> list[int]:
    calls: list[int] = []
    real = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: (calls.append(fd), real(fd))[1])
    return calls


def test_the_log_syncs_each_record_by_default(monkeypatch, tmp_path):
    calls = _count_fsyncs(monkeypatch)
    log = create_durable_event_log(tmp_path, date_stamp=lambda: "20261004")
    for i in range(3):
        log.append(record_layer_exit("cycle-1", 1, i + 1, 10))
    assert len(calls) == 3, "dil-core's guarantee: on disk when the append returns"


def test_synced_once_a_cycle_the_log_keeps_every_record_and_syncs_on_sync(monkeypatch, tmp_path):
    calls = _count_fsyncs(monkeypatch)
    log = create_durable_event_log(tmp_path, date_stamp=lambda: "20261004")
    log.sync_each_cycle()
    for i in range(3):
        log.append(record_layer_exit("cycle-1", 1, i + 1, 10))
    assert calls == [], "not synced each record"
    assert log.size() == 3 and len(log.all()) == 3, "each record written to its file as it came"
    log.sync()
    assert len(calls) == 1, "synced once, at the cycle's close"


def _datum(cycle: int) -> TaggedDatum:
    return TaggedDatum(payload={"n": cycle},
                       fixed=FixedTags(timestamp=cycle, cycle_mark=cycle, provenance="running", floor_tag=1),
                       open={"domain": "test", "kind": "probe", "source": "test"})


def test_synced_once_a_cycle_the_data_reads_at_once_and_reaches_the_file_on_sync():
    path = os.path.join(tempfile.mkdtemp(), "data.sqlite")
    store = create_sqlite_data_store(path)
    store.sync_each_cycle()
    store.put("d-1", _datum(1))
    assert store.get("d-1") is not None, "this process reads every write"
    other = sqlite3.connect(path)
    assert other.execute("SELECT COUNT(*) FROM data").fetchone()[0] == 0, "not yet committed"
    store.sync()
    assert other.execute("SELECT COUNT(*) FROM data").fetchone()[0] == 1, "committed once, at the cycle's close"
    store.close()


def test_the_data_commits_each_write_by_default():
    path = os.path.join(tempfile.mkdtemp(), "data.sqlite")
    store = create_sqlite_data_store(path)
    store.put("d-1", _datum(1))
    assert sqlite3.connect(path).execute("SELECT COUNT(*) FROM data").fetchone()[0] == 1
    store.close()
