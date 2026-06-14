"""
Функции для работы с таблицей напоминаний (reminders).
Используется для восстановления задач APScheduler после перезапуска бота.
"""

from database.db import get_db


async def add_reminder(booking_id: int, user_id: int, remind_at: str, date_str: str, time_str: str) -> int:
    """Добавляет запись о запланированном напоминании, возвращает id записи."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO reminders (booking_id, user_id, remind_at, date, time, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (booking_id, user_id, remind_at, date_str, time_str),
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_reminder_ids_for_booking(booking_id: int) -> list[int]:
    """Возвращает id ожидающих напоминаний для указанной записи."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM reminders WHERE booking_id = ? AND status = 'pending'",
            (booking_id,),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def cancel_reminders_for_booking(booking_id: int):
    """Помечает все напоминания, связанные с записью, как отмененные."""
    async with get_db() as db:
        await db.execute(
            "UPDATE reminders SET status = 'cancelled' WHERE booking_id = ?",
            (booking_id,),
        )
        await db.commit()


async def mark_reminder_sent(reminder_id: int):
    """Помечает напоминание как отправленное."""
    async with get_db() as db:
        await db.execute(
            "UPDATE reminders SET status = 'sent' WHERE id = ?", (reminder_id,)
        )
        await db.commit()


async def get_pending_reminders():
    """Возвращает все ожидающие напоминания (для восстановления при старте бота)."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM reminders WHERE status = 'pending'"
        )
        return await cursor.fetchall()
