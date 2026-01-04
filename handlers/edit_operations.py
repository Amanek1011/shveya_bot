# handlers/edit_operations.py
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import db
from service import user_service, keyboard_service
from states import EditOperationsStates



async def edit_operations_start(message: types.Message, state: FSMContext):
    """Начало изменения показаний"""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    # Только операторы (не закройщики) могут менять свои показания
    if user_service.is_zakroi_sync(user['job']):
        await message.answer("Закройщики не могут менять свои показания через эту функцию")
        return

    await state.set_state(EditOperationsStates.waiting_for_party_selection)

    keyboard = await keyboard_service.get_parties_keyboard(user['job'], with_management=False)
    await message.answer(
        "✏️ Изменение ваших показаний\n"
        "Выберите партию:",
        reply_markup=keyboard
    )


async def edit_party_selected(call: types.CallbackQuery, state: FSMContext):
    """Выбор партии для редактирования"""
    batch_number = call.data.split("_")[1]
    party = await db.get_party_by_number(batch_number)

    if not party:
        await call.message.answer("Партия не найдена")
        await call.answer()
        return

    user = await db.get_user(call.from_user.id)

    # Получаем материалы где этот пользователь что-то делал
    materials = await db.get_materials_by_party(party['id'])
    user_materials = []

    for material in materials:
        # Проверяем все операции этого пользователя
        user_operations = []

        # Проверяем все возможные операции
        if material['four_x'] == user['name'] and material['four_x_count']:
            user_operations.append(("4-х", material['four_x_count'], 'four_x_count'))
        if material['raspash'] == user['name'] and material['raspash_count']:
            user_operations.append(("Распаш", material['raspash_count'], 'raspash_count'))
        if material['beika'] == user['name'] and material['beika_count']:
            user_operations.append(("Бейка", material['beika_count'], 'beika_count'))
        if material['strochka'] == user['name'] and material['strochka_count']:
            user_operations.append(("Строчка", material['strochka_count'], 'strochka_count'))
        if material['gorlo'] == user['name'] and material['gorlo_count']:
            user_operations.append(("Горло", material['gorlo_count'], 'gorlo_count'))
        if material['ytyg'] == user['name'] and material['ytyg_count']:
            user_operations.append(("Утюг", material['ytyg_count'], 'ytyg_count'))
        if material['otk'] == user['name'] and material['otk_count']:
            user_operations.append(("ОТК", material['otk_count'], 'otk_count'))
        if material['ypakovka'] == user['name'] and material['ypakovka_count']:
            user_operations.append(("Упаковка", material['ypakovka_count'], 'ypakovka_count'))

        if user_operations:
            user_materials.append({
                'material': material,
                'operations': user_operations
            })

    if not user_materials:
        await call.message.answer(
            f"В партии №{batch_number} у вас нет записанных работ."
        )
        await state.clear()
        await call.answer()
        return

    await state.set_state(EditOperationsStates.waiting_for_color_selection)
    await state.update_data(party_id=party['id'], batch_number=batch_number, user_materials=user_materials)

    builder = InlineKeyboardBuilder()

    for item in user_materials:
        material = item['material']
        builder.button(
            text=f"🎨 {material['color']}",
            callback_data=f"edit_color_{material['id']}"
        )

    builder.button(text="❌ Отмена", callback_data="cancel_edit")
    builder.adjust(1)

    try:
        await call.message.edit_text(
            f"✏️ Партия №{batch_number}\n"
            "Выберите цвет для редактирования:",
            reply_markup=builder.as_markup()
        )
    except:
        await call.message.answer(
            f"✏️ Партия №{batch_number}\n"
            "Выберите цвет для редактирования:",
            reply_markup=builder.as_markup()
        )
    await call.answer()


