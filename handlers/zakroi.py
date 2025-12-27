from aiogram import types
from aiogram.fsm.context import FSMContext

from db import db
from keyboards import get_cancel_keyboard
from service import user_sessions, PartyService
from states import ZakroiStates


async def zakroi_start(call: types.CallbackQuery, state: FSMContext):
    """Закройщик начинает работу"""
    await state.set_state(ZakroiStates.waiting_for_party_number)
    await call.message.answer(
        "Введите номер партии (например: 26):",
        reply_markup=get_cancel_keyboard()
    )
    await call.answer()


async def zakroi_party_handler(message: types.Message, state: FSMContext):
    batch_number = message.text.strip()

    # Добавляем партию если её нет
    from service import PartyService
    await PartyService.add_party_if_not_exists(batch_number)

    party = await db.get_party_by_number(batch_number)
    await state.update_data(party_id=party['id'], batch_number=batch_number)
    await state.set_state(ZakroiStates.waiting_for_color)

    await message.answer(
        f"Партия №{batch_number}\n"
        "Введите название цвета/материала (например: Грава, Бирюза):",
        reply_markup=get_cancel_keyboard()
    )


async def zakroi_color_handler(message: types.Message, state: FSMContext):
    color = message.text.strip()
    await state.update_data(color=color)
    await state.set_state(ZakroiStates.waiting_for_quantity_line)

    await message.answer(
        f"Цвет: {color}\n"
        "Введите количество линий:",
        reply_markup=get_cancel_keyboard()
    )


async def zakroi_quantity_handler(message: types.Message, state: FSMContext):
    try:
        quantity_line = int(message.text)
        if quantity_line <= 0:
            await message.answer("Количество линий должно быть больше 0. Введите снова:")
            return

        await state.update_data(quantity_line=quantity_line)

        # Автоматически рассчитываем количество футболок
        tshirt_count = quantity_line * 5

        await state.update_data(tshirt_count=tshirt_count)

        # Сразу добавляем запись в БД
        data = await state.get_data()

        success = await db.add_material(
            data['party_id'],
            data['color'],
            data['quantity_line'],
            tshirt_count
        )

        if success:
            # Получаем пользователя и информацию о партии
            user = await db.get_user(message.from_user.id)
            user_job = user['job'] if user else None

            party = await db.get_party_by_id(data['party_id'])

            if party:
                info = await PartyService.format_party_info(party['id'], user_job)

                # Проверяем пришли ли мы из callback (добавление из просмотра партии)
                from_callback = data.get('from_callback', False)

                if from_callback:
                    # Показываем обновленную информацию о партии с кнопкой "добавить еще"
                    keyboard = await PartyService.get_party_keyboard(
                        party['id'],
                        party['batch_number'],
                        user_job,
                        show_add_more=True
                    )

                    await message.answer(
                        f"✅ Материал добавлен!\n"
                        f"🎨 Цвет: {data['color']}\n"
                        f"📏 Линий: {data['quantity_line']}\n"
                        f"👕 Футболок: {tshirt_count}\n\n"
                        f"📦 Партия №{party['batch_number']}:\n\n{info}",
                        reply_markup=keyboard
                    )
                else:
                    # Обычное добавление через "Новая запись"
                    await message.answer(
                        f"✅ Запись добавлена!\n"
                        f"Партия: №{data['batch_number']}\n"
                        f"Цвет: {data['color']}\n"
                        f"Линий: {data['quantity_line']}\n"
                        f"Футболок: {tshirt_count} (автоматически рассчитано: {quantity_line} × 5)"
                    )

                    # Сохраняем текущую партию для пользователя
                    if message.from_user.id not in user_sessions:
                        user_sessions[message.from_user.id] = {}
                    user_sessions[message.from_user.id]['current_party'] = data['batch_number']

        else:
            await message.answer("❌ Ошибка при добавлении записи")

        await state.clear()

    except ValueError:
        await message.answer("Пожалуйста, введите число:")



# Обработчики для кнопок меню
async def new_party_command(message: types.Message, state: FSMContext):
    """Создание новой партии через команду"""

    user = await db.get_user(message.from_user.id)
    if not user or user['job'] != 'Закрой':
        await message.answer("Только закройщик может создавать новые партии")
        return

    await state.set_state(ZakroiStates.waiting_for_party_number)
    await message.answer(
        "Введите номер новой партии:",
        reply_markup=get_cancel_keyboard()
    )


async def new_party_callback(call: types.CallbackQuery, state: FSMContext):
    """Создание новой партии из меню"""

    user = await db.get_user(call.from_user.id)
    if not user or user['job'] != 'Закрой':
        await call.message.answer("Только закройщик может создавать новые партии")
        await call.answer()
        return

    await state.set_state(ZakroiStates.waiting_for_party_number)
    await call.message.edit_text(
        "Введите номер новой партии:",
        reply_markup=get_cancel_keyboard()
    )
    await call.answer()


async def zakroi_start_inline(message: types.Message, state: FSMContext):
    """Запуск работы для закройщика через меню"""

    class FakeCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
            self.data = "zakroi"

    fake_call = FakeCallback(message)
    await zakroi_start(fake_call, state)


async def zakroi_start_menu(message: types.Message, state: FSMContext):
    """Запуск работы для закройщика через меню (кнопку)"""
    # Сначала показываем список партий
    user = await db.get_user(message.from_user.id)
    user_job = user['job'] if user else None

    parties = await db.get_all_parties()
    if not parties:
        await message.answer("Нет доступных партий. Создайте новую партию.")
        return

    from keyboards import get_parties_keyboard
    keyboard = get_parties_keyboard(parties, user_job, with_management=False)

    await message.answer(
        "Выберите партию для добавления материала:",
        reply_markup=keyboard
    )