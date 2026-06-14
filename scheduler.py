"""
Модуль для работы с планировщиком напоминаний (APScheduler).
Содержит функции планирования, отмены и восстановления задач напоминаний.
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from aiogram import Bot

from config import TIMEZONE
from database.reminders import add_reminder, cancel_reminders_for_booking, get_pending_reminders, mark_reminder_sent

logger = logging.getLogger(__name__)

# Глобальный экземпляр планировщика
scheduler = AsyncIOScheduler(timezone=TIMEZONE)


async def send_reminder(bot: Bot, reminder_id: int, user_id: int, time_str: str):
    """Отправляет пользователю напоминание о записи и помечает его как отправленное."""
    text = (
        f"🔔 Напоминаем, что вы записаны на наращивание ресниц завтра в {time_str}.\n"
        f"Ждём вас 💖"
    )
    try:
        await bot.send_message(user_id, text)
    except Exception as e:
        logger.warning(f"Не удалось отправить напоминание пользователю {user_id}: {e}")
    finally:
        await mark_reminder_sent(reminder_id)


async def schedule_reminder(bot: Bot, booking_id: int, user_id: int, date_str: str, time_str: str):
    """
    Планирует напоминание за 24 часа до записи.
    Если запись создана менее чем за 24 часа до визита - напоминание не создается.
    """
    visit_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    remind_dt = visit_dt - timedelta(hours=24)
    now = datetime.now()

    # Если до визита осталось меньше 24 часов - не создаем напоминание
    if remind_dt <= now:
        logger.info(
            f"Запись {booking_id}: визит менее чем через 24 часа, напоминание не создается."
        )
        return

    # Сохраняем напоминание в БД, чтобы восстановить после перезапуска
    reminder_id = await add_reminder(booking_id, user_id, remind_dt.isoformat(), date_str, time_str)

    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=remind_dt),
        args=[bot, reminder_id, user_id, time_str],
        id=f"reminder_{reminder_id}",
        replace_existing=True,
    )
    logger.info(f"Напоминание для записи {booking_id} запланировано на {remind_dt}")


async def cancel_reminder_for_booking(booking_id: int):
    """Удаляет запланированные задачи напоминаний для отмененной записи."""
    from database.reminders import get_pending_reminder_ids_for_booking

    reminder_ids = await get_pending_reminder_ids_for_booking(booking_id)
    await cancel_reminders_for_booking(booking_id)
    await cancel_jobs_by_reminder_ids(reminder_ids)


async def cancel_jobs_by_reminder_ids(reminder_ids: list[int]):
    """Удаляет задачи планировщика по списку id напоминаний."""
    for reminder_id in reminder_ids:
        job_id = f"reminder_{reminder_id}"
        job = scheduler.get_job(job_id)
        if job:
            job.remove()


async def restore_reminders(bot: Bot):
    """
    Восстанавливает запланированные напоминания из базы данных при старте бота.
    Вызывается один раз при запуске.
    """
    pending = await get_pending_reminders()
    now = datetime.now()

    for reminder in pending:
        reminder_id, booking_id, user_id, remind_at, date_str, time_str, status = reminder
        remind_dt = datetime.fromisoformat(remind_at)

        if remind_dt <= now:
            # Время напоминания уже прошло - отправляем сразу (или можно пропустить)
            await send_reminder(bot, reminder_id, user_id, time_str)
            continue

        scheduler.add_job(
            send_reminder,
            trigger=DateTrigger(run_date=remind_dt),
            args=[bot, reminder_id, user_id, time_str],
            id=f"reminder_{reminder_id}",
            replace_existing=True,
        )
        logger.info(f"Восстановлено напоминание {reminder_id} на {remind_dt}")
