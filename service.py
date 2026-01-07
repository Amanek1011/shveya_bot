from db import db
from keyboards import get_parties_keyboard, get_colors_keyboard


class UserService:
    @staticmethod
    async def get_user_job(tg_id: int):
        user = await db.get_user(tg_id)
        return user['job'] if user else None

    @staticmethod
    async def get_user_name(tg_id: int):
        user = await db.get_user(tg_id)
        return user['name'] if user else None

    @staticmethod
    async def get_user_machine_number(tg_id: int):
        """Получить номер машинки пользователя"""
        user = await db.get_user(tg_id)
        return user.get('machine_number') if user else None

    @staticmethod
    async def update_user_machine_number(tg_id: int, machine_number: str):
        """Обновить номер машинки пользователя"""
        if not db.pool:
            await db.create_pool()

        async with db.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users 
                SET machine_number = $1 
                WHERE tg_id = $2
                """,
                machine_number, tg_id
            )
            return True

    @staticmethod
    def is_zakroi_sync(job: str) -> bool:
        """СИНХРОННО проверяет является ли должность закройщиком"""
        from keyboards import is_zakroi_sync as check_zakroi
        return check_zakroi(job)

    @staticmethod
    async def get_user_display_info(tg_id: int):
        """Получить отображаемую информацию о пользователе"""
        user = await db.get_user(tg_id)
        if not user:
            return "Неизвестный пользователь", None

        display_name = user['name']

        # Для 4-х оператора добавляем номер машинки
        if user['job'] == '4-х' and user.get('machine_number'):
            display_name = f"{user['name']} ({user['machine_number']})"

        return display_name, user['job']

class PartyService:
    @staticmethod
    async def add_party_if_not_exists(batch_number: str):
        """Добавить партию если её нет (без дизайна)"""
        party = await db.get_party_by_number(batch_number)
        if not party:
            await db.add_party(batch_number, None)  # Добавляем None для дизайна
            return True
        return False

    @staticmethod
    async def add_party_with_design(batch_number: str, design: str):
        """Добавить партию с дизайном"""
        party = await db.get_party_by_number(batch_number)
        if not party:
            # Добавляем новую партию с дизайном
            success = await db.add_party(batch_number, design)
            return success
        else:
            # Обновляем дизайн существующей партии
            async with db.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE parties SET design = $1 WHERE batch_number = $2",
                    design, batch_number
                )
            return True

    @staticmethod
    async def format_party_info_detailed(party_id: int, user_job=None):
        """Детальное форматирование информации о партии"""
        party = await db.get_party_by_id(party_id)
        materials = await db.get_materials_by_party(party_id)

        if not materials:
            design_text = f"({party.get('design')})" if party.get('design') else ""
            return f"📦 Партия №{party['batch_number']}{design_text}\n\nВ этой партии пока нет материалов"

        # Заголовок с дизайном
        design_text = f"({party.get('design')})" if party.get('design') else ""
        result = f"📦 Партия №{party['batch_number']}{design_text}\n\n"

        material_number = 1
        for material in sorted(materials, key=lambda x: x['color']):
            lines = material['quantity_line'] or 0
            tshirts = material['tshirt_count'] or 0

            result += f"{material_number}. Цвет - {material['color']}\n"
            result += f"       Закрой :  {lines}л - {tshirts}шт\n"

            # Форматируем операции
            ops = [
                ("4-х", material.get('four_x'), material.get('four_x_count')),
                ("Распаш", material.get('raspash'), material.get('raspash_count')),
                ("Бейка", material.get('beika'), material.get('beika_count')),
                ("Строчка", material.get('strochka'), material.get('strochka_count')),
                ("Горло", material.get('gorlo'), material.get('gorlo_count')),
                ("Утюг", material.get('ytyg'), material.get('ytyg_count')),
                ("ОТК", material.get('otk'), material.get('otk_count')),
                ("Упаковка", material.get('ypakovka'), material.get('ypakovka_count'))
            ]

            for op_name, op_person, op_count in ops:
                if op_person and op_count:
                    # Для 4-х оператора добавляем номер машинки
                    if op_name == '4-х':
                        user = await db.get_user_by_name(op_person)
                        machine = f"({user['machine_number']})" if user and user.get('machine_number') else ""
                        result += f"       {op_name}({op_person}{machine}): {op_count}шт\n"
                    else:
                        result += f"       {op_name}({op_person}): {op_count}шт\n"
                else:
                    result += f"       {op_name}(): ---\n"

            result += "\n"
            material_number += 1

        return result

    @staticmethod
    async def format_party_info(party_id: int, user_job=None):
        """Старый метод для обратной совместимости"""
        return await PartyService.format_party_info_detailed(party_id, user_job)

    @staticmethod
    async def format_party_simple(party_id: int, user_job=None):
        """Упрощенный вид партии для операторов"""
        materials = await db.get_materials_by_party(party_id)

        if not materials:
            return "В этой партии пока нет материалов"

        result = f"📦 Цвета в этой партии:\n\n"

        # Группируем материалы по цветам (для операторов показываем только цвета)
        colors = {}
        for material in materials:
            color = material['color']
            if color not in colors:
                total_for_color = sum(1 for m in materials if m['color'] == color)
                colors[color] = total_for_color

        # Пронумерованный список уникальных цветов
        color_number = 1
        for color in sorted(colors.keys()):
            count = colors[color]
            if count > 1:
                result += f"{color_number}. 🎨 {color} ({count} записи)\n"
            else:
                result += f"{color_number}. 🎨 {color}\n"
            color_number += 1

        return result

    @staticmethod
    def get_party_keyboard(party_id: int, batch_number: str, user_job=None, show_add_more=False):
        """Создать клавиатуру для партии"""
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from keyboards import is_zakroi_sync

        builder = InlineKeyboardBuilder()

        if is_zakroi_sync(user_job):
            # Клавиатура для закройщика
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

class KeyboardService:
    @staticmethod
    async def get_parties_keyboard(user_job=None, with_management=False):
        parties = await db.get_all_parties()
        return get_parties_keyboard(parties, user_job, with_management)

    @staticmethod
    async def get_colors_keyboard(party_id: int):
        materials = await db.get_materials_by_party(party_id)
        return get_colors_keyboard(materials)


# СОЗДАЕМ ЭКЗЕМПЛЯРЫ КЛАССОВ
user_service = UserService()
party_service = PartyService()
keyboard_service = KeyboardService()

# Глобальное хранилище сессий
user_sessions = {}