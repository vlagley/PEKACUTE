"""
Функции для работы с записями клиентов (bookings).
"""

from datetime import datetime
from database.db import get_db


async def user_has_active_booking(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя активная (не отмененная) запись."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM bookings WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        count = (await cursor.fetchone())[0]
        return count > 0


async def get_active_booking(user_id: int):
    """Возвращает активную запись пользователя (или None)."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM bookings WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        return await cursor.fetchone()


async def create_booking(user_id: int, username: str, full_name: str,
                          phone: str, slot_id: int, date_str: str, time_str: str) -> int:
    """Создает новую запись и возвращает её id."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO bookings (user_id, username, full_name, phone, slot_id, date, time, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """,
            (user_id, username, full_name, phone, slot_id, date_str, time_str,
             datetime.now().isoformat()),
        )
        await db.commit()
        return cursor.lastrowid


async def cancel_booking(booking_id: int):
    """Отменяет запись по id (статус -> cancelled)."""
    async with get_db() as db:
        await db.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,)
        )
        await db.commit()


async def get_booking_by_id(booking_id: int):
    """Возвращает запись по id."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        return await cursor.fetchone()


async def get_bookings_for_date(date_str: str):
    """Возвращает все активные записи на указанную дату (для админ-панели)."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM bookings WHERE date = ? AND status = 'active' ORDER BY time ASC",
            (date_str,),
        )
        return await cursor.fetchall()


async def get_all_active_bookings():
    """Возвращает все активные записи (используется при восстановлении напоминаний)."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM bookings WHERE status = 'active' ORDER BY date ASC, time ASC"
        )
        return await cursor.fetchall()
