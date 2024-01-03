from aiogram import filters
from aiogram.types import Message

from config import ADMINS


class IsAdmin(filters.Filter):
    async def __call__(self, message) -> bool:
        return message.from_user.id in ADMINS
