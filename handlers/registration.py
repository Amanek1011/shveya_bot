from aiogram import types
from aiogram.fsm.context import FSMContext

from db import db
from keyboards import get_jobs_keyboard, get_main_menu_keyboard, get_cancel_keyboard
from states import RegistrationStates


async def name_handler(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(RegistrationStates.waiting_for_job)
    await message.answer(
        f"Приятно познакомиться, {message.text}!\n"
        "Теперь выберите вашу должность:",
        reply_markup=get_jobs_keyboard()
    )


async def job_selected(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data.get('name')

    # Словарь для преобразования callback_data в русские названия
    job_titles = {
        'zakroi': 'Закрой',
        'fourx': '4-х',
        'raspash': 'Распаш',
        'beika': 'Бейка',
        'strochka': 'Строчка',
        'gorlo': 'Горло',
        'ytyg': 'Утюг',
        'otk': 'OTK',
        'upakovka': 'Упаковка'
    }

    # Получаем русское название должности
    job_key = call.data
    job = job_titles.get(job_key, job_key)

    try:
        # Сохраняем русское название в БД
        await db.add_user(call.from_user.id, name, job, None)  # machine_number для закройщика None
        await state.clear()

        print(f"✅ Зарегистрирован: {name} как '{job}' (ключ: {job_key})")

        await call.message.answer(
            f"Отлично, {name}! Вы зарегистрированы как {job}.\n"
            "Теперь вы можете начать работу с ботом.",
            reply_markup=get_main_menu_keyboard(job)
        )
        await call.message.edit_reply_markup(reply_markup=None)

    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        await call.message.answer(f"Ошибка при регистрации: {e}")

    await call.answer()


async def machine_number_handler(message: types.Message, state: FSMContext):
    """Обработка номера машинки для 4-х оператора"""
    machine_number = message.text.strip()
    data = await state.get_data()
    name = data.get('name')
    job = data.get('job')

    try:
        # Сохраняем пользователя с номером машинки
        await db.add_user(message.from_user.id, name, job, machine_number)
        await state.clear()

        print(f"✅ Зарегистрирован 4-х оператор: {name} на машинке {machine_number}")

        await message.answer(
            f"Отлично, {name}!\n"
            f"Вы зарегистрированы как {job} на машинке {machine_number}.\n"
            "Теперь вы можете начать работу с ботом.",
            reply_markup=get_main_menu_keyboard(job)
        )

    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        await message.answer(f"Ошибка при регистрации: {e}")