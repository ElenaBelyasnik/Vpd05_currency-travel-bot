"""Модуль для работы с AllRatesToday API.

Предоставляет функции для получения курсов валют и конвертации сумм.
API-ключ берётся из переменной окружения CURRENCY_API_KEY через python-dotenv.
Используется requests для надёжных HTTP-запросов.
"""

import os
import requests
from typing import Union

from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# ─── Константы ────────────────────────────────────────────────────────────────

API_BASE_URL: str = "https://allratestoday.com/api/v1"
RATES_ENDPOINT: str = f"{API_BASE_URL}/rates"

API_KEY: str = os.getenv("CURRENCY_API_KEY", "")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}


# ─── Функции API ──────────────────────────────────────────────────────────────


def get_rate(
    source: str, target: Union[str, list[str]]
) -> Union[dict, list[dict]]:
    """Получить курс валюты( currencies ) от AllRatesToday API.

    Запрашивает актуальный курс между source и target валютой(-ами).

    Args:
        source: Код исходной валюты (например, 'USD', 'RUB').
        target: Код целевой валюты или список кодов
                (например, 'EUR' или ['EUR', 'GBP', 'JPY']).

    Returns:
        Если target — одна валюта: dict с полем 'rate', 'source', 'target'.
        Если target — список: list[dict] для каждой валюты.

    Raises:
        ValueError: Если не указан API-ключ.
        requests.exceptions.RequestException: При ошибке запроса.

    Examples:
        >>> get_rate("USD", "EUR")
        {'rate': 0.92, 'source': 'USD', 'target': 'EUR'}

        >>> get_rate("USD", ["EUR", "GBP"])
        [{'rate': 0.92, 'source': 'USD', 'target': 'EUR'},
         {'rate': 0.79, 'source': 'USD', 'target': 'GBP'}]
    """
    if not API_KEY:
        raise ValueError(
            "API-ключ не найден. Создайте файл .env с переменной "
            "CURRENCY_API_KEY=ваш_ключ"
        )

    if isinstance(target, str):
        targets = [t.strip() for t in target.split(",")]
    else:
        targets = [t.strip().upper() for t in target]

    params = {
        "source": source.upper(),
        "target": ",".join(t.upper() for t in targets),
    }

    try:
        response = requests.get(RATES_ENDPOINT, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as e:
        e.response.reason = f"Ошибка HTTP {e.response.status_code}: {e.response.reason}"
        raise
    except requests.exceptions.RequestException as e:
        raise URLError(f"Ошибка соединения: {e}")

    if len(targets) == 1:
        return data[0] if isinstance(data, list) else data

    return data


def convert_currency(
    amount: float, source: str, target: str
) -> dict:
    """Конвертировать сумму из одной валюты в другую.

    Запрашивает у API результат конвертации с учётом текущего курса.

    Args:
        amount: Сумма для конвертации (должна быть > 0).
        source: Код исходной валюты (например, 'USD').
        target: Код целевой валюты (например, 'EUR').

    Returns:
        dict с полями:
        - 'from': {'currency': str, 'amount': float}
        - 'to': {'currency': str, 'amount': float}
        - 'rate': float
        - 'source': str (источник данных)

    Raises:
        ValueError: Если amount <= 0 или не указан API-ключ.
        requests.exceptions.RequestException: При ошибке запроса.

    Examples:
        >>> convert_currency(1000, "USD", "EUR")
        {
            'from': {'currency': 'USD', 'amount': 1000},
            'to': {'currency': 'EUR', 'amount': 923.4},
            'rate': 0.9234,
            'source': 'refinitiv'
        }
    """
    if not API_KEY:
        raise ValueError(
            "API-ключ не найден. Создайте файл .env с переменной "
            "CURRENCY_API_KEY=ваш_ключ"
        )

    if amount <= 0:
        raise ValueError(f"Сумма должна быть больше нуля, получено: {amount}")

    params = {
        "source": source.upper(),
        "target": target.upper(),
        "amount": amount,
    }

    try:
        response = requests.get(RATES_ENDPOINT, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as e:
        e.response.reason = f"Ошибка HTTP {e.response.status_code}: {e.response.reason}"
        raise
    except requests.exceptions.RequestException as e:
        raise URLError(f"Ошибка соединения: {e}")

    return data


def close_session() -> None:
    """Закрыть сессию requests при завершении работы.
    
    Примечание: urllib не использует сессии, эта функция оставлена для совместимости.
    """
    pass
