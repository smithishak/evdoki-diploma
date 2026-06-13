"""FSM-сценарий подачи заявки: категория → место → описание → подтверждение."""

from __future__ import annotations

from loguru import logger
from vkbottle.bot import BotLabeler, Message

from app.db import repository
from app.enums import Category
from app.keyboards import user as kb
from app.runtime import get_bot, get_settings
from app.services import notifications
from app.states import CreateTicket
from app.utils.access import is_admin
from app.utils.formatting import render_draft, render_ticket_full

bl = BotLabeler()

# Частые кабинеты-подсказки на шаге локации (можно вынести в конфиг позже).
LOCATION_HINTS = ["Учительская", "Библиотека", "Спортзал", "Столовая"]


async def _fetch_name(message: Message) -> str:
    """Имя автора через users.get; при ошибке — заглушка."""
    try:
        users = await message.ctx_api.users.get(user_ids=[message.from_id])
        if users:
            return f"{users[0].first_name} {users[0].last_name}".strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("users.get для {} не удался: {}", message.from_id, exc)
    return f"id{message.from_id}"


# Вход в сценарий. Без привязки к состоянию: если пользователь уже заполняет
# заявку и снова жмёт «Новая заявка» — мягко напоминаем.
@bl.message(text=[kb.BTN_NEW_TICKET, "Новая заявка"])
async def start_create(message: Message) -> None:
    bot = get_bot()
    state = await bot.state_dispenser.get(message.peer_id)
    if state is not None and str(state.state).startswith(CreateTicket.__name__):
        await message.answer(
            "У вас уже есть незавершённая заявка. Продолжите заполнение "
            "или нажмите «❌ Отмена», чтобы начать заново.",
            keyboard=kb.cancel_only(),
        )
        return
    await bot.state_dispenser.set(message.peer_id, CreateTicket.CATEGORY)
    await message.answer(
        "Шаг 1 из 3. Выберите категорию проблемы:",
        keyboard=kb.categories(),
    )


@bl.message(state=CreateTicket.CATEGORY)
async def step_category(message: Message) -> None:
    bot = get_bot()
    category: str | None = None

    payload = message.get_payload_json()
    if isinstance(payload, dict) and "category" in payload:
        category = str(payload["category"])
    elif message.text in kb.CATEGORY_BY_LABEL:
        category = kb.CATEGORY_BY_LABEL[message.text].value

    if category is None or category not in {c.value for c in Category}:
        await message.answer(
            "Пожалуйста, выберите категорию кнопкой ниже.",
            keyboard=kb.categories(),
        )
        return

    await bot.state_dispenser.set(
        message.peer_id, CreateTicket.LOCATION, category=category
    )
    await message.answer(
        "Шаг 2 из 3. Укажите кабинет/место (например, «каб. 204» или «учительская»).",
        keyboard=kb.location_hints(LOCATION_HINTS),
    )


@bl.message(state=CreateTicket.LOCATION)
async def step_location(message: Message) -> None:
    bot = get_bot()
    text = (message.text or "").strip()

    if text == kb.BTN_LOCATION_MANUAL:
        await message.answer(
            "Напишите место в ответном сообщении.", keyboard=kb.cancel_only()
        )
        return
    if not text:
        await message.answer(
            "Место не должно быть пустым. Укажите кабинет или место.",
            keyboard=kb.location_hints(LOCATION_HINTS),
        )
        return

    category = message.state_peer.payload.get("category", "") if message.state_peer else ""
    await bot.state_dispenser.set(
        message.peer_id,
        CreateTicket.DESCRIPTION,
        category=category,
        location=text,
    )
    await message.answer(
        "Шаг 3 из 3. Опишите, что случилось.", keyboard=kb.cancel_only()
    )


@bl.message(state=CreateTicket.DESCRIPTION)
async def step_description(message: Message) -> None:
    bot = get_bot()
    text = (message.text or "").strip()
    if not text:
        await message.answer(
            "Описание не должно быть пустым. Опишите проблему.",
            keyboard=kb.cancel_only(),
        )
        return

    payload = message.state_peer.payload if message.state_peer else {}
    category = payload.get("category", "")
    location = payload.get("location", "")
    await bot.state_dispenser.set(
        message.peer_id,
        CreateTicket.CONFIRM,
        category=category,
        location=location,
        description=text,
    )
    await message.answer(
        render_draft(category, location, text), keyboard=kb.confirm()
    )


@bl.message(state=CreateTicket.CONFIRM)
async def step_confirm(message: Message) -> None:
    bot = get_bot()
    text = (message.text or "").strip()
    payload = message.state_peer.payload if message.state_peer else {}
    admin = is_admin(message.from_id, get_settings().admin_ids)

    if text == kb.BTN_CONFIRM_RESTART:
        await bot.state_dispenser.set(message.peer_id, CreateTicket.CATEGORY)
        await message.answer(
            "Начнём заново. Выберите категорию:", keyboard=kb.categories()
        )
        return

    if text != kb.BTN_CONFIRM_SEND:
        await message.answer(
            "Нажмите «✅ Отправить», «✏️ Заполнить заново» или «❌ Отмена».",
            keyboard=kb.confirm(),
        )
        return

    name = await _fetch_name(message)
    ticket = await repository.create_ticket(
        author_vk_id=message.from_id,
        author_name=name,
        location=payload.get("location", ""),
        category=payload.get("category", ""),
        description=payload.get("description", ""),
    )
    await bot.state_dispenser.delete(message.peer_id)
    await message.answer(
        f"✅ Заявка #{ticket.id} принята!\n\n" + render_ticket_full(ticket),
        keyboard=kb.main_menu(admin),
    )
    # Уведомляем техников о новой заявке.
    await notifications.notify_admins_new_ticket(ticket)
