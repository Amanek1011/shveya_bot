from aiogram import types

from aiogram.fsm.context import FSMContext


from db import db
from handlers.edit_operations import edit_operations_start
from keyboards import get_main_menu_keyboard, get_parties_keyboard, get_cancel_keyboard
from service import user_service,user_sessions,party_service
import handlers.zakroi as zakroi_handlers
import handlers.fourx as fourx_handlers
import handlers.raspash as raspash_handlers
import handlers.beika as beika_handlers
import handlers.strochka as strochka_handlers
import handlers.gorlo as gorlo_handlers
import handlers.ytyg as ytyg_handlers
import handlers.otk as otk_handlers
import handlers.upakovka as upakovka_handlers
import handlers.user_management as user_management_handlers
from states import ZakroiStates
import handlers.party_management as party_management_handlers


# ========== ОБЩИЕ КОМАНДЫ ==========
async def start_handler(message: types.Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)

    if user:
        print(f"👤 Пользователь {user['name']} (должность в БД: '{user['job']}') запустил бота")

        await message.answer(
            f"С возвращением, {user['name']}!",
            reply_markup=get_main_menu_keyboard(user['job'])
        )

        if 'current_party' not in user_sessions.get(message.from_user.id, {}):
            user_sessions[message.from_user.id] = {'current_party': None}

    else:
        from states import RegistrationStates
        await state.set_state(RegistrationStates.waiting_for_name)
        await message.answer(
            "Здравствуйте! Это бот для записи данных работы в швейном цеху.\n"
            "Пожалуйста, представьтесь - напишите ваше имя:"
        )


async def show_parties_command(message: types.Message):
    """Показать все партии"""
    user = await db.get_user(message.from_user.id)
    user_job = user['job'] if user else None

    parties = await db.get_all_parties()
    if not parties:
        await message.answer("Пока нет ни одной партии")
        return

    from keyboards import get_parties_keyboard
    keyboard = get_parties_keyboard(parties, user_job, with_management=False)

    await message.answer("Выберите партию:", reply_markup=keyboard)


