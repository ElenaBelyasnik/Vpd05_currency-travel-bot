from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from backend.trip_service import get_supported_countries


def get_country_flag(country_name: str) -> str:
    """Возвращает эмодзи-флаг для страны (если есть)."""
    flags = {
        "Россия": "🇷🇺", "США": "🇺🇸", "Германия": "🇩🇪",
        "Франция": "🇫🇷", "Италия": "🇮🇹", "Турция": "🇹🇷",
        "Великобритания": "🇬🇧", "Англия": "🇬🇧", "Япония": "🇯🇵",
        "Китай": "🇨🇳", "Швейцария": "🇨🇭", "Канада": "🇨🇦",
        "Австралия": "🇦🇺", "Индия": "🇮🇳", "Бразилия": "🇧🇷",
        "Южная Корея": "🇰🇷", "Корея": "🇰🇷", "Мексика": "🇲🇽",
        "Сингапур": "🇸🇬", "ЮАР": "🇿🇦", "Новая Зеландия": "🇳🇿",
        "Швеция": "🇸🇪", "Норвегия": "🇳🇴", "Дания": "🇩🇰",
        "Польша": "🇵🇱", "Таиланд": "🇹🇭", "Индонезия": "🇮🇩",
        "ОАЭ": "🇦🇪", "Саудовская Аравия": "🇸🇦",
        "Евросоюз": "🇪🇺", "Европейский Союз": "🇪🇺",
        "Австрия": "🇦🇹", "Бельгия": "🇧🇪", "Болгария": "🇧🇬",
        "Венгрия": "🇭🇺", "Греция": "🇬🇷", "Ирландия": "🇮🇪",
        "Испания": "🇪🇸", "Кипр": "🇨🇾", "Латвия": "🇱🇻",
        "Литва": "🇱🇹", "Люксембург": "🇱🇺", "Мальта": "🇲🇹",
        "Нидерланды": "🇳🇱", "Португалия": "🇵🇹", "Румыния": "🇷🇴",
        "Словакия": "🇸🇰", "Словения": "🇸🇮", "Финляндия": "🇫🇮",
        "Хорватия": "🇭🇷", "Чехия": "🇨🇿", "Чешская Республика": "🇨🇿",
        "Эстония": "🇪🇪"
    }
    return flags.get(country_name, "🌍")


def main_menu_keyboard():
    """Главное меню с inline-кнопками."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Создать путешествие", callback_data="create_trip"),
        InlineKeyboardButton("📋 Мои путешествия", callback_data="my_trips"),
        InlineKeyboardButton("💰 Баланс", callback_data="balance"),
        InlineKeyboardButton("📜 История расходов", callback_data="history"),
        InlineKeyboardButton("📊 Изменить курс", callback_data="change_rate"),
        InlineKeyboardButton("🗑 Очистить данные", callback_data="clear_data"),
        InlineKeyboardButton("❓ Помощь", callback_data="help")
    )
    return keyboard


def back_to_menu_keyboard():
    """Клавиатура с одной кнопкой 'Назад'."""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))
    return keyboard


def country_choice_keyboard():
    """Клавиатура для выбора страны отправления."""
    keyboard = InlineKeyboardMarkup(row_width=3)
    countries = get_supported_countries()
    for i, country in enumerate(countries):
        keyboard.add(
            InlineKeyboardButton(
                f"{get_country_flag(country)} {country}",
                callback_data=f"c_{i}"
            )
        )
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))
    return keyboard


def countries_list_keyboard():
    """Клавиатура для выбора страны назначения."""
    keyboard = InlineKeyboardMarkup(row_width=3)
    countries = get_supported_countries()
    for i, country in enumerate(countries):
        keyboard.add(
            InlineKeyboardButton(
                f"{get_country_flag(country)} {country}",
                callback_data=f"c_{i}"
            )
        )
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))
    return keyboard