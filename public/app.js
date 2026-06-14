const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Точка конфигурации API бэкенда (автоматически определяет текущий хост)
const API_URL = window.location.origin;

// Инициализация данных пользователя
const user = tg.initDataUnsafe?.user || {
  id: "123456789",
  first_name: "Тестовый Покупатель",
};
// Проверка на статус админа через сервер (сравнение с ADMIN_ID из .env выполняется на бэкенде)
let isAdminMode = false;

// DOM элементы
const calendarInput = document.getElementById("calendarInput");
const slotsSection = document.getElementById("slotsSection");
const slotsContainer = document.getElementById("slotsContainer");
const activeBookingContainer = document.getElementById(
  "activeBookingContainer",
);
const bookingDetails = document.getElementById("bookingDetails");
const cancelBookingBtn = document.getElementById("cancelBookingBtn");
const bookingFormModal = document.getElementById("bookingFormModal");
const selectedSlotInfo = document.getElementById("selectedSlotInfo");
const mainCalendarSection = document.getElementById("mainCalendarSection");
const adminPanel = document.getElementById("adminPanel");
const adminSlotsContainer = document.getElementById("adminSlotsContainer");

let allSlots = [];
let selectedSlot = null;

// Настройка календаря: ограничение на 1 месяц вперед
function setupCalendarLimits() {
  const today = new Date();
  const maxDate = new Date();
  maxDate.setMonth(today.getMonth() + 1);

  calendarInput.min = today.toISOString().split("T")[0];
  calendarInput.max = maxDate.toISOString().split("T")[0];
}

// Загрузка данных
async function loadData() {
  try {
    // Проверка: является ли пользователь админом
    // Для демонстрации проверяем локально, но сервер валидирует операции по API строго.
    // Чтобы узнать, админ ли это, мы можем сделать пустой запрос или сверить ID, если прокинем его.
    // Запросим информацию о наличии личной записи
    const resBooking = await fetch(`${API_URL}/api/user-booking/${user.id}`);
    const bookingData = await resBooking.json();

    if (bookingData.hasBooking) {
      activeBookingContainer.classList.remove("hidden");
      mainCalendarSection.classList.add("hidden");
      bookingDetails.innerHTML = `Дата: <b>${bookingData.booking.date}</b><br>Время: <b>${bookingData.booking.time}</b>`;
      cancelBookingBtn.onclick = () =>
        cancelBooking(bookingData.booking.id, false);
    } else {
      activeBookingContainer.classList.add("hidden");
      mainCalendarSection.classList.remove("hidden");
    }

    // Запрос слотов
    const resSlots = await fetch(`${API_URL}/api/slots`);
    allSlots = await resSlots.json();

    // Проверка на администратора (запрос флага)
    if (user.id.toString() === "123456789") {
      // Будет динамически проверено при вводе даты
      // Для удобства определим режим админа, если у нас совпал ID (на проде подставьте ваш Telegram ID вместо "123456789")
      // Здесь это хардкод для демо, но бэкенд сверяет это жестко через `.env`
    }

    if (calendarInput.value) {
      renderSlots(calendarInput.value);
    }
  } catch (err) {
    console.error("Ошибка загрузки данных:", err);
  }
}

// Отрисовка слотов на выбранную дату
function renderSlots(selectedDate) {
  slotsContainer.innerHTML = "";
  adminSlotsContainer.innerHTML = "";

  const filteredSlots = allSlots.filter((s) => s.date === selectedDate);

  if (filteredSlots.length === 0) {
    slotsContainer.innerHTML = "<p>Нет доступных слотов на этот день.</p>";
    adminSlotsContainer.innerHTML = "<p>Слоты отсутствуют.</p>";
    slotsSection.classList.remove("hidden");
    return;
  }

  filteredSlots.forEach((slot) => {
    // Рендеринг для клиента
    const slotEl = document.createElement("div");
    slotEl.classList.add("slot-item");
    slotEl.innerText = slot.time;

    if (slot.is_booked) {
      slotEl.classList.add("booked");
    } else {
      slotEl.onclick = () => openBookingForm(slot);
    }
    slotsContainer.appendChild(slotEl);

    // Рендеринг для админа
    const adminSlotEl = document.createElement("div");
    adminSlotEl.classList.add("slot-item");
    adminSlotEl.innerText = `${slot.time} ${slot.is_booked ? "❌" : "🗑️"}`;
    if (slot.is_booked) {
      adminSlotEl.classList.add("admin-booked");
      adminSlotEl.title = `Клиент: ${slot.booked_by_name} (${slot.booked_by_phone})`;
      // Клик отменяет запись клиента
      adminSlotEl.onclick = () => {
        if (confirm(`Отменить запись клиента ${slot.booked_by_name}?`)) {
          cancelBooking(slot.id, true);
        }
      };
    } else {
      // Клик удаляет свободный слот
      adminSlotEl.onclick = async () => {
        if (confirm(`Удалить слот времени ${slot.time}?`)) {
          await deleteSlot(slot.id);
        }
      };
    }
    adminSlotsContainer.appendChild(adminSlotEl);
  });

  slotsSection.classList.remove("hidden");
}

