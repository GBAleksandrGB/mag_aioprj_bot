from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from aiogram.enums.chat_action import ChatAction
from aiogram import Router, F, types

from config import (CATALOG,
                    NOTHING,)
from custom_filters import IsAdmin
import loader


catalog_router = Router()


class CategoryCallback(CallbackData, prefix='category'):
    id: str
    action: str


def categories_markup():
    builder = InlineKeyboardBuilder()

    for idx, title in loader.db.fetchall('SELECT * FROM categories'):
        builder.button(text=title,
                       callback_data=CategoryCallback(id=idx, action='view'))

    markup = builder.as_markup()
    return markup


@catalog_router.message(~IsAdmin(), F.text == CATALOG)
async def process_catalog(message: types.Message):
    await message.answer('Выберите раздел, чтобы вывести список товаров:',
                         reply_markup=categories_markup())


@catalog_router.callback_query(~IsAdmin(),
                               CategoryCallback.filter(rule=(F.action == 'view')))
async def category_callback_handler(query: types.CallbackQuery,
                                    callback_data: CategoryCallback):
    products = loader.db.fetchall('''SELECT * FROM products product
    WHERE product.tag = (SELECT title FROM categories WHERE idx=?) 
    AND product.idx NOT IN (SELECT idx FROM cart WHERE cid = ?)''',
                                  (callback_data.id, query.message.chat.id))
    await query.answer('Все доступные товары.')
    await show_products(query.message, products)


class ProductCallback(CallbackData, prefix='product'):
    id: str
    action: str


def product_markup(idx='', price=0):
    builder = InlineKeyboardBuilder()
    builder.button(text=f'Добавить в корзину - {price}₽',
                   callback_data=ProductCallback(id=idx, action='add'))
    markup = builder.as_markup()
    return markup


async def show_products(m, products):

    if len(products) == 0:
        await m.answer(NOTHING)
    else:
        await loader.bot.send_chat_action(m.chat.id, ChatAction.TYPING)

        for idx, title, body, image, price, _ in products:
            markup = product_markup(idx, price)
            text = f'<b>{title}</b>\n\n{body}'
            await m.answer_photo(photo=image,
                                 caption=text,
                                 reply_markup=markup)


@catalog_router.callback_query(~IsAdmin(),
                               ProductCallback.filter(rule=(F.action == 'add')))
async def add_product_callback_handler(query: types.CallbackQuery,
                                       callback_data: ProductCallback):
    loader.db.query('INSERT INTO cart VALUES (?, ?, 1)',
                    (query.message.chat.id, callback_data.id))
    await query.answer('Товар добавлен в корзину!')
    await query.message.delete()
