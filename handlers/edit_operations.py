from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import db
from service import user_service
from states import EditOperationsStates


async def edit_operations_start(message: types.Message, state: FSMContext):
    """Начало изменения показаний КОЛИЧЕСТВА футболок"""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    # Только операторы (не закройщики) могут менять свои показания
    if user_service.is_zakroi_sync(user['job']):
        await message.answer("Закройщики не могут менять свои показания через эту функцию")
        return

    await state.set_state(EditOperationsStates.waiting_for_party_selection)

    # Получаем ВСЕ партии и проверяем каждую
    all_parties = await db.get_all_parties()
    parties_with_work = []

    print(f"🔍 Поиск работ для {user['name']} ({user['job']})")
    print(f"🔍 Всего партий: {len(all_parties)}")

    for party in all_parties:
        materials = await db.get_materials_by_party(party['id'])
        print(f"🔍 Партия {party['batch_number']}: материалов {len(materials)}")

        for material in materials:
            # Проверяем, есть ли записи этого пользователя
            user_name = user['name'].strip().lower()
            found = False

            # Проверяем ВСЕ поля для этого пользователя
            if user['job'] == '4-х':
                if material['four_x'] and material['four_x'].strip().lower() == user_name:
                    print(f"   ✅ Нашел запись 4-х в материале {material['id']}: {material['four_x_count']}шт")
                    found = True
            elif user['job'] == 'Распаш':
                if material['raspash'] and material['raspash'].strip().lower() == user_name:
                    print(f"   ✅ Нашел запись Распаш в материале {material['id']}: {material['raspash_count']}шт")
                    found = True
            elif user['job'] == 'Бейка':
                if material['beika'] and material['beika'].strip().lower() == user_name:
                    print(f"   ✅ Нашел запись Бейка в материале {material['id']}: {material['beika_count']}шт")
                    found = True
            elif user['job'] == 'Строчка':
                if material['strochka'] and material['strochka'].strip().lower() == user_name:
                    print(f"   ✅ Нашел запись Строчка в материале {material['id']}: {material['strochka_count']}шт")
                    found = True
            elif user['job'] == 'Горло':
                if material['gorlo'] and material['gorlo'].strip().lower() == user_name:
                    found = True
            elif user['job'] == 'Утюг':
                if material['ytyg'] and material['ytyg'].strip().lower() == user_name:
                    found = True
            elif user['job'] == 'OTK':
                if material['otk'] and material['otk'].strip().lower() == user_name:
                    found = True
            elif user['job'] == 'Упаковка':
                if material['ypakovka'] and material['ypakovka'].strip().lower() == user_name:
                    found = True

            if found:
                if party not in parties_with_work:
                    parties_with_work.append(party)
                break  # Достаточно одной записи в партии

    print(f"✅ Всего найдено партий с работами: {len(parties_with_work)}")

    if not parties_with_work:
        await message.answer("У вас нет записанных работ для изменения.")
        return

    builder = InlineKeyboardBuilder()
    for party in parties_with_work:
        builder.button(
            text=f"Партия №{party['batch_number']}",
            callback_data=f"party_{party['batch_number']}"
        )

    builder.button(text="❌ Отмена", callback_data="cancel_edit")
    builder.adjust(1)

    await message.answer(
        "✏️ Изменение ваших показаний (количество футболок)\n"
        "Выберите партию:",
        reply_markup=builder.as_markup()
    )


