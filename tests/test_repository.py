"""Тесты слоя БД: CRUD заявок и журнал переходов статусов."""

from __future__ import annotations

import pytest

from app.db import database, repository
from app.enums import Category, Status


@pytest.fixture
async def db(tmp_path):
    """Свежая БД во временном файле на каждый тест."""
    db_path = str(tmp_path / "test.db")
    await database.init_db(db_path)
    yield
    await database.close_db()


async def _make_ticket() -> repository.Ticket:
    return await repository.create_ticket(
        author_vk_id=999,
        author_name="Иван Петров",
        location="каб. 204",
        category=Category.COMPUTER.value,
        description="Не включается",
    )


async def test_create_and_get(db):
    ticket = await _make_ticket()
    assert ticket.id == 1
    assert ticket.status == Status.NEW.value
    assert ticket.assigned_to is None

    fetched = await repository.get_ticket(1)
    assert fetched is not None
    assert fetched.author_name == "Иван Петров"
    assert fetched.location == "каб. 204"


async def test_get_missing_returns_none(db):
    assert await repository.get_ticket(404) is None


async def test_list_by_status_and_author(db):
    await _make_ticket()
    assert len(await repository.list_by_status(Status.NEW.value)) == 1
    assert len(await repository.list_by_author(999)) == 1
    assert len(await repository.list_by_author(123)) == 0


async def test_full_lifecycle_and_status_log(db):
    ticket = await _make_ticket()

    in_progress = await repository.update_status(
        ticket.id,
        new_status=Status.IN_PROGRESS.value,
        changed_by=111,
        assigned_to=111,
    )
    assert in_progress is not None
    assert in_progress.status == Status.IN_PROGRESS.value
    assert in_progress.assigned_to == 111
    assert len(await repository.list_by_assignee(111)) == 1

    done = await repository.update_status(
        ticket.id,
        new_status=Status.DONE.value,
        changed_by=111,
        resolution="Заменили блок питания",
    )
    assert done is not None
    assert done.status == Status.DONE.value
    assert done.resolution == "Заменили блок питания"
    # assigned_to не сбрасывается при последующем обновлении
    assert done.assigned_to == 111

    db_conn = database.get_db()
    async with db_conn.execute(
        "SELECT old_status, new_status, changed_by FROM status_log "
        "WHERE ticket_id = ? ORDER BY id",
        (ticket.id,),
    ) as cursor:
        rows = await cursor.fetchall()
    trail = [(r["old_status"], r["new_status"]) for r in rows]
    assert trail == [
        (None, "new"),
        ("new", "in_progress"),
        ("in_progress", "done"),
    ]


async def test_update_missing_ticket_returns_none(db):
    result = await repository.update_status(
        404, new_status=Status.DONE.value, changed_by=1
    )
    assert result is None
