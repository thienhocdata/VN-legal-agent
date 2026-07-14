import sqlite3

import pytest

from app.database import Database


def test_every_database_connection_enforces_foreign_keys(tmp_path):
    database = Database(tmp_path / "integrity.db")

    with pytest.raises(sqlite3.IntegrityError), database.connect() as con:
        con.execute(
            """INSERT INTO legal_provisions
            (id,document_id,location,text,keywords) VALUES(?,?,?,?,?)""",
            ("orphan", "missing-document", "Điều 1", "Nội dung", "[]"),
        )