async def edit_color_selected(call: types.CallbackQuery, state: FSMContext):
    """Выбор цвета для редактирования"""
    material_id = int(call.data.split("_")[2])

    data = await state.get_data()
    user_materials = data.get('user_materials', [])

    # Находим выбранный материал
    selected_item = None
    for item in user_materials:
        if item['material']['id'] == material_id:
            selected_item = item
            break

    if not selected_item:
        await call.message.answer("Материал не найден")
        await state.clear()
        await call.answer()
        return

    material = selected_item['material']
    operations = selected_item['operations']

    await state.update_data(
        material_id=material_id,
        selected_material=material,
        selected_operations=operations
    )
    await state.set_state(EditOperationsStates.waiting_for_operation)

    builder = InlineKeyboardBuilder()

    for op_name, op_count, op_field in operations:
        builder.button(
            text=f"{op_name}: {op_count}шт → изменить",
            callback_data=f"edit_op_{op_field}"
        )

    builder.button(text="❌ Отмена", callback_data="cancel_edit")
    builder.adjust(1)

    try:
        await call.message.edit_text(
            f"✏️ Редактирование работы:\n"
            f"Партия: №{data['batch_number']}\n"
            f"Цвет: {material['color']}\n\n"
            f"Выберите операцию для изменения:",
            reply_markup=builder.as_markup()
        )
    except:
        await call.message.answer(
            f"✏️ Редактирование работы:\n"
            f"Партия: №{data['batch_number']}\n"
            f"Цвет: {material['color']}\n\n"
            f"Выберите операцию для изменения:",
            reply_markup=builder.as_markup()
        )
    await call.answer()


async def edit_operation_selected(call: types.CallbackQuery, state: FSMContext):
    """Выбор операции для редактирования"""
    op_field = call.data.split("_")[2]  # Например: four_x_count

    data = await state.get_data()
    material = data.get('selected_material')
    operations = data.get('selected_operations', [])

    # Находим выбранную операцию
    selected_op = None
    for op_name, op_count, op_field_name in operations:
        if op_field_name == op_field:
            selected_op = (op_name, op_count, op_field_name)
            break

    if not selected_op:
        await call.message.answer("Операция не найдена")
        await state.clear()
        await call.answer()
        return

    await state.update_data(
        edit_op_field=op_field,
        edit_op_name=selected_op[0],
        current_count=selected_op[1]
    )
    await state.set_state(EditOperationsStates.waiting_for_new_count)

    from keyboards import get_cancel_keyboard

    try:
        await call.message.edit_text(
            f"✏️ Изменение {selected_op[0]}\n"
            f"Партия: №{data['batch_number']}\n"
            f"Цвет: {material['color']}\n"
            f"Текущее количество: {selected_op[1]}шт\n\n"
            f"Введите новое количество:",
            reply_markup=get_cancel_keyboard()
        )
    except:
        await call.message.answer(
            f"✏️ Изменение {selected_op[0]}\n"
            f"Партия: №{data['batch_number']}\n"
            f"Цвет: {material['color']}\n"
            f"Текущее количество: {selected_op[1]}шт\n\n"
            f"Введите новое количество:",
            reply_markup=get_cancel_keyboard()
        )
    await call.answer()


async def edit_count_handler(message: types.Message, state: FSMContext):
    """Обработка нового количества"""
    try:
        new_count = int(message.text)
        if new_count < 0:
            await message.answer("Количество не может быть отрицательным. Введите снова:")
            return

        data = await state.get_data()
        material_id = data.get('material_id')
        op_field = data.get('edit_op_field')
        op_name = data.get('edit_op_name')
        batch_number = data.get('batch_number')

        # Обновляем количество в БД
        async with db.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE materials SET {op_field} = $1 WHERE id = $2",
                new_count, material_id
            )

        await message.answer(
            f"✅ Показания обновлены!\n"
            f"Партия: №{batch_number}\n"
            f"Операция: {op_name}\n"
            f"Новое количество: {new_count}шт\n\n"
            f"Вы можете продолжить редактирование или вернуться в меню."
        )

        # Сбрасываем состояние
        await state.clear()

    except ValueError:
        await message.answer("Пожалуйста, введите число:")


async def cancel_edit_callback(call: types.CallbackQuery, state: FSMContext):
    """Отмена редактирования"""
    await state.clear()
    await call.message.answer("✏️ Редактирование отменено")
    await call.answer()