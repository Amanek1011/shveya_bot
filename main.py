import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DB_HOST, DB_PORT, DB_NAME
from db import db

# Импортируем все обработчики
from handlers.common import (
    start_handler, show_parties_command, cancel_handler,
    me_command, reset_command, info_command,
    party_selected_from_menu, cancel_callback,
    # Добавляем обработчики кнопок меню
    new_record_handler, start_work_handler,
    change_party_handler, my_stats_handler, all_parties_handler, change_machine_command, manage_users_handler,
    manage_users_command, manage_parties_handler, check_my_data, back_to_parties, add_material_callback,
    continue_work_callback, change_party_callback, edit_operations_handler, check_db_data
)
from handlers.edit_operations import (
    edit_party_selected, edit_color_selected,
)
from handlers.registration import name_handler, job_selected, machine_number_handler
from handlers.worker_stats import view_workers_callback
from handlers.zakroi import (
    zakroi_party_handler, zakroi_color_handler,
    zakroi_quantity_handler,
    new_party_command, new_party_callback, zakroishchik_start
)

from handlers.fourx import (
    fourx_start, fourx_party_selected, fourx_color_selected,
    fourx_machine_handler, fourx_count_handler
)
from handlers.raspash import (
    raspash_start, raspash_party_selected,
    raspash_color_selected, raspash_count_handler
)
from handlers.beika import (
    beika_start, beika_party_selected,
    beika_color_selected, beika_count_handler
)
from handlers.strochka import (
    strochka_start, strochka_party_selected,
    strochka_color_selected, strochka_count_handler
)
from handlers.gorlo import (
    gorlo_start, gorlo_party_selected,
    gorlo_color_selected, gorlo_count_handler
)
from handlers.ytyg import (
    ytyg_start, ytyg_party_selected,
    ytyg_color_selected, ytyg_count_handler
)
from handlers.otk import (
    otk_start, otk_party_selected,
    otk_color_selected, otk_count_handler
)
from handlers.upakovka import (
    upakovka_start, upakovka_party_selected,
    upakovka_color_selected, upakovka_count_handler
)

from handlers.user_management import (
    user_management_action,
    list_all_users, delete_user_start, select_user_for_deletion,
    confirm_user_deletion, cancel_user_deletion,

)

from handlers.party_management import (
    party_management_action,
    list_all_parties_with_info, delete_party_start,
    select_party_for_deletion, confirm_party_deletion,
    cancel_party_deletion, manage_parties_callback

)

from handlers.material_management import (
    manage_materials_callback, delete_material_callback,
    confirm_material_delete, cancel_material_delete,
    party_back_callback,
    # Добавляем новые функции:
    manage_colors_callback,
    edit_color_callback
)

from handlers.edit_operations import edit_count_handler

# Импортируем состояния
from states import *

# Инициализация
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ==========

# Общие команды
dp.message.register(start_handler, CommandStart())
dp.message.register(show_parties_command, Command("партии"))
dp.message.register(cancel_handler, Command("отмена"))
dp.message.register(me_command, Command("me"))
dp.message.register(reset_command, Command("reset"))
dp.message.register(info_command, Command("инфо"))
dp.message.register(new_party_command, Command("новая_партия"))
dp.message.register(check_my_data, Command("мои_данные"))


# Регистрация
dp.message.register(name_handler, RegistrationStates.waiting_for_name)
dp.callback_query.register(job_selected, RegistrationStates.waiting_for_job)
dp.message.register(machine_number_handler, RegistrationStates.waiting_for_machine_number)
dp.callback_query.register(view_workers_callback, F.data.startswith("view_workers_"))
dp.callback_query.register(continue_work_callback, F.data.startswith("continue_work_"))
dp.callback_query.register(change_party_callback, F.data == "change_party")

# Закрой
dp.message.register(zakroi_party_handler, ZakroiStates.waiting_for_party_number)
dp.message.register(zakroi_color_handler, ZakroiStates.waiting_for_color)
dp.message.register(zakroi_quantity_handler, ZakroiStates.waiting_for_quantity_line)
dp.callback_query.register(back_to_parties, F.data == "back_to_parties")
dp.callback_query.register(add_material_callback, F.data.startswith("add_material_"))


