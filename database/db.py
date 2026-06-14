"""
Модуль работы с базой данных SQLite.
Содержит инициализацию таблиц и базовые функции-хелперы.
"""

import aiosqlite
from config import DB_PATH


async def init_db():
    """Создает таблицы в базе данных, если они еще не существуют."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица доступных слотов времени
        await db.execute("""
            CREATE TABLE IF NOT EXISTS slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,        -- дата в формате YYYY-MM-DD
                time TEXT NOT NULL,        -- время в формате HH:MM
                is_available INTEGER NOT NULL DEFAULT 1,  -- 1 = свободен, 0 = занят
                is_closed INTEGER NOT NULL DEFAULT 0,     -- 1 = день закрыт администратором
                UNIQUE(date, time)
            )
        """)

        # Таблица записей клиентов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                slot_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',  -- active / cancelled
                created_at TEXT NOT NULL,
                FOREIGN KEY (slot_id) REFERENCES slots (id)
            )
        """)

        # Таблица запланированных напоминаний (для восстановления после перезапуска)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                remind_at TEXT NOT NULL,   -- ISO datetime, когда отправить напоминание
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending / sent / cancelled
                FOREIGN KEY (booking_id) REFERENCES bookings (id)
            )
        """)

        await db.commit()


def get_db():
    """Возвращает новое соединение с базой данных (используется как async context manager)."""
    return aiosqlite.connect(DB_PATH)
