"""SQLite-backed [data] store (DECIDE@IMPL tag F — store representation).

`[data]` is the mutable present — the agent's memory, its content revised as
the loop runs (protocol §9). The durable representation DIL imposes on the host's substrate is
a SQLite table under `store/memory/`, using `sqlite3` from the standard library:
synchronous, matching the DataStore interface, and with no third-party dependency
— which matters here, because a Kaggle session has no network to install one. One
row per key: the `TaggedDatum` serialized as JSON. An upsert keeps each key's
rowid stable, so `entries()` reads back in insertion order.

This is one concrete `DataStore` behind the interface; the dict-backed store in
data_store.py stays a test fixture. RAM is never the store of record — the
store-of-record lives on the requisitioned substrate.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`), where the engine is the same
SQLite reached through `node:sqlite`.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from .tags import FixedTags, TaggedDatum


def _encode(datum: TaggedDatum) -> str:
    return json.dumps(
        {
            "payload": datum.payload,
            "fixed": {
                "timestamp": datum.fixed.timestamp,
                "cycleMark": datum.fixed.cycle_mark,
                "provenance": datum.fixed.provenance,
                "floorTag": datum.fixed.floor_tag,
            },
            "open": datum.open,
        },
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _decode(text: str) -> TaggedDatum:
    obj: dict[str, Any] = json.loads(text)
    f = obj["fixed"]
    return TaggedDatum(
        payload=obj["payload"],
        fixed=FixedTags(
            timestamp=f["timestamp"],
            cycle_mark=f["cycleMark"],
            provenance=f["provenance"],
            floor_tag=f["floorTag"],
        ),
        open=obj["open"],
    )


class SqliteDataStore:
    """A SQLite `[data]` store. Close it with `close()`.

    A port-side optimization, not dil-core's (LOG.md, 2026-09-28): what the table
    holds is also held decoded, in the table's order, read from the table once
    and kept as each write goes to it. Every commit read the whole table back and
    decoded it — the more a run had stored, the more each commit cost. What a
    read returns is what the table holds, decoded from the text written to it."""

    __slots__ = ("_db", "_held", "_each")

    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self._db = sqlite3.connect(db_path)
        self._db.execute("CREATE TABLE IF NOT EXISTS data (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        self._db.commit()
        self._held: dict[str, TaggedDatum] | None = None
        # SYNC_CADENCE (store/decisions.py; dil-core c6b8f30):
        # True commits each write, as dil-core does; False keeps a cycle's writes
        # in one transaction, committed on `sync()` (once a cycle, by the daemon).
        # Reads in this process see every write either way.
        self._each = True

    def _all(self) -> dict[str, TaggedDatum]:
        if self._held is None:
            rows = self._db.execute("SELECT k, v FROM data ORDER BY rowid").fetchall()
            self._held = {k: _decode(v) for k, v in rows}
        return self._held

    def put(self, id: str, datum: TaggedDatum) -> None:
        # Upsert preserves the row's rowid on update, so insertion order is stable
        # (a dict keeps a key's place when its value is replaced, as the table does).
        text = _encode(datum)
        self._db.execute(
            "INSERT INTO data(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v",
            (id, text),
        )
        if self._each:
            self._db.commit()
        if self._held is not None:
            self._held[id] = _decode(text)

    def get(self, id: str) -> TaggedDatum | None:
        return self._all().get(id)

    def has(self, id: str) -> bool:
        return id in self._all()

    def delete(self, id: str) -> bool:
        cur = self._db.execute("DELETE FROM data WHERE k = ?", (id,))
        if self._each:
            self._db.commit()
        if self._held is not None:
            self._held.pop(id, None)
        return cur.rowcount > 0

    def clear(self) -> None:
        self._db.execute("DELETE FROM data")
        if self._each:
            self._db.commit()
        self._held = {}

    def size(self) -> int:
        return len(self._all())

    def entries(self) -> list[tuple[str, TaggedDatum]]:
        return list(self._all().items())

    def sync_each_cycle(self) -> None:
        """Commit once a cycle, not each write (SYNC_CADENCE, declared)."""
        self._each = False

    def sync(self) -> None:
        """Commit the writes not yet committed."""
        self._db.commit()

    def close(self) -> None:
        """Close the underlying database handle."""
        self._db.commit()
        self._db.close()


def create_sqlite_data_store(db_path: str | os.PathLike[str]) -> SqliteDataStore:
    """Open (or create) a SQLite `[data]` store at `db_path`.

    Pass a file path under `store/memory/` for a durable store, or `":memory:"`
    for an ephemeral test store (still SQLite, no file on disk).
    """
    return SqliteDataStore(db_path)
