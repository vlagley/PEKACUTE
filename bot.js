import { Bot, InlineKeyboard } from "grammy";
import dotenv from "dotenv";

dotenv.config();

export const bot = new Bot(process.env.BOT_TOKEN);
const webAppUrl = process.env.WEBAPP_URL;

// Функция отправки сообщений Администратору
export async function sendAdminNotification(text) {
  try {
    await bot.api.sendMessage(process.env.ADMIN_ID, text, {
      parse_mode: "Markdown",
    });
  } catch (err) {
    console.error("Ошибка отправки админу:", err);
  }
}

// Функция публикации логов в информационный канал
export async function sendChannelLog(text) {
  try {
    await bot.api.sendMessage(process.env.CHANNEL_ID, text, {
      parse_mode: "Markdown",
    });
  } catch (err) {
    console.error("Ошибка отправки в канал:", err);
  }
}

// Вспомогательная проверка подписки на канал
async function checkSubscription(ctx, userId) {
  try {
    const member = await ctx.api.getChatMember(process.env.CHANNEL_ID, userId);
    return ["creator", "administrator", "member"].includes(member.status);
  } catch (e) {
    return false;
  }
}

// Главное меню бота
function getMainMenu() {
  return {
    reply_markup: {
      keyboard: [
        [
          {
            text: "💅 Записаться / Личный кабинет",
            web_app: { url: webAppUrl },
          },
        ],
        [{ text: "💵 Прайсы" }, { text: "🖼️ Портфолио" }],
      ],
      resize_keyboard: true,
    },
  };
}

// Хендлер команды /start
bot.command("start", async (ctx) => {
  await ctx.reply(
    `Привет, ${ctx.from.first_name}! 👋\nЯ бот-ассистент студии маникюра. Здесь ты можешь выбрать удобное время, посмотреть прайс и примеры работ.`,
    getMainMenu(),
  );
});

// Кнопка "Прайсы" (HTML форматирование)
bot.hears("💵 Прайсы", async (ctx) => {
  const priceMessage = `
<b>📋 НАШ ПРАЙС-ЛИСТ:</b>
──────────────────
💅 Френч — <b>1000₽</b>
📐 Квадрат — <b>500₽</b>
──────────────────
<i>Идеальные ногти за 1.5 часа!</i>
    `;
  await ctx.reply(priceMessage, { parse_mode: "HTML" });
});

// Кнопка "Портфолио" (Инлайн-кнопка со ссылкой)
bot.hears("🖼️ Портфолио", async (ctx) => {
  const inlineKeyboard = new InlineKeyboard().url(
    "Смотреть портфолио",
    `https://t.me/${process.env.CHANNEL_USERNAME}`,
  );

  await ctx.reply(
    "Нажмите на кнопку ниже, чтобы открыть наш канал с работами:",
    {
      reply_markup: inlineKeyboard,
    },
  );
});

// Проверка подписки по нажатию инлайн-кнопки
bot.on("callback_query:data", async (ctx) => {
  if (ctx.callbackQuery.data === "check_sub") {
    const userId = ctx.from.id;
    const isSubscribed = await checkSubscription(ctx, userId);

    if (isSubscribed) {
      await ctx.answerCallbackQuery("Подписка подтверждена! 🎉");
      await ctx.reply(
        "Спасибо за подписку! Теперь вам открыт полный доступ к онлайн записи.",
        getMainMenu(),
      );
    } else {
      await ctx.answerCallbackQuery("Вы всё еще не подписаны 😔", {
        show_alert: true,
      });
    }
  }
});

// Перехват открытия WebApp для проверки обязательной подписки
bot.on("message", async (ctx, next) => {
  if (
    ctx.message.web_app_data ||
    (ctx.message.text && ctx.message.text.includes("Записаться"))
  ) {
    const isSubscribed = await checkSubscription(ctx, ctx.from.id);

    if (!isSubscribed) {
      const subKeyboard = new InlineKeyboard()
        .url("🚀 Подписаться", `https://t.me/${process.env.CHANNEL_USERNAME}`)
        .row()
        .text("✅ Проверить подписку", "check_sub");

      return await ctx.reply(
        "⚠️ Для записи необходимо подписаться на наш канал!",
        {
          reply_markup: subKeyboard,
        },
      );
    }
  }
  await next();
});

// Запуск бота
bot.start();
console.log("Telegram бот успешно запущен...");
