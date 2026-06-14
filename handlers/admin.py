"""
Хендлеры админ-панели (доступ только по ADMIN_ID).
Позволяет:
- добавлять рабочие дни
- добавлять/удалять временные слоты
- отменять записи клиентов
- полностью закрывать день
- просматривать расписание на дату
"""

from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID, DEFAULT_SLOT_TIMES
from states import AdminStates
from keyboards import (
    admin_menu_kb, admin_slots_management_kb, admin_bookings_kb, back_to_admin_kb, main_menu_kb,
)
from database.slots import (
    add_slot, remove_slot, close_day, get_all_slots_for_date, get_slot_by_id, set_slot_availability,
)
from database.bookings import get_bookings_for_date, get_booking_by_id, cancel_booking
from scheduler import cancel_reminder_for_booking

router = Router()

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def format_date_human(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.strftime('%d.%m.%Y')} ({WEEKDAYS_RU[dt.weekday()]})"


def validate_date(text: str) -> str | None:
    """Проверяет и нормализует дату в формате ДД.ММ.ГГГГ -> YYYY-MM-DD. Возвращает None при ошибке."""
    try:
        dt = datetime.strptime(text.strip(), "%d.%m.%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def validate_time(text: str) -> str | None:
    """Проверяет и нормализует время в формате ЧЧ:МММ -> HH:MM. Возвращает None при ошибке."""
    try:
        dt = datetime.strptime(text.strip(), "%H:%M")
        return dt.strftime("%H:%M")
    except ValueError:
        return None


# ===================== Вход в админ-панель =====================

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Команда входа в админ-панель. Доступна только администратору."""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    await state.clear()
    await message.answer("🔧 <b>Админ-панель</b>\n\nВыберите действие:", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin_panel")
async def callback_admin_panel(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню админ-панели."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text("🔧 <b>Админ-панель</b>\n\nВыберите действие:", reply_markup=admin_menu_kb())
    await callback.answer()


# ===================== Добавление рабочего дня =====================

@router.callback_query(F.data == "admin_add_day")
async def callback_admin_add_day(callback: CallbackQuery, state: FSMContext):
    """Запрашивает дату для добавления нового рабочего дня со стандартным набором слотов."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_new_day)
    await callback.message.edit_text(
        "📅 Введите дату нового рабочего дня в формате <b>ДД.ММ.ГГГГ</b>\n\n"
        f"На день будут добавлены стандартные слоты: {', '.join(DEFAULT_SLOT_TIMES)}",
        reply_markup=back_to_admin_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_new_day)
async def process_admin_add_day(message: Message, state: FSMContext):
    """Создает рабочий день со стандартными слотами на указанную дату."""
    date_str = validate_date(message.text)
    if not date_str:
        await message.answer("⚠️ Неверный формат. Введите дату как ДД.ММ.ГГГГ, например 25.12.2026.")
        return

    for t in DEFAULT_SLOT_TIMES:
        await add_slot(date_str, t)

    await state.clear()
    await message.answer(
        f"✅ Рабочий день {format_date_human(date_str)} добавлен со стандартными слотами.",
        reply_markup=admin_menu_kb(),
    )


# ===================== Добавление слота =====================

@router.callback_query(F.data == "admin_add_slot")
async def callback_admin_add_slot(callback: CallbackQuery, state: FSMContext):
    """Запрашивает дату для добавления конкретного слота."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_new_slot_date)
    await callback.message.edit_text(
        "📅 Введите дату для добавления слота в формате <b>ДД.ММ.ГГГГ</b>:",
        reply_markup=back_to_admin_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_new_slot_date)
async def process_admin_add_slot_date(message: Message, state: FSMContext):
    """Получает дату для нового слота, запрашивает время."""
    date_str = validate_date(message.text)
    if not date_str:
        await message.answer("⚠️ Неверный формат. Введите дату как ДД.ММ.ГГГГ.")
        return

    await state.update_data(slot_date=date_str)
    await state.set_state(AdminStates.waiting_new_slot_time)
    await message.answer("🕐 Введите время слота в формате <b>ЧЧ:ММ</b>, например 14:30:")


@router.message(AdminStates.waiting_new_slot_time)
async def process_admin_add_slot_time(message: Message, state: FSMContext):
    """Добавляет новый слот на указанную дату и время."""
    time_str = validate_time(message.text)
    if not time_str:
        await message.answer("⚠️ Неверный формат. Введите время как ЧЧ:ММ, например 14:30.")
        return

    data = await state.get_data()
    date_str = data["slot_date"]

    await add_slot(date_str, time_str)
    await state.clear()

    await message.answer(
        f"✅ Слот {time_str} на {format_date_human(date_str)} добавлен.",
        reply_markup=admin_menu_kb(),
    )


# ===================== Удаление слота =====================

@router.callback_query(F.data == "admin_remove_slot")
async def callback_admin_remove_slot(callback: CallbackQuery, state: FSMContext):
    """Запрашивает дату для просмотра и удаления слотов."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_remove_slot_date)
    await callback.message.edit_text(
        "📅 Введите дату для удаления слота в формате <b>ДД.ММ.ГГГГ</b>:",
        reply_markup=back_to_admin_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_remove_slot_date)
async def process_admin_remove_slot_date(message: Message, state: FSMContext):
    """Показывает слоты на указанную дату для выбора удаления."""
    date_str = validate_date(message.text)
    if not date_str:
        await message.answer("⚠️ Неверный формат. Введите дату как ДД.ММ.ГГГГ.")
        return

    slots = await get_all_slots_for_date(date_str)
    if not slots:
        await message.answer(
            f"На {format_date_human(date_str)} нет слотов.", reply_markup=admin_menu_kb()
        )
        await state.clear()
        return

    await state.clear()
    await message.answer(
        f"🗑 Слоты на {format_date_human(date_str)}\n"
        f"🟢 - свободен, 🔴 - занят\n\n"
        f"Нажмите на слот, чтобы удалить его:",
        reply_markup=admin_slots_management_kb(slots, date_str),
    )


@router.callback_query(F.data.startswith("admin_slot_del:"))
async def callback_admin_slot_delete(callback: CallbackQuery):
    """Удаляет выбранный слот."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    slot_id = int(callback.data.split(":")[1])
    slot = await get_slot_by_id(slot_id)

    if not slot:
        await callback.answer("Слот не найден.", show_alert=True)
        return

    if not slot[3]:  # is_available == 0, занят
        await callback.answer(
            "⚠️ Этот слот занят активной записью. Сначала отмените запись клиента.",
            show_alert=True,
        )
        return

    await remove_slot(slot_id)
    await callback.answer("✅ Слот удален.")

    # Обновляем список слотов
    date_str = slot[1]
    slots = await get_all_slots_for_date(date_str)
    if slots:
        await callback.message.edit_reply_markup(reply_markup=admin_slots_management_kb(slots, date_str))
    else:
        await callback.message.edit_text(
            f"На {format_date_human(date_str)} больше нет слотов.", reply_markup=admin_menu_kb()
        )


# ===================== Закрытие дня =====================

@router.callback_query(F.data == "admin_close_day")
async def callback_admin_close_day(callback: CallbackQuery, state: FSMContext):
    """Запрашивает дату для полного закрытия дня."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_close_day_date)
    await callback.message.edit_text(
        "🚫 Введите дату для закрытия дня в формате <b>ДД.ММ.ГГГГ</b>\n\n"
        "Все слоты на эту дату станут недоступны для записи.",
        reply_markup=back_to_admin_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_close_day_date)
async def process_admin_close_day(message: Message, state: FSMContext):
    """Полностью закрывает указанный день."""
    date_str = validate_date(message.text)
    if not date_str:
        await message.answer("⚠️ Неверный формат. Введите дату как ДД.ММ.ГГГГ.")
        return

    await close_day(date_str)
    await state.clear()

    await message.answer(
        f"✅ День {format_date_human(date_str)} полностью закрыт для записи.",
        reply_markup=admin_menu_kb(),
    )


# ===================== Просмотр расписания =====================

@router.callback_query(F.data == "admin_view_schedule")
async def callback_admin_view_schedule(callback: CallbackQuery, state: FSMContext):
    """Запрашивает дату для просмотра расписания."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_view_schedule_date)
    await callback.message.edit_text(
        "📋 Введите дату для просмотра расписания в формате <b>ДД.ММ.ГГГГ</b>:",
        reply_markup=back_to_admin_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_view_schedule_date)
async def process_admin_view_schedule(message: Message, state: FSMContext):
    """Показывает полное расписание (слоты и записи) на указанную дату."""
    date_str = validate_date(message.text)
    if not date_str:
        await message.answer("⚠️ Неверный формат. Введите дату как ДД.ММ.ГГГГ.")
        return

    await state.clear()

    slots = await get_all_slots_for_date(date_str)
    bookings = await get_bookings_for_date(date_str)

    if not slots:
        await message.answer(
            f"На {format_date_human(date_str)} расписание не сформировано.",
            reply_markup=admin_menu_kb(),
        )
        return

    bookings_by_time = {b[7]: b for b in bookings}  # b[7] = time

    text = f"📋 <b>Расписание на {format_date_human(date_str)}</b>\n\n"
    for slot_id, time_str, is_available, is_closed in slots:
        if is_closed:
            text += f"🚫 {time_str} — день закрыт\n"
        elif time_str in bookings_by_time:
            b = bookings_by_time[time_str]
            text += f"🔴 {time_str} — занято: {b[3]} ({b[4]})\n"  # full_name, phone
        else:
            text += f"🟢 {time_str} — свободно\n"

    await message.answer(text, reply_markup=admin_menu_kb())


# ===================== Отмена записи клиента (админ) =====================

@router.callback_query(F.data == "admin_cancel_booking")
async def callback_admin_cancel_booking(callback: CallbackQuery, state: FSMContext):
    """Запрашивает дату для просмотра записей и выбора отмены."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_cancel_booking_date)
    await callback.message.edit_text(
        "❌ Введите дату для отмены записи клиента в формате <b>ДД.ММ.ГГГГ</b>:",
        reply_markup=back_to_admin_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_cancel_booking_date)
async def process_admin_cancel_booking_date(message: Message, state: FSMContext):
    """Показывает список записей на указанную дату для отмены."""
    date_str = validate_date(message.text)
    if not date_str:
        await message.answer("⚠️ Неверный формат. Введите дату как ДД.ММ.ГГГГ.")
        return

    bookings = await get_bookings_for_date(date_str)
    await state.clear()

    if not bookings:
        await message.answer(
            f"На {format_date_human(date_str)} нет активных записей.",
            reply_markup=admin_menu_kb(),
        )
        return

    await message.answer(
        f"❌ Записи на {format_date_human(date_str)}\n\nВыберите запись для отмены:",
        reply_markup=admin_bookings_kb(bookings),
    )


@router.callback_query(F.data.startswith("admin_cancel_book:"))
async def callback_admin_cancel_book(callback: CallbackQuery, bot: Bot):
    """Отменяет выбранную запись клиента, освобождает слот, уведомляет клиента."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    booking_id = int(callback.data.split(":")[1])
    booking = await get_booking_by_id(booking_id)

    if not booking or booking[8] != "active":
        await callback.answer("Запись уже отменена.", show_alert=True)
        return

    # Освобождаем слот
    slot_id = booking[5]
    await set_slot_availability(slot_id, 1)

    # Отменяем запись
    await cancel_booking(booking_id)

    # Удаляем напоминание
    await cancel_reminder_for_booking(booking_id)

    await callback.answer("✅ Запись отменена.")

    # Уведомление клиента
    client_user_id = booking[1]
    try:
        await bot.send_message(
            client_user_id,
            "⚠️ <b>Ваша запись была отменена администратором.</b>\n\n"
            f"📅 Дата: {format_date_human(booking[6])}\n"
            f"🕐 Время: {booking[7]}\n\n"
            "Пожалуйста, выберите другое время для записи.",
            reply_markup=main_menu_kb(),
        )
    except Exception:
        pass

    # Обновляем список записей
    date_str = booking[6]
    bookings = await get_bookings_for_date(date_str)
    if bookings:
        await callback.message.edit_reply_markup(reply_markup=admin_bookings_kb(bookings))
    else:
        await callback.message.edit_text(
            f"На {format_date_human(date_str)} больше нет активных записей.",
            reply_markup=admin_menu_kb(),
        )
