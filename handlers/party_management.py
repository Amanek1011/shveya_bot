from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import db
from keyboards import  get_parties_keyboard, is_zakroi_sync, normalize_job_sync
from states import PartyManagementStates


async def party_management_start(message: types.Message, state: FSMContext):
    """Начало управления партиями"""
    user = await db.get_user(message.from_user.id)

    if not user:
        print(f"❌ Пользователь не найден")
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    # Детальная проверка
    normalized_job = normalize_job_sync(user['job'])
    is_zakroi = is_zakroi_sync(user['job'])

    if not is_zakroi:
        await message.answer("Эта функция доступна только закройщикам")
        return

    await state.set_state(PartyManagementStates.waiting_for_action)

    builder = InlineKeyboardBuilder()
    builder.button(text="🗑️ Удалить партию", callback_data="delete_party_action")
    builder.button(text="📋 Список всех партий", callback_data="list_all_parties")
    builder.button(text="❌ Отмена", callback_data="cancel_party_management")
    builder.adjust(1)

    await message.answer(
        "⚙️ Управление партиями:\n"
        "Выберите действие:",
        reply_markup=builder.as_markup()
    )


async def party_management_action(call: types.CallbackQuery, state: FSMContext):
    """Обработка выбора действия"""
    action = call.data

    if action == "delete_party_action":
        await delete_party_start(call, state)
    elif action == "list_all_parties":
        await list_all_parties_with_info(call, state)
    elif action == "cancel_party_management":
        await state.clear()
        await call.message.edit_text("Управление партиями отменено")
        await call.answer()

    await call.answer()


async def list_all_parties_with_info(call: types.CallbackQuery, state: FSMContext):
    """Показать список всех партий с информацией"""
    parties = await db.get_all_parties()

    if not parties:
        await call.message.answer("Партий нет")
        await state.clear()
        await call.answer()
        return



    party_list = "📋 Список всех партий:\n\n"
    for i, party in enumerate(parties, 1):
        # Получаем количество материалов в партии
        materials_count = await db.get_materials_count_by_party(party['id'])

        party_list += f"{i}. Партия №{party['batch_number']}\n"
        party_list += f"   Создана: {party['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
        party_list += f"   Материалов: {materials_count}\n\n"

    await call.message.edit_text(party_list)
    await state.clear()
    await call.answer()


async def delete_party_start(call: types.CallbackQuery, state: FSMContext):
    """Начало процесса удаления партии"""
    parties = await db.get_all_parties()

    if not parties:
        await call.message.answer("Партий для удаления нет")
        await state.clear()
        await call.answer()
        return

    await state.set_state(PartyManagementStates.waiting_for_party_selection)

    # Используем клавиатуру с кнопками удаления
    keyboard = get_parties_keyboard(parties, user_job='Закрой', with_management=True)

    await call.message.edit_text(
        "🗑️ Выберите партию для удаления:\n"
        "⚠️ Внимание: при удалении партии удалятся все связанные материалы!",
        reply_markup=keyboard
    )
    await call.answer()


async def select_party_for_deletion(call: types.CallbackQuery, state: FSMContext):
    """Выбор партии для удаления"""
    batch_number = call.data.split("_")[2]  # delete_party_26 -> 26
    party = await db.get_party_by_number(batch_number)

    if not party:
        await call.message.answer("Партия не найдена")
        await state.clear()
        await call.answer()
        return

    # Получаем информацию о материалах в партии
    materials_count = await db.get_materials_count_by_party(party['id'])

    await state.update_data(
        selected_party_number=batch_number,
        selected_party_id=party['id'],
        materials_count=materials_count
    )
    await state.set_state(PartyManagementStates.waiting_for_confirmation)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data="confirm_party_delete")
    builder.button(text="❌ Нет, отменить", callback_data="cancel_party_delete")
    builder.adjust(2)

    warning_text = ""
    if materials_count > 0:
        warning_text = f"\n⚠️ В партии {materials_count} материалов, они также будут удалены!"

    await call.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить партию №{batch_number}?\n"
        f"Дата создания: {party['created_at'].strftime('%d.%m.%Y %H:%M')}"
        f"{warning_text}",
        reply_markup=builder.as_markup()
    )
    await call.answer()


async def confirm_party_deletion(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления партии"""
    data = await state.get_data()
    batch_number = data.get('selected_party_number')
    materials_count = data.get('materials_count', 0)

    if not batch_number:
        await call.message.answer("Ошибка: партия не выбрана")
        await state.clear()
        await call.answer()
        return

    # Удаляем партию
    success = await db.delete_party(batch_number)

    if success:
        materials_text = f" и {materials_count} материалов" if materials_count > 0 else ""
        await call.message.edit_text(
            f"✅ Партия №{batch_number}{materials_text} успешно удалена!"
        )
    else:
        await call.message.edit_text(
            f"❌ Ошибка при удалении партии №{batch_number}"
        )

    await state.clear()
    await call.answer()


async def cancel_party_deletion(call: types.CallbackQuery, state: FSMContext):
    """Отмена удаления партии"""
    await state.clear()
    await call.message.edit_text("Удаление партии отменено")
    await call.answer()


async def manage_parties_callback(call: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Управление партиями'"""
    user = await db.get_user(call.from_user.id)
    if not user or user['job'] != 'Закрой':
        await call.message.answer("Эта функция доступна только закройщикам")
        await call.answer()
        return

    await party_management_start(call.message, state)
    await call.answer()


async def party_management_menu(message: types.Message, state: FSMContext):
    """Обработка кнопки 'Управление партиями' из меню"""
    await party_management_start(message, state)