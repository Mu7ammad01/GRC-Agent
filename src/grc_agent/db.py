"""Accès à la base GRC (PostgreSQL)."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from .config import settings

_database_url = settings.database_url


def configure(database_url: str) -> None:
    """Change la base cible (utilisé par les tests)."""
    global _database_url
    _database_url = database_url


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(_database_url, row_factory=dict_row) as conn:
        yield conn


def _plain(value: Any) -> Any:
    """Convertit les types SQL en types JSON simples pour le LLM."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def fetch_all(sql: str, params: tuple | dict = ()) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [{k: _plain(v) for k, v in row.items()} for row in rows]


def execute(sql: str, params: tuple | dict = ()) -> int:
    """Exécute une écriture et retourne le nombre de lignes touchées."""
    with connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount


def next_id(table: str, prefix: str) -> str:
    """Prochain identifiant lisible, par ex. R-031."""
    rows = fetch_all(
        f"SELECT id FROM {table} WHERE id LIKE %s ORDER BY id DESC LIMIT 1",  # noqa: S608 (table interne)
        (f"{prefix}-%",),
    )
    last = int(rows[0]["id"].split("-")[1]) if rows else 0
    return f"{prefix}-{last + 1:03d}"