# Обработчики кнопок главного меню
dp.message.register(new_record_handler, F.text == "Новая запись")
dp.message.register(start_work_handler, F.text == "Начать работу")
dp.message.register(change_party_handler, F.text == "Сменить партию")
dp.message.register(my_stats_handler, F.text == "Мои данные")
dp.message.register(all_parties_handler, F.text == "Все партии")
dp.message.register(manage_users_handler, F.text == "Управление пользователями")  # ДОБАВЛЯЕМ
dp.message.register(manage_users_command, Command("управление_пользователями"))
dp.message.register(manage_parties_handler, F.text == "Управление партиями")


# Управление пользователями
dp.callback_query.register(user_management_action, UserManagementStates.waiting_for_action)
dp.callback_query.register(list_all_users, F.data == "list_users")
dp.callback_query.register(delete_user_start, F.data == "delete_user")
dp.callback_query.register(select_user_for_deletion, F.data.startswith("select_user_"), UserManagementStates.waiting_for_user_selection)
dp.callback_query.register(confirm_user_deletion, F.data == "confirm_delete", UserManagementStates.waiting_for_confirmation)
dp.callback_query.register(cancel_user_deletion, F.data == "cancel_delete")

# Управление партиями
dp.callback_query.register(party_management_action, PartyManagementStates.waiting_for_action)
dp.callback_query.register(list_all_parties_with_info, F.data == "list_all_parties")
dp.callback_query.register(delete_party_start, F.data == "delete_party_action")
dp.callback_query.register(select_party_for_deletion, F.data.startswith("delete_party_"), PartyManagementStates.waiting_for_party_selection)
dp.callback_query.register(confirm_party_deletion, F.data == "confirm_party_delete", PartyManagementStates.waiting_for_confirmation)
dp.callback_query.register(cancel_party_deletion, F.data == "cancel_party_delete")
dp.callback_query.register(manage_parties_callback, F.data == "manage_parties")  # Инлайн кнопка

# Обработчики материалов
dp.callback_query.register(manage_materials_callback, F.data.startswith("manage_materials_"))
dp.callback_query.register(delete_material_callback, F.data.startswith("delete_material_"))
dp.callback_query.register(confirm_material_delete, F.data == "confirm_material_delete")
dp.callback_query.register(cancel_material_delete, F.data == "cancel_material_delete")
dp.callback_query.register(party_back_callback, F.data.startswith("party_back_"))


# color_manage
dp.callback_query.register(manage_materials_callback, F.data.startswith("manage_materials_"))
dp.callback_query.register(manage_colors_callback, F.data.startswith("manage_colors_"))
dp.callback_query.register(delete_material_callback, F.data.startswith("delete_material_"))
dp.callback_query.register(confirm_material_delete, F.data == "confirm_material_delete")
dp.callback_query.register(cancel_material_delete, F.data == "cancel_material_delete")
dp.callback_query.register(party_back_callback, F.data.startswith("party_back_"))
dp.callback_query.register(edit_color_callback, F.data.startswith("edit_color_"))
dp.message.register(zakroishchik_start, Command("закройщик"))

# Кнопка "Изменить показания"
dp.message.register(edit_operations_handler, F.text == "Изменить показания")

# Обработчики редактирования показаний
dp.callback_query.register(edit_party_selected, F.data.startswith("party_"), EditOperationsStates.waiting_for_party_selection)
dp.callback_query.register(edit_color_callback, F.data.startswith("edit_color_"))
dp.callback_query.register(edit_color_selected, F.data.startswith("edit_count_"), EditOperationsStates.waiting_for_color_selection)
dp.message.register(check_db_data, Command("проверка"))
dp.message.register(edit_count_handler, EditOperationsStates.waiting_for_new_count)

# 4-х
dp.callback_query.register(fourx_start, F.data == "fourx")
dp.callback_query.register(fourx_party_selected, F.data.startswith("party_"), FourXStates.waiting_for_party_selection)
dp.callback_query.register(fourx_color_selected, F.data.startswith("color_"), FourXStates.waiting_for_color_selection)
dp.message.register(fourx_machine_handler, FourXStates.waiting_for_machine_number)
dp.message.register(fourx_count_handler, FourXStates.waiting_for_count)
dp.message.register(change_machine_command, Command("сменить_машинку"))

