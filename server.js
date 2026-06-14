import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";
import sqlite3 from "sqlite3";
import { open } from "sqlite";
import schedule from "node-schedule";
import { bot, sendAdminNotification, sendChannelLog } from "./bot.js";

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

// Хранилище активных задач node-schedule для отмены
const activeJobs = new Map();

// Инициализация базы данных SQLite
let db;
async function initDb() {
  db = await open({
    filename: "./data/database.sqlite",
    driver: sqlite3.Database,
  });

  // Таблица слотов времени
  await db.exec(`
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            is_booked INTEGER DEFAULT 0,
            booked_by_id TEXT,
            booked_by_name TEXT,
            booked_by_phone TEXT
        )
    `);

  // Восстановление напоминаний при старте
  restoreReminders();
}

// Восстановление задач напоминания из БД
async function restoreReminders() {
  const bookedSlots = await db.all("SELECT * FROM slots WHERE is_booked = 1");
  const now = new Date();

  bookedSlots.forEach((slot) => {
    const appointmentTime = new Date(`${slot.date}T${slot.time}:00`);
    const reminderTime = new Date(
      appointmentTime.getTime() - 24 * 60 * 60 * 1000,
    );

    if (reminderTime > now) {
      scheduleReminder(slot.id, reminderTime, slot.booked_by_id, slot.time);
    }
  });
}

// Планирование напоминания
function scheduleReminder(slotId, reminderTime, userId, timeString) {
  if (activeJobs.has(slotId)) {
    activeJobs.get(slotId).cancel();
  }

  const job = schedule.scheduleJob(reminderTime, async () => {
    try {
      await bot.api.sendMessage(
        userId,
        `🔔 *Напоминание о записи!*\n\nВы записаны на маникюр завтра в *${timeString}*.\nЖдём вас! ❤️`,
        { parse_mode: "Markdown" },
      );
      activeJobs.delete(slotId);
    } catch (err) {
      console.error(`Ошибка отправки напоминания пользователю ${userId}:`, err);
    }
  });

  if (job) activeJobs.set(slotId, job);
}

// API Эндпоинты

