"""SQLite-backed [data] store (DECIDE@IMPL tag F — store representation).

`[data]` is the mutable present — DIL's working memory, overwritten each cycle
(protocol §9). The durable representation DIL imposes on the host's substrate is
a SQLite table under `store/memory/`, using `sqlite3` from the standard library:
synchronous, matching the DataStore interface, and with no third-party dependency
— which matters here, because a Kaggle session has no network to install one. One
row per key: the `TaggedDatum` serialized as JSON. An upsert keeps each key's
rowid stable, so `entries()` reads back in insertion order.

This is one concrete `DataStore` behind the interface; the dict-backed store in
data_store.py stays a test fixture. RAM is never the store of record — the
store-of-record lives on the requisitioned substrate.

Ported from dil-core against DIL protocol v0.3.3, where the engine is the same
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
    """A SQLite `[data]` store. Close it with `close()`."""

    __slots__ = ("_db",)

    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self._db = sqlite3.connect(db_path)
        self._db.execute("CREATE TABLE IF NOT EXISTS data (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        self._db.commit()

    def put(self, id: str, datum: TaggedDatum) -> None:
        # Upsert preserves the row's rowid on update, so insertion order is stable.
        self._db.execute(
            "INSERT INTO data(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v",
            (id, _encode(datum)),
        )
        self._db.commit()

    def get(self, id: str) -> TaggedDatum | None:
        row = self._db.execute("SELECT v FROM data WHERE k = ?", (id,)).fetchone()
        return _decode(row[0]) if row is not None else None

    def has(self, id: str) -> bool:
        return self._db.execute("SELECT 1 FROM data WHERE k = ?", (id,)).fetchone() is not None

    def delete(self, id: str) -> bool:
        cur = self._db.execute("DELETE FROM data WHERE k = ?", (id,))
        self._db.commit()
        return cur.rowcount > 0

    def clear(self) -> None:
        self._db.execute("DELETE FROM data")
        self._db.commit()

    def size(self) -> int:
        return int(self._db.execute("SELECT count(*) FROM data").fetchone()[0])

    def entries(self) -> list[tuple[str, TaggedDatum]]:
        rows = self._db.execute("SELECT k, v FROM data ORDER BY rowid").fetchall()
        return [(k, _decode(v)) for k, v in rows]

    def close(self) -> None:
        """Close the underlying database handle."""
        self._db.close()


def create_sqlite_data_store(db_path: str | os.PathLike[str]) -> SqliteDataStore:
    """Open (or create) a SQLite `[data]` store at `db_path`.

    Pass a file path under `store/memory/` for a durable store, or `":memory:"`
    for an ephemeral test store (still SQLite, no file on disk).
    """
    return SqliteDataStore(db_path)