# Распаш
dp.callback_query.register(raspash_start, F.data == "raspash")
dp.callback_query.register(raspash_party_selected, F.data.startswith("party_"),
                           RaspashStates.waiting_for_party_selection)
dp.callback_query.register(raspash_color_selected, F.data.startswith("color_"),
                           RaspashStates.waiting_for_color_selection)
dp.message.register(raspash_count_handler, RaspashStates.waiting_for_count)

# Бейка
dp.callback_query.register(beika_start, F.data == "beika")
dp.callback_query.register(beika_party_selected, F.data.startswith("party_"), BeikaStates.waiting_for_party_selection)
dp.callback_query.register(beika_color_selected, F.data.startswith("color_"), BeikaStates.waiting_for_color_selection)
dp.message.register(beika_count_handler, BeikaStates.waiting_for_count)

# Строчка
dp.callback_query.register(strochka_start, F.data == "strochka")
dp.callback_query.register(strochka_party_selected, F.data.startswith("party_"),
                           StrochkaStates.waiting_for_party_selection)
dp.callback_query.register(strochka_color_selected, F.data.startswith("color_"),
                           StrochkaStates.waiting_for_color_selection)
dp.message.register(strochka_count_handler, StrochkaStates.waiting_for_count)

# Горло
dp.callback_query.register(gorlo_start, F.data == "gorlo")
dp.callback_query.register(gorlo_party_selected, F.data.startswith("party_"), GorloStates.waiting_for_party_selection)
dp.callback_query.register(gorlo_color_selected, F.data.startswith("color_"), GorloStates.waiting_for_color_selection)
dp.message.register(gorlo_count_handler, GorloStates.waiting_for_count)

# Утюг
dp.callback_query.register(ytyg_start, F.data == "ytyg")
dp.callback_query.register(ytyg_party_selected, F.data.startswith("party_"), YtygStates.waiting_for_party_selection)
dp.callback_query.register(ytyg_color_selected, F.data.startswith("color_"), YtygStates.waiting_for_color_selection)
dp.message.register(ytyg_count_handler, YtygStates.waiting_for_count)

# ОТК
dp.callback_query.register(otk_start, F.data == "otk")
dp.callback_query.register(otk_party_selected, F.data.startswith("party_"), OtkStates.waiting_for_party_selection)
dp.callback_query.register(otk_color_selected, F.data.startswith("color_"), OtkStates.waiting_for_color_selection)
dp.message.register(otk_count_handler, OtkStates.waiting_for_count)

# Упаковка
dp.callback_query.register(upakovka_start, F.data == "upakovka")
dp.callback_query.register(upakovka_party_selected, F.data.startswith("party_"),
                           UpakovkaStates.waiting_for_party_selection)
dp.callback_query.register(upakovka_color_selected, F.data.startswith("color_"),
                           UpakovkaStates.waiting_for_color_selection)
dp.message.register(upakovka_count_handler, UpakovkaStates.waiting_for_count)


# Общие callback
dp.callback_query.register(party_selected_from_menu, F.data.startswith("party_"))
dp.callback_query.register(cancel_callback, F.data == "cancel")
dp.callback_query.register(new_party_callback, F.data == "new_party")


# ========== ЗАПУСК БОТА ==========
async def main():
    # Создаем пул подключений к БД
    await db.create_pool()

    # Автоматически создаем таблицы если их нет
    await db.create_tables_if_not_exist()

    # Проверяем подключение
    print("=" * 50)
    print("🤖 Бот запускается...")
    print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    print(f"🗄️ База данных: {DB_HOST}:{DB_PORT}/{DB_NAME}")

    # ПРОВЕРЯЕМ НАЛИЧИЕ ЗАКРОЙЩИКА В БАЗЕ (только для информации)
    from config import ZAKROISHCHIK_ID
    zakroi_user = await db.get_user(ZAKROISHCHIK_ID)
    if zakroi_user:
        print(f"✅ Закройщик в базе: {zakroi_user['name']}")
    else:
        print(f"ℹ️ Закройщик будет зарегистрирован при первом запуске /start")

    tables = await db.check_tables()
    print(f"📊 Найдены таблицы: {', '.join(tables)}")
    print("=" * 50)

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())