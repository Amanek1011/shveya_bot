from aiogram import types
from aiogram.fsm.context import FSMContext

from db import db
from keyboards import get_cancel_keyboard
from service import user_service, keyboard_service, user_sessions
from states import UpakovkaStates


async def upakovka_start(call: types.CallbackQuery, state: FSMContext):
    """Упаковка начинает работу"""
    await state.set_state(UpakovkaStates.waiting_for_party_selection)

    keyboard = await keyboard_service.get_parties_keyboard()
    await call.message.answer("Выберите партию:", reply_markup=keyboard)
    await call.answer()


async def upakovka_party_selected(call: types.CallbackQuery, state: FSMContext):
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
    await state.set_state(UpakovkaStates.waiting_for_color_selection)

    await call.message.edit_text(
        f"Партия №{batch_number}\nВыберите цвет:",
        reply_markup=keyboard
    )
    await call.answer()


async def upakovka_color_selected(call: types.CallbackQuery, state: FSMContext):
    material_id = int(call.data.split("_")[1])

    # Получаем информацию о материале
    material = await db.get_material_by_id(material_id)
    color = material['color'] if material else "выбранный"
    user_name = await user_service.get_user_name(call.from_user.id)

    await state.update_data(material_id=material_id, color=color)
    await state.set_state(UpakovkaStates.waiting_for_count)

    await call.message.edit_text(
        f"Упаковщик: {user_name}\n"
        f"Цвет: {color}\n\n"
        "Введите количество упакованных футболок:",
        reply_markup=get_cancel_keyboard()
    )
    await call.answer()


async def upakovka_count_handler(message: types.Message, state: FSMContext):
    try:
        count = int(message.text)
        data = await state.get_data()
        user_name = await user_service.get_user_name(message.from_user.id)

        await db.update_ypakovka(data['material_id'], user_name, count)

        # Упрощенное сообщение об успехе
        await message.answer(
            f"✅ Записано: {count}шт\n"
        )

        # Сохраняем текущую партию
        if message.from_user.id not in user_sessions:
            user_sessions[message.from_user.id] = {}
        user_sessions[message.from_user.id]['current_party'] = data['batch_number']

        # Предлагаем продолжить или сменить партию
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(
            text="📝 Продолжить работу",
            callback_data=f"continue_work_{data['party_id']}"
        )
        builder.button(
            text="🔄 Сменить партию",
            callback_data="change_party"
        )
        builder.adjust(1)

        await message.answer(
            "Что хотите сделать дальше?",
            reply_markup=builder.as_markup()
        )

        await state.clear()

    except ValueError:
        await message.answer("Пожалуйста, введите число:")


# Обработчики для кнопок меню
async def upakovka_start_inline(message: types.Message, state: FSMContext):
    """Запуск работы для упаковки через меню"""

    class FakeCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
            self.data = "upakovka"

    fake_call = FakeCallback(message)
    await upakovka_start(fake_call, state)


async def upakovka_start_menu(message: types.Message, state: FSMContext):
    """Запуск работы для упаковки через меню (кнопку)"""
    user = await db.get_user(message.from_user.id)

    await state.set_state(UpakovkaStates.waiting_for_party_selection)

    keyboard = await keyboard_service.get_parties_keyboard(
        user['job'] if user else None,
        with_management=False
    )
    await message.answer("Выберите партию:", reply_markup=keyboard)


async def upakovka_continue_work(call: types.CallbackQuery, state: FSMContext, party_id: int = None):
    """Продолжить работу упаковка"""
    if not party_id:
        party_id = int(call.data.split("_")[2]) if call.data else None

    if not party_id:
        await call.message.answer("Ошибка: партия не указана")
        await call.answer()
        return

    party = await db.get_party_by_id(party_id)
    if not party:
        await call.message.answer("Партия не найдена")
        await call.answer()
        return

    keyboard = await keyboard_service.get_colors_keyboard(party_id)
    if not keyboard.inline_keyboard:
        await call.message.answer("В этой партии пока нет материалов")
        await call.answer()
        return

    await state.set_state(UpakovkaStates.waiting_for_color_selection)
    await state.update_data(party_id=party_id, batch_number=party['batch_number'])

    try:
        await call.message.edit_text(
            f"Партия №{party['batch_number']}\nВыберите цвет:",
            reply_markup=keyboard
        )
    except:
        await call.message.answer(
            f"Партия №{party['batch_number']}\nВыберите цвет:",
            reply_markup=keyboard
        )
    await call.answer()