#!/usr/bin/env python3
"""CLI-точка входа для конвертера валют."""

import argparse
import sys
from typing import Optional

import requests
from colorama import init, Fore, Style

# Инициализация colorama для корректной работы на Windows
init(autoreset=True)

from current_api import get_rate, convert_currency

# ─── Вспомогательные функции ─────────────────────────────────────────────────


def print_error(message: str) -> None:
    """Вывести сообщение об ошибке красным цветом."""
    print(f"{Fore.RED}Ошибка: {message}{Style.RESET_ALL}")


def print_success(message: str) -> None:
    """Вывести успешное сообщение зелёным цветом."""
    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")


def print_info(message: str) -> None:
    """Вывести информационное сообщение белым цветом."""
    print(f"{Fore.WHITE}{message}{Style.RESET_ALL}")


def print_warning(message: str) -> None:
    """Вывести предупреждение жёлтым цветом."""
    print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")


# ─── Обёртки над API с обработкой ошибок ─────────────────────────────────────


def safe_get_rate(source: str, target: str) -> Optional[dict]:
    """Безопасное получение курса с обработкой ошибок.

    Args:
        source: Код исходной валюты.
        target: Код целевой валюты.

    Returns:
        dict с результатом или None в случае ошибки.
    """
    try:
        result = get_rate(source, target)
        return result
    except ValueError as e:
        print_error(str(e))
        return None
    except requests.exceptions.Timeout:
        print_error(f"Таймаут соединения. Проверьте интернет.")
        return None
    except requests.exceptions.ConnectionError:
        print_error(f"Нет соединения с сервером. Проверьте интернет.")
        return None
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "?"
        if status_code == 401:
            print_error("Неверный API-ключ. Проверьте .env")
        elif status_code == 429:
            print_error("Слишком много запросов. Подождите немного.")
        elif status_code == 404:
            print_error("Валюта не найдена. Проверьте коды валют.")
        else:
            print_error(f"Ошибка API ({status_code}): {e.response.reason if e.response else e}")
        return None
    except Exception as e:
        print_error(f"Ошибка API: {e}")
        return None


def safe_convert_currency(
    amount: float, source: str, target: str
) -> Optional[dict]:
    """Безопасная конвертация с обработкой ошибок.

    Args:
        amount: Сумма для конвертации.
        source: Код исходной валюты.
        target: Код целевой валюты.

    Returns:
        dict с результатом или None в случае ошибки.
    """
    try:
        result = convert_currency(amount, source, target)
        return result
    except ValueError as e:
        print_error(str(e))
        return None
    except requests.exceptions.Timeout:
        print_error(f"Таймаут соединения. Проверьте интернет.")
        return None
    except requests.exceptions.ConnectionError:
        print_error(f"Нет соединения с сервером. Проверьте интернет.")
        return None
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "?"
        if status_code == 401:
            print_error("Неверный API-ключ. Проверьте .env")
        elif status_code == 429:
            print_error("Слишком много запросов. Подождите немного.")
        elif status_code == 404:
            print_error("Валюта не найдена. Проверьте коды валют.")
        else:
            print_error(f"Ошибка API ({status_code}): {e.response.reason if e.response else e}")
        return None
    except Exception as e:
        print_error(f"Ошибка API: {e}")
        return None


# ─── Интерактивное меню ──────────────────────────────────────────────────────


# ─── Список популярных валют ──────────────────────────────────────────────────

