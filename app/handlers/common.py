"""Общие хендлеры: отмена, /start, помощь.

Загружается ПЕРВЫМ — чтобы «❌ Отмена» перебивала любые состояния FSM.
"""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message

from app.keyboards import user as kb
from app.runtime import get_bot, get_settings
from app.utils.access import is_admin

bl = BotLabeler()

HELP_TEXT = (
    "ℹ️ Я помогаю подавать заявки на ремонт техники в школе.\n\n"
    "• «📝 Новая заявка» — создать заявку (категория → место → описание).\n"
    "• «📋 Мои заявки» — посмотреть свои заявки и их статусы.\n"
    "• «❌ Отмена» — прервать заполнение в любой момент.\n\n"
    "Заявку ведёт техник: вы получите уведомление при смене статуса."
)


GREETING = (
    "👋 Здравствуйте! Это бот техподдержки школы.\n"
    "Выберите действие на клавиатуре ниже."
)


# «Отмена» — без привязки к состоянию, поэтому срабатывает в любой момент FSM.
@bl.message(text=[kb.BTN_CANCEL, "Отмена", "отмена"])
async def cancel(message: Message) -> None:
    bot = get_bot()
    state = await bot.state_dispenser.get(message.peer_id)
    admin = is_admin(message.from_id, get_settings().admin_ids)
    if state is not None:
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Отменено. Возвращаю в меню.", keyboard=kb.main_menu(admin))
    else:
        await message.answer("Нечего отменять. Главное меню:", keyboard=kb.main_menu(admin))


# /start и приветствия — только когда пользователь НЕ в процессе подачи (state=[]).
@bl.message(state=[], text=["/start", "start", "Начать", "начать", "Меню", "меню"])
async def start(message: Message) -> None:
    admin = is_admin(message.from_id, get_settings().admin_ids)
    await message.answer(GREETING, keyboard=kb.main_menu(admin))


@bl.message(state=[], text=[kb.BTN_HELP, "Помощь", "помощь"])
async def help_handler(message: Message) -> None:
    admin = is_admin(message.from_id, get_settings().admin_ids)
    await message.answer(HELP_TEXT, keyboard=kb.main_menu(admin))