// Получение расписания
app.get("/api/slots", async (req, res) => {
  try {
    const slots = await db.all(
      "SELECT * FROM slots ORDER BY date ASC, time ASC",
    );
    res.json(slots);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Проверка: есть ли уже активная запись у пользователя
app.get("/api/user-booking/:userId", async (req, res) => {
  try {
    const booking = await db.get(
      "SELECT * FROM slots WHERE booked_by_id = ? AND is_booked = 1",
      [req.params.userId],
    );
    res.json({ hasBooking: !!booking, booking: booking || null });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Бронирование слота
app.post("/api/book", async (req, res) => {
  const { slotId, userId, name, phone } = req.body;

  try {
    // Защита от мульти-аккаунта (1 запись на юзера)
    const existing = await db.get(
      "SELECT id FROM slots WHERE booked_by_id = ? AND is_booked = 1",
      [userId],
    );
    if (existing) {
      return res.status(400).json({ error: "У вас уже есть активная запись!" });
    }

    // Проверяем, свободен ли слот
    const slot = await db.get("SELECT * FROM slots WHERE id = ?", [slotId]);
    if (!slot || slot.is_booked) {
      return res
        .status(400)
        .json({ error: "Этот слот уже занят или не существует" });
    }

    // Обновляем статус в БД
    await db.run(
      "UPDATE slots SET is_booked = 1, booked_by_id = ?, booked_by_name = ?, booked_by_phone = ? WHERE id = ?",
      [userId, name, phone, slotId],
    );

    // Планирование автонапоминания за 24 часа
    const appointmentTime = new Date(`${slot.date}T${slot.time}:00`);
    const reminderTime = new Date(
      appointmentTime.getTime() - 24 * 60 * 60 * 1000,
    );
    const now = new Date();

    if (reminderTime > now) {
      scheduleReminder(slotId, reminderTime, userId, slot.time);
    }

    // Уведомления администратора и в канал
    await sendAdminNotification(
      `➕ *Новая запись!*\n\n👤 Клиент: ${name}\n📞 Тел: ${phone}\n📅 Дата: ${slot.date}\n⏰ Время: ${slot.time}`,
    );
    await sendChannelLog(
      `📅 *Новая бронь в расписании:*\nЗанят слот ${slot.date} в ${slot.time}`,
    );

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Отмена записи клиентом или админом
app.post("/api/cancel", async (req, res) => {
  const { slotId, userId, isAdmin } = req.body;

  try {
    let slot;
    if (isAdmin) {
      slot = await db.get("SELECT * FROM slots WHERE id = ?", [slotId]);
    } else {
      slot = await db.get(
        "SELECT * FROM slots WHERE id = ? AND booked_by_id = ?",
        [slotId, userId],
      );
    }

    if (!slot || !slot.is_booked) {
      return res.status(400).json({ error: "Запись не найдена" });
    }

    // Освобождаем слот
    await db.run(
      "UPDATE slots SET is_booked = 0, booked_by_id = NULL, booked_by_name = NULL, booked_by_phone = NULL WHERE id = ?",
      [slotId],
    );

    // Удаляем запланированное напоминание
    if (activeJobs.has(slotId)) {
      activeJobs.get(slotId).cancel();
      activeJobs.delete(slotId);
    }

    // Уведомления
    await sendAdminNotification(
      `❌ *Запись отменена!*\n\n📅 Дата: ${slot.date}\n⏰ Время: ${slot.time}\n👤 Бывший клиент: ${slot.booked_by_name}`,
    );
    await sendChannelLog(
      `🔓 *Слот освободился в расписании:*\n${slot.date} — ${slot.time}`,
    );

    // Если отменил админ, уведомляем пользователя напрямую через бота
    if (isAdmin && slot.booked_by_id) {
      try {
        await bot.api.sendMessage(
          slot.booked_by_id,
          `⚠️ Ваша запись на *${slot.date}* в *${slot.time}* была отменена мастером.`,
        );
      } catch (e) {
        console.error(e);
      }
    }

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// АДМИН-ПАНЕЛЬ: Добавление слота
app.post("/api/admin/add-slot", async (req, res) => {
  const { adminId, date, time } = req.body;
  if (adminId != process.env.ADMIN_ID)
    return res.status(403).json({ error: "Доступ запрещен" });

  try {
    // Проверка на дубликат
    const exist = await db.get(
      "SELECT id FROM slots WHERE date = ? AND time = ?",
      [date, time],
    );
    if (exist)
      return res.status(400).json({ error: "Такой слот уже существует" });

    await db.run("INSERT INTO slots (date, time) VALUES (?, ?)", [date, time]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// АДМИН-ПАНЕЛЬ: Удаление пустого слота
app.post("/api/admin/delete-slot", async (req, res) => {
  const { adminId, slotId } = req.body;
  if (adminId != process.env.ADMIN_ID)
    return res.status(403).json({ error: "Доступ запрещен" });

  try {
    await db.run("DELETE FROM slots WHERE id = ? AND is_booked = 0", [slotId]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// АДМИН-ПАНЕЛЬ: Полное закрытие дня
app.post("/api/admin/close-day", async (req, res) => {
  const { adminId, date } = req.body;
  if (adminId != process.env.ADMIN_ID)
    return res.status(403).json({ error: "Доступ запрещен" });

  try {
    // Находим все забронированные слоты на этот день, чтобы уведомить людей
    const booked = await db.all(
      "SELECT * FROM slots WHERE date = ? AND is_booked = 1",
      [date],
    );
    for (let slot of booked) {
      try {
        await bot.api.sendMessage(
          slot.booked_by_id,
          `⚠️ Ваша запись на *${slot.date}* в *${slot.time}* отменена. Мастер закрыл рабочий день.`,
        );
        if (activeJobs.has(slot.id)) {
          activeJobs.get(slot.id).cancel();
          activeJobs.delete(slot.id);
        }
      } catch (e) {
        console.error(e);
      }
    }

    await db.run("DELETE FROM slots WHERE date = ?", [date]);
    await sendChannelLog(`🔒 *День полностью закрыт для записи:* ${date}`);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Запуск Express приложения и базы данных
const PORT = process.env.PORT || 3000;
initDb().then(() => {
  app.listen(PORT, () => {
    console.log(`Сервер запущен на порту ${PORT}`);
  });
});
