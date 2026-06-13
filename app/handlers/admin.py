"""Хендлеры техника/админа: списки заявок, смена статусов, ввод резолюции.

Действия над конкретной заявкой приходят через inline-кнопки (MessageEvent).
Закрытие/отклонение требует комментария — для этого технику ставится состояние
AdminResolution.WAITING_TEXT с ticket_id и action в payload.
"""

from __future__ import annotations

from loguru import logger
from vkbottle import GroupEventType
from vkbottle.bot import BotLabeler, Message, MessageEvent

from app.db import repository
from app.enums import Status
from app.keyboards import admin as akb
from app.keyboards import user as kb
from app.runtime import get_bot, get_settings
from app.services import notifications
from app.states import AdminResolution
from app.utils.access import is_admin
from app.utils.formatting import render_ticket_full

bl = BotLabeler()

LIST_LIMIT = 20


def _is_admin(vk_id: int) -> bool:
    return is_admin(vk_id, get_settings().admin_ids)


async def _send_ticket_cards(message: Message, tickets, empty_text: str) -> None:
    """Шлёт по сообщению на заявку с её inline-кнопками действий."""
    admin = True  # сюда попадают только техники
    if not tickets:
        await message.answer(empty_text, keyboard=kb.main_menu(admin))
        return
    await message.answer(
        f"Найдено заявок: {len(tickets)}", keyboard=kb.main_menu(admin)
    )
    for ticket in tickets:
        keyboard = akb.ticket_actions(ticket.id, ticket.status)
        await message.answer(
            render_ticket_full(ticket),
            keyboard=keyboard or None,
        )


@bl.message(state=[], text=[kb.BTN_ADMIN_NEW, "Новые заявки"])
async def list_new(message: Message) -> None:
    if not _is_admin(message.from_id):
        return
    tickets = await repository.list_by_status(Status.NEW.value, limit=LIST_LIMIT)
    await _send_ticket_cards(message, tickets, "Новых заявок нет 🎉")


@bl.message(state=[], text=[kb.BTN_ADMIN_IN_PROGRESS, "В работе"])
async def list_in_progress(message: Message) -> None:
    if not _is_admin(message.from_id):
        return
    tickets = await repository.list_by_assignee(message.from_id, limit=LIST_LIMIT)
    await _send_ticket_cards(message, tickets, "У вас нет заявок в работе.")


# --- Inline-кнопки действий над заявкой ---------------------------------------


@bl.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
async def on_ticket_action(event: MessageEvent) -> None:
    user_id = event.object.user_id
    peer_id = event.object.peer_id
    bot = get_bot()
    logger.info(
        "message_event получен: user={} peer={} payload={}",
        user_id,
        peer_id,
        event.get_payload_json(),
    )

    if not _is_admin(user_id):
        await event.show_snackbar("Действие доступно только техникам.")
        return

    payload = event.get_payload_json() or {}
    action = payload.get("action")
    ticket_id = payload.get("ticket_id")
    if action is None or ticket_id is None:
        await event.show_snackbar("Не понял действие.")
        return

    ticket = await repository.get_ticket(int(ticket_id))
    if ticket is None:
        await event.show_snackbar("Заявка не найдена.")
        return

    if action == akb.ACTION_TAKE:
        if ticket.status != Status.NEW.value:
            await event.show_snackbar("Заявка уже взята или закрыта.")
            return
        updated = await repository.update_status(
            ticket.id,
            new_status=Status.IN_PROGRESS.value,
            changed_by=user_id,
            assigned_to=user_id,
        )
        await event.show_snackbar(f"Заявка #{ticket.id} взята в работу.")
        if updated:
            await _refresh_card(peer_id, event, updated)
            await notifications.notify_author_status_change(updated)
        return

    if action in (akb.ACTION_DONE, akb.ACTION_REJECT):
        if ticket.status in (Status.DONE.value, Status.REJECTED.value):
            await event.show_snackbar("Заявка уже закрыта.")
            return
        # Просим комментарий: ставим технику состояние ожидания текста.
        await bot.state_dispenser.set(
            peer_id,
            AdminResolution.WAITING_TEXT,
            ticket_id=ticket.id,
            action=action,
        )
        verb = "выполнения" if action == akb.ACTION_DONE else "отклонения"
        await event.show_snackbar(f"Напишите комментарий для {verb}.")
        await bot.api.messages.send(
            peer_id=peer_id,
            random_id=0,
            message=(
                f"Заявка #{ticket.id}: напишите короткий комментарий "
                f"({'что сделано' if action == akb.ACTION_DONE else 'причина отклонения'}). "
                "Или «❌ Отмена»."
            ),
            keyboard=kb.cancel_only(),
        )
        return

    await event.show_snackbar("Неизвестное действие.")


async def _refresh_card(peer_id: int, event: MessageEvent, ticket) -> None:
    """Перерисовывает карточку заявки (обновляет статус и кнопки)."""
    keyboard = akb.ticket_actions(ticket.id, ticket.status)
    try:
        await event.edit_message(
            message=render_ticket_full(ticket),
            keyboard=keyboard or None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось обновить карточку #{}: {}", ticket.id, exc)


# --- Ввод комментария-резолюции -----------------------------------------------


@bl.message(state=AdminResolution.WAITING_TEXT)
async def resolution_text(message: Message) -> None:
    bot = get_bot()
    text = (message.text or "").strip()
    payload = message.state_peer.payload if message.state_peer else {}
    ticket_id = payload.get("ticket_id")
    action = payload.get("action")
    admin = _is_admin(message.from_id)

    if not text:
        await message.answer(
            "Комментарий не должен быть пустым. Напишите текст или «❌ Отмена».",
            keyboard=kb.cancel_only(),
        )
        return

    new_status = (
        Status.DONE.value if action == akb.ACTION_DONE else Status.REJECTED.value
    )
    updated = await repository.update_status(
        int(ticket_id),
        new_status=new_status,
        changed_by=message.from_id,
        resolution=text,
    )
    await bot.state_dispenser.delete(message.peer_id)
    if updated is None:
        await message.answer("Заявка не найдена.", keyboard=kb.main_menu(admin))
        return
    await message.answer(
        "Готово. Заявка обновлена:\n\n" + render_ticket_full(updated),
        keyboard=kb.main_menu(admin),
    )
    await notifications.notify_author_status_change(updated)