// Логика открытия формы бронирования
function openBookingForm(slot) {
  selectedSlot = slot;
  mainCalendarSection.classList.add("hidden");
  bookingFormModal.classList.remove("hidden");
  selectedSlotInfo.innerHTML = `Выбранная дата: <b>${slot.date}</b><br>Время: <b>${slot.time}</b>`;
}

// Закрыть форму записи
document.getElementById("closeFormBtn").onclick = () => {
  bookingFormModal.classList.add("hidden");
  mainCalendarSection.classList.remove("hidden");
};

// Запрос на бронирование
document.getElementById("confirmBookingBtn").onclick = async () => {
  const name = document.getElementById("clientName").value.trim();
  const phone = document.getElementById("clientPhone").value.trim();

  if (!name || !phone) {
    alert("Пожалуйста, заполните ваше имя и телефон!");
    return;
  }

  try {
    const response = await fetch(`${API_URL}/api/book`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        slotId: selectedSlot.id,
        userId: user.id.toString(),
        name: name,
        phone: phone,
      }),
    });

    const result = await response.json();
    if (result.success) {
      alert("Запись успешно оформлена! 🎉");
      bookingFormModal.classList.add("hidden");
      loadData();
    } else {
      alert(`Ошибка: ${result.error}`);
    }
  } catch (e) {
    alert("Произошла ошибка при отправке запроса.");
  }
};

// Отмена записи (универсальная для юзера и админа)
async function cancelBooking(slotId, isAdmin = false) {
  try {
    const response = await fetch(`${API_URL}/api/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        slotId: slotId,
        userId: user.id.toString(),
        isAdmin: isAdmin,
        adminId: user.id.toString(), // Передаем как проверку
      }),
    });

    const result = await response.json();
    if (result.success) {
      alert("Запись успешно отменена.");
      loadData();
    } else {
      alert(`Ошибка при отмене: ${result.error}`);
    }
  } catch (e) {
    alert("Не удалось отменить запись.");
  }
}

// --- Скрипты Админ-Панели ---

// Активация админки, если текущий ID совпадает с конфигом
// Бэкенд проверяет безопасность. Здесь мы просто переключаем UI для удобства владельца
function checkAdminUI(selectedDate) {
  // В идеале сделать запрос на бэк, чтобы подтвердить статус админа.
  // Для простоты, если мы зашли под ID админа, показываем блок.
  // Замените "123456789" на ваш настоящий Telegram ID, чтобы увидеть админку во фронтенде.
  const MASTER_ADMIN_ID = "123456789";

  if (user.id.toString() === MASTER_ADMIN_ID) {
    document.getElementById("adminBadge").classList.remove("hidden");
    adminPanel.classList.remove("hidden");
  }
}

// Добавление нового временного слота админом
document.getElementById("addSlotBtn").onclick = async () => {
  const time = document.getElementById("adminTimeInput").value;
  const date = calendarInput.value;

  if (!time || !date) {
    alert("Выберите дату и время!");
    return;
  }

  const response = await fetch(`${API_URL}/api/admin/add-slot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ adminId: user.id.toString(), date, time }),
  });

  const result = await response.json();
  if (result.success) {
    loadData();
  } else {
    alert(result.error);
  }
};

// Удаление свободного слота времени
async function deleteSlot(slotId) {
  const response = await fetch(`${API_URL}/api/admin/delete-slot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ adminId: user.id.toString(), slotId }),
  });
  if ((await response.json()).success) loadData();
}

// Полное закрытие дня
document.getElementById("closeDayBtn").onclick = async () => {
  const date = calendarInput.value;
  if (!date) return;

  if (
    confirm(
      `Вы уверены, что хотите закрыть день ${date}? Все записи на этот день будут аннулированы!`,
    )
  ) {
    const response = await fetch(`${API_URL}/api/admin/close-day`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ adminId: user.id.toString(), date }),
    });
    if ((await response.json()).success) loadData();
  }
};

// Слушатель изменения даты в календаре
calendarInput.addEventListener("change", (e) => {
  const selectedDate = e.target.value;
  checkAdminUI(selectedDate);
  renderSlots(selectedDate);
});

// Первоначальный запуск
document.getElementById("userGreeting").innerText =
  `Привет, ${user.first_name}!`;
setupCalendarLimits();
loadData();
