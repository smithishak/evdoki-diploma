"""FSM-состояния диалогов vkbottle (state dispenser)."""

from __future__ import annotations

from vkbottle import BaseStateGroup


class CreateTicket(BaseStateGroup):
    """Шаги подачи заявки."""

    CATEGORY = "category"
    LOCATION = "location"
    DESCRIPTION = "description"
    CONFIRM = "confirm"


class AdminResolution(BaseStateGroup):
    """Ввод комментария техником при закрытии/отклонении заявки."""

    WAITING_TEXT = "waiting_text"
