"""Статусы и категории заявок — константы в одном месте.

Никаких магических литералов по коду: и логика, и подписи для кнопок берутся
отсюда.
"""

from __future__ import annotations

from enum import StrEnum


class Status(StrEnum):
    """Статус заявки."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    REJECTED = "rejected"


class Category(StrEnum):
    """Категория проблемы."""

    COMPUTER = "computer"
    PROJECTOR = "projector"
    INTERNET = "internet"
    PRINTER = "printer"
    OTHER = "other"


# Человекочитаемые подписи с эмодзи — для кнопок и рендера.
STATUS_LABELS: dict[Status, str] = {
    Status.NEW: "🆕 Новая",
    Status.IN_PROGRESS: "🔧 В работе",
    Status.DONE: "✅ Выполнена",
    Status.REJECTED: "🚫 Отклонена",
}

CATEGORY_LABELS: dict[Category, str] = {
    Category.COMPUTER: "💻 Компьютер",
    Category.PROJECTOR: "📽 Проектор",
    Category.INTERNET: "🌐 Интернет",
    Category.PRINTER: "🖨 Принтер",
    Category.OTHER: "❓ Другое",
}


def status_label(status: str) -> str:
    """Подпись статуса; неизвестный статус возвращаем как есть."""
    try:
        return STATUS_LABELS[Status(status)]
    except ValueError:
        return status


def category_label(category: str) -> str:
    """Подпись категории; неизвестную возвращаем как есть."""
    try:
        return CATEGORY_LABELS[Category(category)]
    except ValueError:
        return category
