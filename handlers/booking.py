"""
Хендлеры процесса записи клиента на маникюр:
выбор даты -> выбор времени -> имя -> телефон -> подтверждение.
"""

import re
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from keyboards import calendar_kb, times_kb, confirm_kb, main_menu_kb, cancel_confirm_kb
from states import BookingStates
from database.slots import get_available_dates, get_available_times, get_slot_by_id, set_slot_availability
from database.bookings import (
    user_has_active_booking, create_booking, get_active_booking, cancel_booking, get_booking_by_id,
)
from config import ADMIN_ID, SCHEDULE_CHANNEL_ID
from utils import is_user_subscribed
from handlers.start import send_subscription_required, WELCOME_TEXT
from scheduler import schedule_reminder, cancel_reminder_for_booking

router = Router()

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def format_date_human(date_str: str) -> str:
    """Преобразует 'YYYY-MM-DD' в 'ДД.ММ.ГГГГ (День недели)'."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.strftime('%d.%m.%Y')} ({WEEKDAYS_RU[dt.weekday()]})"


# ===================== Старт записи =====================

@router.callback_query(F.data == "book_start")
async def callback_book_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Начало процесса записи: проверка подписки, проверка существующей записи, показ календаря."""
    user_id = callback.from_user.id

    # 1. Проверка подписки на канал
    if not await is_user_subscribed(bot, user_id):
        await send_subscription_required(callback)
        await callback.answer()
        return

    # 2. Проверка, что у пользователя нет активной записи
    if await user_has_active_booking(user_id):
        await callback.answer(
            "❗ У вас уже есть активная запись. Отмените её, чтобы создать новую.",
            show_alert=True,
        )
        return

    # 3. Показываем календарь с доступными датами
    available_dates = await get_available_dates()
    if not available_dates:
        await callback.message.edit_text(
            "😔 К сожалению, на ближайшее время нет свободных дат.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    await state.set_state(BookingStates.choosing_date)
    await callback.message.edit_text(
        "📅 <b>Выберите дату записи:</b>",
        reply_markup=calendar_kb(available_dates, prefix="date"),
    )
    await callback.answer()


# ===================== Выбор даты =====================

@router.callback_query(BookingStates.choosing_date, F.data.startswith("date:"))
async def callback_choose_date(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты - показываем доступное время."""
    date_str = callback.data.split(":")[1]

    slots = await get_available_times(date_str)
    if not slots:
        await callback.answer("На эту дату нет свободного времени.", show_alert=True)
        return

    await state.update_data(date=date_str)
    await state.set_state(BookingStates.choosing_time)

    await callback.message.edit_text(
        f"📅 Дата: <b>{format_date_human(date_str)}</b>\n\n"
        f"🕐 <b>Выберите время:</b>",
        reply_markup=times_kb(slots, date_str, prefix="time"),
    )
    await callback.answer()


# ===================== Выбор времени =====================

@router.callback_query(BookingStates.choosing_time, F.data.startswith("time:"))
async def callback_choose_time(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени - запрашиваем имя клиента."""
    slot_id = int(callback.data.split(":")[1])

    slot = await get_slot_by_id(slot_id)
    if not slot or not slot[3]:  # slot[3] = is_available
        await callback.answer("Этот слот уже занят, выберите другой.", show_alert=True)
        return

    await state.update_data(slot_id=slot_id, time=slot[2])  # slot[2] = time
    await state.set_state(BookingStates.entering_name)

    data = await state.get_data()
    await callback.message.edit_text(
        f"📅 Дата: <b>{format_date_human(data['date'])}</b>\n"
        f"🕐 Время: <b>{slot[2]}</b>\n\n"
        f"✏️ Введите ваше <b>имя</b>:"
    )
    await callback.answer()


# ===================== Ввод имени =====================

@router.message(BookingStates.entering_name)
async def process_name(message: Message, state: FSMContext):
    """Получение имени клиента, запрос номера телефона."""
    name = message.text.strip()

    if len(name) < 2 or len(name) > 50:
        await message.answer("⚠️ Введите корректное имя (от 2 до 50 символов).")
        return

    await state.update_data(name=name)
    await state.set_state(BookingStates.entering_phone)

    await message.answer(
        "📱 Теперь введите ваш <b>номер телефона</b> (например, +79991234567):"
    )


# ===================== Ввод телефона =====================

@router.message(BookingStates.entering_phone)
async def process_phone(message: Message, state: FSMContext):
    """Получение телефона клиента, показ подтверждения записи."""
    phone = message.text.strip()

    # Простая проверка формата номера телефона
    if not re.match(r"^\+?\d{10,15}$", phone.replace(" ", "").replace("-", "")):
        await message.answer(
            "⚠️ Неверный формат номера. Введите номер в формате +79991234567."
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(BookingStates.confirming)

    data = await state.get_data()
    await message.answer(
        "📝 <b>Проверьте данные записи:</b>\n\n"
        f"📅 Дата: <b>{format_date_human(data['date'])}</b>\n"
        f"🕐 Время: <b>{data['time']}</b>\n"
        f"👤 Имя: <b>{data['name']}</b>\n"
        f"📱 Телефон: <b>{data['phone']}</b>\n\n"
        "Все верно?",
        reply_markup=confirm_kb(),
    )


# ===================== Подтверждение записи =====================

@router.callback_query(BookingStates.confirming, F.data == "confirm_booking")
async def callback_confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение записи: сохранение в БД, уведомления, планирование напоминания."""
    data = await state.get_data()
    user = callback.from_user

    # Повторная проверка, что слот еще свободен (на случай гонки запросов)
    slot = await get_slot_by_id(data["slot_id"])
    if not slot or not slot[3]:
        await callback.message.edit_text(
            "😔 К сожалению, этот слот уже занят. Попробуйте выбрать другое время.",
            reply_markup=main_menu_kb(),
        )
        await state.clear()
        await callback.answer()
        return

    # Сохраняем запись в БД
    booking_id = await create_booking(
        user_id=user.id,
        username=user.username or "",
        full_name=data["name"],
        phone=data["phone"],
        slot_id=data["slot_id"],
        date_str=data["date"],
        time_str=data["time"],
    )

    # Делаем слот недоступным
    await set_slot_availability(data["slot_id"], 0)

    # Сообщение клиенту
    await callback.message.edit_text(
        "✅ <b>Запись успешно создана!</b>\n\n"
        f"📅 Дата: <b>{format_date_human(data['date'])}</b>\n"
        f"🕐 Время: <b>{data['time']}</b>\n"
        f"👤 Имя: <b>{data['name']}</b>\n"
        f"📱 Телефон: <b>{data['phone']}</b>\n\n"
        "Ждём вас! Если нужно отменить запись - используйте меню.",
        reply_markup=main_menu_kb(),
    )

    # Уведомление администратору
    username_part = f"@{user.username}" if user.username else "нет username"
    try:
        await bot.send_message(
            ADMIN_ID,
            "🆕 <b>Новая запись!</b>\n\n"
            f"📅 Дата: <b>{format_date_human(data['date'])}</b>\n"
            f"🕐 Время: <b>{data['time']}</b>\n"
            f"👤 Имя: <b>{data['name']}</b>\n"
            f"📱 Телефон: <b>{data['phone']}</b>\n"
            f"💬 Telegram: {username_part} (ID: {user.id})",
        )
    except Exception:
        pass

    # Сообщение в канал с расписанием
    try:
        await bot.send_message(
            SCHEDULE_CHANNEL_ID,
            "📋 <b>Новая запись в расписании</b>\n\n"
            f"📅 {format_date_human(data['date'])}\n"
            f"🕐 {data['time']}\n"
            f"👤 {data['name']}",
        )
    except Exception:
        pass

    # Планирование напоминания за 24 часа
    await schedule_reminder(bot, booking_id, user.id, data["date"], data["time"])

    await state.clear()
    await callback.answer()


# ===================== Отмена записи (клиент) =====================

@router.callback_query(F.data == "cancel_booking")
async def callback_cancel_booking_start(callback: CallbackQuery):
    """Показывает информацию о текущей записи и предлагает отменить."""
    booking = await get_active_booking(callback.from_user.id)

    if not booking:
        await callback.answer("У вас нет активных записей.", show_alert=True)
        return

    booking_id = booking[0]
    date_str = booking[6]
    time_str = booking[7]

    await callback.message.edit_text(
        "❗ <b>Ваша текущая запись:</b>\n\n"
        f"📅 Дата: <b>{format_date_human(date_str)}</b>\n"
        f"🕐 Время: <b>{time_str}</b>\n\n"
        "Вы уверены, что хотите отменить запись?",
        reply_markup=cancel_confirm_kb(booking_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("do_cancel:"))
async def callback_do_cancel(callback: CallbackQuery, bot: Bot):
    """Подтвержденная отмена записи: освобождает слот, удаляет напоминание, уведомляет админа."""
    booking_id = int(callback.data.split(":")[1])

    booking = await get_booking_by_id(booking_id)
    if not booking or booking[8] != "active":  # booking[8] = status
        await callback.answer("Эта запись уже отменена.", show_alert=True)
        return

    # Освобождаем слот
    slot_id = booking[5]
    await set_slot_availability(slot_id, 1)

    # Отменяем запись в БД
    await cancel_booking(booking_id)

    # Удаляем запланированное напоминание
    await cancel_reminder_for_booking(booking_id)

    await callback.message.edit_text(
        "✅ Ваша запись отменена. Слот снова доступен для записи.",
        reply_markup=main_menu_kb(),
    )

    # Уведомление администратору об отмене
    try:
        await bot.send_message(
            ADMIN_ID,
            "⚠️ <b>Клиент отменил запись</b>\n\n"
            f"📅 Дата: {format_date_human(booking[6])}\n"
            f"🕐 Время: {booking[7]}\n"
            f"👤 Имя: {booking[3]}",
        )
    except Exception:
        pass

    await callback.answer()
