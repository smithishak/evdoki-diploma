"""Точка входа: сборка бота, регистрация blueprints, запуск Long Poll."""

from __future__ import annotations

import asyncio

# Заставляем Python доверять системному хранилищу сертификатов (Windows/Linux).
# Нужно там, где HTTPS-трафик перехватывает антивирус или корпоративный прокси:
# их корневой CA есть в хранилище ОС, но нет в бандле certifi, который Python
# использует по умолчанию. Внедряем ДО любых сетевых вызовов.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    # truststore не установлен — на серверах с корректными CA он не обязателен.
    pass

from loguru import logger  # noqa: E402
from vkbottle import Bot  # noqa: E402

from app import runtime
from app.config import Settings, load_settings
from app.db.database import close_db, init_db
from app.handlers import admin, common, create_ticket, fallback, user

# Порядок загрузки важен:
#   1) common   — «Отмена» должна перебивать любые состояния FSM.
#   2) create_ticket / user / admin — основная логика.
#   3) fallback — ловит всё остальное, поэтому ПОСЛЕДНИЙ.
HANDLER_MODULES = [common, create_ticket, user, admin, fallback]


def build_bot(settings: Settings) -> Bot:
    bot = Bot(token=settings.vk_token)
    runtime.setup(bot, settings)
    for module in HANDLER_MODULES:
        bot.labeler.load(module.bl)
    logger.info(
        "Бот собран. Техников в белом списке: {}. Заявки от всех: {}.",
        len(settings.admin_ids),
        settings.allow_all_users,
    )
    return bot


async def ensure_long_poll(bot: Bot) -> None:
    """Включает Long Poll и нужные типы событий через API при старте.

    Самое важное здесь — message_event: без него VK не присылает нажатия
    inline-кнопок («Взять в работу», «Выполнено», «Отклонить»), и они «не
    работают». Делаем это программно, чтобы не зависеть от галочек в интерфейсе
    сообщества. Требует, чтобы токен сообщества имел права на управление.
    """
    try:
        groups = await bot.api.groups.get_by_id()
        # В разных версиях API ответ — либо список, либо объект с .groups.
        items = getattr(groups, "groups", groups)
        group_id = items[0].id
        await bot.api.groups.set_long_poll_settings(
            group_id=group_id,
            enabled=True,
            api_version="5.131",
            message_new=True,
            message_event=True,
            message_reply=True,
            message_allow=True,
            message_deny=True,
        )
        logger.info("Long Poll и события (вкл. message_event) настроены для группы {}", group_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Не удалось автоматически настроить Long Poll: {}. "
            "Включите вручную в Управление → Работа с API → Long Poll API "
            "событие «Событие в callback-кнопке».",
            exc,
        )


async def _run() -> None:
    settings = load_settings()
    await init_db(settings.db_path)
    bot = build_bot(settings)
    await ensure_long_poll(bot)
    try:
        await bot.run_polling()
    finally:
        await close_db()


def main() -> None:
    try:
        asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановка бота")


if __name__ == "__main__":
    main()
