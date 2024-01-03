from aiogram.fsm.context import FSMContext
from aiogram.filters.callback_data import CallbackData
from aiogram import types, F, Router, filters
from aiogram.enums.chat_action import ChatAction
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import loader

from custom_filters import IsAdmin
from config import (QUESTIONS,
                    CANCEL_MSG,
                    ALL_RIGHT_MSG,)


questions_router = Router()


class QuestionsCallback(CallbackData, prefix='questions'):
    cid: int
    action: str


@questions_router.message(IsAdmin(),
                          filters.or_f(F.text == QUESTIONS,
                                       filters.Command('sos')))
async def process_questions(message: types.Message):
    await loader.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    questions = loader.db.fetchall('SELECT * FROM questions')

    if len(questions) == 0:
        await message.answer('Нет вопросов.')
    else:
        builder = InlineKeyboardBuilder()

        for cid, question in questions:
            builder.button(text='Ответить',
                           callback_data=QuestionsCallback(cid=cid,
                                                           action='answer'))
            markup = builder.as_markup()
            await message.answer(question, reply_markup=markup)


class AnswerState(filters.state.StatesGroup):
    answer = filters.state.State()
    submit = filters.state.State()


@questions_router.callback_query(IsAdmin(),
                                 QuestionsCallback.filter(rule=(F.action == 'answer')))
async def process_answer(query: types.CallbackQuery,
                         callback_data: QuestionsCallback,
                         state: FSMContext):
    await state.update_data(cid=callback_data.cid)
    await query.message.answer('Напиши ответ.',
                               reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AnswerState.answer)


@questions_router.message(IsAdmin(), AnswerState.answer)
async def process_submit(message: types.Message,
                         state: FSMContext):
    await state.update_data(answer=message.text)
    await state.set_state(AnswerState.submit)
    await message.answer('Убедитесь, что не ошиблись в ответе.',
                         reply_markup=submit_markup())


def submit_markup():
    builder = ReplyKeyboardBuilder()
    builder.button(text=CANCEL_MSG)
    builder.button(text=ALL_RIGHT_MSG)
    markup = builder.as_markup()
    markup.resize_keyboard = True
    markup.selective = True
    return markup


@questions_router.message(IsAdmin(), F.text == CANCEL_MSG,
                          AnswerState.submit)
async def process_send_answer(message: types.Message,
                              state: FSMContext):
    await message.answer('Отменено!',
                         reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@questions_router.message(IsAdmin(), F.text == ALL_RIGHT_MSG,
                          AnswerState.submit)
async def process_send_answer(message: types.Message,
                              state: FSMContext):
    data = await state.get_data()
    answer = data['answer']
    cid = data['cid']
    question = loader.db.fetchone(
        'SELECT question FROM questions WHERE cid=?', (cid,))[0]
    loader.db.query('DELETE FROM questions WHERE cid=?', (cid,))
    text = f'Вопрос: <b>{question}</b>\n\nОтвет: <b>{answer}</b>'
    await message.answer('Отправлено!',
                         reply_markup=types.ReplyKeyboardRemove())
    await loader.bot.send_message(cid, text)
    await state.clear()
