from aiogram import types, F, Router
import loader

from custom_filters import IsAdmin
from config import (ORDERS,)


orders_router = Router()


@orders_router.message(IsAdmin(), F.text == ORDERS)
async def process_orders(message: types.Message):
    orders = loader.db.fetchall('SELECT * FROM orders')

    if len(orders) == 0:
        await message.answer('У вас нет заказов.')
    else:
        await order_answer(message, orders)


async def order_answer(message, orders):
    res = ''

    for order in orders:
        res += f'Заказ <b>№{order[3]}</b>\n\n'

    await message.answer(res)
