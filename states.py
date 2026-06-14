"""
Состояния FSM (Finite State Machine) для процесса записи и админ-панели.
"""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Состояния процесса записи клиента."""
    choosing_date = State()      # выбор даты
    choosing_time = State()      # выбор времени
    entering_name = State()      # ввод имени
    entering_phone = State()     # ввод номера телефона
    confirming = State()         # подтверждение записи


class AdminStates(StatesGroup):
    """Состояния админ-панели."""
    waiting_new_day = State()         # ввод даты для добавления рабочего дня
    waiting_new_slot_date = State()   # ввод даты для нового слота
    waiting_new_slot_time = State()   # ввод времени для нового слота
    waiting_remove_slot_date = State()  # ввод даты для удаления слота
    waiting_close_day_date = State()  # ввод даты для закрытия дня
    waiting_view_schedule_date = State()  # ввод даты для просмотра расписания
    waiting_cancel_booking_date = State()  # ввод даты для отмены записи клиента
