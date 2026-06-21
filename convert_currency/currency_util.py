"""
Модуль для работы с курсами валют через API Центрального Банка РФ.
Использует бесплатную JSON-обёртку: https://www.cbr-xml-daily.ru/daily_json.js
"""

from typing import Dict, Optional
import requests


API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"

CURRENCIES: Dict[str, str] = {
    "RUB": "Российский рубль",
    "USD": "Доллар США",
    "EUR": "Евро",
    "GBP": "Британский фунт стерлингов",
    "JPY": "Японская иена",
    "CNY": "Китайский юань",
    "CHF": "Швейцарский франк",
    "CAD": "Канадский доллар",
    "AUD": "Австралийский доллар",
    "INR": "Индийская рупия",
    "BRL": "Бразильский реал",
    "KRW": "Южнокорейская вона",
    "MXN": "Мексиканское песо",
    "SGD": "Сингапурский доллар",
    "TRY": "Турецкая лира",
    "ZAR": "Южноафриканский рэнд",
    "NZD": "Новозеландский доллар",
    "SEK": "Шведская крона",
    "NOK": "Норвежская крона",
    "DKK": "Датская крона",
    "PLN": "Польский злотый",
    "THB": "Тайский бат",
    "IDR": "Индонезийская рупия",
    "AED": "Дирхам ОАЭ",
    "SAR": "Саудовский риал",
}

# Словарь: название страны -> код валюты
COUNTRY_TO_CURRENCY: Dict[str, str] = {
    # Россия
    "Россия": "RUB",
    "Российская Федерация": "RUB",
    # США
    "США": "USD",
    "Соединённые Штаты": "USD",
    "Америка": "USD",
    # Евросоюз (EUR)
    "Евросоюз": "EUR",
    "Европейский Союз": "EUR",
    "Австрия": "EUR",
    "Бельгия": "EUR",
    "Болгария": "EUR",
    "Венгрия": "EUR",
    "Германия": "EUR",
    "Греция": "EUR",
    "Ирландия": "EUR",
    "Испания": "EUR",
    "Италия": "EUR",
    "Кипр": "EUR",
    "Латвия": "EUR",
    "Литва": "EUR",
    "Люксембург": "EUR",
    "Мальта": "EUR",
    "Нидерланды": "EUR",
    "Португалия": "EUR",
    "Румыния": "EUR",
    "Словакия": "EUR",
    "Словения": "EUR",
    "Финляндия": "EUR",
    "Франция": "EUR",
    "Хорватия": "EUR",
    "Чехия": "EUR",
    "Чешская Республика": "EUR",
    "Эстония": "EUR",
    # Великобритания
    "Великобритания": "GBP",
    "Англия": "GBP",
    # Япония
    "Япония": "JPY",
    # Китай
    "Китай": "CNY",
    # Швейцария
    "Швейцария": "CHF",
    # Канада
    "Канада": "CAD",
    # Австралия
    "Австралия": "AUD",
    # Индия
    "Индия": "INR",
    # Бразилия
    "Бразилия": "BRL",
    # Южная Корея
    "Южная Корея": "KRW",
    "Корея": "KRW",
    # Мексика
    "Мексика": "MXN",
    # Сингапур
    "Сингапур": "SGD",
    # Турция
    "Турция": "TRY",
    # ЮАР
    "ЮАР": "ZAR",
    # Новая Зеландия
    "Новая Зеландия": "NZD",
    # Швеция
    "Швеция": "SEK",
    # Норвегия
    "Норвегия": "NOK",
    # Дания
    "Дания": "DKK",
    # Польша
    "Польша": "PLN",
    # Таиланд
    "Таиланд": "THB",
    # Индонезия
    "Индонезия": "IDR",
    # ОАЭ
    "ОАЭ": "AED",
    "Объединённые Арабские Эмираты": "AED",
    # Саудовская Аравия
    "Саудовская Аравия": "SAR",
}


class CurrencyAPIError(Exception):
    """Исключение для ошибок API валют."""

    pass


def _fetch_data() -> Optional[Dict]:
    """
    Загружает данные о курсах валют с API ЦБ РФ.

    Returns:
        Словарь с данными о курсах валют или None при ошибке.

    Raises:
        CurrencyAPIError: При ошибке подключения или получении данных.
    """
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError as e:
        raise CurrencyAPIError(f"Ошибка подключения к API: {e}")
    except requests.exceptions.Timeout as e:
        raise CurrencyAPIError(f"Превышено время ожидания ответа от API: {e}")
    except requests.exceptions.HTTPError as e:
        raise CurrencyAPIError(f"HTTP ошибка при запросе к API: {e}")
    except ValueError as e:
        raise CurrencyAPIError(f"Ошибка парсинга JSON ответа: {e}")


