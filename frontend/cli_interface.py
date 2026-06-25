#!/usr/bin/env python3
"""
CLI-интерфейс для тестирования бизнес-логики путешествий.
Запуск: python frontend/cli_interface.py
"""

import sys
import logging
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from colorama import init, Fore
from backend.database import Database
from backend.trip_service import (
    get_user_id,
    create_trip,
    get_active_trip,
    get_all_trips,
    get_trip_rest,
    add_expense,
    switch_trip,
    change_rate,
    clear_all_data,
    get_supported_countries
)
from ui_messages import (
    print_header, print_success, print_error, print_info,
    print_balance, print_trip_summary, print_trip, print_supported_countries,
    get_valid_country, get_valid_amount
)

# Инициализация colorama
init(autoreset=True)

# Константы
DB_PATH = Path(__file__).parent.parent / "database" / "travel_bot.db"


# ==================== ОБЁРТКИ ДЛЯ CLI ====================

def cli_create_trip(db: Database, user_id: int) -> None:
    """CLI-обёртка для создания путешествия."""
    print_header("СОЗДАНИЕ ПУТЕШЕСТВИЯ")
    
    country_from = get_valid_country("Введите страну отправления", default="Россия")
    country_to = get_valid_country("Введите страну назначения")
    budget = get_valid_amount("Введите сумму в валюте отправления")
    
    try:
        trip = create_trip(db, user_id, country_from, country_to, budget)
        if trip:
            print_trip_summary(trip)
            rest = get_trip_rest(db, trip['id'])
            print_balance(trip, rest['rest_from'], rest['rest_to'])
    except Exception as e:
        print_error(f"Ошибка: {e}")


def cli_add_expense(db: Database, user_id: int) -> None:
    """CLI-обёртка для добавления расхода."""
    print_header("ВВОД СУММЫ РАСХОДА")
    
    trip = get_active_trip(db, user_id)
    if not trip:
        print_error("Нет активного путешествия. Создайте новое.")
        return
    
    print_info(f"Активное путешествие: {trip['country_from']} → {trip['country_to']}")
    print_info(f"Валюта расчёта: {trip['currency_to']}")
    
    rest = get_trip_rest(db, trip['id'])
    print_info(f"Доступный остаток: {rest['rest_to']:.2f} {trip['currency_to']}")
    
    amount_to = get_valid_amount(f"Введите сумму в {trip['currency_to']}")
    
    try:
        result = add_expense(db, trip['id'], amount_to)
        print(f"\n{Fore.CYAN}Конвертация расхода:")
        print(f"  {Fore.WHITE}{result['expense']['amount_to']:.2f} {trip['currency_to']} = {result['expense']['amount_from']:.2f} {trip['currency_from']}")
        
        confirm = input(f"{Fore.YELLOW}Учесть как расход? (Y/n): {Fore.WHITE}").strip().lower()
        if confirm and confirm not in ('y', 'да', 'yes', ''):
            print_info("Операция отменена")
            # Удаляем только что добавленный расход
            db.delete_one("expenses", "id = ?", (result['expense']['id'],))
            return
        
        print_success(f"Расход учтён! ID={result['expense']['id']}")
        print(f"\n{Fore.CYAN}💳 ОБНОВЛЁННЫЙ ОСТАТОК:")
        print(f"  {Fore.WHITE}{result['rest_from']:.2f} {trip['currency_from']}")
        print(f"  {Fore.WHITE}{result['rest_to']:.2f} {trip['currency_to']}")
    except Exception as e:
        print_error(f"Ошибка: {e}")


def cli_my_trips(db: Database, user_id: int) -> None:
    """CLI-обёртка для показа и переключения путешествий."""
    print_header("МОИ ПУТЕШЕСТВИЯ")
    
    trips = get_all_trips(db, user_id)
    if not trips:
        print_info("У вас нет ни одного путешествия")
        return
    
    print(f"{Fore.CYAN}Ваши путешествия:")
    for t in trips:
        print_trip(t, show_active=True)
    
    answer = input(f"\n{Fore.YELLOW}Введите ID путешествия для переключения (или Enter для отмены): {Fore.WHITE}").strip()
    if not answer:
        return
    
    try:
        trip_id = int(answer)
        trip = switch_trip(db, user_id, trip_id)
        print_success(f"Активное путешествие переключено на ID={trip_id}")
        rest = get_trip_rest(db, trip['id'])
        print_balance(trip, rest['rest_from'], rest['rest_to'])
    except ValueError as e:
        print_error(f"Ошибка: {e}")
    except Exception as e:
        print_error(f"Ошибка: {e}")


def cli_balance(db: Database, user_id: int) -> None:
    """CLI-обёртка для показа баланса."""
    print_header("БАЛАНС")
    
    trip = get_active_trip(db, user_id)
    if not trip:
        print_error("Нет активного путешествия. Создайте новое.")
        return
    
    rest = get_trip_rest(db, trip['id'])
    print_balance(trip, rest['rest_from'], rest['rest_to'])


