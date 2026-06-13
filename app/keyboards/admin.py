"""Inline-клавиатуры техника для действий над конкретной заявкой.

Inline-кнопки несут payload с ticket_id и action — так бот понимает, над какой
заявкой и что делать, не спрашивая лишнего.
"""

from __future__ import annotations

from vkbottle import Callback, Keyboard, KeyboardButtonColor

from app.enums import Status

# Значения action в payload inline-кнопок.
ACTION_TAKE = "take"  # взять в работу (new → in_progress)
ACTION_DONE = "done"  # выполнено (→ done, спрашиваем резолюцию)
ACTION_REJECT = "reject"  # отклонить (→ rejected, спрашиваем резолюцию)


def ticket_actions(ticket_id: int, status: str) -> str:
    """Инлайн-кнопки действий под карточкой заявки, зависят от статуса.

    Для закрытых заявок (done/rejected) кнопок нет.
    """
    kb = Keyboard(inline=True)
    has_buttons = False

    if status == Status.NEW.value:
        kb.add(
            Callback(
                "▶️ Взять в работу",
                payload={"action": ACTION_TAKE, "ticket_id": ticket_id},
            ),
            color=KeyboardButtonColor.PRIMARY,
        )
        kb.row()
        has_buttons = True

    if status in (Status.NEW.value, Status.IN_PROGRESS.value):
        kb.add(
            Callback(
                "✅ Выполнено",
                payload={"action": ACTION_DONE, "ticket_id": ticket_id},
            ),
            color=KeyboardButtonColor.POSITIVE,
        )
        kb.add(
            Callback(
                "🚫 Отклонить",
                payload={"action": ACTION_REJECT, "ticket_id": ticket_id},
            ),
            color=KeyboardButtonColor.NEGATIVE,
        )
        has_buttons = True

    if not has_buttons:
        # vkbottle не отправляет полностью пустую inline-клавиатуру корректно —
        # в таком случае вернём пустую строку, хендлер её не приложит.
        return ""
    return kb.get_json()
