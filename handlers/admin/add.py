from aiogram import F, filters, types, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.filters.callback_data import CallbackData
from aiogram.enums.chat_action import ChatAction
from hashlib import md5

import loader
from custom_filters import IsAdmin
from config import (SETTINGS,
                    DELETE_CATEGORY,
                    DELETE_PROD,
                    CANCEL_MSG,
                    ADD_PRODUCT,
                    BACK_MSG,
                    ALL_RIGHT_MSG)

add_router = Router()


class CategoryCallback(CallbackData, prefix='category'):
    id: str
    action: str


@add_router.message(IsAdmin(), F.text == SETTINGS)
async def process_settings(message: types.Message):
    builder = InlineKeyboardBuilder()

    for idx, title in loader.db.fetchall('SELECT * FROM categories'):
        builder.button(
            text=title,
            callback_data=CategoryCallback(id=idx, action='view'))

    builder.add(types.InlineKeyboardButton(
        text='+ Добавить категорию', callback_data='add_category'))
    builder.adjust(1)
    markup = builder.as_markup()
    markup.resize_keyboard = True
    await message.answer('Настройка категорий:', reply_markup=markup)


class CategoryState(filters.state.StatesGroup):
    title = filters.state.State()


@add_router.callback_query(IsAdmin(), F.data == 'add_category')
async def add_category_callback_query(query: types.CallbackQuery,
                                      state: FSMContext):
    await query.message.delete()
    await query.message.answer('Название категории?')
    await state.set_state(CategoryState.title)


@add_router.message(IsAdmin(), CategoryState.title)
async def set_category_title_handler(message: types.Message, state: FSMContext):
    category = message.text
    idx = md5(category.encode('utf-8')).hexdigest()
    loader.db.query('INSERT INTO categories VALUES (?, ?)', (idx, category))
    await state.clear()
    await process_settings(message)


@add_router.callback_query(IsAdmin(),
                           CategoryCallback.filter(rule=(F.action == 'view')))
async def category_callback_handler(query: types.CallbackQuery,
                                    callback_data: CategoryCallback,
                                    state: FSMContext):
    category_idx = callback_data.id
    products = loader.db.fetchall('''SELECT * FROM products product
    WHERE product.tag = (SELECT title FROM categories WHERE idx=?)''',
                                  (category_idx,))
    await query.message.delete()
    await query.answer('Все добавленные товары в эту категорию.')
    await state.update_data(category_index=category_idx)
    await show_products(query.message, products, category_idx)


class ProductCallback(CallbackData, prefix='product'):
    id: str
    action: str


async def show_products(m, products, category_idx):
    await loader.bot.send_chat_action(chat_id=m.chat.id,
                                      action=ChatAction.TYPING)

    for idx, title, body, image, price, tag in products:
        text_msg = f'<b>{title}</b>\n\n{body}\n\nЦена: {price} рублей.'
        builder = InlineKeyboardBuilder()
        builder.button(
            text=DELETE_PROD,
            callback_data=ProductCallback(id=idx, action='delete'))
        markup = builder.as_markup()
        await m.answer_photo(photo=image,
                             caption=text_msg,
                             reply_markup=markup)

    kbrd = [[types.KeyboardButton(text=ADD_PRODUCT)],
            [types.KeyboardButton(text=DELETE_CATEGORY)]]
    markup = types.ReplyKeyboardMarkup(keyboard=kbrd,
                                       resize_keyboard=True)
    await m.answer('Хотите что-нибудь добавить или удалить?',
                   reply_markup=markup)


@add_router.message(IsAdmin(), F.text == DELETE_CATEGORY)
async def delete_category_handler(message: types.Message,
                                  state: FSMContext):
    data = await state.get_data()

    if 'category_index' in data.keys():
        idx = data['category_index']
        loader.db.query(
            'DELETE FROM products WHERE tag IN (SELECT '
            'title FROM categories WHERE idx=?)',
            (idx,))
        loader.db.query('DELETE FROM categories WHERE idx=?', (idx,))
        await message.answer('Готово!',
                             reply_markup=types.ReplyKeyboardRemove())
        await process_settings(message)


class ProductState(filters.state.StatesGroup):
    title = filters.state.State()
    body = filters.state.State()
    image = filters.state.State()
    price = filters.state.State()
    confirm = filters.state.State()


@add_router.message(IsAdmin(), F.text == ADD_PRODUCT)
async def process_add_product(message: types.Message,
                              state: FSMContext):
    await state.set_state(ProductState.title)
    kbrd = [[types.KeyboardButton(text=CANCEL_MSG)]]
    markup = types.ReplyKeyboardMarkup(keyboard=kbrd,
                                       resize_keyboard=True)
    await message.answer('Название?', reply_markup=markup)


@add_router.message(IsAdmin(), F.text == CANCEL_MSG, ProductState.title)
async def process_cancel(message: types.Message, state: FSMContext):
    await message.answer('Ок, отменено!',
                         reply_markup=types.ReplyKeyboardRemove())
    await state.clear()
    await process_settings(message)


