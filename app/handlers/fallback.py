"""Запасной хендлер: ловит всё, что не подошло другим (вне FSM).

Загружается ПОСЛЕДНИМ. Привязан к state=[] — поэтому не перехватывает
сообщения внутри сценариев FSM.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.keyboards import user as kb
from app.runtime import get_settings
from app.utils.access import is_admin

bl = BotLabeler()


@bl.message(state=[])
async def fallback(message: Message) -> None:
    admin = is_admin(message.from_id, get_settings().admin_ids)
    await message.answer(
        "Не совсем понял. Воспользуйтесь кнопками меню ниже 👇",
        keyboard=kb.main_menu(admin),
    )
