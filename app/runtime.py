"""Доступ к единственному экземпляру Bot и настройкам из любых blueprint'ов.

Message в vkbottle не несёт ссылку на state_dispenser, поэтому держим бота
и настройки в модуле-синглтоне. main.py вызывает setup(), хендлеры — get_bot()
и get_settings().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vkbottle import Bot

    from app.config import Settings

_bot: "Bot | None" = None
_settings: "Settings | None" = None


def setup(bot: "Bot", settings: "Settings") -> None:
    global _bot, _settings
    _bot = bot
    _settings = settings


def get_bot() -> "Bot":
    if _bot is None:
        raise RuntimeError("Bot не инициализирован: вызовите runtime.setup().")
    return _bot


def get_settings() -> "Settings":
    if _settings is None:
        raise RuntimeError("Settings не инициализированы: вызовите runtime.setup().")
    return _settings