@add_router.message(IsAdmin(), ProductState.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(ProductState.body)
    await message.answer('Описание?', reply_markup=back_markup())


def back_markup():
    kbrd = [[types.KeyboardButton(text=BACK_MSG)]]
    markup = types.ReplyKeyboardMarkup(keyboard=kbrd,
                                       resize_keyboard=True,
                                       selective=True)
    return markup


@add_router.message(IsAdmin(), F.text == BACK_MSG, ProductState.title)
async def process_title_back(message: types.Message, state: FSMContext):
    await process_add_product(message)


@add_router.message(IsAdmin(), F.text == BACK_MSG, ProductState.body)
async def process_body_back(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(ProductState.title)
    await message.answer(f"Изменить название с <b>{data['title']}</b>?",
                         reply_markup=back_markup())


@add_router.message(IsAdmin(), ProductState.body)
async def process_body(message: types.Message, state: FSMContext):
    await state.update_data(body=message.text)
    await state.set_state(ProductState.image)
    await message.answer('Фото?', reply_markup=back_markup())


@add_router.message(IsAdmin(),
                    ProductState.image,
                    F.content_type == types.ContentType.PHOTO)
async def process_image_photo(message: types.Message, state: FSMContext):
    fileID = message.photo[0].file_id
    file_info = await loader.bot.get_file(fileID)
    downloaded_file = (await loader.bot.download_file(
        file_path=file_info.file_path)).read()
    await state.update_data(image=fileID)
    await state.set_state(ProductState.price)
    await message.answer('Цена?', reply_markup=back_markup())


@add_router.message(IsAdmin(), F.text.isdigit(), ProductState.price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    data = await state.get_data()
    await state.set_state(ProductState.confirm)
    text = f"<b>{data['title']}</b>\n\n{data['body']}\n\nЦена: {data['price']} рублей."
    markup = check_markup()
    await message.answer_photo(photo=data['image'],
                               caption=text,
                               reply_markup=markup)


def check_markup():
    kbrd = [
        [types.KeyboardButton(text=BACK_MSG)],
        [types.KeyboardButton(text=ALL_RIGHT_MSG)]
    ]
    markup = types.ReplyKeyboardMarkup(keyboard=kbrd,
                                       resize_keyboard=True,
                                       selective=True)
    return markup


@add_router.message(IsAdmin(),
                    F.text == ALL_RIGHT_MSG,
                    ProductState.confirm)
async def process_confirm(message: types.Message, state: FSMContext):
    data = await state.get_data()

    tag = loader.db.fetchone(
        'SELECT title FROM categories WHERE idx=?',
        (data['category_index'],))[0]

    idx = md5(' '.join(
        [data['title'], data['body'], data['price'], tag]).
        encode('utf-8')).hexdigest()

    loader.db.query('INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)',
                    (idx, data['title'], data['body'], data['image'],
                     int(data['price']), tag))

    await state.clear()
    await message.answer('Готово!',
                         reply_markup=types.ReplyKeyboardRemove())
    await process_settings(message)


@add_router.callback_query(IsAdmin(),
                           ProductCallback.filter(rule=(F.action == 'delete')))
async def delete_product_callback_handler(query: types.CallbackQuery,
                                          callback_data: ProductCallback):
    product_idx = callback_data.id
    loader.db.query('DELETE FROM products WHERE idx=?', (product_idx,))
    await query.answer('Удалено!')
    await query.message.delete()


@add_router.message(IsAdmin(), F.text == BACK_MSG, ProductState.confirm)
async def process_confirm_back(message: types.Message, state: FSMContext):
    await state.set_state(ProductState.price)
    data = await state.get_data()
    await message.answer(f"Изменить цену с <b>{data['price']}</b>?",
                         reply_markup=back_markup())


@add_router.message(IsAdmin(), F.content_type == types.ContentType.TEXT,
                    ProductState.image)
async def process_image_url(message: types.Message, state: FSMContext):
    if message.text == BACK_MSG:
        await state.set_state(ProductState.body)
        data = await state.get_data()
        await message.answer(f"Изменить описание с <b>{data['body']}</b>?",
                             reply_markup=back_markup())
    else:
        await message.answer('Вам нужно прислать фото товара.')


@add_router.message(IsAdmin(),
                    ~F.text.isdigit(),
                    ProductState.price)
async def process_price_invalid(message: types.Message, state: FSMContext):
    if message.text == BACK_MSG:
        await state.set_state(ProductState.image)
        # await state.get_data()
        await message.answer("Другое изображение?",
                             reply_markup=back_markup())
    else:
        await message.answer('Укажите цену в виде числа!')


@add_router.message(IsAdmin(),
                    ~(F.text.in_({BACK_MSG, ALL_RIGHT_MSG})),
                    ProductState.confirm)
async def process_confirm_invalid(message: types.Message, state: FSMContext):
    await message.answer('Такого варианта не было.')
