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
    async def format_party_info(party_id: int, user_job=None):
        """Форматировать информацию о партии"""
        materials = await db.get_materials_by_party(party_id)
        if not materials:
            return "В этой партии пока нет материалов"

        result = f"📦 Партия:\n\n"
        for material in materials:
            result += f"🎨 {material['color']}:\n"
            result += f"   Линий: {material['quantity_line']}\n"
            result += f"   Футболок: {material['tshirt_count']}\n"

            if material['four_x']:
                result += f"   4-х: {material['four_x']} ({material['four_x_count']} шт)\n"
            if material['raspash']:
                result += f"   Распаш: {material['raspash']} ({material['raspash_count']} шт)\n"
            if material['beika']:
                result += f"   Бейка: {material['beika']} ({material['beika_count']} шт)\n"
            if material['strochka']:
                result += f"   Строчка: {material['strochka']} ({material['strochka_count']} шт)\n"
            if material['gorlo']:
                result += f"   Горло: {material['gorlo']} ({material['gorlo_count']} шт)\n"
            if material['ytyg']:
                result += f"   Утюг: {material['ytyg']} ({material['ytyg_count']} шт)\n"
            if material['otk']:
                result += f"   ОТК: {material['otk']} ({material['otk_count']} шт)\n"
            if material['ypakovka']:
                result += f"   Упаковка: {material['ypakovka']} ({material['ypakovka_count']} шт)\n"

            result += "\n"

        return result

    @staticmethod
    async def get_party_keyboard(party_id: int, batch_number: str, user_job=None, show_add_more=False):
        """Создать клавиатуру для партии"""
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from keyboards import is_zakroi_sync

        builder = InlineKeyboardBuilder()

        # Кнопка добавления материала только для закройщика
        if is_zakroi_sync(user_job):
            if show_add_more:
                builder.button(
                    text="➕ Добавить еще материал",
                    callback_data=f"add_material_{party_id}"
                )
            else:
                builder.button(
                    text="➕ Добавить материал",
                    callback_data=f"add_material_{party_id}"
                )

        builder.button(text="◀️ Назад к списку партий", callback_data="back_to_parties")

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