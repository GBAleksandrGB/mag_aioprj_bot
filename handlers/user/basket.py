import logging
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import Router, F, types, filters
from aiogram.enums.chat_action import ChatAction
from aiogram.fsm.context import FSMContext

import loader
from custom_filters import IsAdmin
from config import (CART,
                    CHECKOUT,
                    BACK,
                    NEXT,
                    ALL_RIGHT_MSG,
                    BACK_MSG,
                    CONFIRM_MSG,)


basket_router = Router()


class BasketCallback(CallbackData, prefix='basket'):
    id: str
    action: str


class BasketState(filters.state.StatesGroup):
    products = filters.state.State()
    check_cart = filters.state.State()
    name = filters.state.State()
    address = filters.state.State()
    confirm = filters.state.State()


def basket_markup(idx, count):
    builder = InlineKeyboardBuilder()
    builder.button(text=BACK,
                   callback_data=BasketCallback(id=idx,
                                                action='decrease'))
    builder.button(text=str(count),
                   callback_data=BasketCallback(id=idx,
                                                action='count'))
    builder.button(text=NEXT,
                   callback_data=BasketCallback(id=idx,
                                                action='increase'))
    markup = builder.as_markup()
    return markup


@basket_router.message(~IsAdmin(), F.text == CART)
async def process_cart(message: types.Message,
                       state: FSMContext):
    cart_data = loader.db.fetchall(
        'SELECT * FROM cart WHERE cid=?', (message.chat.id,))
    await state.set_state(BasketState.products)

    if len(cart_data) == 0:
        await message.answer('Ваша корзина пуста.')
    else:
        await loader.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        order_cost = 0

        for _, idx, count_in_cart in cart_data:
            product = loader.db.fetchone(
                'SELECT * FROM products WHERE idx=?', (idx,))

            if product is None:
                loader.db.query('DELETE FROM cart WHERE idx=?', (idx,))
            else:
                _, title, body, image, price, _ = product
                order_cost += price
                await state.update_data(products={idx: [title, price, count_in_cart]})
                markup = basket_markup(idx, count_in_cart)
                text = f'<b>{title}</b>\n\n{body}\n\nЦена: {price}₽.'
                await message.answer_photo(photo=image,
                                           caption=text,
                                           reply_markup=markup)

        if order_cost != 0:
            kbrd = [[types.KeyboardButton(text=CHECKOUT)]]
            markup = types.ReplyKeyboardMarkup(keyboard=kbrd,
                                               resize_keyboard=True,
                                               selective=True)
            await message.answer('Перейти к оформлению?',
                                 reply_markup=markup)


@basket_router.callback_query(~IsAdmin(),
                              BasketCallback.filter(rule=(F.action == 'count')))
@basket_router.callback_query(~IsAdmin(),
                              BasketCallback.filter(rule=(F.action == 'increase')))
@basket_router.callback_query(~IsAdmin(),
                              BasketCallback.filter(rule=(F.action == 'decrease')))
async def basket_callback_handler(query: types.CallbackQuery,
                                  callback_data: BasketCallback,
                                  state: FSMContext):
    idx = callback_data.id
    action = callback_data.action

    if 'count' == action:
        data = await state.get_data()

        if 'products' not in data.keys():
            await process_cart(query.message, state)
        else:
            await query.answer(f'Количество - {data["products"][idx][2]}')

    else:
        data = await state.get_data()

        if 'products' not in data.keys():
            await process_cart(query.message, state)
        else:
            data['products'][idx][2] += 1 if 'increase' == action else -1
            count_in_cart = data['products'][idx][2]

            if count_in_cart == 0:
                loader.db.query('''DELETE FROM cart
                                WHERE cid = ? AND idx = ?''',
                                (query.message.chat.id, idx))
                await query.message.delete()
            else:
                loader.db.query('''UPDATE cart SET quantity = ? 
                                WHERE cid = ? AND idx = ?''',
                                (count_in_cart, query.message.chat.id, idx))
                await query.message.edit_reply_markup(
                    reply_markup=basket_markup(idx, count_in_cart))


@basket_router.message(~IsAdmin(), F.text == CHECKOUT)
async def process_checkout(message: types.Message,
                           state: FSMContext):

    await state.set_state(BasketState.check_cart)
    await checkout(message, state)


async def checkout(message, state):
    answer = ''
    total_price = 0
    data = await state.get_data()

    for title, price, count_in_cart in data['products'].values():
        tp = count_in_cart * price
        answer += f'<b>{title}</b> * {count_in_cart}шт. = {tp}₽\n'
        total_price += tp

    await message.answer(f'{answer}\nОбщая сумма заказа: {total_price}₽.',
                         reply_markup=check_markup())


