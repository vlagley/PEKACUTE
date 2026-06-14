"""
Утилита для проверки подписки пользователя на канал.
"""

from aiogram import Bot
from config import CHANNEL_ID


async def is_user_subscribed(bot: Bot, user_id: int) -> bool:
    """
    Проверяет, подписан ли пользователь на канал CHANNEL_ID.
    Возвращает True, если пользователь является участником, админом или создателем канала.
    """
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        # Если бот не админ канала или пользователь не найден - считаем, что не подписан
        return False