async def edit_party_selected(call: types.CallbackQuery, state: FSMContext):
    """Выбор партии для редактирования КОЛИЧЕСТВА"""
    batch_number = call.data.split("_")[1]
    party = await db.get_party_by_number(batch_number)

    if not party:
        await call.message.answer("Партия не найдена")
        await call.answer()
        return

    user = await db.get_user(call.from_user.id)
    user_name = user['name'].strip().lower()

    print(f"🔍 Поиск работ в партии {batch_number} для {user['name']} ({user['job']})")

    # Получаем все материалы в партии
    materials = await db.get_materials_by_party(party['id'])
    user_materials = []

    for material in materials:
        print(f"🔍 Материал {material['id']} - цвет: {material['color']}")

        # Проверяем по всем полям для этой должности
        current_count = None
        operation_field = None
        found = False

        if user['job'] == '4-х':
            if material['four_x'] and material['four_x'].strip().lower() == user_name:
                current_count = material['four_x_count']
                operation_field = 'four_x_count'
                found = True
                print(
                    f"   ✅ four_x: '{material['four_x']}' == '{user_name}'? {material['four_x'].strip().lower() == user_name}")
                print(f"   ✅ Количество: {current_count}")
        elif user['job'] == 'Распаш':
            if material['raspash'] and material['raspash'].strip().lower() == user_name:
                current_count = material['raspash_count']
                operation_field = 'raspash_count'
                found = True
        elif user['job'] == 'Бейка':
            if material['beika'] and material['beika'].strip().lower() == user_name:
                current_count = material['beika_count']
                operation_field = 'beika_count'
                found = True
        elif user['job'] == 'Строчка':
            if material['strochka'] and material['strochka'].strip().lower() == user_name:
                current_count = material['strochka_count']
                operation_field = 'strochka_count'
                found = True
        elif user['job'] == 'Горло':
            if material['gorlo'] and material['gorlo'].strip().lower() == user_name:
                current_count = material['gorlo_count']
                operation_field = 'gorlo_count'
                found = True
        elif user['job'] == 'Утюг':
            if material['ytyg'] and material['ytyg'].strip().lower() == user_name:
                current_count = material['ytyg_count']
                operation_field = 'ytyg_count'
                found = True
        elif user['job'] == 'OTK':
            if material['otk'] and material['otk'].strip().lower() == user_name:
                current_count = material['otk_count']
                operation_field = 'otk_count'
                found = True
        elif user['job'] == 'Упаковка':
            if material['ypakovka'] and material['ypakovka'].strip().lower() == user_name:
                current_count = material['ypakovka_count']
                operation_field = 'ypakovka_count'
                found = True

        if found and current_count is not None:
            user_materials.append({
                'material': material,
                'current_count': current_count,
                'operation_field': operation_field
            })
            print(
                f"   ✅ Добавлена запись: ID={material['id']}, цвет={material['color']}, count={current_count}, поле={operation_field}")

    print(f"✅ Всего найдено записей: {len(user_materials)}")

    if not user_materials:
        await call.message.answer(
            f"В партии №{batch_number} у вас нет записанных работ.\n"
            f"Имя для поиска: '{user['name']}' (в нижнем регистре: '{user_name}')"
        )
        await state.clear()
        await call.answer()
        return

    await state.set_state(EditOperationsStates.waiting_for_color_selection)
    await state.update_data(
        party_id=party['id'],
        batch_number=batch_number,
        user_materials=user_materials
    )

    builder = InlineKeyboardBuilder()

    for item in user_materials:
        material = item['material']
        current_count = item['current_count']
        operation_field = item['operation_field']

        # Определяем название операции
        operation_name = {
            'four_x_count': '4-х',
            'raspash_count': 'Распаш',
            'beika_count': 'Бейка',
            'strochka_count': 'Строчка',
            'gorlo_count': 'Горло',
            'ytyg_count': 'Утюг',
            'otk_count': 'ОТК',
            'ypakovka_count': 'Упаковка'
        }.get(operation_field, 'работа')

        # ИСПРАВЛЕНИЕ: Проверяем что генерируем
        callback_data = f"edit_count_{material['id']}_{operation_field}"
        print(f"   📝 Генерируем колбэк: {callback_data}")

        builder.button(
            text=f"🎨 {material['color']} ({operation_name}): {current_count}шт",
            callback_data=callback_data
        )

    builder.button(text="❌ Отмена", callback_data="cancel_edit")
    builder.adjust(1)

    try:
        await call.message.edit_text(
            f"✏️ Партия №{batch_number}\n"
            "Выберите запись для изменения количества:",
            reply_markup=builder.as_markup()
        )
    except:
        await call.message.answer(
            f"✏️ Партия №{batch_number}\n"
            "Выберите запись для изменения количества:",
            reply_markup=builder.as_markup()
        )
    await call.answer()


