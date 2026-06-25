# Summary.md — Контекст проекта для AI-агентов

## 📌 Обзор проекта

**Название:** Финансовый помощник для путешествий  
**Тип:** Telegram-бот + CLI-интерфейс  
**Язык:** Python 3.7+  
**Цель:** Управление бюджетом в путешествиях с конвертацией валют через API ЦБ РФ

---

## 🏗 Архитектура

```
├── backend/
│   ├── database.py          # Обёртка над SQLite3 (CRUD, транзакции)
│   └── trip_service.py      # Бизнес-логика (путешествия, расходы, курсы)
├── frontend/
│   ├── cli_interface.py     # CLI-интерфейс (тестирование)
│   ├── telegram_bot.py      # Точка входа Telegram-бота (ТОЛЬКО инициализация)
│   ├── ui_messages.py       # Цветной вывод для CLI
│   └── bot/
│       ├── handlers.py      # ВСЕ обработчики бота (главный файл логики)
│       ├── keyboards.py     # Генерация inline-клавиатур
│       ├── states.py        # FSM-состояния (TravelStates)
│       └── formatters.py    # Форматирование сообщений для бота
├── convert_currency/
│   └── currency_util.py     # API ЦБ РФ, курсы валют, страны
├── tests/
│   └── test_currency_cli.py # Тестовый CLI для конвертера
├── database/
│   └── travel_bot.db        # SQLite база данных (создаётся автоматически)
└── requirements.txt         # Зависимости
```

---

## 🔑 Ключевые файлы

### `frontend/telegram_bot.py`
**ТОЛЬКО инициализация!** Никаких обработчиков здесь нет.
- Загружает `.env` для `TELEGRAM_BOT_TOKEN`
- Создаёт БД и таблицы (users, trips, expenses)
- Вызывает `register_handlers(bot, db, USER_ID)`

### `frontend/bot/handlers.py`
**Главный файл логики бота.** Содержит `register_handlers(bot, db, USER_ID)`, который регистрирует все обработчики:
- Команды: `/start`
- Callback'и: создание путешествия, мои поездки, баланс, история, изменение курса, очистка
- FSM-обработчики: `WAITING_COUNTRY_FROM`, `WAITING_COUNTRY_TO`, `WAITING_BUDGET`, `WAITING_NEW_RATE`
- Общий текстовый обработчик: распознаёт числа как расходы

### `frontend/bot/keyboards.py`
Генерирует inline-клавиатуры. `callback_data` использует индексы (`c_0`, `c_1`...) — это важно, чтобы не превысить лимит Telegram в 64 байта.

### `frontend/bot/states.py`
FSM-состояния:
- `WAITING_COUNTRY_FROM` — ввод страны отправления
- `WAITING_COUNTRY_TO` — ввод страны назначения
- `WAITING_BUDGET` — ввод бюджета
- `WAITING_NEW_RATE` — ввод нового курса

---

## ⚠️ Известные паттерны и правила

### FSM-хранилище
- Используется `StateMemoryStorage` (данные в памяти, теряются при перезапуске)

### 🔴 КРИТИЧЕСКИ: порядок аргументов в FSM-методах
**ВСЕ FSM-методы в pyTelegramBotAPI принимают user_id ПЕРВЫМ, chat_id ВТОРЫМ:**

```python
# ✅ ПРАВИЛЬНО:
bot.get_state(user_id, chat_id)        # user_id=from_user.id, chat_id=chat.id
bot.set_state(user_id, state, chat_id) # user_id=from_user.id, chat_id=chat.id
bot.delete_state(user_id, chat_id)     # user_id=from_user.id, chat_id=chat.id
bot.retrieve_data(user_id, chat_id)    # user_id=from_user.id, chat_id=chat.id

# ❌ НЕПРАВИЛЬНО (БЫЛО):
bot.get_state(chat.id, from_user.id)   # ПЕРЕПУТАНО!
bot.set_state(chat.id, state, from_user.id)  # ПЕРЕПУТАНО!
```

**Ошибка:** `retrieve_data(chat.id, from_user.id)` сохраняет данные в storage по ключу `{chat.id: {from_user.id: ...}}`, но `get_state(from_user.id, chat.id)` ищет по `{from_user.id: {chat.id: ...}}`. Данные не находятся → FSM-состояние теряется → `handle_budget` не вызывается → срабатывает `handle_expense` → "Нет активного путешествия".

### Работа с БД
- `is_active = 1` — активное путешествие
- `get_active_trip(db, user_id)` — возвращает активное путешествие
- `switch_trip(db, user_id, trip_id)` — деактивирует все, активирует нужный
- `add_expense(db, trip_id, amount_to)` — добавляет расход с проверкой остатка

### Callback-данные
- Формат: `c_{index}` (например, `c_0`, `c_36`)
- Индекс маппится на название страны через `get_supported_countries()[index]`
- Это защищает от превышения лимита в 64 байта

### Пользователь
- Тестовый пользователь: `telegram_id = 1`, `username = "TestUser"`
- Функция `get_user_id(db)` создаёт пользователя, если нет

---

## 🐛 Текущие проблемы

