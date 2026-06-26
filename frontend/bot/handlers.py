import logging
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from backend.database import Database
from backend.trip_service import (
    get_user_id, create_trip, get_active_trip, get_all_trips,
    get_trip_rest, add_expense, switch_trip, change_rate,
    clear_all_data, get_supported_countries
)
from frontend.bot.states import TravelStates
from frontend.bot.keyboards import (
    main_menu_keyboard, back_to_menu_keyboard,
    country_choice_keyboard, countries_list_keyboard
)
from frontend.bot.formatters import (
    format_trip_summary, format_balance, format_trip_list, format_history
)


def register_handlers(bot, db, USER_ID):
    """Регистрирует все обработчики бота."""
    print("🔍 [REGISTER] Начало регистрации хендлеров")

    # Простой словарь состояний вместо FSM-хранилища
    user_states = {}  # {chat_id: state}
    user_data = {}    # {chat_id: {country_from, country_to, rate, ...}}

    def safe_send_message(chat_id, text, reply_markup=None, parse_mode=None, max_retries=3):
        """Отправка сообщения с повторными попытками при таймауте."""
        for attempt in range(max_retries):
            try:
                kwargs = {"chat_id": chat_id, "text": text}
                if reply_markup:
                    kwargs["reply_markup"] = reply_markup
                if parse_mode:
                    kwargs["parse_mode"] = parse_mode
                return bot.send_message(**kwargs)
            except Exception as e:
                print(f"⚠️ [SEND] Попытка {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"❌ [SEND] Не удалось отправить сообщение: {e}")
                    return None

    def safe_delete_message(chat_id, message_id, max_retries=3):
        """Удаление сообщения с повторными попытками."""
        for attempt in range(max_retries):
            try:
                return bot.delete_message(chat_id, message_id)
            except Exception as e:
                print(f"⚠️ [DELETE] Попытка {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"❌ [DELETE] Не удалось удалить сообщение: {e}")
                    return None

    def set_state(chat_id, state):
        user_states[chat_id] = state

    def get_state(chat_id):
        return user_states.get(chat_id)

    def clear_state(chat_id):
        user_states.pop(chat_id, None)
        user_data.pop(chat_id, None)

    def get_data(chat_id):
        if chat_id not in user_data:
            user_data[chat_id] = {}
        return user_data[chat_id]

    # ==================== КОМАНДЫ ====================

    @bot.message_handler(commands=['start'])
    def cmd_start(message):
        print(f"🔍 [START] Получено от user_id={message.from_user.id}")
        try:
            safe_send_message(
                message.chat.id,
                "👋 *Привет! Я твой финансовый помощник для путешествий!*\n\n"
                "Я помогу тебе управлять бюджетом в поездках:\n"
                "• Создавать путешествия\n"
                "• Учитывать расходы\n"
                "• Отслеживать баланс\n"
                "• Переключаться между поездками\n\n"
                "⬇️ *Выбери действие в меню ниже:*",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"❌ [START] Ошибка: {e}")
            import traceback
            traceback.print_exc()

    @bot.message_handler(commands=['newtrip'])
    def cmd_newtrip(message):
        print("🔍 [NEWTRIP] Команда /newtrip — запуск создания путешествия")
        safe_delete_message(message.chat.id, message.message_id)
        
        active = get_active_trip(db, USER_ID)
        if active:
            safe_send_message(
                message.chat.id,
                f"⚠️ У тебя уже есть активное путешествие:\n"
                f"{active['country_from']} → {active['country_to']}\n\n"
                f"При создании нового оно станет активным автоматически.\n"
                f"Продолжить?",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("✅ Да, создать", callback_data="create_force"),
                    InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")
                )
            )
        else:
            safe_send_message(
                message.chat.id,
                "🌍 *Создание нового путешествия*\n\n"
                "Выберите страну отправления:",
                reply_markup=country_choice_keyboard(),
                parse_mode="Markdown"
            )
        set_state(message.chat.id, TravelStates.WAITING_COUNTRY_FROM)

    # ==================== CALLBACK: НАВИГАЦИЯ ====================

    @bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
    def callback_back_to_menu(call):
        safe_delete_message(call.message.chat.id, call.message.message_id)
        safe_send_message(
            call.message.chat.id,
            "⬇️ *Главное меню:*",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data == "help")
    def callback_help(call):
        safe_delete_message(call.message.chat.id, call.message.message_id)
        safe_send_message(
            call.message.chat.id,
            "❓ *Помощь*\n\n"
            "🔹 *Создать путешествие* — укажи страну отправления, страну назначения и бюджет.\n"
            "🔹 *Мои путешествия* — список всех поездок, можно переключить активную.\n"
            "🔹 *Баланс* — текущий остаток в двух валютах.\n"
            "🔹 *История расходов* — все твои траты.\n"
            "🔹 *Изменить курс* — обновить курс вручную.\n"
            "🔹 *Очистить данные* — удалить все путешествия и расходы (осторожно!).\n\n"
            "💡 *Просто отправляй число* — и я учту его как расход в активном путешествии.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="Markdown"
        )

    # ==================== CALLBACK: СОЗДАНИЕ ПУТЕШЕСТВИЯ ====================

    @bot.callback_query_handler(func=lambda call: call.data == "create_trip")
    def callback_create_trip(call):
        print("🔍 [CALLBACK] create_trip вызван")
        safe_delete_message(call.message.chat.id, call.message.message_id)
        
        active = get_active_trip(db, USER_ID)
        if active:
            safe_send_message(
                call.message.chat.id,
                f"⚠️ У тебя уже есть активное путешествие:\n"
                f"{active['country_from']} → {active['country_to']}\n\n"
                f"При создании нового оно станет активным автоматически.\n"
                f"Продолжить?",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("✅ Да, создать", callback_data="create_force"),
                    InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")
                )
            )
        else:
            safe_send_message(
                call.message.chat.id,
                "🌍 *Создание нового путешествия*\n\n"
                "Выберите страну отправления:",
                reply_markup=country_choice_keyboard(),
                parse_mode="Markdown"
            )
        set_state(call.message.chat.id, TravelStates.WAITING_COUNTRY_FROM)

    @bot.callback_query_handler(func=lambda call: call.data == "create_force")
    def callback_create_force(call):
        print("🔍 [CALLBACK] create_force вызван")
        safe_delete_message(call.message.chat.id, call.message.message_id)
        safe_send_message(
            call.message.chat.id,
            "🌍 *Создание нового путешествия*\n\n"
            "Выберите страну отправления:",
            reply_markup=country_choice_keyboard(),
            parse_mode="Markdown"
        )
        set_state(call.message.chat.id, TravelStates.WAITING_COUNTRY_FROM)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("c_"))
    def callback_set_country(call):
        """Обработка выбора страны из кнопки."""
        print("🔍 [CALLBACK] set_country НАЧАЛО")
        print(f"🔍 [CALLBACK] call.data: {call.data}")
        try:
            country_index = int(call.data.split("_")[1])
            print(f"🔍 [CALLBACK] Индекс страны: {country_index}")
            
            supported = get_supported_countries()
            if country_index < 0 or country_index >= len(supported):
                raise ValueError(f"Неверный индекс страны: {country_index}")
            country = supported[country_index]
            print(f"🔍 [CALLBACK] Страна: {country}")
            
            safe_delete_message(call.message.chat.id, call.message.message_id)
            current_state = get_state(call.message.chat.id)
            print(f"🔍 [CALLBACK] Состояние: {current_state}")
            
            data = get_data(call.message.chat.id)
            next_state = None
            
            if 'WAITING_COUNTRY_FROM' in str(current_state):
                data['country_from'] = country
                print(f"🔍 [CALLBACK] Сохранена страна отправления: {country}")
                
                safe_send_message(
                    call.message.chat.id,
                    f"✅ Страна отправления: {country}\n\n"
                    "Теперь выберите страну назначения:",
                    reply_markup=countries_list_keyboard()
                )
                next_state = TravelStates.WAITING_COUNTRY_TO
                
            elif 'WAITING_COUNTRY_TO' in str(current_state):
                country_from = data.get('country_from')
                if not country_from:
                    raise ValueError("Потеряны данные о стране отправления")

                data['country_to'] = country
                print(f"🔍 [CALLBACK] Сохранена страна назначения: {country}")

                try:
                    from convert_currency.currency_util import get_rate, COUNTRY_TO_CURRENCY
                    currency_from = COUNTRY_TO_CURRENCY.get(country_from)
                    currency_to = COUNTRY_TO_CURRENCY.get(country)
                    
                    if not currency_from or not currency_to:
                        raise ValueError(f"Не найдены валюты для {country_from} или {country}")

                    rate = get_rate(currency_from, currency_to)
                    if rate is None:
                        raise ValueError("Не удалось получить курс валют")

                    print(f"🔍 [CALLBACK] Курс: 1 {currency_from} = {rate:.4f} {currency_to}")
                    
                    safe_send_message(
                        call.message.chat.id,
                        f"💱 Курс: 1 {currency_from} = {rate:.4f} {currency_to}\n\n"
                        f"💰 Введите сумму в валюте отправления ({currency_from}):",
                        reply_markup=back_to_menu_keyboard()
                    )
                    
                    data['rate'] = rate
                    data['currency_from'] = currency_from
                    data['currency_to'] = currency_to
                    
                    next_state = TravelStates.WAITING_BUDGET
                    
                except Exception as e:
                    print(f"🔍 [CALLBACK] Ошибка при расчете курса: {e}")
                    safe_send_message(
                        call.message.chat.id,
                        f"❌ Ошибка расчета курса: {e}",
                        reply_markup=back_to_menu_keyboard()
                    )
                    clear_state(call.message.chat.id)
                    return
            else:
                print(f"🔍 [CALLBACK] Неожиданное состояние: {current_state}")
                safe_send_message(
                    call.message.chat.id,
                    "⚠️ Произошла ошибка состояния. Начните создание заново.",
                    reply_markup=back_to_menu_keyboard()
                )
                clear_state(call.message.chat.id)
                return
            
            # Устанавливаем состояние
            if next_state:
                set_state(call.message.chat.id, next_state)
                print(f"🔍 [CALLBACK] Состояние изменено на {next_state}")
            
        except Exception as e:
            print(f"🔍 [CALLBACK] КРИТИЧЕСКАЯ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            safe_send_message(
                call.message.chat.id,
                "❌ Произошла ошибка. Попробуйте позже.",
                reply_markup=back_to_menu_keyboard()
            )

    # ==================== STATE HANDLERS ====================

    @bot.message_handler(state=TravelStates.WAITING_COUNTRY_FROM)
    def handle_country_from(message):
        print(f"🔍 [FROM] Получено сообщение: {message.text}")
        country_from = message.text.strip()
        supported = get_supported_countries()
        
        if country_from not in supported:
            safe_send_message(
                message.chat.id,
                f"❌ Страна '{country_from}' не найдена.\n\n"
                "Попробуйте выбрать из списка:",
                reply_markup=country_choice_keyboard()
            )
            return
        
        data = get_data(message.chat.id)
        data['country_from'] = country_from
        
        safe_send_message(
            message.chat.id,
            f"✅ Страна отправления: {country_from}\n\n"
            "Теперь выберите страну назначения:",
            reply_markup=countries_list_keyboard()
        )
        set_state(message.chat.id, TravelStates.WAITING_COUNTRY_TO)

    @bot.message_handler(state=TravelStates.WAITING_COUNTRY_TO)
    def handle_country_to(message):
        print(f"🔍 [TO] Получено сообщение: {message.text}")
        country_to = message.text.strip()
        supported = get_supported_countries()
        
        if country_to not in supported:
            safe_send_message(
                message.chat.id,
                f"❌ Страна '{country_to}' не найдена.\n\n"
                "Попробуйте выбрать из списка:",
                reply_markup=countries_list_keyboard()
            )
            return
        
        data = get_data(message.chat.id)
        country_from = data.get('country_from')
        if not country_from:
            safe_send_message(
                message.chat.id,
                "❌ Ошибка: страна отправления не найдена. Начните заново.",
                reply_markup=back_to_menu_keyboard()
            )
            clear_state(message.chat.id)
            return
        data['country_to'] = country_to
        
        try:
            from convert_currency.currency_util import get_rate, COUNTRY_TO_CURRENCY
            currency_from = COUNTRY_TO_CURRENCY[country_from]
            currency_to = COUNTRY_TO_CURRENCY[country_to]
            rate = get_rate(currency_from, currency_to)
            
            safe_send_message(
                message.chat.id,
                f"💱 Курс: 1 {currency_from} = {rate:.4f} {currency_to}\n\n"
                f"💰 Введите сумму в валюте отправления ({currency_from}):",
                reply_markup=back_to_menu_keyboard()
            )
            data['rate'] = rate
            data['currency_from'] = currency_from
            data['currency_to'] = currency_to
            
            set_state(message.chat.id, TravelStates.WAITING_BUDGET)
        except Exception as e:
            safe_send_message(
                message.chat.id,
                f"❌ Ошибка при получении курса: {e}\n\n"
                "Попробуйте позже.",
                reply_markup=back_to_menu_keyboard()
            )
            clear_state(message.chat.id)
            return
        
    @bot.message_handler(state=TravelStates.WAITING_BUDGET)
    def handle_budget(message):
        print(f"🔍 [BUDGET] Получено сообщение: {message.text}")
        print(f"🔍 [BUDGET] state_handler вызван для user={message.from_user.id}, chat={message.chat.id}")
        try:
            budget = float(message.text.strip().replace(',', '.'))
            if budget <= 0:
                raise ValueError("Сумма должна быть > 0")
        except ValueError:
            safe_send_message(
                message.chat.id,
                "❌ Введите корректное число (например, 1000 или 1000.50):",
                reply_markup=back_to_menu_keyboard()
            )
            return
        
        data = get_data(message.chat.id)
        country_from = data.get('country_from')
        country_to = data.get('country_to')
        rate = data.get('rate')
        currency_from = data.get('currency_from')
        currency_to = data.get('currency_to')
        print(f"🔍 [BUDGET] Данные из FSM: country_from={country_from}, country_to={country_to}, rate={rate}")
        
        if not all([country_from, country_to, rate, currency_from, currency_to]):
            safe_send_message(
                message.chat.id,
                f"❌ Ошибка: потеряны данные. Начните создание заново. country_from={country_from}, country_to={country_to}",
                reply_markup=back_to_menu_keyboard()
            )
            clear_state(message.chat.id)
            return
        
        try:
            trip = create_trip(db, USER_ID, country_from, country_to, budget)
            if trip:
                safe_delete_message(message.chat.id, message.message_id)
                safe_send_message(
                    message.chat.id,
                    format_trip_summary(trip),
                    reply_markup=main_menu_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                safe_send_message(
                    message.chat.id,
                    "❌ Не удалось создать путешествие. Попробуйте позже.",
                    reply_markup=back_to_menu_keyboard()
                )
        except Exception as e:
            safe_send_message(
                message.chat.id,
                f"❌ Ошибка: {e}",
                reply_markup=back_to_menu_keyboard()
            )
        clear_state(message.chat.id)

    # ==================== CALLBACK: ОСТАЛЬНЫЕ ФУНКЦИИ ====================

    @bot.callback_query_handler(func=lambda call: call.data == "my_trips")
    def callback_my_trips(call):
        print("🔍 [CALLBACK] my_trips вызван")
        safe_delete_message(call.message.chat.id, call.message.message_id)
        trips = get_all_trips(db, USER_ID)
        if not trips:
            safe_send_message(
                call.message.chat.id,
                "📭 У вас нет ни одного путешествия.\n\n"
                "Создайте новое через главное меню.",
                reply_markup=back_to_menu_keyboard()
            )
            return
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        for t in trips:
            active = " ✅" if t['is_active'] else ""
            keyboard.add(
                InlineKeyboardButton(
                    f"{t['country_from']} → {t['country_to']} (ID:{t['id']}){active}",
                    callback_data=f"switch_trip_{t['id']}"
                )
            )
        keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))
        
        safe_send_message(
            call.message.chat.id,
            format_trip_list(trips),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("switch_trip_"))
    def callback_switch_trip(call):
        print(f"🔍 [CALLBACK] switch_trip вызван: {call.data}")
        trip_id = int(call.data.split("_")[2])
        try:
            trip = switch_trip(db, USER_ID, trip_id)
            rest = get_trip_rest(db, trip['id'])
            safe_delete_message(call.message.chat.id, call.message.message_id)
            safe_send_message(
                call.message.chat.id,
                f"✅ Активное путешествие переключено!\n\n"
                f"{format_balance(trip, rest['rest_from'], rest['rest_to'])}",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as e:
            safe_send_message(
                call.message.chat.id,
                f"❌ Ошибка: {e}",
                reply_markup=back_to_menu_keyboard()
            )

    @bot.callback_query_handler(func=lambda call: call.data == "balance")
    def callback_balance(call):
        print("🔍 [CALLBACK] balance вызван")
        safe_delete_message(call.message.chat.id, call.message.message_id)
        trip = get_active_trip(db, USER_ID)
        if not trip:
            safe_send_message(
                call.message.chat.id,
                "❌ Нет активного путешествия.\n\n"
                "Создайте новое через главное меню.",
                reply_markup=back_to_menu_keyboard()
            )
            return
        rest = get_trip_rest(db, trip['id'])
        safe_send_message(
            call.message.chat.id,
            format_balance(trip, rest['rest_from'], rest['rest_to']),
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data == "history")
    def callback_history(call):
        print("🔍 [CALLBACK] history вызван")
        safe_delete_message(call.message.chat.id, call.message.message_id)
        trip = get_active_trip(db, USER_ID)
        if not trip:
            safe_send_message(
                call.message.chat.id,
                "❌ Нет активного путешествия.\n\n"
                "Создайте новое через главное меню.",
                reply_markup=back_to_menu_keyboard()
            )
            return
        expenses = db.fetch_all(
            "SELECT * FROM expenses WHERE trip_id = ? ORDER BY created_at DESC LIMIT 20",
            (trip['id'],)
        )
        safe_send_message(
            call.message.chat.id,
            format_history(expenses, trip),
            reply_markup=back_to_menu_keyboard(),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data == "change_rate")
    def callback_change_rate(call):
        print("🔍 [CALLBACK] change_rate вызван")
        safe_delete_message(call.message.chat.id, call.message.message_id)
        trip = get_active_trip(db, USER_ID)
        if not trip:
            safe_send_message(
                call.message.chat.id,
                "❌ Нет активного путешествия.\n\n"
                "Создайте новое через главное меню.",
                reply_markup=back_to_menu_keyboard()
            )
            return
        safe_send_message(
            call.message.chat.id,
            f"📊 *Изменение курса*\n\n"
            f"Текущий курс: 1 {trip['currency_from']} = {trip['exchange_rate']:.4f} {trip['currency_to']}\n\n"
            f"Введите новый курс (например, 0.0120):",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="Markdown"
        )
        set_state(call.message.chat.id, TravelStates.WAITING_NEW_RATE)

    @bot.message_handler(state=TravelStates.WAITING_NEW_RATE)
    def handle_new_rate(message):
        print(f"🔍 [RATE] Получено сообщение: {message.text}")
        try:
            new_rate = float(message.text.strip().replace(',', '.'))
            if new_rate <= 0:
                raise ValueError("Курс должен быть > 0")
        except ValueError:
            safe_send_message(
                message.chat.id,
                "❌ Введите корректное число (например, 0.0120):",
                reply_markup=back_to_menu_keyboard()
            )
            return
        
        trip = get_active_trip(db, USER_ID)
        if not trip:
            safe_send_message(
                message.chat.id,
                "❌ Нет активного путешествия.",
                reply_markup=back_to_menu_keyboard()
            )
            clear_state(message.chat.id)
            return
        
        try:
            trip_updated = change_rate(db, trip['id'], new_rate)
            rest = get_trip_rest(db, trip_updated['id'])
            safe_delete_message(message.chat.id, message.message_id)
            safe_send_message(
                message.chat.id,
                f"✅ Курс обновлён!\n\n"
                f"{format_balance(trip_updated, rest['rest_from'], rest['rest_to'])}",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as e:
            safe_send_message(
                message.chat.id,
                f"❌ Ошибка: {e}",
                reply_markup=back_to_menu_keyboard()
            )
        clear_state(message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "clear_data")
    def callback_clear_data(call):
        print("🔍 [CALLBACK] clear_data вызван")
        safe_delete_message(call.message.chat.id, call.message.message_id)
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("⚠️ ДА, удалить всё", callback_data="clear_confirm"),
            InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")
        )
        safe_send_message(
            call.message.chat.id,
            "⚠️ *ВНИМАНИЕ!*\n\n"
            "Это действие удалит все путешествия и расходы.\n"
            "Данные пользователей будут сохранены.\n\n"
            "Ты уверен(а)?",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data == "clear_confirm")
    def callback_clear_confirm(call):
        print("🔍 [CALLBACK] clear_confirm вызван")
        safe_delete_message(call.message.chat.id, call.message.message_id)
        try:
            clear_all_data(db)
            safe_send_message(
                call.message.chat.id,
                "🗑 Все данные успешно удалены!",
                reply_markup=main_menu_keyboard()
            )
        except Exception as e:
            safe_send_message(
                call.message.chat.id,
                f"❌ Ошибка при очистке: {e}",
                reply_markup=back_to_menu_keyboard()
            )

    # ==================== ОБРАБОТЧИК ТЕКСТА (РАСХОДЫ И СОСТОЯНИЯ) ====================

    @bot.message_handler(content_types=['text'])
    def handle_expense(message):
        state = get_state(message.chat.id)
        print(f"🔍 [EXPENSE] text={message.text}, chat.id={message.chat.id}")
        print(f"🔍 [EXPENSE] state={state}")
        
        # Если пользователь в процессе создания/настройки — обрабатываем по состоянию
        if state:
            # ---- WAITING_BUDGET ----
            if 'WAITING_BUDGET' in str(state):
                return handle_budget(message)
            
            # ---- WAITING_NEW_RATE ----
            if 'WAITING_NEW_RATE' in str(state):
                return handle_new_rate(message)
            
            # ---- WAITING_COUNTRY_FROM / WAITING_COUNTRY_TO (на случай ввода текстом) ----
            if 'WAITING_COUNTRY_FROM' in str(state):
                return handle_country_from(message)
            if 'WAITING_COUNTRY_TO' in str(state):
                return handle_country_to(message)
            
            # Неизвестное состояние — игнорируем
            return
        
        if message.text.startswith('/'):
            return
        
        try:
            amount = float(message.text.strip().replace(',', '.'))
            if amount <= 0:
                safe_send_message(
                    message.chat.id,
                    "❌ Сумма должна быть больше 0.",
                    reply_markup=main_menu_keyboard()
                )
                return
        except ValueError:
            safe_send_message(
                message.chat.id,
                "❌ Я не понял. Если это расход — введите число.",
                reply_markup=main_menu_keyboard()
            )
            return
        
        trip = get_active_trip(db, USER_ID)
        if not trip:
            safe_send_message(
                message.chat.id,
                "❌ Нет активного путешествия.",
                reply_markup=main_menu_keyboard()
            )
            return
        
        rest = get_trip_rest(db, trip['id'])
        if amount > rest['rest_to']:
            safe_send_message(
                message.chat.id,
                f"❌ Недостаточно средств! Доступно: {rest['rest_to']:.2f} {trip['currency_to']}",
                reply_markup=main_menu_keyboard()
            )
            return

        try:
            result = add_expense(db, trip['id'], amount)
            msg = (
                f"✅ Расход учтён!\n\n"
                f"💱 Конвертация:\n"
                f"  {result['expense']['amount_to']:.2f} {trip['currency_to']} → "
                f"{result['expense']['amount_from']:.2f} {trip['currency_from']}\n\n"
                f"💰 Обновлённый остаток:\n"
                f"  {trip['currency_from']}: {result['rest_from']:.2f}\n"
                f"  {trip['currency_to']}: {result['rest_to']:.2f}"
            )
            safe_send_message(
                message.chat.id,
                msg,
                reply_markup=main_menu_keyboard()
            )
        except Exception as e:
            safe_send_message(
                message.chat.id,
                f"❌ Ошибка: {e}",
                reply_markup=main_menu_keyboard()
            )
    print("🔍 [REGISTER] Все хендлеры зарегистрированы")
