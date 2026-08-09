"""Shared pytest fixtures (in-memory database + temp files)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from database.database import Database


@pytest.fixture()
def db():
    database = Database(":memory:")
    yield database
    database.close()


@pytest.fixture()
def conn(db):
    return db.conn


@pytest.fixture()
def tmp_db_file(tmp_path):
    path = tmp_path / "sales.db"
    database = Database(str(path))
    yield database, str(path)
    database.close()