### 1. Потеря FSM при перезапуске
`StateMemoryStorage` стирает данные при перезапуске бота. Если пользователь вводит данные, а бот перезапускается — диалог теряется.  
**Решение:** добавить `StateRedisStorage` или файловое хранилище.

### 2. Дублирование кода в `handlers.py`
Многие обработчики дублируют логику (создание путешествия, баланс и т.д.).  
**Решение:** вынести общие функции в отдельные модули.

### 3. Жёстко заданный USER_ID
Бот работает только с `telegram_id = 1`.  
**Решение:** получать ID пользователя из `message.from_user.id`.

### 4. Баг `pyTelegramBotAPI` 4.18.0: `set_state` внутри `retrieve_data` не работает
**Проблема:** `bot.set_state()` вызванный ВНУТРИ `with bot.retrieve_data()...` не сохраняет состояние в storage. Состояние теряется, `handle_budget` не вызывается, число уходит в `handle_expense` → "Нет активного путешествия".

**Обходное решение:** `set_state` вызывается **ПОСЛЕ** выхода из `with bot.retrieve_data()`. Данные сохраняются в `with`, состояние — после.

```python
with bot.retrieve_data(user_id, chat_id) as data:
    data['key'] = value
    # ❌ set_state ЗДЕСЬ НЕ РАБОТАЕТ в pyTelegramBotAPI 4.18.0
next_state = TravelStates.WAITING_BUDGET
# ✅ set_state ЗДЕСЬ — ПОСЛЕ with
bot.set_state(user_id, next_state, chat_id)
```

**Корневая причина:** `retrieve_data` создаёт `StateContext`, который при выходе вызывает `save()`, перезаписывая FSM-запись. Если `set_state` вызван внутри `with`, `save()` перезаписывает запись и стирает состояние.

---

## 📝 Ход работ

### 23.06.2026
- **Очищен `telegram_bot.py`** — удалены устаревшие обработчики и клавиатуры, оставлена только инициализация БД и вызов `register_handlers()`
- **Исправлен `BUTTON_DATA_INVALID`** — длинные названия стран в `callback_data` превышали лимит Telegram 64 байта. Заменены на индексы (`c_0`, `c_1`...), маппинг в `handlers.py`
- **Исправлены аргументы FSM** — все вызовы `set_state`, `get_state`, `delete_state`, `retrieve_data` используют `user_id` (первый аргумент = `from_user.id`), `chat_id` (второй = `chat.id`)

### 24.06.2026
- **Найдена и исправлена потеря FSM-состояния** — `set_state` внутри `retrieve_data` не срабатывает в pyTelegramBotAPI 4.18.0. Перенесены все `set_state` ПОСЛЕ `with retrieve_data()`

---

## 📊 Схема БД

### users
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
telegram_id INTEGER UNIQUE NOT NULL
username TEXT
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### trips
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
user_id INTEGER NOT NULL
country_from TEXT NOT NULL
currency_from TEXT NOT NULL
country_to TEXT NOT NULL
currency_to TEXT NOT NULL
exchange_rate REAL NOT NULL
initial_amount_from REAL NOT NULL
initial_amount_to REAL NOT NULL
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
is_active INTEGER DEFAULT 1
FOREIGN KEY (user_id) REFERENCES users (id)
```

### expenses
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
trip_id INTEGER NOT NULL
amount_from REAL NOT NULL
amount_to REAL NOT NULL
description TEXT
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
FOREIGN KEY (trip_id) REFERENCES trips (id)
```

---

## 🚀 Запуск

### CLI
```bash
python frontend/cli_interface.py
```

### Telegram-бот
1. Создать `.env` с `TELEGRAM_BOT_TOKEN=your_token`
2. `python frontend/telegram_bot.py`

---

## 📦 Зависимости
```
requests>=2.28.0
colorama>=0.4.6
pyTelegramBotAPI==4.18.0
python-dotenv
```

---

## 💡 Советы для следующего AI-агента

1. **Никогда не добавляй обработчики в `telegram_bot.py`** — всё идёт в `handlers.py`
2. **ВСЕ FSM-методы принимают user_id ПЕРВЫМ, chat_id ВТОРЫМ!** Это самая частая ошибка:
   - `bot.get_state(from_user.id, chat.id)` — ПРАВИЛЬНО
   - `bot.set_state(from_user.id, state, chat.id)` — ПРАВИЛЬНО
   - `bot.delete_state(from_user.id, chat.id)` — ПРАВИЛЬНО
   - `bot.retrieve_data(from_user.id, chat.id)` — ПРАВИЛЬНО
   - ❌ НЕ перепутай `chat.id` и `from_user.id` — данные сохранятся по неправильному ключу
3. **НИКОГДА не вызывай `set_state` ВНУТРИ `with retrieve_data()`** — в pyTelegramBotAPI 4.18.0 это не сохраняет состояние. Вызывай `set_state` ПОСЛЕ выхода из `with`:
   ```python
   with bot.retrieve_data(user_id, chat_id) as data:
       data['key'] = value
   bot.set_state(user_id, next_state, chat_id)  # ПОСЛЕ with
   ```
4. **БД — единственный источник правды** для путешествий и расходов. FSM — только для промежуточных шагов диалога.
