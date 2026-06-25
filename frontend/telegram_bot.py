#!/usr/bin/env python3
"""
Telegram-бот для управления путешествиями.
Использует бизнес-логику из backend/trip_service.py.
"""

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from telebot import TeleBot
from telebot.storage import StateMemoryStorage

from backend.database import Database
from backend.trip_service import get_user_id
from frontend.bot.handlers import register_handlers

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и FSM
state_storage = StateMemoryStorage()
bot = TeleBot(BOT_TOKEN, state_storage=state_storage)

# Пробуем get_me() с повторами — может падать из-за сети при старте
import time as _time
print("🔍 Подключение к Telegram API...")
for attempt in range(5):
    try:
        bot.get_me()
        print("✅ Подключено к Telegram API")
        break
    except Exception as e:
        print(f"⚠️ Попытка {attempt + 1}/5: {e}")
        if attempt < 4:
            _time.sleep(3)
        else:
            print("⚠️ Не удалось подключиться, но бот продолжит работу")

# Подключение к БД
DB_PATH = Path(__file__).parent.parent / "database" / "travel_bot.db"
DB_PATH.parent.mkdir(exist_ok=True)
db = Database(str(DB_PATH))

# Создаём таблицы (если их нет)
tables_created = False
if not db.table_exists("users"):
    db.create_table("users", """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """)
    tables_created = True

if not db.table_exists("trips"):
    db.create_table("trips", """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        country_from TEXT NOT NULL,
        currency_from TEXT NOT NULL,
        country_to TEXT NOT NULL,
        currency_to TEXT NOT NULL,
        exchange_rate REAL NOT NULL,
        initial_amount_from REAL NOT NULL,
        initial_amount_to REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users (id)
    """)
    tables_created = True

if not db.table_exists("expenses"):
    db.create_table("expenses", """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id INTEGER NOT NULL,
        amount_from REAL NOT NULL,
        amount_to REAL NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trip_id) REFERENCES trips (id)
    """)
    tables_created = True

# Регистрация хендлеров из frontend/bot/handlers.py
USER_ID = get_user_id(db)
print(f"🔍 USER_ID={USER_ID}")
register_handlers(bot, db, USER_ID)

if __name__ == "__main__":
    print("🤖 Бот запущен...")
    bot.infinity_polling()