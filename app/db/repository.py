"""CRUD-операции над заявками и журналом статусов.

Все обращения к БД — async (aiosqlite), чтобы не блокировать event loop.
Возвращаем dataclass Ticket, а не сырые Row, чтобы хендлеры не зависели от
структуры таблицы.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import aiosqlite

from app.db.database import get_db
from app.enums import Status


def _now() -> str:
    """Текущее время в ISO 8601 (UTC)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(slots=True)
class Ticket:
    """Заявка как объект приложения."""

    id: int
    author_vk_id: int
    author_name: str
    location: str
    category: str
    description: str
    status: str
    assigned_to: int | None
    resolution: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "Ticket":
        return cls(
            id=row["id"],
            author_vk_id=row["author_vk_id"],
            author_name=row["author_name"],
            location=row["location"],
            category=row["category"],
            description=row["description"],
            status=row["status"],
            assigned_to=row["assigned_to"],
            resolution=row["resolution"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


async def create_ticket(
    *,
    author_vk_id: int,
    author_name: str,
    location: str,
    category: str,
    description: str,
) -> Ticket:
    """Создаёт заявку в статусе new и пишет первую запись в журнал."""
    db = get_db()
    now = _now()
    cursor = await db.execute(
        """
        INSERT INTO tickets
            (author_vk_id, author_name, location, category, description,
             status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            author_vk_id,
            author_name,
            location,
            category,
            description,
            Status.NEW.value,
            now,
            now,
        ),
    )
    ticket_id = cursor.lastrowid
    assert ticket_id is not None
    await db.execute(
        """
        INSERT INTO status_log (ticket_id, old_status, new_status, changed_by, changed_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ticket_id, None, Status.NEW.value, author_vk_id, now),
    )
    await db.commit()
    ticket = await get_ticket(ticket_id)
    assert ticket is not None
    return ticket


async def get_ticket(ticket_id: int) -> Ticket | None:
    """Возвращает заявку по id или None."""
    db = get_db()
    async with db.execute(
        "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
    ) as cursor:
        row = await cursor.fetchone()
    return Ticket.from_row(row) if row else None


async def list_by_status(status: str, limit: int = 20) -> list[Ticket]:
    """Заявки с указанным статусом, новые сверху."""
    db = get_db()
    async with db.execute(
        "SELECT * FROM tickets WHERE status = ? ORDER BY id DESC LIMIT ?",
        (status, limit),
    ) as cursor:
        rows = await cursor.fetchall()
    return [Ticket.from_row(r) for r in rows]


async def list_by_author(author_vk_id: int, limit: int = 10) -> list[Ticket]:
    """Последние заявки конкретного автора."""
    db = get_db()
    async with db.execute(
        "SELECT * FROM tickets WHERE author_vk_id = ? ORDER BY id DESC LIMIT ?",
        (author_vk_id, limit),
    ) as cursor:
        rows = await cursor.fetchall()
    return [Ticket.from_row(r) for r in rows]


async def list_by_assignee(assigned_to: int, limit: int = 20) -> list[Ticket]:
    """Заявки в работе у конкретного техника."""
    db = get_db()
    async with db.execute(
        """
        SELECT * FROM tickets
        WHERE assigned_to = ? AND status = ?
        ORDER BY id DESC LIMIT ?
        """,
        (assigned_to, Status.IN_PROGRESS.value, limit),
    ) as cursor:
        rows = await cursor.fetchall()
    return [Ticket.from_row(r) for r in rows]


async def update_status(
    ticket_id: int,
    *,
    new_status: str,
    changed_by: int,
    assigned_to: int | None = None,
    resolution: str | None = None,
) -> Ticket | None:
    """Меняет статус заявки, пишет запись в журнал и возвращает обновлённую заявку.

    `assigned_to` и `resolution` обновляются только если переданы (not None).
    Возвращает None, если заявки нет.
    """
    db = get_db()
    ticket = await get_ticket(ticket_id)
    if ticket is None:
        return None

    now = _now()
    fields = ["status = ?", "updated_at = ?"]
    params: list[object] = [new_status, now]
    if assigned_to is not None:
        fields.append("assigned_to = ?")
        params.append(assigned_to)
    if resolution is not None:
        fields.append("resolution = ?")
        params.append(resolution)
    params.append(ticket_id)

    await db.execute(
        f"UPDATE tickets SET {', '.join(fields)} WHERE id = ?", params
    )
    await db.execute(
        """
        INSERT INTO status_log (ticket_id, old_status, new_status, changed_by, changed_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ticket_id, ticket.status, new_status, changed_by, now),
    )
    await db.commit()
    return await get_ticket(ticket_id)
