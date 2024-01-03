from aiogram import filters, Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import loader

from custom_filters import IsAdmin
from config import (CANCEL_MSG,
                    ALL_RIGHT_MSG,)


sos_router = Router()


class SosState(filters.state.StatesGroup):
    question = filters.state.State()
    submit = filters.state.State()


@sos_router.message(~IsAdmin(), filters.Command('sos'))
async def cmd_sos(message: types.Message,
                  state: FSMContext):
    await state.set_state(SosState.question)
    await message.answer(
        'В чем суть проблемы? Опишите как можно детальнее'
        ' и администратор обязательно вам ответит.',
        reply_markup=types.ReplyKeyboardRemove())


def submit_markup():
    builder = ReplyKeyboardBuilder()
    builder.button(text=CANCEL_MSG)
    builder.button(text=ALL_RIGHT_MSG)
    markup = builder.as_markup()
    markup.resize_keyboard = True
    markup.selective = True
    return markup


@sos_router.message(~IsAdmin(), SosState.question)
async def process_question(message: types.Message,
                           state: FSMContext):
    await state.update_data(question=message.text)
    await message.answer('Убедитесь, что все верно.',
                         reply_markup=submit_markup())
    await state.set_state(SosState.submit)


@sos_router.message(~IsAdmin(),
                    ~F.text.in_({CANCEL_MSG, ALL_RIGHT_MSG}),
                    SosState.submit)
async def process_price_invalid(message: types.Message):
    await message.answer('Такого варианта не было.')


@sos_router.message(~IsAdmin(), F.text == CANCEL_MSG, SosState.submit)
async def process_cancel(message: types.Message,
                         state: FSMContext):
    await message.answer('Отменено!',
                         reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@sos_router.message(~IsAdmin(), F.text == ALL_RIGHT_MSG, SosState.submit)
async def process_submit(message: types.Message,
                         state: FSMContext):
    cid = message.chat.id

    if loader.db.fetchone('SELECT * FROM questions WHERE cid=?',
                          (cid,)) is None:
        data = await state.get_data()
        loader.db.query('INSERT INTO questions VALUES (?, ?)',
                        (cid, data['question']))
        await message.answer('Отправлено!',
                             reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer(
            'Превышен лимит на количество задаваемых вопросов.',
            reply_markup=types.ReplyKeyboardRemove())

    await state.clear()
