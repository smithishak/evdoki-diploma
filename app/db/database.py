"""Инициализация SQLite через aiosqlite и создание схемы.

Одно соединение на процесс (бот однопоточный, один Long Poll). Соединение
хранится в модуле и переиспользуется хендлерами через get_db().
"""

from __future__ import annotations

import aiosqlite
from loguru import logger

_db: aiosqlite.Connection | None = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    author_vk_id INTEGER NOT NULL,
    author_name  TEXT    NOT NULL,
    location     TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    description  TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'new',
    assigned_to  INTEGER,
    resolution   TEXT,
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS status_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id  INTEGER NOT NULL REFERENCES tickets(id),
    old_status TEXT,
    new_status TEXT    NOT NULL,
    changed_by INTEGER NOT NULL,
    changed_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_author ON tickets(author_vk_id);
CREATE INDEX IF NOT EXISTS idx_tickets_assigned ON tickets(assigned_to);
CREATE INDEX IF NOT EXISTS idx_status_log_ticket ON status_log(ticket_id);
"""


async def init_db(db_path: str) -> aiosqlite.Connection:
    """Открывает соединение, включает FK и создаёт таблицы при первом запуске."""
    global _db
    if _db is not None:
        return _db

    logger.info("Открываю БД: {}", db_path)
    conn = await aiosqlite.connect(db_path)
    # Возвращать строки как dict-подобные объекты (доступ по имени колонки).
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.executescript(SCHEMA)
    await conn.commit()
    _db = conn
    logger.info("Схема БД готова")
    return _db


def get_db() -> aiosqlite.Connection:
    """Возвращает активное соединение. Падает, если init_db ещё не вызван."""
    if _db is None:
        raise RuntimeError("БД не инициализирована: сначала вызовите init_db().")
    return _db


async def close_db() -> None:
    """Закрывает соединение (при остановке бота)."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("Соединение с БД закрыто")
