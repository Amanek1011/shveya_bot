from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Словарь для преобразования должностей (синхронный)
JOB_TRANSLATION = {
    'zakroi': 'Закрой',
    'Закрой': 'Закрой',
    'fourx': '4-х',
    '4-х': '4-х',
    'raspash': 'Распаш',
    'Распаш': 'Распаш',
    'beika': 'Бейка',
    'Бейка': 'Бейка',
    'strochka': 'Строчка',
    'Строчка': 'Строчка',
    'gorlo': 'Горло',
    'Горло': 'Горло',
    'ytyg': 'Утюг',
    'Утюг': 'Утюг',
    'otk': 'OTK',
    'OTK': 'OTK',
    'upakovka': 'Упаковка',
    'Упаковка': 'Упаковка'
}


# Синхронная функция нормализации должности
def normalize_job_sync(job: str) -> str:
    """Синхронно приводит должность к стандартному виду"""
    if not job:
        return job

    # Сначала проверяем точное совпадение
    if job in JOB_TRANSLATION:
        return JOB_TRANSLATION[job]

    # Проверяем регистронезависимо
    job_lower = job.lower()
    for key, value in JOB_TRANSLATION.items():
        if key.lower() == job_lower:
            return value

    # Если не нашли, возвращаем как есть
    return job


# Синхронная функция проверки закройщика
def is_zakroi_sync(job: str) -> bool:
    """Синхронно проверяет является ли должность закройщиком"""
    if not job:
        return False

    normalized = normalize_job_sync(job)
    return normalized == 'Закрой'


# Клавиатура выбора должности
def get_jobs_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='Закрой', callback_data='zakroi'),
            InlineKeyboardButton(text='4-х', callback_data='fourx'),
            InlineKeyboardButton(text='Распаш', callback_data='raspash'),
        ],
        [
            InlineKeyboardButton(text='Бейка', callback_data='beika'),
            InlineKeyboardButton(text='Строчка', callback_data='strochka'),
            InlineKeyboardButton(text='Горло', callback_data='gorlo'),
        ],
        [
            InlineKeyboardButton(text='Утюг', callback_data='ytyg'),
            InlineKeyboardButton(text='OTK', callback_data='otk'),
            InlineKeyboardButton(text='Упаковка', callback_data='upakovka'),
        ]
    ])


# Клавиатура отмены
def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='❌ Отмена', callback_data='cancel')]
    ])


# Клавиатура выбора партии с функциями управления
def get_parties_keyboard(parties, user_job=None, with_management=False):
    """
    with_management: если True, показывает кнопки управления (удалить) для каждой партии
    """
    builder = InlineKeyboardBuilder()

    # Нормализуем должность синхронно
    normalized_job = normalize_job_sync(user_job) if user_job else None

    for party in parties:
        if with_management and normalized_job == 'Закрой':
            # Для закройщика в режиме управления показываем кнопки с удалением
            builder.button(
                text=f"🗑️ Партия №{party['batch_number']}",
                callback_data=f"delete_party_{party['batch_number']}"
            )
        else:
            # Обычный выбор партии
            builder.button(
                text=f"Партия №{party['batch_number']}",
                callback_data=f"party_{party['batch_number']}"
            )

    # Показываем кнопку "Новая партия" только закройщикам
    if normalized_job == 'Закрой':
        builder.button(text="➕ Новая партия", callback_data="new_party")


    # Размещаем кнопки в зависимости от их количества
    if normalized_job == 'Закрой':
        if with_management:
            builder.adjust(1, 2, 1)  # По 1 партии в ряду (с иконкой), затем 2 кнопки, затем отмена
        else:
            builder.adjust(2, 2, 1, 1)  # 2 партии в ряду, затем 2, затем новая партия, затем отмена
    else:
        builder.adjust(2, 2, 1)  # 2 партии в ряду, затем 2, затем отмена

    return builder.as_markup()


