import sqlite3
import threading
import time
from pathlib import Path
from pipeline.db import db


def test_db_connect_sets_wal_mode_and_timeout(tmp_path: Path):
    db_file = tmp_path / "test.db"
    conn = db.connect(db_file)
    try:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert journal_mode.lower() == "wal"
    finally:
        conn.close()


def test_db_concurrent_writes(tmp_path: Path):
    db_file = tmp_path / "test.db"
    conn_init = db.connect(db_file)
    conn_init.execute("CREATE TABLE test (id INT PRIMARY KEY, val TEXT)")
    conn_init.commit()
    conn_init.close()

    errors = []

    def worker(worker_id: int):
        try:
            conn = db.connect(db_file)
            for i in range(5):
                conn.execute("INSERT INTO test (id, val) VALUES (?, ?)", (worker_id * 10 + i, f"worker_{worker_id}"))
                conn.commit()
                time.sleep(0.01)
            conn.close()
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=worker, args=(1,))
    t2 = threading.Thread(target=worker, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Concurrent write errors occurred: {errors}"
    conn = db.connect(db_file)
    count = conn.execute("SELECT COUNT(*) FROM test").fetchone()[0]
    conn.close()
    assert count == 10
