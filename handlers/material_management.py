from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import db
from keyboards import get_cancel_keyboard
from service import party_service, user_service
from states import ZakroiStates, MaterialManagementStates


class MaterialManagementStates(StatesGroup):
    waiting_for_confirmation = State()


async def manage_materials_callback(call: types.CallbackQuery):
    """Управление материалами партии - УПРОЩЕННОЕ"""
    party_id = int(call.data.split("_")[2])

    user = await db.get_user(call.from_user.id)
    if not user or not user_service.is_zakroi_sync(user['job']):
        await call.message.answer("Только закройщик может управлять материалами")
        await call.answer()
        return

    materials = await db.get_materials_by_party(party_id)

    if not materials:
        await call.message.answer("В этой партии нет материалов")
        await call.answer()
        return

    party = await db.get_party_by_id(party_id)

    # Упрощенная клавиатура - только удаление по ID
    builder = InlineKeyboardBuilder()

    for material in materials:
        builder.button(
            text=f"🗑️ {material['color']} (ID: {material['id']})",
            callback_data=f"delete_material_{material['id']}"
        )

    builder.button(text="◀️ Назад к партии", callback_data=f"party_back_{party_id}")
    builder.adjust(1)  # Все кнопки в один столбец

    try:
        await call.message.edit_text(
            f"🗑️ Удаление материалов из партии №{party['batch_number']}\n"
            f"Выберите материал для удаления:",
            reply_markup=builder.as_markup()
        )
    except:
        await call.message.answer(
            f"🗑️ Удаление материалов из партии №{party['batch_number']}\n"
            f"Выберите материал для удаления:",
            reply_markup=builder.as_markup()
        )
    await call.answer()


async def delete_material_callback(call: types.CallbackQuery, state: FSMContext):
    """Выбор материала для удаления с подтверждением"""
    material_id = int(call.data.split("_")[2])

    material = await db.get_material_by_id(material_id)

    if not material:
        await call.message.answer("Материал не найден")
        await call.answer()
        return

    party = await db.get_party_by_id(material['party_id'])

    await state.set_state(MaterialManagementStates.waiting_for_confirmation)
    await state.update_data(
        material_id=material_id,
        material_color=material['color'],
        party_id=material['party_id'],
        batch_number=party['batch_number']
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data="confirm_material_delete")
    builder.button(text="❌ Нет, отменить", callback_data="cancel_material_delete")
    builder.adjust(2)  # Две кнопки в ряд

    try:
        await call.message.edit_text(
            f"Вы уверены, что хотите удалить материал?\n\n"
            f"Партия: №{party['batch_number']}\n"
            f"Цвет: {material['color']}\n"
            f"Линий: {material['quantity_line']}\n"
            f"Футболок: {material['tshirt_count']}",
            reply_markup=builder.as_markup()
        )
    except:
        await call.message.answer(
            f"Вы уверены, что хотите удалить материал?\n\n"
            f"Партия: №{party['batch_number']}\n"
            f"Цвет: {material['color']}\n"
            f"Линий: {material['quantity_line']}\n"
            f"Футболок: {material['tshirt_count']}",
            reply_markup=builder.as_markup()
        )
    await call.answer()


