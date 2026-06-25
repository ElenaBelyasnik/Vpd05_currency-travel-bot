from telebot.handler_backends import State, StatesGroup


class TravelStates(StatesGroup):
    """Состояния для FSM бота."""
    WAITING_COUNTRY_FROM = State()
    WAITING_COUNTRY_TO = State()
    WAITING_BUDGET = State()
    WAITING_EXPENSE = State()
    WAITING_NEW_RATE = State()
    WAITING_SWITCH_TRIP = State()