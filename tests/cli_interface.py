#!/usr/bin/env python3
"""
CLI-интерфейс для тестирования бизнес-логики путешествий.
Запуск: python tests/cli_interface.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from colorama import init, Fore
from backend.database import Database
from ui_messages import print_header, print_success, print_error, print_info
from trip_service import (
    get_user_id,
    menu_create_trip,
    menu_my_trips,
    menu_add_expense,
    menu_balance,
    menu_history,
    menu_change_rate,
    menu_clear_all
)

# Инициализация colorama
init(autoreset=True)

# Константы
DB_PATH = Path(__file__).parent.parent / "database" / "travel_bot.db"


def main():
    """Главная функция — интерактивное меню."""
    print_header("ФИНАНСОВЫЙ ПОМОЩНИК ДЛЯ ПУТЕШЕСТВИЙ")

    DB_PATH.parent.mkdir(exist_ok=True)
    db = Database(str(DB_PATH))

    # Создаём таблицы
    db.create_table("users", """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """)

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

    db.create_table("expenses", """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id INTEGER NOT NULL,
        amount_from REAL NOT NULL,
        amount_to REAL NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trip_id) REFERENCES trips (id)
    """)

    user_id = get_user_id(db)
    print_success(f"БД готова, пользователь ID={user_id}")

    # Главное меню
    menu_actions = {
        "1": ("Создать путешествие", menu_create_trip),
        "2": ("Мои путешествия", menu_my_trips),
        "3": ("Ввести сумму расхода", menu_add_expense),
        "4": ("Баланс", menu_balance),
        "5": ("История расходов", menu_history),
        "6": ("Изменить курс", menu_change_rate),
        "7": ("Очистить все таблицы (с VACUUM)", menu_clear_all),
        "8": ("Выход", None)
    }

    while True:
        print("\n" + "=" * 60)
        print(f"{Fore.CYAN}ГЛАВНОЕ МЕНЮ")
        print("=" * 60)
        print(f"  {Fore.WHITE}1. Создать путешествие")
        print(f"  {Fore.WHITE}2. Мои путешествия")
        print(f"  {Fore.WHITE}3. Ввести сумму расхода")
        print(f"  {Fore.WHITE}4. Баланс")
        print(f"  {Fore.WHITE}5. История расходов")
        print(f"  {Fore.WHITE}6. Изменить курс")
        print(f"  {Fore.RED}7. Очистить все таблицы (с VACUUM)")
        print(f"  {Fore.WHITE}8. Выход")
        print("=" * 60)

        choice = input(f"{Fore.YELLOW}Выберите действие (1-8): {Fore.WHITE}").strip()

        if choice == "8":
            print_info("До свидания!")
            break

        if choice in menu_actions:
            _, action = menu_actions[choice]
            if action:
                action(db, user_id)
        else:
            print_error("Неверный выбор. Попробуйте снова.")

        input(f"\n{Fore.CYAN}Нажмите Enter для продолжения...{Fore.WHITE}")


if __name__ == "__main__":
    main()