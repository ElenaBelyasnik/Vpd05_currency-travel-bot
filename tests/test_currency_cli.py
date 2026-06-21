"""
CLI-интерфейс для тестирования модуля currency_util.
"""

import sys
import os

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from convert_currency.currency_util import (
    CURRENCIES,
    COUNTRY_TO_CURRENCY,
    CurrencyAPIError,
    get_currency_code_by_country,
    get_currency_pair_rate,
)


def print_currencies_and_countries() -> None:
    """Выводит список всех доступных валют и стран."""
    print("\n" + "=" * 60)
    print("ДОСТУПНЫЕ ВАЛЮТЫ")
    print("=" * 60)
    for code, name in sorted(CURRENCIES.items()):
        print(f"  {code:6} — {name}")

    print("\n" + "=" * 60)
    print("ДОСТУПНЫЕ СТРАНЫ")
    print("=" * 60)
    for country in sorted(COUNTRY_TO_CURRENCY.keys()):
        currency_code = COUNTRY_TO_CURRENCY[country]
        currency_name = CURRENCIES.get(currency_code, "Неизвестно")
        print(f"  {country:30} — {currency_code} ({currency_name})")
    print()


def get_currency_ratio() -> None:
    """
    Запрашивает названия стран и сумму,
    выводит курс и конвертированную сумму.
    """
    print("\n" + "=" * 60)
    print("СООТНОШЕНИЕ КУРСОВ ВАЛЮТ")
    print("=" * 60)

    # Запрос страны 1
    country1 = input("\nВведите название первой страны (например, 'Россия'): ").strip()
    if not country1:
        print("Ошибка: название страны не может быть пустым.")
        return

    # Запрос страны 2
    country2 = input("Введите название второй страны (например, 'США'): ").strip()
    if not country2:
        print("Ошибка: название страны не может быть пустым.")
        return

    # Запрос суммы
    amount_str = input(f"Введите сумму в валюте страны '{country1}': ").strip()
    if not amount_str:
        print("Ошибка: сумма не может быть пустой.")
        return

    try:
        amount = float(amount_str)
        if amount < 0:
            print("Ошибка: сумма не может быть отрицательной.")
            return
    except ValueError:
        print("Ошибка: введите корректное числовое значение.")
        return

    # Получаем коды валют
    currency1 = get_currency_code_by_country(country1)
    currency2 = get_currency_code_by_country(country2)

    if currency1 is None:
        print(f"Ошибка: страна '{country1}' не найдена.")
        print("Доступные страны:", ", ".join(sorted(COUNTRY_TO_CURRENCY.keys())[:10]), "...")
        return

    if currency2 is None:
        print(f"Ошибка: страна '{country2}' не найдена.")
        print("Доступные страны:", ", ".join(sorted(COUNTRY_TO_CURRENCY.keys())[:10]), "...")
        return

    # Получаем курс
    try:
        rate = get_currency_pair_rate(currency1, currency2)
        if rate is None:
            print("Ошибка: не удалось получить курс валют.")
            return

        converted_amount = amount * rate

        print("\n" + "-" * 60)
        print("РЕЗУЛЬТАТ")
        print("-" * 60)
        print(f"Страна 1: {country1} ({currency1})")
        print(f"Страна 2: {country2} ({currency2})")
        print(f"Курс: 1 {currency1} = {rate:.6f} {currency2}")
        print(f"Сумма: {amount:,.2f} {currency1} = {converted_amount:,.2f} {currency2}")
        print("-" * 60)

    except CurrencyAPIError as e:
        print(f"Ошибка API: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")


def print_menu() -> None:
    """Выводит главное меню."""
    print("\n" + "=" * 60)
    print("МЕНЮ")
    print("=" * 60)
    print("1. Список валют и стран")
    print("2. Соотношение курсов валют")
    print("3. Выход")
    print("=" * 60)


def main() -> None:
    """Основной цикл CLI-интерфейса."""
    print("\n" + "=" * 60)
    print("КОНВЕРТЕР ВАЛЮТ ЦБ РФ")
    print("=" * 60)

    while True:
        print_menu()
        choice = input("Выберите пункт меню (1-3): ").strip()

        if choice == "1":
            print_currencies_and_countries()
        elif choice == "2":
            get_currency_ratio()
        elif choice == "3":
            print("\nДо свидания!")
            break
        else:
            print("\nОшибка: введите число от 1 до 3.")


if __name__ == "__main__":
    main()
