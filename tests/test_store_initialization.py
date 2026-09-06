"""Bounded regression controls for concurrent schema replacement (no inference)."""
import concurrent.futures
import sqlite3
import threading
import time
from unittest.mock import patch

import pytest

from cortex.store import Store


def test_concurrent_trigger_replacement_is_atomic(tmp_path):
    path = tmp_path / "cortex.db"
    Store(path).close()
    connect = sqlite3.connect
    barrier = threading.Barrier(4)

    def traced_connect(*args, **kwargs):
        db = connect(*args, **kwargs)
        # Enlarge the exact formerly unprotected DROP/CREATE interval.
        db.set_trace_callback(lambda sql: time.sleep(0.02) if
                              "DROP TRIGGER IF EXISTS activation_conformance" in sql else None)
        return db

    def open_store():
        barrier.wait(timeout=10)
        store = Store(path)
        try:
            assert store.integrity_check()
            return store.db.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name IN "
                "('activation_conformance_receipts_no_update', "
                "'activation_conformance_chain_tip_identity_immutable')"
            ).fetchone()[0]
        finally:
            store.close()

    with patch("cortex.store.sqlite3.connect", side_effect=traced_connect):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            assert list(pool.map(lambda _: open_store(), range(4))) == [2] * 4


def test_failed_schema_rolls_back_guards_and_closes_connection(tmp_path):
    path = tmp_path / "cortex.db"
    Store(path).close()
    connect = sqlite3.connect
    connections = []

    def tracked_connect(*args, **kwargs):
        db = connect(*args, **kwargs)
        connections.append(db)
        return db

    broken = """BEGIN IMMEDIATE;
    DROP TRIGGER activation_conformance_receipts_no_update;
    THIS IS NOT SQL;
    """
    with patch("cortex.store.SCHEMA", broken), patch(
        "cortex.store.sqlite3.connect", side_effect=tracked_connect
    ):
        with pytest.raises(sqlite3.OperationalError):
            Store(path)
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connections[0].execute("SELECT 1")
    db = connect(path)
    try:
        assert db.execute("SELECT 1 FROM sqlite_master WHERE name="
                          "'activation_conformance_receipts_no_update'").fetchone()
    finally:
        db.close()
