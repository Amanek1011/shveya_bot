from aiogram import types, F
from aiogram.fsm.context import FSMContext

from db import db
from keyboards import get_cancel_keyboard
from service import user_service, keyboard_service, user_sessions
from states import RaspashStates


async def raspash_start(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(RaspashStates.waiting_for_party_selection)

    keyboard = await keyboard_service.get_parties_keyboard()
    await call.message.answer("Выберите партию:", reply_markup=keyboard)
    await call.answer()


async def raspash_party_selected(call: types.CallbackQuery, state: FSMContext):
    batch_number = call.data.split("_")[1]
    party = await db.get_party_by_number(batch_number)

    if not party:
        await call.message.answer("Партия не найдена")
        await call.answer()
        return

    keyboard = await keyboard_service.get_colors_keyboard(party['id'])
    if not keyboard.inline_keyboard:
        await call.message.answer("В этой партии пока нет материалов")
        await call.answer()
        return

    await state.update_data(party_id=party['id'], batch_number=batch_number)
    await state.set_state(RaspashStates.waiting_for_color_selection)

    await call.message.edit_text(
        f"Партия №{batch_number}\nВыберите цвет:",
        reply_markup=keyboard
    )
    await call.answer()


async def raspash_color_selected(call: types.CallbackQuery, state: FSMContext):
    material_id = int(call.data.split("_")[1])
    await state.update_data(material_id=material_id)
    await state.set_state(RaspashStates.waiting_for_count)

    user_name = await user_service.get_user_name(call.from_user.id)

    await call.message.edit_text(
        f"Оператор: {user_name}\n"
        "Введите количество сделанных футболок:",
        reply_markup=get_cancel_keyboard()
    )
    await call.answer()


async def raspash_count_handler(message: types.Message, state: FSMContext):
    try:
        count = int(message.text)
        data = await state.get_data()
        user_name = await user_service.get_user_name(message.from_user.id)

        await db.update_raspash(data['material_id'], user_name, count)

        await message.answer(
            f"✅ Работа записана!\n"
            f"Партия: №{data['batch_number']}\n"
            f"Оператор: {user_name}\n"
            f"Количество: {count} шт"
        )

        if message.from_user.id not in user_sessions:
            user_sessions[message.from_user.id] = {}
        user_sessions[message.from_user.id]['current_party'] = data['batch_number']

        await state.clear()

    except ValueError:
        await message.answer("Пожалуйста, введите число:")


# Обработчики для кнопок меню
async def raspash_start_inline(message: types.Message, state: FSMContext):
    """Запуск работы для распаш через меню"""

    class FakeCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
            self.data = "raspash"

    fake_call = FakeCallback(message)
    await raspash_start(fake_call, state)


async def raspash_start_menu(message: types.Message, state: FSMContext):
    """Запуск работы для распаш через меню (кнопку)"""
    user = await db.get_user(message.from_user.id)

    await state.set_state(RaspashStates.waiting_for_party_selection)

    keyboard = await keyboard_service.get_parties_keyboard(
        user['job'] if user else None,
        with_management=False  # <-- ДОБАВИТЬ
    )
    await message.answer("Выберите партию:", reply_markup=keyboard)