def get_rate(source: str, target: str) -> Optional[float]:
    """
    Возвращает курс одной валюты к другой.

    Args:
        source: Код исходной валюты (например, 'USD').
        target: Код целевой валюты (например, 'RUB').

    Returns:
        Курс обмена от source к target, или None при ошибке.

    Raises:
        CurrencyAPIError: При ошибке подключения или неверном коде валюты.

    Example:
        >>> rate = get_rate('USD', 'RUB')
        >>> print(f"1 USD = {rate} RUB")
    """
    source = source.upper()
    target = target.upper()

    if source not in CURRENCIES:
        raise CurrencyAPIError(f"Неизвестный код валюты: {source}")
    if target not in CURRENCIES:
        raise CurrencyAPIError(f"Неизвестный код валюты: {target}")

    data = _fetch_data()
    if data is None:
        return None

    # Если целевая валюта RUB, берём напрямую Value
    if target == "RUB":
        if source == "RUB":
            return 1.0
        currency_data = data.get("Valute", {}).get(source)
        if currency_data is None:
            raise CurrencyAPIError(f"Валюта {source} не найдена в ответе API")
        return currency_data.get("Value")

    # Если исходная валюта RUB, используем обратный курс
    if source == "RUB":
        if target == "RUB":
            return 1.0
        currency_data = data.get("Valute", {}).get(target)
        if currency_data is None:
            raise CurrencyAPIError(f"Валюта {target} не найдена в ответе API")
        nominal = currency_data.get("Nominal", 1)
        value = currency_data.get("Value")
        return nominal / value

    # Конвертация через RUB (кросс-курс)
    source_data = data.get("Valute", {}).get(source)
    target_data = data.get("Valute", {}).get(target)

    if source_data is None:
        raise CurrencyAPIError(f"Валюта {source} не найдена в ответе API")
    if target_data is None:
        raise CurrencyAPIError(f"Валюта {target} не найдена в ответе API")

    source_nominal = source_data.get("Nominal", 1)
    source_value = source_data.get("Value")
    target_nominal = target_data.get("Nominal", 1)
    target_value = target_data.get("Value")

    # Курс source к RUB
    source_to_rub = source_value / source_nominal
    # Курс target к RUB
    target_to_rub = target_value / target_nominal

    # Курс source к target
    return source_to_rub / target_to_rub


def get_currency_code_by_country(country_name: str) -> Optional[str]:
    """
    Возвращает 3-х буквенный код валюты по названию страны.

    Args:
        country_name: Название страны на русском языке
                      (например, 'Россия', 'США', 'Япония').

    Returns:
        Код валюты страны (например, 'RUB', 'USD', 'JPY'),
        или None, если страна не найдена.

    Example:
        >>> code = get_currency_code_by_country('Россия')
        >>> print(code)
        RUB
    """
    country_upper = country_name.strip().title()
    # Пробуем найти точное совпадение (с учётом регистра)
    for country, currency in COUNTRY_TO_CURRENCY.items():
        if country.lower() == country_name.lower().strip():
            return currency
    return None


def get_currency_pair_rate(currency1: str, currency2: str) -> Optional[float]:
    """
    Возвращает курс первой валюты ко второй.

    Args:
        currency1: Код первой валюты (например, 'USD').
        currency2: Код второй валюты (например, 'RUB').

    Returns:
        Курс валюты currency1 к валюте currency2, или None при ошибке.

    Raises:
        CurrencyAPIError: При ошибке подключения или неверном коде валюты.

    Example:
        >>> rate = get_currency_pair_rate('USD', 'RUB')
        >>> print(f"1 USD = {rate} RUB")
    """
    return get_rate(currency1, currency2)


def _print_usage() -> None:
    """Выводит инструкцию по использованию скрипта."""
    print("Использование:")
    print("  python currency_util.py <Страна1> <Страна2>")
    print("  python currency_util.py <Страна1> <Страна2> <сумма>")
    print()
    print("Примеры:")
    print("  python currency_util.py Россия США")
    print("  python currency_util.py Германия Япония 1000")
    print()
    print("Доступные страны:", ", ".join(sorted(COUNTRY_TO_CURRENCY.keys())[:15]), "...")


if __name__ == "__main__":
    import sys

    # Проверяем количество аргументов
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Ошибка: неверное количество аргументов.")
        _print_usage()
        sys.exit(1)

    country1 = sys.argv[1]
    country2 = sys.argv[2]

    # Получаем коды валют
    currency1 = get_currency_code_by_country(country1)
    currency2 = get_currency_code_by_country(country2)

    if currency1 is None:
        print(f"Ошибка: страна '{country1}' не найдена.")
        _print_usage()
        sys.exit(1)

    if currency2 is None:
        print(f"Ошибка: страна '{country2}' не найдена.")
        _print_usage()
        sys.exit(1)

    try:
        # Получаем курс
        rate = get_currency_pair_rate(currency1, currency2)
        if rate is None:
            print("Ошибка: не удалось получить курс валют.")
            sys.exit(1)

        print("=" * 60)
        print(f"Курс: 1 {currency1} ({country1}) = {rate:.6f} {currency2} ({country2})")

        # Если передана сумма, конвертируем
        if len(sys.argv) == 4:
            try:
                amount = float(sys.argv[3])
                if amount < 0:
                    print("Ошибка: сумма не может быть отрицательной.")
                    sys.exit(1)

                converted = amount * rate
                print(f"Сумма: {amount:,.2f} {currency1} = {converted:,.2f} {currency2}")
            except ValueError:
                print(f"Ошибка: '{sys.argv[3]}' не является корректным числом.")
                sys.exit(1)

        print("=" * 60)

    except CurrencyAPIError as e:
        print(f"Ошибка API: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)

