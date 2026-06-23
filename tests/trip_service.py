#!/usr/bin/env python3
"""
Модуль с бизнес-логикой управления путешествиями.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from colorama import Fore

from backend.database import Database
from convert_currency.currency_util import (
    get_currency_code_by_country,
    get_rate,
    CURRENCIES,
    COUNTRY_TO_CURRENCY,
    CurrencyAPIError
)
from ui_messages import (
    print_header, print_success, print_error, print_info,
    print_balance, print_trip_summary, print_trip, print_supported_countries
)


def get_supported_countries() -> list:
    """Возвращает список стран, поддерживаемых API."""
    supported = []
    for country, code in COUNTRY_TO_CURRENCY.items():
        if code in CURRENCIES:
            supported.append(country)
    return sorted(supported)


def get_valid_country(prompt: str) -> str:
    """Запрашивает страну и проверяет поддержку."""
    supported = get_supported_countries()
    while True:
        country = input(f"{Fore.YELLOW}{prompt}: {Fore.WHITE}").strip()
        if not country:
            print_error("Название страны не может быть пустым")
            continue
        if country in supported:
            return country
        print_error(f"Страна '{country}' не найдена или не поддерживается API")
        print_supported_countries(supported)


def get_valid_amount(prompt: str) -> float:
    """Запрашивает сумму и проверяет, что это число > 0."""
    while True:
        amount_str = input(f"{Fore.YELLOW}{prompt}: {Fore.WHITE}").strip()
        if not amount_str:
            print_error("Сумма не может быть пустой")
            continue
        try:
            amount = float(amount_str.replace(',', '.'))
            if amount <= 0:
                print_error("Сумма должна быть больше 0")
                continue
            return amount
        except ValueError:
            print_error("Сумма должна быть числом (например, 1000 или 1000.50)")


def get_user_id(db: Database) -> int:
    """Получает ID тестового пользователя. Если нет — создаёт."""
    TEST_TELEGRAM_ID = 1
    TEST_USERNAME = "TestUser"
    
    user = db.fetch_one("SELECT id FROM users WHERE telegram_id = ?", (TEST_TELEGRAM_ID,))
    if user:
        return user['id']

    user_id = db.insert_one("users", {
        "telegram_id": TEST_TELEGRAM_ID,
        "username": TEST_USERNAME
    })
    print_success(f"Создан тестовый пользователь: ID={user_id}, telegram_id={TEST_TELEGRAM_ID}")
    return user_id


def get_active_trip(db: Database, user_id: int) -> dict:
    """Возвращает активное путешествие пользователя или None."""
    return db.fetch_one(
        "SELECT * FROM trips WHERE user_id = ? AND is_active = 1",
        (user_id,)
    )


def get_all_trips(db: Database, user_id: int) -> list:
    """Возвращает все путешествия пользователя."""
    return db.fetch_all(
        "SELECT * FROM trips WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )


def menu_create_trip(db: Database, user_id: int) -> None:
    """Создаёт новое путешествие."""
    print_header("СОЗДАНИЕ ПУТЕШЕСТВИЯ")

    country_from = get_valid_country("Введите страну отправления")
    country_to = get_valid_country("Введите страну назначения")

    currency_from = COUNTRY_TO_CURRENCY[country_from]
    currency_to = COUNTRY_TO_CURRENCY[country_to]

    print_info(f"Валюта отправления: {currency_from}")
    print_info(f"Валюта назначения: {currency_to}")

    try:
        rate = get_rate(currency_from, currency_to)
        if rate is None:
            print_error("Не удалось получить курс. Попробуйте позже.")
            return
        print_info(f"Курс: 1 {currency_from} = {rate:.4f} {currency_to}")
    except CurrencyAPIError as e:
        print_error(f"Ошибка API: {e}")
        return

    budget = get_valid_amount("Введите сумму в валюте отправления")
    converted_budget = budget * rate

    db.update_one("trips", {"is_active": 0}, "user_id = ?", (user_id,))

    trip_id = db.insert_one("trips", {
        "user_id": user_id,
        "country_from": country_from,
        "currency_from": currency_from,
        "country_to": country_to,
        "currency_to": currency_to,
        "exchange_rate": rate,
        "initial_amount_from": budget,
        "initial_amount_to": converted_budget,
        "is_active": 1
    })

    print_success(f"Путешествие создано! ID={trip_id}")
    trip = db.fetch_one("SELECT * FROM trips WHERE id = ?", (trip_id,))
    if trip:
        print_trip_summary(trip)


def menu_my_trips(db: Database, user_id: int) -> None:
    """Показывает все путешествия и позволяет переключить активное."""
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
        trip = db.fetch_one("SELECT id FROM trips WHERE id = ? AND user_id = ?", (trip_id, user_id))
        if not trip:
            print_error(f"Путешествие с ID={trip_id} не найдено")
            return

        db.update_one("trips", {"is_active": 0}, "user_id = ?", (user_id,))
        db.update_one("trips", {"is_active": 1}, "id = ?", (trip_id,))

        print_success(f"Активное путешествие переключено на ID={trip_id}")
        trip = db.fetch_one("SELECT * FROM trips WHERE id = ?", (trip_id,))
        if trip:
            print_balance(trip)
    except ValueError:
        print_error("Введите число")


def menu_add_expense(db: Database, user_id: int) -> None:
    """Добавляет расход: записывает в expenses, НЕ трогает trips."""
    print_header("ВВОД СУММЫ РАСХОДА")

    trip = get_active_trip(db, user_id)
    if not trip:
        print_error("Нет активного путешествия. Создайте новое.")
        return

    print_info(f"Активное путешествие: {trip['country_from']} → {trip['country_to']}")
    print_info(f"Валюта расчёта: {trip['currency_to']}")

    # Рассчитываем текущий остаток
    rest = db.fetch_one("""
        SELECT 
            t.initial_amount_to - COALESCE(SUM(e.amount_to), 0) AS rest_to
        FROM trips t
        LEFT JOIN expenses e ON t.id = e.trip_id
        WHERE t.id = ?
        GROUP BY t.id
    """, (trip['id'],))

    if rest:
        print_info(f"Доступный остаток: {rest['rest_to']:.2f} {trip['currency_to']}")

    amount_to = get_valid_amount(f"Введите сумму в {trip['currency_to']}")

    if rest and amount_to > rest['rest_to']:
        print_error(f"Недостаточно средств! Доступно: {rest['rest_to']:.2f} {trip['currency_to']}")
        return

    # Конвертируем в валюту отправления
    rate = trip['exchange_rate']
    amount_from = amount_to / rate

    print(f"\n{Fore.CYAN}Конвертация расхода:")
    print(f"  {Fore.WHITE}{amount_to:.2f} {trip['currency_to']} = {amount_from:.2f} {trip['currency_from']}")

    confirm = input(f"{Fore.YELLOW}Учесть как расход? (Y/n): {Fore.WHITE}").strip().lower()
    if confirm and confirm not in ('y', 'да', 'yes', ''):
        print_info("Операция отменена")
        return

    # Просто добавляем строку в expenses
    expense_id = db.insert_one("expenses", {
        "trip_id": trip['id'],
        "amount_from": amount_from,
        "amount_to": amount_to,
        "description": None
    })

    print_success(f"Расход учтён! ID={expense_id}")

    # Показываем обновлённый остаток
    rest_updated = db.fetch_one("""
        SELECT 
            t.initial_amount_from - COALESCE(SUM(e.amount_from), 0) AS rest_from,
            t.initial_amount_to - COALESCE(SUM(e.amount_to), 0) AS rest_to
        FROM trips t
        LEFT JOIN expenses e ON t.id = e.trip_id
        WHERE t.id = ?
        GROUP BY t.id
    """, (trip['id'],))

    if rest_updated:
        print(f"\n{Fore.CYAN}💳 ОБНОВЛЁННЫЙ ОСТАТОК:")
        print(f"  {Fore.WHITE}{rest_updated['rest_from']:.2f} {trip['currency_from']}")
        print(f"  {Fore.WHITE}{rest_updated['rest_to']:.2f} {trip['currency_to']}")


def menu_balance(db: Database, user_id: int) -> None:
    """Показывает баланс активного путешествия."""
    print_header("БАЛАНС")

    trip = get_active_trip(db, user_id)
    if not trip:
        print_error("Нет активного путешествия. Создайте новое.")
        return

    # Рассчитываем остаток через SUM
    rest = db.fetch_one("""
        SELECT 
            t.initial_amount_from - COALESCE(SUM(e.amount_from), 0) AS rest_from,
            t.initial_amount_to - COALESCE(SUM(e.amount_to), 0) AS rest_to
        FROM trips t
        LEFT JOIN expenses e ON t.id = e.trip_id
        WHERE t.id = ?
        GROUP BY t.id
    """, (trip['id'],))

    if not rest:
        print_error("Не удалось рассчитать остаток")
        return

    print_balance(trip, rest['rest_from'], rest['rest_to'])


def menu_history(db: Database, user_id: int) -> None:
    """Показывает историю расходов активного путешествия."""
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


def menu_change_rate(db: Database, user_id: int) -> None:
    """Позволяет вручную изменить курс для активного путешествия."""
    print_header("ИЗМЕНЕНИЕ КУРСА")

    trip = get_active_trip(db, user_id)
    if not trip:
        print_error("Нет активного путешествия. Создайте новое.")
        return

    print_info(f"Текущий курс: 1 {trip['currency_from']} = {trip['exchange_rate']:.4f} {trip['currency_to']}")
    print_info(f"Текущий баланс: {trip['initial_amount_from']:.2f} {trip['currency_from']} / {trip['initial_amount_to']:.2f} {trip['currency_to']}")

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

    # Пересчитываем баланс в валюте назначения
    new_initial_to = trip['initial_amount_from'] * new_rate

    db.update_one(
        "trips",
        {"exchange_rate": new_rate, "initial_amount_to": new_initial_to},
        "id = ?",
        (trip['id'],)
    )

    print_success(f"Курс обновлён: 1 {trip['currency_from']} = {new_rate:.4f} {trip['currency_to']}")
    print_info(f"Баланс пересчитан: {trip['initial_amount_from']:.2f} {trip['currency_from']} = {new_initial_to:.2f} {trip['currency_to']}")

    trip_updated = db.fetch_one("SELECT * FROM trips WHERE id = ?", (trip['id'],))
    if trip_updated:
        print_balance(trip_updated)


def menu_clear_all(db: Database, user_id: int) -> None:
    """Очищает все таблицы (DELETE + VACUUM)."""
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

    db.delete_all("expenses")
    db.delete_all("trips")
    db.delete_all("users")
    db.vacuum()

    print_success("Все таблицы очищены, БД сжата (VACUUM)")