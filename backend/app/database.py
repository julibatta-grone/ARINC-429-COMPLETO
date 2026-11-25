"""Acceso SQLite y creación del esquema de la aplicación."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = Path(
    os.environ.get(
        "ARINC429_DATABASE",
        PROJECT_ROOT / "backend" / "data" / "arinc429.db",
    )
)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Abre y cierra una conexión configurada para trabajar con filas nombradas."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    """Crea las tablas necesarias si todavía no existen."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS instruments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                arinc_label TEXT NOT NULL,
                min_value REAL NOT NULL,
                max_value REAL NOT NULL,
                encoding_type TEXT NOT NULL,
                arinc_config TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (min_value <= max_value)
            );

            CREATE TABLE IF NOT EXISTS sends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument_id INTEGER NOT NULL,
                value REAL NOT NULL,
                sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                validation_status TEXT NOT NULL,
                generated_word TEXT,
                details TEXT,
                FOREIGN KEY (instrument_id)
                    REFERENCES instruments(id) ON DELETE RESTRICT
            );

            CREATE INDEX IF NOT EXISTS idx_sends_instrument_id
                ON sends(instrument_id);
            CREATE INDEX IF NOT EXISTS idx_sends_sent_at
                ON sends(sent_at);
            """
        )
