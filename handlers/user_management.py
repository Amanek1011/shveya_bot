from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import db
from keyboards import  is_zakroi_sync
from states import UserManagementStates


async def user_management_start(message: types.Message, state: FSMContext):
    """Начало управления пользователями"""
    user = await db.get_user(message.from_user.id)

    if not user:
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    # Используем синхронную проверку из keyboards.py
    is_zakroi = is_zakroi_sync(user['job'])

    print(f"🔍 Проверка доступа для управления пользователями:")
    print(f"   Пользователь: {user['name']}")
    print(f"   Должность: '{user['job']}'")
    print(f"   is_zakroi_sync: {is_zakroi}")

    if not is_zakroi:
        await message.answer("Эта функция доступна только закройщикам")
        return

    await state.set_state(UserManagementStates.waiting_for_action)

    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Список пользователей", callback_data="list_users")
    builder.button(text="🗑️ Удалить пользователя", callback_data="delete_user")
    builder.button(text="❌ Отмена", callback_data="cancel_user_management")
    builder.adjust(1)

    await message.answer(
        "Управление пользователями:\n"
        "Выберите действие:",
        reply_markup=builder.as_markup()
    )

async def user_management_action(call: types.CallbackQuery, state: FSMContext):
    """Обработка выбора действия"""
    action = call.data

    if action == "list_users":
        await list_all_users(call, state)
    elif action == "delete_user":
        await delete_user_start(call, state)
    elif action == "cancel_user_management":
        await state.clear()
        await call.message.edit_text("Управление пользователями отменено")
        await call.answer()

    await call.answer()


async def list_all_users(call: types.CallbackQuery, state: FSMContext):
    """Показать список всех пользователей"""
    users = await db.get_all_users()

    if not users:
        await call.message.answer("Пользователей нет")
        await state.clear()
        await call.answer()
        return

    user_list = "📋 Список пользователей:\n\n"
    for i, user in enumerate(users, 1):
        machine_info = f" | Машинка: {user['machine_number']}" if user['machine_number'] else ""
        user_list += f"{i}. {user['name']} - {user['job']}{machine_info}\n"

    await call.message.edit_text(user_list)
    await state.clear()
    await call.answer()


async def delete_user_start(call: types.CallbackQuery, state: FSMContext):
    """Начало процесса удаления пользователя"""
    users = await db.get_all_users()

    if not users:
        await call.message.answer("Пользователей для удаления нет")
        await state.clear()
        await call.answer()
        return

    builder = InlineKeyboardBuilder()
    for user in users:
        builder.button(
            text=f"{user['name']} - {user['job']}",
            callback_data=f"select_user_{user['id']}"
        )

    builder.button(text="❌ Отмена", callback_data="cancel_delete")
    builder.adjust(1)

    await state.set_state(UserManagementStates.waiting_for_user_selection)
    await call.message.edit_text(
        "Выберите пользователя для удаления:",
        reply_markup=builder.as_markup()
    )
    await call.answer()


async def select_user_for_deletion(call: types.CallbackQuery, state: FSMContext):
    """Выбор пользователя для удаления"""
    user_id = int(call.data.split("_")[2])
    user = await db.get_user_by_id(user_id)

    if not user:
        await call.message.answer("Пользователь не найден")
        await state.clear()
        await call.answer()
        return

    await state.update_data(selected_user_id=user_id, selected_user_name=user['name'])
    await state.set_state(UserManagementStates.waiting_for_confirmation)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data="confirm_delete")
    builder.button(text="❌ Нет, отменить", callback_data="cancel_delete")
    builder.adjust(2)

    await call.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить пользователя?\n"
        f"Имя: {user['name']}\n"
        f"Должность: {user['job']}\n"
        f"ID: {user['tg_id']}",
        reply_markup=builder.as_markup()
    )
    await call.answer()


async def confirm_user_deletion(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления пользователя"""
    data = await state.get_data()
    user_id = data.get('selected_user_id')
    user_name = data.get('selected_user_name')

    if not user_id:
        await call.message.answer("Ошибка: пользователь не выбран")
        await state.clear()
        await call.answer()
        return

    # Удаляем пользователя
    await db.delete_user(user_id)

    await call.message.edit_text(
        f"✅ Пользователь '{user_name}' успешно удален!"
    )

    await state.clear()
    await call.answer()


async def cancel_user_deletion(call: types.CallbackQuery, state: FSMContext):
    """Отмена удаления пользователя"""
    await state.clear()
    await call.message.edit_text("Удаление пользователя отменено")
    await call.answer()


async def user_management_menu(message: types.Message, state: FSMContext):
    """Обработка кнопки 'Управление пользователями' из меню"""
    await user_management_start(message, state)