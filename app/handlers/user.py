"""Хендлеры заявителя: просмотр своих заявок."""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.db import repository
from app.keyboards import user as kb
from app.runtime import get_settings
from app.utils.access import is_admin
from app.utils.formatting import render_ticket_short

bl = BotLabeler()

MY_TICKETS_LIMIT = 10


@bl.message(state=[], text=[kb.BTN_MY_TICKETS, "Мои заявки"])
async def my_tickets(message: Message) -> None:
    admin = is_admin(message.from_id, get_settings().admin_ids)
    tickets = await repository.list_by_author(message.from_id, limit=MY_TICKETS_LIMIT)
    if not tickets:
        await message.answer(
            "У вас пока нет заявок. Нажмите «📝 Новая заявка», чтобы создать.",
            keyboard=kb.main_menu(admin),
        )
        return
    body = "\n\n".join(render_ticket_short(t) for t in tickets)
    await message.answer(
        f"📋 Ваши последние заявки ({len(tickets)}):\n\n{body}",
        keyboard=kb.main_menu(admin),
    )
