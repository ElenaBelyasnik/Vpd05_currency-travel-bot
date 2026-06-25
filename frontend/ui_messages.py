#!/usr/bin/env python3
"""
Модуль с функциями для цветного вывода в CLI.
"""

from colorama import Fore, Style, Back


def print_header(text: str) -> None:
    """Печатает заголовок."""
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.CYAN}{text.center(60)}")
    print(f"{Fore.CYAN}{'=' * 60}\n")


def print_success(text: str) -> None:
    """Печатает сообщение об успехе."""
    print(f"{Fore.GREEN}✅ {text}")


def print_error(text: str) -> None:
    """Печатает сообщение об ошибке."""
    print(f"{Fore.RED}❌ {text}")


def print_info(text: str) -> None:
    """Печатает информационное сообщение."""
    print(f"{Fore.YELLOW}ℹ️ {text}")


def print_balance(trip: dict, rest_from: float = None, rest_to: float = None) -> None:
    """Печатает баланс путешествия с расчётом остатка."""
    if not trip:
        print_error("Путешествие не найдено")
        return

    # Если остаток не передан — считаем через SUM
    if rest_from is None or rest_to is None:
        print_error("Для отображения баланса нужны рассчитанные остатки")
        return

    # Выводим информацию о путешествии
    print(f"\n{Fore.CYAN}Активное путешествие: {trip['country_from']} → {trip['country_to']}")

    currency_from = trip.get('currency_from', '')
    currency_to = trip.get('currency_to', '')
    rate = trip.get('exchange_rate', 1)
    initial_from = trip.get('initial_amount_from', 0)
    initial_to = trip.get('initial_amount_to', 0)
    
    expense_from = initial_from - rest_from
    expense_to = initial_to - rest_to

    print(f"\n{Fore.CYAN}💳 БАЛАНС ПУТЕШЕСТВИЯ")
    print(f"{Fore.CYAN}{'=' * 40}")

    print(f"\n{Fore.WHITE}{currency_from} ({currency_from}):")
    print(f"  {Fore.WHITE}Начальная сумма: {initial_from:>10.2f} {currency_from}")
    print(f"  {Fore.WHITE}Расход:          {expense_from:>10.2f} {currency_from}")
    print(f"  {Fore.WHITE}Остаток:         {rest_from:>10.2f} {currency_from}")

    print(f"\n{Fore.WHITE}{currency_to} ({currency_to}):")
    print(f"  {Fore.WHITE}Начальная сумма: {initial_to:>10.2f} {currency_to}")
    print(f"  {Fore.WHITE}Расход:          {expense_to:>10.2f} {currency_to}")
    print(f"  {Fore.WHITE}Остаток:         {rest_to:>10.2f} {currency_to}")

    print(f"\n{Fore.MAGENTA}Курс: 1 {currency_from} = {rate:.4f} {currency_to}")


def print_trip_summary(trip: dict) -> None:
    """Печатает красивое резюме после создания путешествия."""
    if not trip:
        return

    print(f"\n{Fore.GREEN}{'=' * 60}")
    print(f"{Fore.GREEN}  ✅ ПУТЕШЕСТВИЕ СОЗДАНО!")
    print(f"{Fore.GREEN}{'=' * 60}")
    print(f"\n{Fore.WHITE}  {trip['country_from']} → {trip['country_to']}!")
    print(f"  {Fore.WHITE}Начальная сумма: {trip['initial_amount_from']:.2f} {trip['currency_from']}")
    print(f"  {Fore.WHITE}Курс: 1 {trip['currency_from']} = {trip['exchange_rate']:.4f} {trip['currency_to']}")
    print(f"  {Fore.WHITE}Получишь: {trip['initial_amount_to']:.2f} {trip['currency_to']}")
    print(f"\n{Fore.YELLOW}  💡 Теперь просто отправляй мне суммы расходов и я буду их учитывать.")
    print(f"{Fore.GREEN}{'=' * 60}\n")


def print_trip(trip: dict, show_active: bool = False) -> None:
    """Печатает информацию о путешествии."""
    if not trip:
        return

    active_text = f" {Fore.GREEN}✅ АКТИВНО" if trip.get('is_active') and show_active else ""
    print(f"  {Fore.WHITE}ID={trip['id']}: {trip['country_from']} → {trip['country_to']}  "
          f"{trip['initial_amount_from']:.2f} {trip['currency_from']}  "
          f"({trip['initial_amount_to']:.2f} {trip['currency_to']}){active_text}")


def print_supported_countries(countries: list) -> None:
    """Печатает список поддерживаемых стран."""
    print(f"\n{Fore.CYAN}Доступные страны (поддерживаемые API):")
    for i in range(0, len(countries), 5):
        print(f"  {Fore.WHITE}{', '.join(countries[i:i+5])}")

def get_supported_countries() -> list:
    """Возвращает список стран, поддерживаемых API."""
    # Импортируем здесь, чтобы избежать циклических импортов
    from convert_currency.currency_util import CURRENCIES, COUNTRY_TO_CURRENCY
    supported = []
    for country, code in COUNTRY_TO_CURRENCY.items():
        if code in CURRENCIES:
            supported.append(country)
    return sorted(supported)


def get_valid_country(prompt: str, default: str = None) -> str:
    """Запрашивает страну и проверяет поддержку. Если default задан и пользователь нажал Enter — возвращает default."""
    supported = get_supported_countries()
    while True:
        # Изменённая строка — добавлена подсказка с default
        if default:
            user_input = input(f"{Fore.YELLOW}{prompt} (по умолчанию {default} - нажмите Enter): {Fore.WHITE}").strip()
        else:
            user_input = input(f"{Fore.YELLOW}{prompt}: {Fore.WHITE}").strip()
        
        # Если пользователь нажал Enter и есть default
        if not user_input and default:
            if default in supported:
                print_info(f"Выбрана страна по умолчанию: {default}")
                return default
            else:
                print_error(f"Страна по умолчанию '{default}' не поддерживается API")
                continue
        
        if not user_input:
            print_error("Название страны не может быть пустым")
            continue
            
        if user_input in supported:
            return user_input
        
        print_error(f"Страна '{user_input}' не найдена или не поддерживается API")
        print_supported_countries(supported)


def get_valid_amount(prompt: str) -> float:
    """Запрашивает сумму и проверяет, что это число > 0."""
    from colorama import Fore
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