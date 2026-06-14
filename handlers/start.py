"""
Хендлеры команды /start, главного меню, прайсов и портфолио.
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from keyboards import main_menu_kb, subscribe_kb, portfolio_kb
from config import CHANNEL_LINK
from utils import is_user_subscribed

router = Router()

WELCOME_TEXT = (
    "👋 <b>Добро пожаловать!</b>\n\n"
    "Я бот для записи на маникюр. С моей помощью вы можете:\n"
    "📅 Записаться на удобное время\n"
    "💰 Посмотреть прайс-лист\n"
    "🖼 Посмотреть портфолио работ\n\n"
    "Выберите действие в меню ниже 👇"
)

PRICES_TEXT = (
    "💅 <b>Прайс-лист</b>\n\n"
    "🔹 Френч — <b>1000₽</b>\n"
    "🔹 Квадрат — <b>500₽</b>"
)

PORTFOLIO_TEXT = "🖼 <b>Портфолио наших работ</b>\n\nНажмите на кнопку ниже, чтобы посмотреть 👇"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start - сбрасывает состояние и показывает главное меню."""
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await state.clear()
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "prices")
async def callback_prices(callback: CallbackQuery):
    """Показывает прайс-лист (без FSM)."""
    await callback.message.answer(PRICES_TEXT)
    await callback.answer()


@router.callback_query(F.data == "portfolio")
async def callback_portfolio(callback: CallbackQuery):
    """Показывает ссылку на портфолио."""
    await callback.message.answer(
        PORTFOLIO_TEXT,
        reply_markup=portfolio_kb("https://ru.pinterest.com/crystalwithluv/_created/"),
    )
    await callback.answer()


@router.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Проверяет подписку пользователя на канал после нажатия кнопки 'Проверить подписку'."""
    if await is_user_subscribed(bot, callback.from_user.id):
        await callback.answer("✅ Подписка подтверждена!", show_alert=True)
        await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_kb())
    else:
        await callback.answer(
            "❌ Вы еще не подписались на канал. Подпишитесь и попробуйте снова.",
            show_alert=True,
        )


async def send_subscription_required(callback: CallbackQuery):
    """Отправляет сообщение с требованием подписки на канал."""
    await callback.message.edit_text(
        "🔒 Для записи необходимо подписаться на канал.",
        reply_markup=subscribe_kb(CHANNEL_LINK),
    )
