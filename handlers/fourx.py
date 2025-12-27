from aiogram import types
from aiogram.fsm.context import FSMContext

from db import db
from keyboards import get_cancel_keyboard
from service import user_service, keyboard_service, user_sessions
from states import FourXStates


async def fourx_start(call: types.CallbackQuery, state: FSMContext):
    """4-х оператор начинает работу"""
    await state.set_state(FourXStates.waiting_for_party_selection)

    keyboard = await keyboard_service.get_parties_keyboard()
    await call.message.answer("Выберите партию:", reply_markup=keyboard)
    await call.answer()


async def fourx_party_selected(call: types.CallbackQuery, state: FSMContext):
    batch_number = call.data.split("_")[1]
    party = await db.get_party_by_number(batch_number)

    if not party:
        await call.message.answer("Партия не найдена")
        await call.answer()
        return

    # Получаем должность пользователя для отображения правильной клавиатуры
    user = await db.get_user(call.from_user.id)
    user_job = user['job'] if user else None

    keyboard = await keyboard_service.get_colors_keyboard(party['id'])
    if not keyboard.inline_keyboard:
        await call.message.answer("В этой партии пока нет материалов")
        await call.answer()
        return

    await state.update_data(party_id=party['id'], batch_number=batch_number)
    await state.set_state(FourXStates.waiting_for_color_selection)

    await call.message.edit_text(
        f"Партия №{batch_number}\nВыберите цвет:",
        reply_markup=keyboard
    )
    await call.answer()


async def fourx_color_selected(call: types.CallbackQuery, state: FSMContext):
    material_id = int(call.data.split("_")[1])

    try:
        # Получаем номер машинки пользователя из БД
        machine_number = await user_service.get_user_machine_number(call.from_user.id)

        if not machine_number:
            # Если номер машинки не указан, просим указать
            await state.update_data(material_id=material_id)
            await state.set_state(FourXStates.waiting_for_machine_number)

            await call.message.edit_text(
                "У вас не указан номер машинки.\n"
                "Введите номер машинки (например: Кундуз №3):",
                reply_markup=get_cancel_keyboard()
            )
        else:
            # Номер машинки есть, переходим к вводу количества
            await state.update_data(material_id=material_id, four_x=machine_number)
            await state.set_state(FourXStates.waiting_for_count)

            user_name = await user_service.get_user_name(call.from_user.id)

            await call.message.edit_text(
                f"Оператор: {user_name}\n"
                f"Машинка: {machine_number}\n"
                "Введите количество сделанных футболок:",
                reply_markup=get_cancel_keyboard()
            )

    except AttributeError as e:
        print(f"❌ Ошибка в fourx_color_selected: {e}")
        await call.message.answer("Ошибка при получении данных. Пожалуйста, попробуйте еще раз.")
        await state.clear()

    await call.answer()


async def fourx_machine_handler(message: types.Message, state: FSMContext):
    """Обработка номера машинки для 4-х оператора (если не было при регистрации)"""
    machine_number = message.text.strip()
    await state.update_data(four_x=machine_number)
    await state.set_state(FourXStates.waiting_for_count)

    try:
        # Сохраняем номер машинки в БД
        await user_service.update_user_machine_number(message.from_user.id, machine_number)

        user_name = await user_service.get_user_name(message.from_user.id)

        await message.answer(
            f"Оператор: {user_name}\n"
            f"Машинка: {machine_number}\n"
            "Введите количество сделанных футболок:",
            reply_markup=get_cancel_keyboard()
        )
    except AttributeError as e:
        print(f"❌ Ошибка в fourx_machine_handler: {e}")
        await message.answer("Ошибка при сохранении данных. Пожалуйста, попробуйте еще раз.")
        await state.clear()


async def fourx_count_handler(message: types.Message, state: FSMContext):
    try:
        count = int(message.text)
        data = await state.get_data()
        user_name = await user_service.get_user_name(message.from_user.id)

        await db.update_fourx(data['material_id'], data['four_x'], count)

        await message.answer(
            f"✅ Работа записана!\n"
            f"Партия: №{data['batch_number']}\n"
            f"Оператор: {user_name}\n"
            f"Машинка: {data['four_x']}\n"
            f"Количество: {count} шт"
        )

        if message.from_user.id not in user_sessions:
            user_sessions[message.from_user.id] = {}
        user_sessions[message.from_user.id]['current_party'] = data['batch_number']

        await state.clear()

    except ValueError:
        await message.answer("Пожалуйста, введите число:")


async def fourx_start_menu(message: types.Message, state: FSMContext):
    """Запуск работы для 4-х через меню (кнопку)"""
    user = await db.get_user(message.from_user.id)

    await state.set_state(FourXStates.waiting_for_party_selection)

    keyboard = await keyboard_service.get_parties_keyboard(
        user['job'] if user else None,
        with_management=False  # Убедитесь, что это есть
    )
    await message.answer("Выберите партию:", reply_markup=keyboard)