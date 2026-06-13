"""Рассылка уведомлений: техникам — о новых заявках, заявителю — о смене статуса.

VK может ограничивать рассылки. Каждую отправку оборачиваем в try/except, чтобы
один недоступный получатель не ронял остальную рассылку и сам процесс.
"""

from __future__ import annotations

import random

from loguru import logger

from app.db.repository import Ticket
from app.keyboards import admin as admin_kb
from app.runtime import get_bot, get_settings
from app.utils.formatting import render_ticket_full


async def _safe_send(peer_id: int, text: str, keyboard: str | None = None) -> bool:
    """Отправляет сообщение, проглатывая ошибки доставки конкретному адресату."""
    bot = get_bot()
    try:
        await bot.api.messages.send(
            peer_id=peer_id,
            message=text,
            random_id=random.randint(1, 2**31),
            keyboard=keyboard or None,
        )
        return True
    except Exception as exc:  # noqa: BLE001 — намеренно не роняем рассылку
        logger.warning("Не удалось отправить сообщение {}: {}", peer_id, exc)
        return False


async def notify_admins_new_ticket(ticket: Ticket) -> None:
    """Сообщает всем техникам о новой заявке (с inline-кнопками действий)."""
    settings = get_settings()
    text = "🔔 Новая заявка!\n\n" + render_ticket_full(ticket)
    keyboard = admin_kb.ticket_actions(ticket.id, ticket.status)
    delivered = 0
    for admin_id in settings.admin_ids:
        if await _safe_send(admin_id, text, keyboard or None):
            delivered += 1
    logger.info(
        "Заявка #{}: уведомлено техников {}/{}",
        ticket.id,
        delivered,
        len(settings.admin_ids),
    )


async def notify_author_status_change(ticket: Ticket) -> None:
    """Сообщает автору заявки о смене статуса (с текстом резолюции, если есть)."""
    text = "🔔 Статус вашей заявки изменился.\n\n" + render_ticket_full(ticket)
    await _safe_send(ticket.author_vk_id, text)
