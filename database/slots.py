"""
Функции для работы со слотами (доступное время для записи).
"""

from datetime import date, timedelta
from database.db import get_db
from config import DEFAULT_SLOT_TIMES, SCHEDULE_DAYS_AHEAD


async def ensure_schedule_generated():
    """
    Проверяет, что на ближайшие SCHEDULE_DAYS_AHEAD дней есть слоты,
    и генерирует недостающие с временем по умолчанию.
    Вызывается при старте бота, чтобы расписание всегда было на месяц вперед.
    """
    today = date.today()
    async with get_db() as db:
        for i in range(SCHEDULE_DAYS_AHEAD):
            day = today + timedelta(days=i)
            day_str = day.isoformat()

            # Проверяем, есть ли уже слоты на этот день
            cursor = await db.execute(
                "SELECT COUNT(*) FROM slots WHERE date = ?", (day_str,)
            )
            count = (await cursor.fetchone())[0]

            if count == 0:
                for t in DEFAULT_SLOT_TIMES:
                    await db.execute(
                        "INSERT OR IGNORE INTO slots (date, time, is_available, is_closed) "
                        "VALUES (?, ?, 1, 0)",
                        (day_str, t),
                    )
        await db.commit()


async def get_available_dates():
    """
    Возвращает список дат (str), на которые есть хотя бы один свободный слот
    и день не закрыт администратором.
    """
    today_str = date.today().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT DISTINCT date FROM slots
            WHERE is_available = 1 AND is_closed = 0 AND date >= ?
            ORDER BY date ASC
            """,
            (today_str,),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_available_times(date_str: str):
    """Возвращает список доступных слотов времени (id, time) для указанной даты."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, time FROM slots
            WHERE date = ? AND is_available = 1 AND is_closed = 0
            ORDER BY time ASC
            """,
            (date_str,),
        )
        return await cursor.fetchall()


async def get_slot_by_id(slot_id: int):
    """Возвращает строку слота по id."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM slots WHERE id = ?", (slot_id,))
        return await cursor.fetchone()


async def set_slot_availability(slot_id: int, is_available: int):
    """Меняет доступность слота (занят/свободен)."""
    async with get_db() as db:
        await db.execute(
            "UPDATE slots SET is_available = ? WHERE id = ?", (is_available, slot_id)
        )
        await db.commit()


async def add_slot(date_str: str, time_str: str):
    """Добавляет новый слот на указанную дату и время."""
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO slots (date, time, is_available, is_closed) "
            "VALUES (?, ?, 1, 0)",
            (date_str, time_str),
        )
        await db.commit()


async def remove_slot(slot_id: int):
    """Удаляет слот из расписания (если он не занят активной записью)."""
    async with get_db() as db:
        await db.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
        await db.commit()


async def close_day(date_str: str):
    """Полностью закрывает день: помечает все слоты как закрытые."""
    async with get_db() as db:
        await db.execute(
            "UPDATE slots SET is_closed = 1 WHERE date = ?", (date_str,)
        )
        await db.commit()


async def open_day(date_str: str):
    """Открывает ранее закрытый день."""
    async with get_db() as db:
        await db.execute(
            "UPDATE slots SET is_closed = 0 WHERE date = ?", (date_str,)
        )
        await db.commit()


async def get_all_slots_for_date(date_str: str):
    """Возвращает все слоты на дату (для админ-панели), включая занятые."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, time, is_available, is_closed FROM slots WHERE date = ? ORDER BY time ASC",
            (date_str,),
        )
        return await cursor.fetchall()


async def get_all_dates_with_slots():
    """Возвращает все даты, на которые сгенерированы слоты (для админ-календаря)."""
    today_str = date.today().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT DISTINCT date FROM slots WHERE date >= ? ORDER BY date ASC",
            (today_str,),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