def check_markup():
    kbrd = [
        [types.KeyboardButton(text=BACK_MSG)],
        [types.KeyboardButton(text=ALL_RIGHT_MSG)]
    ]
    markup = types.ReplyKeyboardMarkup(keyboard=kbrd,
                                       resize_keyboard=True,
                                       selective=True)
    return markup


@basket_router.message(~IsAdmin(),
                       ~F.text.in_({ALL_RIGHT_MSG, BACK_MSG}),
                       BasketState.check_cart)
async def process_check_cart_invalid(message: types.Message):
    await message.reply('Такого варианта не было.')


@basket_router.message(~IsAdmin(), F.text == BACK_MSG,
                       BasketState.check_cart)
async def process_check_cart_back(message: types.Message,
                                  state: FSMContext):
    await state.clear()
    await process_cart(message, state)


@basket_router.message(~IsAdmin(), F.text == ALL_RIGHT_MSG,
                       BasketState.check_cart)
async def process_check_cart_all_right(message: types.Message,
                                       state: FSMContext):
    await state.set_state(BasketState.name)
    await message.answer('Укажите свое имя.',
                         reply_markup=back_markup())


def back_markup():
    kbrd = [[types.KeyboardButton(text=BACK_MSG)]]
    markup = types.ReplyKeyboardMarkup(keyboard=kbrd,
                                       resize_keyboard=True,
                                       selective=True)
    return markup


@basket_router.message(~IsAdmin(), F.text == BACK_MSG,
                       BasketState.name)
async def process_name_back(message: types.Message,
                            state: FSMContext):
    await state.set_state(BasketState.check_cart)
    await checkout(message, state)


@basket_router.message(~IsAdmin(),
                       BasketState.name)
async def process_name(message: types.Message,
                       state: FSMContext):
    await state.update_data(name=message.text)
    data = await state.get_data()

    if 'address' in data.keys():
        await confirm(message)
        await state.set_state(BasketState.confirm)
    else:
        await state.set_state(BasketState.address)
        await message.answer('Укажите свой адрес места жительства.',
                             reply_markup=back_markup())


@basket_router.message(~IsAdmin(), F.text == BACK_MSG,
                       BasketState.address)
async def process_address_back(message: types.Message,
                               state: FSMContext):
    data = await state.get_data()
    await message.answer('Изменить имя с <b>' + data['name'] + '</b>?',
                         reply_markup=back_markup())
    await state.set_state(BasketState.name)


@basket_router.message(~IsAdmin(),
                       BasketState.address)
async def process_address(message: types.Message,
                          state: FSMContext):
    await state.update_data(address=message.text)
    await confirm(message)
    await state.set_state(BasketState.confirm)


async def confirm(message):
    await message.answer(
        'Убедитесь, что все правильно оформлено и подтвердите заказ.',
        reply_markup=confirm_markup())


def confirm_markup():
    builder = ReplyKeyboardBuilder()
    builder.button(text=CONFIRM_MSG)
    builder.button(text=BACK_MSG)
    markup = builder.as_markup()
    markup.resize_keyboard = True
    markup.selective = True
    return markup


@basket_router.message(~IsAdmin(),
                       ~F.text.in_({CONFIRM_MSG, BACK_MSG}),
                       BasketState.confirm)
async def process_confirm_invalid(message: types.Message):
    await message.reply('Такого варианта не было.')


@basket_router.message(~IsAdmin(), F.text == BACK_MSG,
                       BasketState.confirm)
async def process_confirm(message: types.Message,
                          state: FSMContext):

    await state.set_state(BasketState.address)
    data = await state.get_data()
    await message.answer(f'Изменить адрес с <b> {data["address"]} </b>?',
                         reply_markup=back_markup())


@basket_router.message(~IsAdmin(), F.text == CONFIRM_MSG,
                       BasketState.confirm)
async def process_confirm(message: types.Message,
                          state: FSMContext):
    markup = types.ReplyKeyboardRemove()
    logging.info('Deal was made.')

    data = await state.get_data()
    cid = message.chat.id
    products = [idx + '=' + str(quantity)
                for idx, quantity in loader.db.fetchall(
                    '''SELECT idx, quantity FROM cart WHERE cid=?''', (cid,))]
    loader.db.query('INSERT INTO orders VALUES (?, ?, ?, ?)',
                    (cid, data['name'], data['address'], ' '.join(products)))
    loader.db.query('DELETE FROM cart WHERE cid=?', (cid,))
    await message.answer(f'Ок! Ваш заказ уже в пути 🚀\n'
                         f'Имя: <b> {data["name"]}'
                         f'</b>\nАдрес: <b> {data["address"]} </b>',
                         reply_markup=markup)
    await state.clear()