# Клавиатура выбора цвета
def get_colors_keyboard(materials):
    builder = InlineKeyboardBuilder()

    for material in materials:
        builder.button(
            text=f"{material['color']}",
            callback_data=f"color_{material['id']}"
        )

    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


# Основное меню для работников
def get_main_menu_keyboard(job: str):
    """Основное меню для работников"""
    # Нормализуем должность СИНХРОННО
    normalized_job = normalize_job_sync(job)

    job_actions = {
        'Закрой': ['Новая запись', 'Управление партиями','Управление пользователями', 'Все партии'],
        '4-х': ['Начать работу', 'Сменить партию', 'Мои данные', 'Изменить показания'],
        'Распаш': ['Начать работу', 'Сменить партию', 'Мои данные', 'Изменить показания'],
        'Бейка': ['Начать работу', 'Сменить партию', 'Мои данные', 'Изменить показания'],
        'Строчка': ['Начать работу', 'Сменить партию', 'Мои данные', 'Изменить показания'],
        'Горло': ['Начать работу', 'Сменить партию', 'Мои данные', 'Изменить показания'],
        'Утюг': ['Начать работу', 'Сменить партию', 'Мои данные', 'Изменить показания'],
        'OTK': ['Начать работу', 'Сменить партию', 'Мои данные', 'Изменить показания'],
        'Упаковка': ['Начать работу', 'Сменить партию', 'Мои данные', 'Изменить показания']
    }

    # Если должность не найдена
    if normalized_job not in job_actions:
        print(f"⚠️ Должность '{job}' -> '{normalized_job}' не найдена в списке действий")

        # Возвращаем меню с базовыми кнопками
        keyboard = [
            [KeyboardButton(text='Начать работу')],
            [KeyboardButton(text='Сменить партию')],
            [KeyboardButton(text='Мои данные')]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    keyboard = []
    for action in job_actions.get(normalized_job, []):
        keyboard.append([KeyboardButton(text=action)])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_materials_management_keyboard(materials, party_id, user_job):
    """Клавиатура для управления материалами - УПРОЩЕННАЯ"""
    builder = InlineKeyboardBuilder()

    # Только кнопки удаления
    for material in materials:
        builder.button(
            text=f"🗑️ {material['color']}",
            callback_data=f"delete_material_{material['id']}"
        )

    builder.button(text="◀️ Назад", callback_data=f"party_back_{party_id}")

    builder.adjust(1)
    return builder.as_markup()


def get_party_keyboard(party_id: int, batch_number: str, user_job=None, show_add_more=False):
    """Создать клавиатуру для партии"""
    builder = InlineKeyboardBuilder()

    if is_zakroi_sync(user_job):
        if show_add_more:
            builder.button(
                text="➕ Добавить материал",
                callback_data=f"add_material_{party_id}"
            )
        else:
            builder.button(
                text="➕ Добавить материал",
                callback_data=f"add_material_{party_id}"
            )

        builder.button(
            text="🎨 Управление цветами",
            callback_data=f"manage_colors_{party_id}"
        )

        builder.button(
            text="👥 Кто что сделал",
            callback_data=f"view_workers_{party_id}"
        )

    else:
        # Клавиатура для оператора
        builder.button(
            text="🔄 Сменить партию",
            callback_data="change_party"
        )

        builder.button(
            text="📝 Продолжить работу",
            callback_data=f"continue_work_{party_id}"
        )

    builder.button(text="◀️ Назад", callback_data="back_to_parties")

    builder.adjust(1)
    return builder.as_markup()


def get_simple_colors_keyboard(materials, user_job=None):
    """Упрощенная клавиатура выбора цвета для операторов"""
    builder = InlineKeyboardBuilder()

    # Показываем цвета без ID, только названия
    colors_shown = set()
    for material in materials:
        color = material['color']
        if color not in colors_shown:
            builder.button(
                text=f"🎨 {color}",
                callback_data=f"color_{material['id']}"
            )
            colors_shown.add(color)

    builder.button(text="◀️ Назад", callback_data="back_to_parties")
    builder.adjust(1)
    return builder.as_markup()