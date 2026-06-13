# VK Helpdesk Bot для школы

Бот сообщества ВКонтакте для приёма и обработки заявок по техническим неполадкам
(компьютеры, проекторы, интернет, принтеры). Учителя подают заявки через кнопочный
диалог, техник ведёт их по статусам, обе стороны получают уведомления.

- **Заявитель** — создаёт заявки (категория → место → описание), смотрит свои заявки.
- **Техник/админ** — видит новые заявки, берёт в работу, закрывает/отклоняет с
  комментарием. Определяется по списку VK ID в `.env`.

Технологии: Python 3.12+, [vkbottle](https://github.com/vkbottle/vkbottle) (Bot Long Poll),
SQLite через `aiosqlite`, `pydantic-settings`, `loguru`.

---

## 🚀 Runbook для агента-деплойера (Ubuntu + systemd)

> Это самодостаточная инструкция, чтобы развернуть бота на чистом сервере «под ключ».
> Разделы 1–8 ниже — справочник; здесь — готовый сценарий по шагам.

### Что нужно получить от человека (без этого деплой невозможен)

| Параметр | Что это | Где взять |
|---|---|---|
| `VK_TOKEN` | Токен сообщества ВК | Управление сообществом → Работа с API → Ключи доступа. **Создавать со всеми правами**, включая «Управление» — иначе бот не сможет сам включить события inline-кнопок. |
| `ADMIN_IDS` | Числовые VK ID техников через запятую | Профиль техника → числовой id (например, через regvk.com/id) |
| Доступ к серверу | SSH с правами `sudo` | У человека/хостера |

Также человек должен заранее выполнить **раздел 1** (включить сообщения сообщества).
Настройку Long Poll бот делает сам при старте — вручную не нужно.

### Предположения

- Чистый VPS на **Ubuntu 22.04/24.04**, есть `sudo`, есть исходящий интернет.
- Код доставляется в `/opt/vk-helpdesk-bot` (через `git clone` или `scp`/`rsync`).

### Шаги

```bash
# 1. Системные пакеты
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git ca-certificates
sudo update-ca-certificates

# 2. Доставить код (вариант с git; либо залить rsync/scp в этот же путь)
sudo mkdir -p /opt/vk-helpdesk-bot
sudo chown "$USER" /opt/vk-helpdesk-bot
git clone <REPO_URL> /opt/vk-helpdesk-bot
cd /opt/vk-helpdesk-bot

# 3. Виртуальное окружение и зависимости
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# 4. Конфиг (подставить реальные значения вместо <…>)
cat > .env <<'EOF'
VK_TOKEN=<ВСТАВИТЬ_ТОКЕН>
ADMIN_IDS=<ID1,ID2>
ALLOW_ALL_USERS=true
DB_PATH=/opt/vk-helpdesk-bot/helpdesk.db
EOF
chmod 600 .env

# 5. Прогнать тесты (быстрая проверка, что код жив)
.venv/bin/pip install pytest pytest-asyncio
.venv/bin/python -m pytest -q

# 6. Установить службу systemd
sudo tee /etc/systemd/system/vk-helpdesk-bot.service >/dev/null <<'EOF'
[Unit]
Description=VK Helpdesk Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/vk-helpdesk-bot
ExecStart=/opt/vk-helpdesk-bot/.venv/bin/python -m app.main
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now vk-helpdesk-bot
```

### Проверка успешного деплоя

```bash
sudo systemctl status vk-helpdesk-bot --no-pager
journalctl -u vk-helpdesk-bot -n 50 --no-pager
```

В логах должны быть строки (признак успеха):

- `Схема БД готова`
- `Бот собран. Техников в белом списке: N.`
- `Long Poll и события (вкл. message_event) настроены для группы …`
- `Starting BotPolling …`

Затем — функциональная проверка вживую:

1. Написать боту в личку сообщества любое сообщение → должно прийти меню.
2. Подать тестовую заявку (категория → место → описание → отправить).
3. Техник (его id в `ADMIN_IDS`) получает уведомление с inline-кнопками; нажать
   «Взять в работу» → статус меняется, заявителю приходит уведомление.

### Обслуживание

```bash
# логи в реальном времени
journalctl -u vk-helpdesk-bot -f

# обновить код и перезапустить
cd /opt/vk-helpdesk-bot && git pull
.venv/bin/pip install -r requirements.txt
sudo systemctl restart vk-helpdesk-bot

# бэкап БД (можно в cron, см. раздел 6)
cp /opt/vk-helpdesk-bot/helpdesk.db /opt/backups/helpdesk-$(date +%F).db
```

### Траблшутинг (грабли, уже встреченные на практике)

| Симптом в логах / поведение | Причина | Решение |
|---|---|---|
| `SSL: CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain` | TLS-трафик перехватывает антивирус/прокси (типично на рабочих ПК, не на чистом VPS) | Уже подключён пакет `truststore` (берёт CA из хранилища ОС). На сервере достаточно `sudo apt install ca-certificates && sudo update-ca-certificates`. При корпоративном прокси — добавить его корневой CA в систему. |
| Inline-кнопки техника не реагируют; нет строки `message_event получен` | Не включён тип события `message_event` | Бот включает его сам при старте. Если не вышло (`Не удалось автоматически настроить Long Poll …`) — у токена нет прав «Управление»: пересоздать токен со всеми правами. |
| `Не удалось автоматически настроить Long Poll …` | У токена нет прав на управление сообществом | Пересоздать `VK_TOKEN` со всеми правами, обновить `.env`, `systemctl restart`. |
| Бот стартует, но дублирует/теряет апдейты | Запущено две копии на одном токене | Должен быть **один** процесс на токен. Остановить лишние (`systemctl stop`, убить ручные запуски). |
| `VK_TOKEN не задан …` при старте | Пустой/незаполненный `.env` | Заполнить `VK_TOKEN` в `/opt/vk-helpdesk-bot/.env`. |
| Бот не отвечает на сообщения | В сообществе выключены сообщения/боты | Управление → Сообщения → включить сообщения и «Возможности ботов». |

> Альтернатива systemd — Docker (см. раздел 5). На чистом сервере systemd проще.

---

## 1. Настройка сообщества ВКонтакте

1. Создайте сообщество (или возьмите существующее школьное).
2. **Управление → Работа с API → Ключи доступа** → создайте ключ с правами на
   **сообщения сообщества**. Это и есть `VK_TOKEN`.
3. **Управление → Сообщения** → включите сообщения сообщества и «Возможности ботов».
4. Соберите числовые **VK ID** будущих техников (можно через
   [regvk.com/id](https://regvk.com/id/) или открыв профиль) — это `ADMIN_IDS`.

> **Про Long Poll и кнопки.** Бот при старте сам включает Long Poll и нужные типы
> событий через API (`groups.setLongPollSettings`), в том числе `message_event` —
> без него не работают inline-кнопки техника («Взять в работу», «Выполнено»,
> «Отклонить»). Поэтому вручную в настройках ничего включать не нужно — **но** для
> этого токен сообщества должен иметь права на **управление сообществом**. Если при
> старте в логах появится `Не удалось автоматически настроить Long Poll …` —
> пересоздайте токен со всеми правами или включите события вручную в
> **Управление → Работа с API → Long Poll API → Типы событий**.

---

## 2. Конфигурация

Скопируйте шаблон и заполните:

```bash
cp .env.example .env
```

```dotenv
VK_TOKEN=          # токен сообщества (см. шаг 1)
ADMIN_IDS=123456,789012   # VK ID техников через запятую
ALLOW_ALL_USERS=true      # принимать заявки от всех
DB_PATH=helpdesk.db       # путь к файлу БД
```

Файл `.env` в git не попадает (см. `.gitignore`). Если `VK_TOKEN` пуст — бот упадёт
на старте с понятной ошибкой.

---

## 3. Запуск локально (для теста)

### Вариант с uv (быстрее)

```bash
uv venv
uv pip install -e .
uv run python -m app.main
```

### Вариант с pip + venv

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python -m app.main
```

При первом запуске создаётся файл БД (`helpdesk.db`) с нужными таблицами.
Напишите боту в личку сообщения — он ответит главным меню.

### Тесты

```bash
pip install -e ".[dev]"   # или: pip install pytest pytest-asyncio
pytest
```

---

## 4. Развёртывание на VPS через systemd

Подойдёт минимальный тариф (Timeweb, Selectel и т.п.), Ubuntu. Как альтернатива
почти бесплатно — Raspberry Pi или старый компьютер прямо в школе.

```bash
# на сервере
git clone <repo> /opt/vk-helpdesk-bot
cd /opt/vk-helpdesk-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env   # заполнить токен и ADMIN_IDS
```

Создайте `/etc/systemd/system/vk-helpdesk-bot.service`:

```ini
[Unit]
Description=VK Helpdesk Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/vk-helpdesk-bot
ExecStart=/opt/vk-helpdesk-bot/.venv/bin/python -m app.main
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vk-helpdesk-bot
sudo systemctl status vk-helpdesk-bot
journalctl -u vk-helpdesk-bot -f   # смотреть логи
```

> **Один процесс — один Long Poll.** Не запускайте две копии бота на одном токене:
> получите конфликты апдейтов.

---

## 5. Развёртывание через Docker (альтернатива)

```bash
docker build -t vk-helpdesk-bot .
docker run -d --name vk-helpdesk-bot \
  --restart unless-stopped \
  --env-file .env \
  -v "$(pwd)/data:/data" \
  -e DB_PATH=/data/helpdesk.db \
  vk-helpdesk-bot
```

Том `data` хранит файл БД вне контейнера, чтобы он переживал пересборку.

---

## 6. Бэкап БД

SQLite бэкапится копированием файла. Пример: ежедневная копия по cron.

```cron
0 3 * * * cp /opt/vk-helpdesk-bot/helpdesk.db /opt/backups/helpdesk-$(date +\%F).db
```

---

## 7. Структура проекта

```
app/
├── main.py            # точка входа: сборка Bot, загрузка blueprints, run
├── config.py          # настройки из .env (pydantic-settings)
├── runtime.py         # доступ к Bot/Settings из хендлеров
├── enums.py           # Status, Category + подписи для кнопок
├── states.py          # FSM-состояния
├── db/
│   ├── database.py    # инициализация SQLite, создание таблиц
│   └── repository.py  # CRUD заявок и журнал статусов
├── keyboards/         # клавиатуры заявителя и inline-кнопки техника
├── handlers/          # common, create_ticket, user, admin, fallback
├── services/
│   └── notifications.py  # рассылка техникам и заявителю
└── utils/             # access (права), formatting (рендер заявок)
tests/                 # pytest-тесты слоя БД
```

---

## 8. Что дальше (вне MVP)

Архитектура (`status_log`, слой `services/`) заложена под расширение:
фото к заявке, экспорт в CSV/Sheets для завуча, статистика, приоритеты,
SLA-напоминания, маршрутизация по техникам. См. ТЗ `vk-helpdesk-bot.md`, раздел 9.
