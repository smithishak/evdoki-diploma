"""Клавиатуры заявителя: главное меню и шаги подачи заявки."""

from __future__ import annotations

from vkbottle import Keyboard, KeyboardButtonColor, Text

from app.enums import CATEGORY_LABELS, Category

# Подписи кнопок главного меню — на них же завязаны хендлеры (по тексту).
BTN_NEW_TICKET = "📝 Новая заявка"
BTN_MY_TICKETS = "📋 Мои заявки"
BTN_HELP = "ℹ️ Помощь"
BTN_ADMIN_NEW = "🔧 Новые заявки"
BTN_ADMIN_IN_PROGRESS = "📂 В работе"

# Кнопки внутри FSM.
BTN_CANCEL = "❌ Отмена"
BTN_CONFIRM_SEND = "✅ Отправить"
BTN_CONFIRM_RESTART = "✏️ Заполнить заново"
BTN_LOCATION_MANUAL = "✍️ Ввести вручную"


def main_menu(is_admin: bool = False) -> str:
    """Главное (постоянное) меню. Технику добавляем админ-кнопки."""
    kb = Keyboard(one_time=False)
    kb.add(Text(BTN_NEW_TICKET), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text(BTN_MY_TICKETS))
    kb.add(Text(BTN_HELP))
    if is_admin:
        kb.row()
        kb.add(Text(BTN_ADMIN_NEW), color=KeyboardButtonColor.SECONDARY)
        kb.add(Text(BTN_ADMIN_IN_PROGRESS), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def categories() -> str:
    """Выбор категории. По две кнопки в ряд + отмена."""
    kb = Keyboard(one_time=True)
    items = list(CATEGORY_LABELS.items())
    for index, (category, label) in enumerate(items):
        kb.add(Text(label, payload={"category": category.value}))
        # Переносим ряд после каждой второй кнопки (кроме последней).
        if index % 2 == 1 and index != len(items) - 1:
            kb.row()
    kb.row()
    kb.add(Text(BTN_CANCEL), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def location_hints(hints: list[str] | None = None) -> str:
    """Подсказки частых кабинетов + ручной ввод + отмена."""
    kb = Keyboard(one_time=True)
    hints = hints or []
    for index, hint in enumerate(hints):
        kb.add(Text(hint))
        if index % 2 == 1 and index != len(hints) - 1:
            kb.row()
    if hints:
        kb.row()
    kb.add(Text(BTN_LOCATION_MANUAL))
    kb.row()
    kb.add(Text(BTN_CANCEL), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def cancel_only() -> str:
    """Только кнопка отмены — на шаге свободного ввода описания."""
    kb = Keyboard(one_time=True)
    kb.add(Text(BTN_CANCEL), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def confirm() -> str:
    """Экран подтверждения заявки."""
    kb = Keyboard(one_time=True)
    kb.add(Text(BTN_CONFIRM_SEND), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text(BTN_CONFIRM_RESTART))
    kb.add(Text(BTN_CANCEL), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def empty() -> str:
    """Пустая клавиатура (убрать кнопки)."""
    return Keyboard().get_json()


# Множества для удобной проверки в хендлерах.
CATEGORY_BY_LABEL: dict[str, Category] = {
    label: cat for cat, label in CATEGORY_LABELS.items()
}