async def confirm_material_delete(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления материала"""
    data = await state.get_data()
    material_id = data.get('material_id')
    material_color = data.get('material_color')
    party_id = data.get('party_id')
    batch_number = data.get('batch_number')

    if not material_id:
        await call.message.answer("Ошибка: материал не выбран")
        await state.clear()
        await call.answer()
        return

    # Удаляем материал
    success = await db.delete_material(material_id)

    if success:
        text = f"✅ Материал '{material_color}' успешно удален из партии №{batch_number}!"
    else:
        text = f"❌ Ошибка при удалении материала"

    await state.clear()

    try:
        await call.message.edit_text(text)
    except:
        await call.message.answer(text)

    # Возвращаемся к управлению цветами
    if party_id:
        fake_call = create_fake_call(call, f"manage_colors_{party_id}")
        await manage_colors_callback(fake_call)

    await call.answer()


def create_fake_call(original_call, callback_data):
    """Создать fake callback для перехода"""

    class FakeCallback:
        def __init__(self, original_call, callback_data):
            self.message = original_call.message
            self.from_user = original_call.from_user
            self.data = callback_data

    return FakeCallback(original_call, callback_data)


async def cancel_material_delete(call: types.CallbackQuery, state: FSMContext):
    """Отмена удаления материала"""
    data = await state.get_data()
    party_id = data.get('party_id')

    await state.clear()
    await call.message.answer("❌ Удаление отменено")
    await call.answer()

    # Возвращаемся к управлению цветами
    if party_id:
        # Создаем новый fake call
        class FakeCallback:
            def __init__(self, original_call, party_id):
                self.message = original_call.message
                self.from_user = original_call.from_user
                self.data = f"manage_colors_{party_id}"

        fake_call = FakeCallback(call, party_id)
        await manage_colors_callback(fake_call)


async def party_back_callback(call: types.CallbackQuery):
    """Возврат к просмотру партии"""
    party_id = int(call.data.split("_")[2])

    party = await db.get_party_by_id(party_id)
    if not party:
        await call.message.answer("Партия не найдена")
        await call.answer()
        return

    user = await db.get_user(call.from_user.id)
    user_job = user['job'] if user else None

    info = await party_service.format_party_info(party_id, user_job)
    keyboard = party_service.get_party_keyboard(party_id, party['batch_number'], user_job)

    try:
        await call.message.edit_text(
            f"📦 Партия №{party['batch_number']}\n\n{info}",
            reply_markup=keyboard
        )
    except:
        await call.message.answer(
            f"📦 Партия №{party['batch_number']}\n\n{info}",
            reply_markup=keyboard
        )
    await call.answer()


async def manage_colors_callback(call: types.CallbackQuery = None, party_id: int = None):
    """Управление цветами - УПРОЩЕННОЕ (только изменение)"""
    # Если вызываем из confirm_material_delete, call.data будет неправильным
    # Поэтому передаем party_id отдельно

    if not party_id and call:
        # Получаем party_id из callback_data
        if call.data and call.data.startswith("manage_colors_"):
            party_id = int(call.data.split("_")[2])
        else:
            # Если нет callback_data, используем сохраненный party_id
            party_id = int(call.data.split("_")[2]) if call.data and "_" in call.data else None

    if not party_id:
        await call.message.answer("Ошибка: партия не указана")
        if call:
            await call.answer()
        return

    # Получаем user_id из call или создаем фейковый
    user_id = call.from_user.id if call else None

    if user_id:
        user = await db.get_user(user_id)
        if not user or not user_service.is_zakroi_sync(user['job']):
            await call.message.answer("Только закройщик может управлять цветами")
            if call:
                await call.answer()
            return

    party = await db.get_party_by_id(party_id)
    materials = await db.get_materials_by_party(party_id)

    if not materials:
        text = f"🎨 Изменение цветов\n"
        text += f"Партия: №{party['batch_number']}\n\n"
        text += "В этой партии пока нет цветов.\n"

        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад к партии", callback_data=f"party_back_{party_id}")
        builder.adjust(1)

        if call:
            try:
                await call.message.edit_text(text, reply_markup=builder.as_markup())
            except:
                await call.message.answer(text, reply_markup=builder.as_markup())
            await call.answer()
        return

    text = f"🎨 Изменение цветов\n"
    text += f"Партия: №{party['batch_number']}\n\n"

    builder = InlineKeyboardBuilder()

    for material in sorted(materials, key=lambda x: x['color']):
        # Кнопки изменения и удаления ПАРНО
        builder.button(
            text=f"✏️ {material['color']}",
            callback_data=f"edit_color_{material['id']}"
        )
        builder.button(
            text=f"🗑️",
            callback_data=f"delete_material_{material['id']}"
        )

    builder.button(text="◀️ Назад к партии", callback_data=f"party_back_{party_id}")

    # Размещаем кнопки: 2 в ряд (изменить и удалить), затем назад
    builder.adjust(2, 2, 1)

    if call:
        try:
            await call.message.edit_text(text, reply_markup=builder.as_markup())
        except:
            await call.message.answer(text, reply_markup=builder.as_markup())
        await call.answer()


async def edit_color_callback(call: types.CallbackQuery, state: FSMContext):
    """Редактирование цвета материала"""
    material_id = int(call.data.split("_")[2])

    material = await db.get_material_by_id(material_id)
    if not material:
        await call.message.answer("Материал не найден")
        await call.answer()
        return

    party = await db.get_party_by_id(material['party_id'])

    await state.set_state(ZakroiStates.waiting_for_color)
    await state.update_data(
        edit_mode=True,
        material_id=material_id,
        party_id=material['party_id'],
        batch_number=party['batch_number'],
        current_color=material['color']
    )

    try:
        await call.message.edit_text(
            f"✏️ Изменение цвета\n\n"
            f"Партия: №{party['batch_number']}\n"
            f"Текущий цвет: {material['color']}\n"
            f"ID материала: {material_id}\n\n"
            f"Введите новый цвет:",
            reply_markup=get_cancel_keyboard()
        )
    except:
        await call.message.answer(
            f"✏️ Изменение цвета\n\n"
            f"Партия: №{party['batch_number']}\n"
            f"Текущий цвет: {material['color']}\n"
            f"ID материала: {material_id}\n\n"
            f"Введите новый цвет:",
            reply_markup=get_cancel_keyboard()
        )
    await call.answer()