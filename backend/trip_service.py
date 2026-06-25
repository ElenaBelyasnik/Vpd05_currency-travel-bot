#!/usr/bin/env python3
"""
Модуль с бизнес-логикой управления путешествиями.
Не зависит от интерфейса (CLI/Telegram).
Возвращает данные, а не печатает их.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import Database
from convert_currency.currency_util import (
    get_currency_code_by_country,
    get_rate,
    CURRENCIES,
    COUNTRY_TO_CURRENCY,
    CurrencyAPIError
)


def get_supported_countries() -> list:
    """Возвращает список стран, поддерживаемых API."""
    supported = []
    for country, code in COUNTRY_TO_CURRENCY.items():
        if code in CURRENCIES:
            supported.append(country)
    return sorted(supported)


def get_user_id(db: Database) -> int:
    """Получает или создаёт тестового пользователя. Возвращает DB ID."""
    TEST_TELEGRAM_ID = 1
    TEST_USERNAME = "TestUser"
    
    user = db.fetch_one("SELECT id FROM users WHERE telegram_id = ?", (TEST_TELEGRAM_ID,))
    if user:
        return user['id']

    user_id = db.insert_one("users", {
        "telegram_id": TEST_TELEGRAM_ID,
        "username": TEST_USERNAME
    })
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


def get_trip_rest(db: Database, trip_id: int) -> dict:
    """
    Рассчитывает остаток по путешествию.
    Возвращает словарь с rest_from и rest_to.
    """
    result = db.fetch_one("""
        SELECT 
            t.initial_amount_from - COALESCE(SUM(e.amount_from), 0) AS rest_from,
            t.initial_amount_to - COALESCE(SUM(e.amount_to), 0) AS rest_to
        FROM trips t
        LEFT JOIN expenses e ON t.id = e.trip_id
        WHERE t.id = ?
        GROUP BY t.id
    """, (trip_id,))
    
    return result if result else {"rest_from": 0, "rest_to": 0}


def create_trip(db: Database, user_id: int, country_from: str, country_to: str, budget: float) -> dict:
    """
    Создаёт новое путешествие.
    Возвращает данные созданного путешествия.
    """
    currency_from = COUNTRY_TO_CURRENCY[country_from]
    currency_to = COUNTRY_TO_CURRENCY[country_to]
    
    rate = get_rate(currency_from, currency_to)
    if rate is None:
        raise CurrencyAPIError("Не удалось получить курс")
    
    converted_budget = budget * rate
    
    # Деактивируем все текущие путешествия
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
    
    trip = db.fetch_one("SELECT * FROM trips WHERE id = ?", (trip_id,))
    return trip


def add_expense(db: Database, trip_id: int, amount_to: float, description: str = None) -> dict:
    """
    Добавляет расход в путешествие.
    Возвращает данные добавленного расхода и обновлённые остатки.
    """
    # Получаем путешествие
    trip = db.fetch_one("SELECT * FROM trips WHERE id = ?", (trip_id,))
    if not trip:
        raise ValueError(f"Путешествие {trip_id} не найдено")
    
    # Проверяем остаток
    rest = get_trip_rest(db, trip_id)
    if amount_to > rest['rest_to']:
        raise ValueError(f"Недостаточно средств! Доступно: {rest['rest_to']:.2f} {trip['currency_to']}")
    
    # Конвертируем
    rate = trip['exchange_rate']
    amount_from = amount_to / rate
    
    # Добавляем расход
    expense_id = db.insert_one("expenses", {
        "trip_id": trip_id,
        "amount_from": amount_from,
        "amount_to": amount_to,
        "description": description
    })
    
    expense = db.fetch_one("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    rest_updated = get_trip_rest(db, trip_id)
    
    return {
        "expense": expense,
        "rest_from": rest_updated['rest_from'],
        "rest_to": rest_updated['rest_to']
    }


def switch_trip(db: Database, user_id: int, trip_id: int) -> dict:
    """
    Переключает активное путешествие.
    Возвращает данные активированного путешествия.
    """
    # Проверяем, существует ли такое путешествие у пользователя
    trip = db.fetch_one("SELECT id FROM trips WHERE id = ? AND user_id = ?", (trip_id, user_id))
    if not trip:
        raise ValueError(f"Путешествие с ID={trip_id} не найдено")
    
    db.update_one("trips", {"is_active": 0}, "user_id = ?", (user_id,))
    db.update_one("trips", {"is_active": 1}, "id = ?", (trip_id,))
    
    trip = db.fetch_one("SELECT * FROM trips WHERE id = ?", (trip_id,))
    return trip


def change_rate(db: Database, trip_id: int, new_rate: float) -> dict:
    """
    Изменяет курс для путешествия и пересчитывает начальную сумму в валюте назначения.
    Возвращает обновлённые данные путешествия.
    """
    trip = db.fetch_one("SELECT * FROM trips WHERE id = ?", (trip_id,))
    if not trip:
        raise ValueError(f"Путешествие {trip_id} не найдено")
    
    new_initial_to = trip['initial_amount_from'] * new_rate
    
    db.update_one(
        "trips",
        {"exchange_rate": new_rate, "initial_amount_to": new_initial_to},
        "id = ?",
        (trip_id,)
    )
    
    trip_updated = db.fetch_one("SELECT * FROM trips WHERE id = ?", (trip_id,))
    return trip_updated


def clear_all_data(db: Database) -> None:
    """Очищает все таблицы."""
    db.delete_all("expenses")
    db.delete_all("trips")
    db.delete_all("users")
    db.vacuum()