async def edit_color_selected(call: types.CallbackQuery, state: FSMContext):
    """Выбор записи для изменения КОЛИЧЕСТВА футболок"""
    print(f"🔍 Колбэк данные: {call.data}")

    # ИСПРАВЛЕНИЕ: Правильно разбираем колбэк-данные
    if not call.data.startswith("edit_count_"):
        # Это не наш колбэк, пропускаем
        await call.answer()
        return

    parts = call.data.split("_")
    print(f"🔍 Разбитые части: {parts}")

    if len(parts) < 4:
        await call.message.answer("Некорректный запрос")
        await call.answer()
        return

    # parts: ['edit', 'count', '31', 'four'] или ['edit', 'count', '31', 'four', 'x', 'count']
    material_id = int(parts[2])

    # ИСПРАВЛЕНИЕ: Правильно собираем operation_field
    if len(parts) == 4:
        # Старый формат: edit_count_31_four
        operation_field = parts[3]  # 'four'
    else:
        # Новый формат: edit_count_31_four_x_count
        operation_field = '_'.join(parts[3:])  # 'four_x_count'

    print(f"🔍 Выбран материал ID: {material_id}, поле: {operation_field}")

    data = await state.get_data()
    user_materials = data.get('user_materials', [])

    print(f"🔍 Всего материалов в списке: {len(user_materials)}")
    print(f"🔍 Ожидаемые поля в списке:")
    for i, item in enumerate(user_materials):
        print(f"   {i}: ID={item['material']['id']}, поле={item['operation_field']}")

    # Находим выбранный материал
    selected_item = None
    for i, item in enumerate(user_materials):
        if item['material']['id'] == material_id:
            # ИСПРАВЛЕНИЕ: Проверяем только material_id, так как operation_field может не совпадать
            selected_item = item
            print(f"✅ Найден выбранный элемент по ID")
            break

    if not selected_item:
        print(f"❌ Запись не найдена: material_id={material_id}")
        await call.message.answer("Запись не найдена")
        await state.clear()
        await call.answer()
        return

    # ИСПРАВЛЕНИЕ: Берем operation_field из найденного элемента, а не из колбэка
    current_count = selected_item['current_count']
    operation_field = selected_item['operation_field']  # Используем правильное поле

    material = selected_item['material']

    print(f"✅ Материал найден: цвет={material['color']}, count={current_count}, поле={operation_field}")

    # Определяем название операции
    operation_name = {
        'four_x_count': '4-х',
        'raspash_count': 'Распаш',
        'beika_count': 'Бейка',
        'strochka_count': 'Строчка',
        'gorlo_count': 'Горло',
        'ytyg_count': 'Утюг',
        'otk_count': 'ОТК',
        'ypakovka_count': 'Упаковка'
    }.get(operation_field, 'работа')

    await state.update_data(
        material_id=material_id,
        edit_op_field=operation_field,
        edit_op_name=operation_name,
        current_count=current_count
    )
    await state.set_state(EditOperationsStates.waiting_for_new_count)

    from keyboards import get_cancel_keyboard

    try:
        await call.message.edit_text(
            f"✏️ Изменение показаний КОЛИЧЕСТВА\n"
            f"Партия: №{data['batch_number']}\n"
            f"Цвет: {material['color']}\n"
            f"Операция: {operation_name}\n"
            f"Текущее количество: {current_count}шт\n\n"
            f"Введите новое количество футболок:",
            reply_markup=get_cancel_keyboard()
        )
    except:
        await call.message.answer(
            f"✏️ Изменение показаний КОЛИЧЕСТВА\n"
            f"Партия: №{data['batch_number']}\n"
            f"Цвет: {material['color']}\n"
            f"Операция: {operation_name}\n"
            f"Текущее количество: {current_count}шт\n\n"
            f"Введите новое количество футболок:",
            reply_markup=get_cancel_keyboard()
        )
    await call.answer()


async def edit_count_handler(message: types.Message, state: FSMContext):
    """Обработка нового количества футболок"""
    try:
        new_count = int(message.text)
        data = await state.get_data()

        material_id = data.get('material_id')
        op_field = data.get('edit_op_field')
        op_name = data.get('edit_op_name')
        batch_number = data.get('batch_number')
        current_count = data.get('current_count')

        if not material_id or not op_field:
            await message.answer("Ошибка: данные не найдены")
            await state.clear()
            return

        # Обновляем количество в БД
        async with db.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE materials SET {op_field} = $1 WHERE id = $2",
                new_count, material_id
            )

        # Получаем материал для информации о цвете
        material = await db.get_material_by_id(material_id)

        # Вычисляем разницу
        difference = new_count - current_count
        diff_text = f"+{difference}" if difference > 0 else str(difference)

        await message.answer(
            f"✅ Показания обновлены!\n"
            f"Партия: №{batch_number}\n"
            f"Цвет: {material['color']}\n"
            f"Операция: {op_name}\n"
            f"Было: {current_count}шт\n"
            f"Стало: {new_count}шт\n"
            f"Изменение: {diff_text}шт\n\n"
            f"Вы можете продолжить редактирование через меню 'Изменить показания'."
        )

        await state.clear()

    except ValueError:
        await message.answer("Пожалуйста, введите число:")