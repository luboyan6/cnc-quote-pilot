"""The isolated SQLite fixture must release an interrupted read on Windows."""

import sqlite3

from tests.cnc.quote._quote_support import FixtureSQLiteConnection


def test_fixture_connection_finalizes_unconsumed_cursor(tmp_path):
    path = tmp_path / "interrupted.db"
    connection = sqlite3.connect(path, factory=FixtureSQLiteConnection)
    connection.execute("CREATE TABLE sample (value INTEGER)")
    connection.executemany("INSERT INTO sample VALUES (?)", [(1,), (2,)])
    connection.commit()
    cursor = connection.cursor()
    cursor.execute("SELECT value FROM sample")
    assert cursor.fetchone() == (1,)
    connection.close()

    # Keep cursor alive here: an unfinalized statement otherwise holds the
    # closed connection's file handle and makes Windows unlink fail.
    path.unlink()
