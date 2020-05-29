import sqlite3
from src.picturecommands_utils import (
    as_text,
    as_ids,
)

id_text_pairs = [
    ["1", "1"],
    ["hi", "hi"],
    [203285581004931072, "203285581004931072"],
    [3, 3],
    [
        {"Hello": 203285581004931072},
        {"Hello": "203285581004931072"}
    ],
    [None, None]
]


def test_as_text():
    for id_val, text_val in id_text_pairs:
        assert as_text(id_val) == text_val


def test_as_ids():
    for id_val, text_val in id_text_pairs:
        assert as_ids(text_val) == id_val


def fresh_db():
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    c.execute(
        """
        CREATE DATABASE media
        CREATE TABLE media.commands (
            cmd TEXT PRIMARY KEY,
            uid CHARACTER(18));
        CREATE TABLE media.images (
            cmd TEXT REFERENCES media.commands(cmd) ON DELETE CASCADE,
            image_key TEXT,
            uid CHARACTER(18),
            sid CHARACTER(18),
            md5 TEXT,
            PRIMARY KEY (cmd, image_key));
        CREATE TABLE media.server_command_associations (
            sid CHARACTER(18),
            cmd TEXT REFERENCES media.commands(cmd) ON DELETE CASCADE,
            PRIMARY KEY (sid, cmd));
        CREATE TABLE media.aliases (
            alias TEXT PRIMARY KEY,
            real TEXT);
        """
    )
    return c


def test_set_properties():
    c = fresh_db()
    assert 1 == 1
