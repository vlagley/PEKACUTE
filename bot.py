"""
Точка входа бота.
Инициализирует базу данных, диспетчер, регистрирует роутеры,
восстанавливает напоминания и запускает polling.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from database.slots import ensure_schedule_generated
from scheduler import scheduler, restore_reminders

from handlers import start, booking, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # Инициализация бота с HTML-разметкой по умолчанию
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров (порядок важен: специфичные раньше общих)
    dp.include_router(admin.router)
    dp.include_router(booking.router)
    dp.include_router(start.router)

    # Инициализация базы данных
    await init_db()

    # Генерация расписания на месяц вперед (если еще не сформировано)
    await ensure_schedule_generated()

    # Восстановление напоминаний из БД (после возможного перезапуска бота)
    await restore_reminders(bot)

    # Запуск планировщика напоминаний
    scheduler.start()

    logger.info("Бот запущен.")

    # Удаляем накопленные обновления и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
