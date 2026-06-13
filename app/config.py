"""Конфигурация приложения через pydantic-settings.

Читает .env. Токен и список админов держим вне кода.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки бота, валидируемые при старте."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Токен сообщества VK. Без него бот не стартует.
    vk_token: str

    # VK ID техников/админов. В .env — строка "123,456", парсим в список int.
    # NoDecode отключает попытку pydantic-settings декодировать значение как JSON,
    # чтобы разбором занялся наш field_validator ниже.
    admin_ids: Annotated[list[int], NoDecode] = []

    # Принимать заявки от всех или только из белого списка.
    allow_all_users: bool = True

    # Путь к файлу БД SQLite.
    db_path: str = "helpdesk.db"

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> list[int]:
        """Разбирает "123,456" из .env в [123, 456].

        pydantic v2 по умолчанию ждёт для list[int] JSON-массив, поэтому
        строку из .env разбираем вручную.
        """
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [int(part.strip()) for part in value.split(",") if part.strip()]
        if isinstance(value, (list, tuple)):
            return [int(v) for v in value]
        raise ValueError(f"Не удалось разобрать ADMIN_IDS: {value!r}")

    @field_validator("vk_token")
    @classmethod
    def _token_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError(
                "VK_TOKEN не задан. Укажите токен сообщества в .env "
                "(Управление сообществом → Работа с API → Ключи доступа)."
            )
        return value.strip()


def load_settings() -> Settings:
    """Загружает и валидирует настройки. Падает с понятной ошибкой при проблеме."""
    return Settings()  # type: ignore[call-arg]
