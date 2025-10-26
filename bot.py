import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "7466930103:AAFQp3rfNSer7-hIHLgVuokh6OtNvmwX2Y0"
ADMIN_ID = 897721072

dp = Dispatcher(storage=MemoryStorage())


class SupportState(StatesGroup):
    waiting_for_message = State()


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💬 Написать в поддержку")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await message.answer(
        "Привет! Добро пожаловать в бота\n\n"
        "💬 Поддержка - свяжись с администратором",
        reply_markup=keyboard,
        resize_keyboard=True,
    )


@dp.message(F.text == "💬 Написать в поддержку")
async def support_start(message: types.Message, state: FSMContext):
    await state.set_state(SupportState.waiting_for_message)

    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        "Напишите ваше сообщение для администратора:",
        reply_markup=cancel_keyboard,
        resize_keyboard=True,
    )


@dp.message(SupportState.waiting_for_message)
async def process_support_message(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💬 Написать в поддержку")]
            ],
            resize_keyboard=True
        )
        await message.answer("Отменено", reply_markup=keyboard, resize_keyboard=True)
        await state.clear()
        return

    try:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_{message.from_user.id}")]
            ]
        )

        await message.bot.send_message(
            ADMIN_ID,
            f"📨 Новое сообщение в поддержку!\n\n"
            f"👤 От: {message.from_user.full_name} (@{message.from_user.username or 'без username'})\n"
            f"🆔 ID: {message.from_user.id}\n\n"
            f"💬 Сообщение:\n{message.text}",
            reply_markup=keyboard,
        )

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💬 Написать в поддержку")]
            ],
            resize_keyboard=True
        )

        await message.answer(
            "Ваше сообщение отправлено администратору!\n"
            "Ожидайте ответа.",
            reply_markup=keyboard,
            resize_keyboard=True,
        )

    except Exception as e:
        await message.answer(
            "❌ Произошла ошибка при отправке сообщения.\n"
            "Попробуйте позже."
        )
    await state.clear()


@dp.callback_query(F.data.startswith("reply_"))
async def admin_reply_button(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав для этого действия!")
        return

    user_id = int(callback.data.split("_")[1])
    await state.update_data(reply_to_user=user_id)

    await callback.message.answer(
        f"Напишите ответ пользователю {user_id}:\n"
        "(Отправьте сообщение, и оно будет переслано пользователю)"
    )
    await callback.answer()


@dp.message(F.from_user.id == ADMIN_ID)
async def admin_reply_message(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    reply_to_user = user_data.get("reply_to_user")

    if reply_to_user:
        try:
            await message.bot.send_message(
                reply_to_user,
                f"📩 Ответ от администратора:\n\n{message.text}"
            )
            await message.answer("Ответ отправлен пользователю!")
            await state.clear()
        except Exception as e:
            await message.answer(f"Ошибка при отправке ответа: {str(e)}")


@dp.message()
async def handle_other_messages(message: types.Message):
    await message.answer(
        "Используйте кнопки меню для навигации по боту:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💬 Написать в поддержку")]
            ],
            resize_keyboard=True
        )
    )


async def main():
    bot = Bot(token=TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    print('Бот запущен!')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())