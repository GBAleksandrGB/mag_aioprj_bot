from aiogram import Router, types, filters

from custom_filters import IsAdmin
from config import (SETTINGS,
                    QUESTIONS,
                    ORDERS,
                    CATALOG,
                    CART,
                    DELIVERY_STATUS)

menu_router = Router()


@menu_router.message(IsAdmin(), filters.Command("menu"))
async def admin_menu(message: types.Message):
    kbrd = [
        [types.KeyboardButton(text=SETTINGS)],
        [types.KeyboardButton(text=QUESTIONS),
         types.KeyboardButton(text=ORDERS)]
    ]
    markup = types.ReplyKeyboardMarkup(keyboard=kbrd,
                                       resize_keyboard=True,
                                       selective=True)
    await message.answer('меню', reply_markup=markup)


@menu_router.message(~IsAdmin(), filters.Command('menu'))
async def user_menu(message: types.Message):
    kbrd = [
        [types.KeyboardButton(text=CATALOG)],
        [types.KeyboardButton(text=CART),
         types.KeyboardButton(text=DELIVERY_STATUS)]
    ]
    markup = types.ReplyKeyboardMarkup(keyboard=kbrd,
                                       resize_keyboard=True,
                                       selective=True)
    await message.answer('меню', reply_markup=markup)