async def cancel_handler(message: types.Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer("Действие отменено", reply_markup=types.ReplyKeyboardRemove())


async def me_command(message: types.Message):
    """Информация о пользователе"""
    user = await db.get_user(message.from_user.id)
    if user:
        machine_info = f"Машинка: {user['machine_number']}\n" if user['machine_number'] else ""
        await message.answer(
            f"Ваш профиль:\n"
            f"Имя: {user['name']}\n"
            f"Должность: {user['job']}\n"
            f"{machine_info}"
            f"ID: {user['tg_id']}"
        )
    else:
        await message.answer("Вы не зарегистрированы. Используйте /start")


async def reset_command(message: types.Message, state: FSMContext):
    """Сброс состояния"""
    await state.clear()
    await message.answer("Состояние сброшено. Используйте /start для регистрации.")


async def info_command(message: types.Message):
    """Показать информацию о текущей партии"""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    current_party = user_sessions.get(message.from_user.id, {}).get('current_party')
    if not current_party:
        await message.answer("У вас не выбрана текущая партия. Используйте 'Сменить партию'")
        return

    party = await db.get_party_by_number(current_party)
    if not party:
        await message.answer("Партия не найдена")
        return

    info = await party_service.format_party_info(party['id'])
    await message.answer(f"📦 Текущая партия: №{current_party}\n\n{info}")


async def party_selected_from_menu(call: types.CallbackQuery):
    """Обработка выбора партии из меню"""
    if not call.data.startswith("party_"):
        return

    batch_number = call.data.split("_")[1]
    party = await db.get_party_by_number(batch_number)

    if not party:
        await call.message.answer("Партия не найдена")
        await call.answer()
        return

    user = await db.get_user(call.from_user.id)
    user_job = user['job'] if user else None

    # Сохраняем выбранную партию
    if call.from_user.id not in user_sessions:
        user_sessions[call.from_user.id] = {}
    user_sessions[call.from_user.id]['current_party'] = batch_number

    # Разный текст для закройщика и оператора
    if user_service.is_zakroi_sync(user_job):
        # Для закройщика - полная информация
        info = await party_service.format_party_info(party['id'], user_job)
        await call.message.answer(
            f"✅ Выбрана партия №{batch_number}\n\n{info}",
            reply_markup=party_service.get_party_keyboard(party['id'], batch_number, user_job)
        )
    else:
        # Для оператора - упрощенный вид
        info = await party_service.format_party_simple(party['id'], user_job)
        await call.message.answer(
            f"✅ Выбрана партия №{batch_number}\n\n{info}",
            reply_markup=party_service.get_party_keyboard(party['id'], batch_number, user_job)
        )

    await call.answer()


async def cancel_callback(call: types.CallbackQuery, state: FSMContext):
    """Отмена через callback"""
    await state.clear()
    await call.message.edit_text("Действие отменено")
    await call.answer()


# ========== ОБРАБОТКА КНОПОК ГЛАВНОГО МЕНЮ ==========

async def new_record_handler(message: types.Message, state: FSMContext):
    """Обработка кнопки 'Новая запись' для закройщика"""
    user = await db.get_user(message.from_user.id)
    if user and user_service.is_zakroi_sync(user['job']):
        # Показываем список партий для выбора
        await zakroi_handlers.zakroi_start_menu(message, state)
    else:
        await message.answer("Эта функция доступна только закройщикам")


async def start_work_handler(message: types.Message, state: FSMContext):
    """Обработка кнопки 'Начать работу'"""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    job = user['job']
    print(f"🚀 Начало работы для {user['name']} ({job})")

    if job == '4-х':
        await fourx_handlers.fourx_start_menu(message, state)
    elif job == 'Распаш':
        await raspash_handlers.raspash_start_menu(message, state)
    elif job == 'Бейка':
        await beika_handlers.beika_start_menu(message, state)
    elif job == 'Строчка':
        await strochka_handlers.strochka_start_menu(message, state)
    elif job == 'Горло':
        await gorlo_handlers.gorlo_start_menu(message, state)
    elif job == 'Утюг':
        await ytyg_handlers.ytyg_start_menu(message, state)
    elif job == 'OTK':
        await otk_handlers.otk_start_menu(message, state)
    elif job == 'Упаковка':
        await upakovka_handlers.upakovka_start_menu(message, state)
    else:
        await message.answer(f"Для должности '{job}' нет активных действий")


async def change_party_handler(message: types.Message):
    """Обработка кнопки 'Сменить партию'"""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    parties = await db.get_all_parties()
    if not parties:
        await message.answer("Нет доступных партий")
        return

    # Для обычных пользователей - without management
    # Для закройщика - с кнопкой управления
    is_zakroi = user['job'] == 'Закрой'
    keyboard = get_parties_keyboard(parties, user['job'], with_management=False and not is_zakroi)
    await message.answer("Выберите партию для работы:", reply_markup=keyboard)


async def my_stats_handler(message: types.Message):
    """Обработка кнопки 'Моя статистика'"""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    current_party = user_sessions.get(message.from_user.id, {}).get('current_party', 'не выбрана')

    # Получаем статистику по работам пользователя
    async with db.pool.acquire() as conn:
        # Для каждой должности своя статистика
        if user['job'] == 'Закрой':
            materials_count = await conn.fetchval(
                "SELECT COUNT(*) FROM materials WHERE party_id IN (SELECT id FROM parties)"
            )
            stats_text = f"Создано материалов: {materials_count or 0}"
        else:
            # Для остальных должностей
            job_column = {
                '4-х': 'four_x_count',
                'Распаш': 'raspash_count',
                'Бейка': 'beika_count',
                'Строчка': 'strochka_count',
                'Горло': 'gorlo_count',
                'Утюг': 'ytyg_count',
                'OTK': 'otk_count',
                'Упаковка': 'ypakovka_count'
            }.get(user['job'])

            if job_column:
                total_count = await conn.fetchval(
                    f"SELECT SUM({job_column}) FROM materials WHERE {job_column} IS NOT NULL"
                )
                stats_text = f"Выполнено работ: {total_count or 0} шт"
            else:
                stats_text = "Статистика не доступна"

    await message.answer(
        f"📊 Ваша статистика:\n"
        f"Имя: {user['name']}\n"
        f"Должность: {user['job']}\n"
        f"Текущая партия: {current_party}\n"
        f"{stats_text}\n\n"
        f"Используйте /партии чтобы посмотреть все партии"
    )


async def all_parties_handler(message: types.Message):
    """Обработка кнопки 'Все партии'"""
    await show_parties_command(message)


async def handle_unknown(message: types.Message):
    """Обработка неизвестных сообщений"""
    user = await db.get_user(message.from_user.id)
    if user:
        await message.answer(
            "Неизвестная команда. Используйте кнопки меню или команды:\n"
            "/start - Главное меню\n"
            "/партии - Список партий\n"
            "/инфо - Информация о партии\n"
            "/me - Информация о себе\n"
            "/отмена - Отмена действия",
            reply_markup=get_main_menu_keyboard(user['job'])
        )
    else:
        await message.answer("Сначала пройдите регистрацию через /start")


async def change_machine_command(message: types.Message, state: FSMContext):
    """Сменить номер машинки"""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    if user['job'] != '4-х':
        await message.answer("Эта команда доступна только 4-х операторам")
        return

    from states import FourXStates
    await state.set_state(FourXStates.waiting_for_machine_number)
    await message.answer(
        "Введите новый номер машинки (например: Кундуз №3):",
        reply_markup=get_cancel_keyboard()
    )

async def manage_users_handler(message: types.Message, state: FSMContext):
    """Обработка кнопки 'Управление пользователями'"""
    await user_management_handlers.user_management_menu(message, state)

async def manage_users_command(message: types.Message, state: FSMContext):
    """Команда для управления пользователями"""
    await user_management_handlers.user_management_start(message, state)


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


async def manage_parties_handler(message: types.Message, state: FSMContext):
    """Обработка кнопки 'Управление партиями'"""
    print(f"🔍 Кнопка 'Управление партиями' нажата пользователем {message.from_user.id}")

    user = await db.get_user(message.from_user.id)

    if not user:
        print(f"❌ Пользователь не найден в БД")
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    print(f"✅ Пользователь найден: {user['name']}, должность: '{user['job']}'")

    # Временно отключаем проверку чтобы увидеть что происходит
    print(f"🔄 Переходим к управлению партиями...")
    await party_management_handlers.party_management_start(message, state)


async def check_my_data(message: types.Message):
    """Проверить мои данные в БД"""
    user = await db.get_user(message.from_user.id)

    if not user:
        await message.answer("Вы не зарегистрированы в БД")
        return

    # Проверяем все поля
    from keyboards import is_zakroi_sync, normalize_job_sync

    normalized_job = normalize_job_sync(user['job'])
    is_zakroi = is_zakroi_sync(user['job'])

    response = (
        f"📊 Ваши данные в БД:\n\n"
        f"ID: {user['id']}\n"
        f"Telegram ID: {user['tg_id']}\n"
        f"Имя: {user['name']}\n"
        f"Должность в БД: '{user['job']}'\n"
        f"Длина: {len(user['job'])}\n"
        f"Коды символов: {[ord(c) for c in str(user['job'])]}\n\n"
        f"Проверки:\n"
        f"Нормализованная должность: '{normalized_job}'\n"
        f"is_zakroi_sync: {is_zakroi}\n"
        f"user['job'] == 'Закрой': {user['job'] == 'Закрой'}\n"
        f"user['job'].lower() == 'закрой': {user['job'].lower() == 'закрой'}\n"
        f"user['job'] in ['Закрой', 'zakroi']: {user['job'] in ['Закрой', 'zakroi']}"
    )

    await message.answer(response)



async def back_to_parties(call: types.CallbackQuery):
    """Возврат к списку партий"""
    user = await db.get_user(call.from_user.id)
    user_job = user['job'] if user else None

    parties = await db.get_all_parties()
    if not parties:
        await call.message.answer("Пока нет ни одной партии")
        await call.answer()
        return

    from keyboards import get_parties_keyboard
    keyboard = get_parties_keyboard(parties, user_job, with_management=False)

    await call.message.edit_text(
        "Выберите партию:",
        reply_markup=keyboard
    )
    await call.answer()


async def add_material_callback(call: types.CallbackQuery, state: FSMContext):
    """Добавление материала к партии"""
    # Получаем ID партии из callback_data: add_material_{party_id}
    party_id = int(call.data.split("_")[2])

    # Получаем информацию о партии
    party = await db.get_party_by_id(party_id)
    if not party:
        await call.message.answer("Партия не найдена")
        await call.answer()
        return

    # Проверяем права (только закройщик)
    user = await db.get_user(call.from_user.id)
    if not user or not user_service.is_zakroi_sync(user['job']):
        await call.message.answer("Только закройщик может добавлять материалы")
        await call.answer()
        return

    # Начинаем процесс добавления материала
    from states import ZakroiStates
    await state.set_state(ZakroiStates.waiting_for_color)
    await state.update_data(
        party_id=party_id,
        batch_number=party['batch_number'],
        from_callback=True  # Флаг что мы пришли из callback
    )

    await call.message.answer(
        f"Добавление материала в партию №{party['batch_number']}\n"
        "Введите название цвета/материала (например: Грава, Бирюза):",
        reply_markup=get_cancel_keyboard()
    )
    await call.answer()


async def continue_work_callback(call: types.CallbackQuery, state: FSMContext):
    """Продолжить работу в той же партии"""
    party_id = int(call.data.split("_")[2])

    user = await db.get_user(call.from_user.id)
    if not user:
        await call.message.answer("Ошибка: пользователь не найден")
        await call.answer()
        return

    # Определяем должность и запускаем соответствующую работу
    job = user['job']

    if job == '4-х':
        await fourx_handlers.fourx_continue_work(call, state, party_id)
    elif job == 'Распаш':
        await raspash_handlers.raspash_continue_work(call, state, party_id)
    elif job == 'Бейка':
        await beika_handlers.beika_continue_work(call, state, party_id)
    elif job == 'Строчка':
        await strochka_handlers.strochka_continue_work(call, state, party_id)
    elif job == 'Горло':
        await gorlo_handlers.gorlo_continue_work(call, state, party_id)
    elif job == 'Утюг':
        await ytyg_handlers.ytyg_continue_work(call, state, party_id)
    elif job == 'OTK':
        await otk_handlers.otk_continue_work(call, state, party_id)
    elif job == 'Упаковка':
        await upakovka_handlers.upakovka_continue_work(call, state, party_id)
    else:
        await call.message.answer(f"Для должности '{job}' нет активных действий")
        await call.answer()


async def change_party_callback(call: types.CallbackQuery, state: FSMContext):
    """Сменить партию"""
    user = await db.get_user(call.from_user.id)
    if not user:
        await call.message.answer("Сначала пройдите регистрацию")
        await call.answer()
        return

    parties = await db.get_all_parties()
    if not parties:
        await call.message.answer("Нет доступных партий")
        await call.answer()
        return

    from keyboards import get_parties_keyboard
    keyboard = get_parties_keyboard(parties, user['job'], with_management=False)

    await call.message.edit_text(
        "Выберите партию для работы:",
        reply_markup=keyboard
    )
    await call.answer()


async def workers_stats_command(message: types.Message):
    """Команда для просмотра статистики работников"""
    user = await db.get_user(message.from_user.id)
    if not user or not user_service.is_zakroi_sync(user['job']):
        await message.answer("Эта команда доступна только закройщикам")
        return

    from handlers.worker_stats import full_workers_stats_callback

    class FakeCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
            self.data = "full_workers_stats"

    fake_call = FakeCallback(message)
    await full_workers_stats_callback(fake_call)


async def edit_operations_handler(message: types.Message, state: FSMContext):
    """Обработка кнопки 'Изменить показания'"""
    await edit_operations_start(message, state)