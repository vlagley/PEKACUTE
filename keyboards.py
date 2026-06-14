"""
Генерация inline-клавиатур, в том числе календаря для выбора даты.
"""

from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ===================== Главное меню =====================

def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Записаться", callback_data="book_start")
    builder.button(text="❌ Отменить запись", callback_data="cancel_booking")
    builder.button(text="💰 Прайсы", callback_data="prices")
    builder.button(text="🖼 Портфолио", callback_data="portfolio")
    builder.adjust(1)
    return builder.as_markup()


# ===================== Проверка подписки =====================

def subscribe_kb(channel_link: str) -> InlineKeyboardMarkup:
    """Клавиатура с предложением подписаться на канал и проверить подписку."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Подписаться", url=channel_link)
    builder.button(text="✅ Проверить подписку", callback_data="check_subscription")
    builder.adjust(1)
    return builder.as_markup()


# ===================== Портфолио =====================

def portfolio_kb(link: str) -> InlineKeyboardMarkup:
    """Клавиатура со ссылкой на портфолио."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Смотреть портфолио", url=link)
    return builder.as_markup()


# ===================== Календарь для клиента =====================

def calendar_kb(available_dates: list[str], prefix: str = "date") -> InlineKeyboardMarkup:
    """
    Клавиатура со списком доступных дат.
    available_dates - список строк 'YYYY-MM-DD'.
    prefix - префикс callback_data ('date' для клиента, 'admin_date' для админа).
    """
    builder = InlineKeyboardBuilder()
    for date_str in available_dates:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        # Отображаем дату в формате "12.06 (Чт)"
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        label = f"{dt.strftime('%d.%m')} ({weekdays[dt.weekday()]})"
        builder.button(text=label, callback_data=f"{prefix}:{date_str}")
    builder.button(text="⬅️ В меню", callback_data="main_menu")
    builder.adjust(3)
    return builder.as_markup()


# ===================== Выбор времени =====================

def times_kb(slots: list[tuple], date_str: str, prefix: str = "time") -> InlineKeyboardMarkup:
    """
    Клавиатура со списком доступного времени.
    slots - список (slot_id, time_str).
    """
    builder = InlineKeyboardBuilder()
    for slot_id, time_str in slots:
        builder.button(text=time_str, callback_data=f"{prefix}:{slot_id}")
    builder.button(text="⬅️ К датам", callback_data="book_start")
    builder.adjust(3)
    return builder.as_markup()


# ===================== Подтверждение записи =====================

def confirm_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_booking")
    builder.button(text="❌ Отмена", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()


# ===================== Отмена записи (клиент) =====================

def cancel_confirm_kb(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения отмены записи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, отменить", callback_data=f"do_cancel:{booking_id}")
    builder.button(text="◀️ Назад", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()


# ===================== Админ-панель =====================

def admin_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить рабочий день", callback_data="admin_add_day")
    builder.button(text="➕ Добавить слот", callback_data="admin_add_slot")
    builder.button(text="➖ Удалить слот", callback_data="admin_remove_slot")
    builder.button(text="🚫 Закрыть день", callback_data="admin_close_day")
    builder.button(text="📋 Расписание на дату", callback_data="admin_view_schedule")
    builder.button(text="❌ Отменить запись клиента", callback_data="admin_cancel_booking")
    builder.button(text="⬅️ В меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_slots_management_kb(slots: list[tuple], date_str: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для управления слотами на дату (удаление).
    slots - список (id, time, is_available, is_closed).
    """
    builder = InlineKeyboardBuilder()
    for slot_id, time_str, is_available, is_closed in slots:
        status = "🟢" if is_available else "🔴"
        builder.button(text=f"{status} {time_str}", callback_data=f"admin_slot_del:{slot_id}")
    builder.button(text="⬅️ Назад", callback_data="admin_panel")
    builder.adjust(3)
    return builder.as_markup()


def admin_bookings_kb(bookings: list[tuple]) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком записей для отмены администратором.
    bookings - список строк bookings.
    """
    builder = InlineKeyboardBuilder()
    for b in bookings:
        booking_id = b[0]
        time_str = b[7]
        name = b[3]
        builder.button(
            text=f"❌ {time_str} — {name}",
            callback_data=f"admin_cancel_book:{booking_id}",
        )
    builder.button(text="⬅️ Назад", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()


def back_to_admin_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в админ-панель."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="admin_panel")
    return builder.as_markup()
