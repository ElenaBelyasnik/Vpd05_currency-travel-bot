def format_trip_summary(trip: dict) -> str:
    """Форматирует информацию о созданном путешествии."""
    if not trip:
        return "❌ Ошибка: путешествие не найдено"
    
    return (
        f"✅ *ПУТЕШЕСТВИЕ СОЗДАНО!*\n\n"
        f"🌍 {trip['country_from']} → {trip['country_to']}\n"
        f"💰 Начальная сумма: {trip['initial_amount_from']:.2f} {trip['currency_from']}\n"
        f"💱 Курс: 1 {trip['currency_from']} = {trip['exchange_rate']:.4f} {trip['currency_to']}\n"
        f"🔄 Получишь: {trip['initial_amount_to']:.2f} {trip['currency_to']}\n\n"
        f"💡 *Теперь просто отправляй мне суммы расходов.*"
    )


def format_balance(trip: dict, rest_from: float, rest_to: float) -> str:
    """Форматирует баланс путешествия."""
    if not trip:
        return "❌ Нет активного путешествия"
    
    initial_from = trip['initial_amount_from']
    initial_to = trip['initial_amount_to']
    expense_from = initial_from - rest_from
    expense_to = initial_to - rest_to
    
    return (
        f"🌍 *Активное путешествие:* {trip['country_from']} → {trip['country_to']}\n\n"
        f"💳 *БАЛАНС ПУТЕШЕСТВИЯ*\n"
        f"{'=' * 30}\n\n"
        f"*{trip['currency_from']} ({trip['currency_from']}):*\n"
        f"  Начальная сумма: {initial_from:.2f}\n"
        f"  Расход:          {expense_from:.2f}\n"
        f"  Остаток:         {rest_from:.2f}\n\n"
        f"*{trip['currency_to']} ({trip['currency_to']}):*\n"
        f"  Начальная сумма: {initial_to:.2f}\n"
        f"  Расход:          {expense_to:.2f}\n"
        f"  Остаток:         {rest_to:.2f}\n\n"
        f"💱 Курс: 1 {trip['currency_from']} = {trip['exchange_rate']:.4f} {trip['currency_to']}"
    )


def format_trip_list(trips: list) -> str:
    """Форматирует список путешествий."""
    if not trips:
        return "📭 У вас нет ни одного путешествия"
    
    msg = "📋 *Ваши путешествия:*\n\n"
    for t in trips:
        active = " ✅ АКТИВНО" if t['is_active'] else ""
        msg += (
            f"*ID:{t['id']}* {t['country_from']} → {t['country_to']}\n"
            f"  {t['initial_amount_from']:.2f} {t['currency_from']} "
            f"({t['initial_amount_to']:.2f} {t['currency_to']}){active}\n"
        )
    return msg


def format_history(expenses: list, trip: dict) -> str:
    """Форматирует историю расходов."""
    if not expenses:
        return "📭 История расходов пуста"
    
    msg = f"📜 *История расходов* ({trip['country_from']} → {trip['country_to']})\n\n"
    for exp in expenses:
        date_str = exp['created_at'][:16] if exp['created_at'] else ''
        desc = exp['description'] or ''
        msg += (
            f"🕒 {date_str}\n"
            f"  {exp['amount_to']:.2f} {trip['currency_to']} → "
            f"{exp['amount_from']:.2f} {trip['currency_from']}\n"
            f"  📝 {desc}\n\n"
        )
    return msg