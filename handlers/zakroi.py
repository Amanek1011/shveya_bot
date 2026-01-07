
from aiogram import types
from aiogram.fsm.context import FSMContext

from db import db
from keyboards import get_cancel_keyboard, get_main_menu_keyboard
from service import  user_sessions
from states import ZakroiStates
from config import ZAKROISHCHIK_ID


async def zakroi_start_menu(message: types.Message, state: FSMContext):
    """Запуск работы для закройщика через меню (кнопку)"""
    user = await db.get_user(message.from_user.id)
    if not user or user['job'] != 'Закрой':
        await message.answer("Только закройщик может создавать новые записи")
        return

    # Сначала проверяем есть ли партии
    parties = await db.get_all_parties()

    if not parties:
        # Если партий нет, сразу предлагаем создать новую
        await state.set_state(ZakroiStates.waiting_for_party_number)
        await message.answer(
            "Партий нет. Создайте новую партию:\n"
            "Введите номер новой партии (например: 100):",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Если партии есть, показываем список для выбора
    from keyboards import get_parties_keyboard
    keyboard = get_parties_keyboard(parties, user['job'], with_management=False)

    await message.answer(
        "Выберите партию для добавления материала:",
        reply_markup=keyboard
    )


async def auto_register_zakroishchik(bot):
    """Автоматически регистрирует закройщика при запуске бота"""
    try:
        # Проверяем, есть ли уже закройщик в БД
        existing_user = await db.get_user(ZAKROISHCHIK_ID)

        if not existing_user:
            # Регистрируем закройщика
            await db.add_user(
                tg_id=ZAKROISHCHIK_ID,
                name="Закройщик",
                job="Закрой",
                machine_number=None
            )
        else:
            print(f"✅ Закройщик уже в базе: {existing_user['name']}")

    except Exception as e:
        print(f"❌ Ошибка при регистрации закройщика: {e}")


async def zakroishchik_start(message: types.Message, state: FSMContext):
    """Старт для закройщика"""
    if message.from_user.id != ZAKROISHCHIK_ID:
        await message.answer("У вас нет доступа к этой функции")
        return

    await message.answer(
        "👋 Добро пожаловать, Закройщик!\n"
        "Вы можете управлять партиями и материалами.",
        reply_markup=get_main_menu_keyboard("Закрой")
    )


async def zakroi_party_handler(message: types.Message, state: FSMContext):
    """Обработка номера партии"""
    batch_number = message.text.strip()

    # Проверяем валидность номера
    if not batch_number:
        await message.answer("Номер партии не может быть пустым. Введите снова:")
        return

    # Сохраняем номер партии и переходим к вводу дизайна
    await state.update_data(batch_number=batch_number)
    await state.set_state(ZakroiStates.waiting_for_design)

    await message.answer(
        f"Номер партии: {batch_number}\n"
        f"Теперь введите название дизайна (например: Nike, Adidas, Puma):",
        reply_markup=get_cancel_keyboard()
    )


async def zakroi_design_handler(message: types.Message, state: FSMContext):
    """Обработка названия дизайна"""
    design = message.text.strip()
    data = await state.get_data()
    batch_number = data['batch_number']

    try:
        # Проверяем есть ли партия в БД
        print(f"🔍 Проверяю партию №{batch_number} в БД...")
        party = await db.get_party_by_number(batch_number)

        if party:
            print(f"✅ Партия найдена в БД: {party}")
            print(f"🔍 Дизайн в БД: '{party.get('design')}'")
        else:
            print(f"❌ Партия не найдена в БД")

        if not party:
            # Партии нет - создаем с дизайном
            success = await db.add_party(batch_number, design)

            if not success:
                print(f"❌ Не удалось создать партию")
                await message.answer(f"❌ Не удалось создать партию №{batch_number}")
                await state.clear()
                return
        else:
            # Партия уже есть - обновляем дизайн
            try:
                async with db.pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE parties SET design = $1 WHERE batch_number = $2",
                        design, batch_number
                    )
            except Exception as e:
                print(f"❌ Ошибка при обновлении дизайна: {e}")
                import traceback
                traceback.print_exc()

        # Получаем обновленную партию
        party = await db.get_party_by_number(batch_number)

        if not party:
            print(f"❌ Партия не найдена после обновления")
            await message.answer("❌ Ошибка: партия не найдена после создания")
            await state.clear()
            return

        await state.update_data(party_id=party['id'], design=design)
        await state.set_state(ZakroiStates.waiting_for_color)
        await message.answer(
            f"✅ Партия создана/обновлена!\n"
            f"Партия: №{batch_number}\n"
            f"Дизайн: {design}\n\n"
            f"Теперь введите название цвета/материала (например: Черный, Белый, Грава):",
            reply_markup=get_cancel_keyboard()
        )

    except Exception as e:
        print(f"❌ Критическая ошибка в zakroi_design_handler: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(f"Произошла ошибка: {e}")
        await state.clear()


async def zakroi_color_handler(message: types.Message, state: FSMContext):
    color = message.text.strip()
    data = await state.get_data()

    if data.get('edit_mode'):
        # Режим редактирования
        material_id = data.get('material_id')

        # Обновляем цвет в БД
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE materials SET color = $1 WHERE id = $2",
                color, material_id
            )

        party = await db.get_party_by_id(data['party_id'])

        await message.answer(
            f"✅ Цвет изменен!\n"
            f"Старый цвет: {data.get('current_color', 'неизвестно')}\n"
            f"Новый цвет: {color}\n"
            f"Партия: №{party['batch_number']}"
        )

        # Возвращаем к управлению цветами
        from handlers.material_management import manage_colors_callback

        # Создаем новый callback
        class FakeCallback:
            def __init__(self, message, party_id):
                self.message = message
                self.from_user = message.from_user
                self.data = f"manage_colors_{party_id}"

        fake_call = FakeCallback(message, data['party_id'])

        # Вызываем через create_task чтобы избежать проблем с answer
        import asyncio
        asyncio.create_task(manage_colors_callback(fake_call))

        await state.clear()
    else:
        # Обычный режим добавления
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
                from service import party_service

                info = await party_service.format_party_info_detailed(party['id'], user_job)

                from_callback = data.get('from_callback', False)

                if from_callback:
                    keyboard = party_service.get_party_keyboard(
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
                    await message.answer(
                        f"✅ Запись добавлена!\n"
                        f"Партия: №{data['batch_number']}\n"
                        f"Цвет: {data['color']}\n"
                        f"Линий: {data['quantity_line']}\n"
                        f"Футболок: {tshirt_count} (автоматически рассчитано: {quantity_line} × 5)"
                    )

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






