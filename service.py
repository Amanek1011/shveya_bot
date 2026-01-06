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
        """Добавить партию если её нет"""
        party = await db.get_party_by_number(batch_number)
        if not party:
            await db.add_party(batch_number)
            return True
        return False

    @staticmethod
    async def format_party_info(party_id: int, user_job=None, show_detailed=False):
        """Форматировать информацию о партии - простой вариант для закройщика"""
        materials = await db.get_materials_by_party(party_id)

        if not materials:
            return "В этой партии пока нет материалов"

        result = f"📦 Партия:\n\n"

        # Сортируем материалы по цвету
        materials_sorted = sorted(materials, key=lambda x: x['color'])

        # Пронумерованный список материалов
        material_number = 1
        total_lines = 0
        total_tshirts = 0

        for material in materials_sorted:
            lines = material['quantity_line'] or 0
            tshirts = material['tshirt_count'] or 0

            result += f"{material_number}.  {material['color']} - {lines}л - {tshirts}шт:\n"

            # Прогресс по операциям - ПРАВИЛЬНОЕ СРАВНЕНИЕ
            operations = []

            four_x_count = material.get('four_x_count') or 0
            if four_x_count > 0 and material.get('four_x'):
                operations.append(f"4-х: {four_x_count}шт")

            raspash_count = material.get('raspash_count') or 0
            if raspash_count > 0 and material.get('raspash'):
                operations.append(f"    Распаш: {raspash_count}шт ")

            beika_count = material.get('beika_count') or 0
            if beika_count > 0 and material.get('beika'):
                operations.append(f"    Бейка: {beika_count}шт")

            strochka_count = material.get('strochka_count') or 0
            if strochka_count > 0 and material.get('strochka'):
                operations.append(f"    Строчка: {strochka_count}шт")

            gorlo_count = material.get('gorlo_count') or 0
            if gorlo_count > 0 and material.get('gorlo'):
                operations.append(f"    Горло: {gorlo_count}шт")

            ytyg_count = material.get('ytyg_count') or 0
            if ytyg_count > 0 and material.get('ytyg'):
                operations.append(f"    Утюг: {ytyg_count}шт")

            otk_count = material.get('otk_count') or 0
            if otk_count > 0 and material.get('otk'):
                operations.append(f"    ОТК: {otk_count}шт")

            ypakovka_count = material.get('ypakovka_count') or 0
            if ypakovka_count > 0 and material.get('ypakovka'):
                operations.append(f"    Упаковка: {ypakovka_count}шт")

            # result += f"   ID: {material['id']}\n\n"
            if operations:
                result += f"    {' \n'.join(operations)}\n\n"

            total_lines += lines
            total_tshirts += tshirts
            material_number += 1

        # Добавляем общую статистику (только для закройщика)
        from keyboards import is_zakroi_sync
        if user_job and is_zakroi_sync(user_job):
            result += "=" * 30 + "\n"
            result += f"📈 ОБЩАЯ СТАТИСТИКА:\n"
            result += f"• Всего материалов: {len(materials)}\n"
            result += f"• Всего линий: {total_lines}\n"
            result += f"• Всего футболок: {total_tshirts}\n"

            # Расчет выполнения
            completed = 0

            # Подсчет выполненных работ по операциям
            completed_operations = {
                'four_x_count': 0,
                'raspash_count': 0,
                'beika_count': 0,
                'strochka_count': 0,
                'gorlo_count': 0,
                'ytyg_count': 0,
                'otk_count': 0,
                'ypakovka_count': 0
            }

            operations_names = {
                'four_x_count': '4-х',
                'raspash_count': 'Распаш',
                'beika_count': 'Бейка',
                'strochka_count': 'Строчка',
                'gorlo_count': 'Горло',
                'ytyg_count': 'Утюг',
                'otk_count': 'ОТК',
                'ypakovka_count': 'Упаковка'
            }

            for material in materials:
                for operation in completed_operations.keys():
                    count = material.get(operation) or 0
                    completed_operations[operation] += count
                    completed += count

            result += f"• Выполнено футболок: {completed}шт\n"

        return result

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