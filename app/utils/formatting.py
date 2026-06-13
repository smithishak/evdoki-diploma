"""Рендер заявок в текст сообщений VK."""

from __future__ import annotations

from datetime import datetime

from app.db.repository import Ticket
from app.enums import category_label, status_label


def _fmt_dt(iso: str) -> str:
    """ISO 8601 → человекочитаемая дата 'ДД.ММ.ГГГГ ЧЧ:ММ'."""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return iso


def render_ticket_full(ticket: Ticket) -> str:
    """Полная карточка заявки — для техника и экрана подтверждения."""
    lines = [
        f"📋 Заявка #{ticket.id}",
        f"Статус: {status_label(ticket.status)}",
        f"Категория: {category_label(ticket.category)}",
        f"Место: {ticket.location}",
        f"Описание: {ticket.description}",
        f"Автор: {ticket.author_name}",
        f"Создана: {_fmt_dt(ticket.created_at)}",
    ]
    if ticket.resolution:
        lines.append(f"Комментарий: {ticket.resolution}")
    return "\n".join(lines)


def render_ticket_short(ticket: Ticket) -> str:
    """Однострочная сводка — для списков."""
    return (
        f"#{ticket.id} · {category_label(ticket.category)} · "
        f"{status_label(ticket.status)}\n"
        f"   {ticket.location} — {_shorten(ticket.description)}"
    )


def render_draft(category: str, location: str, description: str) -> str:
    """Черновик заявки на экране подтверждения (заявка ещё не в БД)."""
    return "\n".join(
        [
            "📋 Проверьте заявку:",
            f"Категория: {category_label(category)}",
            f"Место: {location}",
            f"Описание: {description}",
        ]
    )


def _shorten(text: str, limit: int = 60) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"