def cli_history(db: Database, user_id: int) -> None:
    """CLI-обёртка для показа истории расходов."""
    print_header("ИСТОРИЯ РАСХОДОВ")
    
    trip = get_active_trip(db, user_id)
    if not trip:
        print_error("Нет активного путешествия")
        return
    
    expenses = db.fetch_all(
        "SELECT * FROM expenses WHERE trip_id = ? ORDER BY created_at DESC LIMIT 20",
        (trip['id'],)
    )
    
    if not expenses:
        print_info("История расходов пуста")
        return
    
    print(f"  {Fore.CYAN}Дата{' ' * 10}  Сумма ({trip['currency_to']})  →  Сумма ({trip['currency_from']})  Описание")
    print(f"  {Fore.CYAN}{'-' * 65}")
    
    for exp in expenses:
        date_str = exp['created_at'][:16] if exp['created_at'] else ''
        desc = exp['description'] or ''
        print(f"  {Fore.WHITE}{date_str}  "
              f"{exp['amount_to']:>10.2f}  →  {exp['amount_from']:>10.2f}  {Fore.YELLOW}{desc}")


def cli_change_rate(db: Database, user_id: int) -> None:
    """CLI-обёртка для изменения курса."""
    print_header("ИЗМЕНЕНИЕ КУРСА")
    
    trip = get_active_trip(db, user_id)
    if not trip:
        print_error("Нет активного путешествия. Создайте новое.")
        return
    
    print_info(f"Текущий курс: 1 {trip['currency_from']} = {trip['exchange_rate']:.4f} {trip['currency_to']}")
    
    while True:
        rate_str = input(f"{Fore.YELLOW}Введите новый курс (1 {trip['currency_from']} = X {trip['currency_to']}): {Fore.WHITE}").strip()
        if not rate_str:
            print_info("Отмена")
            return
        try:
            new_rate = float(rate_str.replace(',', '.'))
            if new_rate <= 0:
                print_error("Курс должен быть больше 0")
                continue
            break
        except ValueError:
            print_error("Введите число")
    
    try:
        trip_updated = change_rate(db, trip['id'], new_rate)
        print_success(f"Курс обновлён: 1 {trip['currency_from']} = {new_rate:.4f} {trip['currency_to']}")
        rest = get_trip_rest(db, trip_updated['id'])
        print_balance(trip_updated, rest['rest_from'], rest['rest_to'])
    except Exception as e:
        print_error(f"Ошибка: {e}")


def cli_clear_all(db: Database, user_id: int) -> None:
    """CLI-обёртка для очистки данных."""
    print_header("ОЧИСТКА ВСЕХ ТАБЛИЦ")
    
    count_users = db.get_count("SELECT COUNT(*) FROM users")
    count_trips = db.get_count("SELECT COUNT(*) FROM trips")
    count_expenses = db.get_count("SELECT COUNT(*) FROM expenses")
    
    if count_users == 0 and count_trips == 0 and count_expenses == 0:
        print_info("База данных уже пуста")
        return
    
    print(f"{Fore.RED}⚠️  ВНИМАНИЕ! Будут удалены ВСЕ данные:")
    print(f"  Пользователи: {count_users}")
    print(f"  Путешествия: {count_trips}")
    print(f"  Расходы: {count_expenses}")
    
    answer = input(f"{Fore.YELLOW}Продолжить? (Y/n): {Fore.WHITE}").strip().lower()
    if answer and answer not in ('y', 'да', 'yes', ''):
        print_info("Очистка отменена")
        return
    
    clear_all_data(db)
    print_success("Все таблицы очищены, БД сжата (VACUUM)")


# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================

def main():
    """Главная функция — интерактивное меню."""
    print_header("ФИНАНСОВЫЙ ПОМОЩНИК ДЛЯ ПУТЕШЕСТВИЙ")
    
    DB_PATH.parent.mkdir(exist_ok=True)
    db = Database(str(DB_PATH))
    
    # Создаём таблицы (только если их нет)
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
    
    if tables_created:
        print_success("Структура БД создана")
    else:
        print_info("Структура БД уже существует")
    
    user_id = get_user_id(db, 1)  # CLI использует тестового пользователя с telegram_id=1
    print_success(f"БД готова, пользователь ID={user_id}")
    
    # Главное меню
    menu_actions = {
        "1": ("Создать путешествие", cli_create_trip),
        "2": ("Мои путешествия", cli_my_trips),
        "3": ("Ввести сумму расхода", cli_add_expense),
        "4": ("Баланс", cli_balance),
        "5": ("История расходов", cli_history),
        "6": ("Изменить курс", cli_change_rate),
        "7": ("Очистить все таблицы (с VACUUM)", cli_clear_all),
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