POPULAR_CURRENCIES = {
    "USD": "Доллар США",
    "EUR": "Евро",
    "GBP": "Британский фунт",
    "JPY": "Японская иена",
    "RUB": "Российский рубль",
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


def show_menu() -> None:
    """Вывести основное меню программы."""
    print()
    print(f"{Fore.CYAN}{'=' * 40}")
    print(f"{Fore.CYAN}  Конвертер валют (AllRatesToday)")
    print(f"{Fore.CYAN}{'=' * 40}")
    print(f"{Fore.YELLOW}  1. Получить курс валюты")
    print(f"{Fore.YELLOW}  2. Конвертировать сумму")
    print(f"{Fore.YELLOW}  3. Показать список валют")
    print(f"{Fore.YELLOW}  4. Выход")
    print(f"{Fore.CYAN}{'=' * 40}")
    print()


def interactive_mode() -> None:
    """Запуск интерактивного режима с меню."""
    while True:
        show_menu()
        choice = input(f"{Fore.WHITE}Выберите действие (1-4): {Style.RESET_ALL}").strip()

        if choice == "1":
            get_rate_interactive()
        elif choice == "2":
            convert_interactive()
        elif choice == "3":
            show_currencies()
        elif choice == "4":
            print_success("До свидания!")
            break
        else:
            print_warning("Неверный выбор. Попробуйте снова.")


def show_currencies() -> None:
    """Показать список популярных валют."""
    print(f"\n{Fore.CYAN}--- Популярные валюты ---{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{'Код':<6} {'Название':<30}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'-' * 36}{Style.RESET_ALL}")
    
    for code, name in sorted(POPULAR_CURRENCIES.items()):
        print(f"{Fore.GREEN}{code:<6} {name:<30}{Style.RESET_ALL}")
    
    print(f"\n{Fore.WHITE}Всего: {len(POPULAR_CURRENCIES)} валют{Style.RESET_ALL}")
    print_info("Поддерживаются и другие валюты. Вводите код (например, USD, EUR, RUB).")


def get_rate_interactive() -> None:
    """Интерактивное получение курса валюты."""
    print(f"{Fore.WHITE}--- Получение курса валюты ---{Style.RESET_ALL}")
    print_info("По умолчанию исходная валюта — RUB (российский рубль).")

    source = input(f"{Fore.WHITE}Введите исходную валюту [RUB]: {Style.RESET_ALL}").strip().upper()
    if not source:
        source = "RUB"
    
    target = input(f"{Fore.WHITE}Введите целевую валюту (например, EUR,GBP): {Style.RESET_ALL}").strip().upper()

    if not source or not target:
        print_warning("Валюты не могут быть пустыми.")
        return

    result = safe_get_rate(source, target)
    if result is None:
        return

    # Ответ может быть списком (несколько валют) или одиночным объектом
    if isinstance(result, list):
        for item in result:
            rate = item.get("rate", "N/A")
            src = item.get("source", source)
            tgt = item.get("target", target)
            print_success(f"Курс 1 {src} = {rate} {tgt}")
    elif isinstance(result, dict):
        rate = result.get("rate", "N/A")
        src = result.get("source", source)
        tgt = result.get("target", target)
        print_success(f"Курс 1 {src} = {rate} {tgt}")
    else:
        print_warning("Неизвестный формат ответа от сервера.")


def convert_interactive() -> None:
    """Интерактивная конвертация суммы."""
    print(f"{Fore.WHITE}--- Конвертация суммы ---{Style.RESET_ALL}")
    print_info("По умолчанию исходная валюта — RUB (российский рубль).")

    amount_str = input(f"{Fore.WHITE}Введите сумму: {Style.RESET_ALL}").strip()
    source = input(f"{Fore.WHITE}Из какой валюты [RUB]: {Style.RESET_ALL}").strip().upper()
    if not source:
        source = "RUB"
    
    target = input(f"{Fore.WHITE}В какую валюту (например, EUR): {Style.RESET_ALL}").strip().upper()

    if not source or not target:
        print_warning("Валюты не могут быть пустыми.")
        return

    try:
        amount = float(amount_str)
    except ValueError:
        print_warning("Введите число.")
        return

    result = safe_convert_currency(amount, source, target)
    if result is None:
        return

    # API возвращает список с одним элементом
    if isinstance(result, list):
        item = result[0]
        rate = item.get("rate", "N/A")
        print_success(f"{amount} {source} = {amount * rate:.2f} {target}")
        print_info(f"Курс: 1 {source} = {rate} {target}")
    elif isinstance(result, dict):
        from_currency = result.get("from", {}).get("currency", source)
        from_amount = result.get("from", {}).get("amount", amount)
        to_currency = result.get("to", {}).get("currency", target)
        to_amount = result.get("to", {}).get("amount", "N/A")
        rate = result.get("rate", "N/A")
        print_success(f"{from_amount} {from_currency} = {to_amount} {to_currency}")
        print_info(f"Курс: 1 {from_currency} = {rate} {to_currency}")
    else:
        print_warning("Неизвестный формат ответа от сервера.")


# ─── CLI-аргументы ────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    """Парсинг аргументов командной строки.

    Returns:
        argparse.Namespace: распаршенные аргументы.
    """
    parser = argparse.ArgumentParser(
        description="Конвертер валют с использованием AllRatesToday API"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--rate",
        nargs=2,
        metavar=("SOURCE", "TARGET"),
        help="Получить курс: --rate USD EUR",
    )
    group.add_argument(
        "--convert",
        nargs=3,
        metavar=("AMOUNT", "SOURCE", "TARGET"),
        help="Конвертировать сумму: --convert 1000 USD EUR",
    )

    return parser.parse_args()


def run_cli(args: argparse.Namespace) -> None:
    """Выполнение CLI-команды.

    Args:
        args: распаршенные аргументы командной строки.
    """
    if args.rate:
        source, target = args.rate
        source = source.upper()
        target = target.upper()

        result = safe_get_rate(source, target)
        if result is None:
            sys.exit(1)

        if isinstance(result, list):
            for item in result:
                rate = item.get("rate", "N/A")
                src = item.get("source", source)
                tgt = item.get("target", target)
                print_success(f"Курс 1 {src} = {rate} {tgt}")
        elif isinstance(result, dict):
            rate = result.get("rate", "N/A")
            src = result.get("source", source)
            tgt = result.get("target", target)
            print_success(f"Курс 1 {src} = {rate} {tgt}")

    elif args.convert:
        amount_str, source, target = args.convert
        source = source.upper()
        target = target.upper()

        try:
            amount = float(amount_str)
        except ValueError:
            print_warning("Введите число.")
            sys.exit(1)

        result = safe_convert_currency(amount, source, target)
        if result is None:
            sys.exit(1)

        # API возвращает список с одним элементом
        if isinstance(result, list):
            item = result[0]
            rate = item.get("rate", "N/A")
            print_success(f"{amount} {source} = {amount * rate:.2f} {target}")
            print_info(f"Курс: 1 {source} = {rate} {target}")
        elif isinstance(result, dict):
            from_currency = result.get("from", {}).get("currency", source)
            from_amount = result.get("from", {}).get("amount", amount)
            to_currency = result.get("to", {}).get("currency", target)
            to_amount = result.get("to", {}).get("amount", "N/A")
            rate = result.get("rate", "N/A")
            print_success(f"{from_amount} {from_currency} = {to_amount} {to_currency}")
            print_info(f"Курс: 1 {from_currency} = {rate} {to_currency}")
        else:
            print_warning("Неизвестный формат ответа от сервера.")


# ─── Точка входа ──────────────────────────────────────────────────────────────


def main() -> None:
    """Главная функция — определение режима работы."""
    # Проверяем наличие CLI-аргументов
    if len(sys.argv) > 1:
        args = parse_args()
        run_cli(args)
    else:
        # Интерактивный режим
        interactive_mode()


if __name__ == "__main__":
    main()
