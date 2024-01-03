from aiogram import Router, types, F
import loader

from custom_filters import IsAdmin
from config import (DELIVERY_STATUS,)


delivery_router = Router()


@delivery_router.message(~IsAdmin(), F.text == DELIVERY_STATUS)
async def process_delivery_status(message: types.Message):
    orders = loader.db.fetchall('SELECT * FROM orders WHERE cid=?',
                                (message.chat.id,))
    if len(orders) == 0:
        await message.answer('У вас нет активных заказов.')
    else:
        await delivery_status_answer(message, orders)


async def delivery_status_answer(message, orders):
    res = ''

    for order in orders:
        res += f'Заказ <b>№{order[3]}</b>'
        answer = [
            ' лежит на складе.',
            ' уже в пути!',
            ' прибыл и ждет вас на почте!'
        ]

        res += answer[0]
        res += '\n\n'

    await message.answer(res)
