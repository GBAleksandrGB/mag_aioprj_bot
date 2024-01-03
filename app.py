import asyncio
import sys
import logging
from aiogram import types, filters, F

import loader
from config import ADMIN, USER, ADMINS, START_MSG, ADMIN_MODE, USER_MODE


@loader.dp.message(filters.CommandStart())
async def start_handler(message: types.Message):
    kbrd = [
        [types.KeyboardButton(text=USER),
         types.KeyboardButton(text=ADMIN)]
    ]
    markup = types.ReplyKeyboardMarkup(keyboard=kbrd,
                                       resize_keyboard=True)
    await message.answer(START_MSG, reply_markup=markup)


@loader.dp.message(F.text == ADMIN)
async def admin_mode_handler(message: types.Message):
    cid = message.chat.id

    if cid not in ADMINS:
        ADMINS.append(cid)

    await message.answer(text=ADMIN_MODE,
                         reply_markup=types.ReplyKeyboardRemove())


@loader.dp.message(F.text == USER)
async def user_mode_handler(message: types.Message):
    cid = message.chat.id

    if cid in ADMINS:
        ADMINS.remove(cid)

    await message.answer(text=USER_MODE,
                         reply_markup=types.ReplyKeyboardRemove())


async def main() -> None:
    await loader.dp.start_polling(loader.bot)


if __name__ == "__main__":
    loader.db.create_tables()
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
