from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db import db
from service import user_service


async def view_workers_callback(call: types.CallbackQuery):
    """Показать кто что сделал в партии с указанием цветов"""
    party_id = int(call.data.split("_")[2])

    user = await db.get_user(call.from_user.id)
    if not user or not user_service.is_zakroi_sync(user['job']):
        await call.message.answer("Эта информация доступна только закройщикам")
        await call.answer()
        return

    party = await db.get_party_by_id(party_id)
    materials = await db.get_materials_by_party(party_id)

    # Собираем детальную информацию о работах
    workers_stats = {}

    for material in materials:
        color = material['color']

        # 4-х операторы
        if material['four_x'] and material['four_x_count']:
            worker = material['four_x']
            if worker not in workers_stats:
                workers_stats[worker] = {'4-х': []}

            workers_stats[worker]['4-х'].append({
                'color': color,
                'count': material['four_x_count'],
                'material_id': material['id']
            })

        # Распаш
        if material['raspash'] and material['raspash_count']:
            worker = material['raspash']
            if worker not in workers_stats:
                workers_stats[worker] = {'Распаш': []}

            workers_stats[worker]['Распаш'].append({
                'color': color,
                'count': material['raspash_count'],
                'material_id': material['id']
            })

        # Бейка
        if material['beika'] and material['beika_count']:
            worker = material['beika']
            if worker not in workers_stats:
                workers_stats[worker] = {'Бейка': []}

            workers_stats[worker]['Бейка'].append({
                'color': color,
                'count': material['beika_count'],
                'material_id': material['id']
            })

        # Строчка
        if material['strochka'] and material['strochka_count']:
            worker = material['strochka']
            if worker not in workers_stats:
                workers_stats[worker] = {'Строчка': []}

            workers_stats[worker]['Строчка'].append({
                'color': color,
                'count': material['strochka_count'],
                'material_id': material['id']
            })

        # Горло
        if material['gorlo'] and material['gorlo_count']:
            worker = material['gorlo']
            if worker not in workers_stats:
                workers_stats[worker] = {'Горло': []}

            workers_stats[worker]['Горло'].append({
                'color': color,
                'count': material['gorlo_count'],
                'material_id': material['id']
            })

        # Утюг
        if material['ytyg'] and material['ytyg_count']:
            worker = material['ytyg']
            if worker not in workers_stats:
                workers_stats[worker] = {'Утюг': []}

            workers_stats[worker]['Утюг'].append({
                'color': color,
                'count': material['ytyg_count'],
                'material_id': material['id']
            })

        # ОТК
        if material['otk'] and material['otk_count']:
            worker = material['otk']
            if worker not in workers_stats:
                workers_stats[worker] = {'ОТК': []}

            workers_stats[worker]['ОТК'].append({
                'color': color,
                'count': material['otk_count'],
                'material_id': material['id']
            })

        # Упаковка
        if material['ypakovka'] and material['ypakovka_count']:
            worker = material['ypakovka']
            if worker not in workers_stats:
                workers_stats[worker] = {'Упаковка': []}

            workers_stats[worker]['Упаковка'].append({
                'color': color,
                'count': material['ypakovka_count'],
                'material_id': material['id']
            })

    text = f"👥 **Кто что сделал в партии №{party['batch_number']}:**\n\n"

    if not workers_stats:
        text += "Пока никто не начал работу.\n"
    else:
        for worker, jobs in sorted(workers_stats.items()):
            text += f"**{worker}:**\n"

            for job_name, details in jobs.items():
                total_for_job = sum(item['count'] for item in details)
                text += f"   {job_name}: {total_for_job}шт\n"

                # Детали по цветам
                for item in details:
                    text += f"      • {item['color']}: {item['count']}шт (ID: {item['material_id']})\n"

                text += "\n"
            text += "\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад к партии", callback_data=f"party_back_{party_id}")
    builder.adjust(1)

    try:
        await call.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await call.message.answer(text, reply_markup=builder.as_markup())
    await call.answer()


async def full_workers_stats_callback(call: types.CallbackQuery):
    """Полная статистика работников по всем партиям"""
    user = await db.get_user(call.from_user.id)
    if not user or not user_service.is_zakroi_sync(user['job']):
        await call.message.answer("Эта информация доступна только закройщикам")
        await call.answer()
        return

    # Получаем все партии
    parties = await db.get_all_parties()

    if not parties:
        await call.message.answer("Пока нет ни одной партии")
        await call.answer()
        return

    text = f"👥 **Статистика работников по всем партиям:**\n\n"

    # Собираем статистику по всем партиям
    all_workers_stats = {}

    for party in parties:
        materials = await db.get_materials_by_party(party['id'])

        for material in materials:
            color = material['color']
            party_info = f"Партия №{party['batch_number']}, {color}"

            # 4-х операторы
            if material['four_x'] and material['four_x_count']:
                worker = material['four_x']
                if worker not in all_workers_stats:
                    all_workers_stats[worker] = {}
                if '4-х' not in all_workers_stats[worker]:
                    all_workers_stats[worker]['4-х'] = []

                all_workers_stats[worker]['4-х'].append({
                    'party': party['batch_number'],
                    'color': color,
                    'count': material['four_x_count'],
                    'material_id': material['id']
                })

            # Распаш
            if material['raspash'] and material['raspash_count']:
                worker = material['raspash']
                if worker not in all_workers_stats:
                    all_workers_stats[worker] = {}
                if 'Распаш' not in all_workers_stats[worker]:
                    all_workers_stats[worker]['Распаш'] = []

                all_workers_stats[worker]['Распаш'].append({
                    'party': party['batch_number'],
                    'color': color,
                    'count': material['raspash_count'],
                    'material_id': material['id']
                })

            # ... аналогично для остальных операций ...

    if not all_workers_stats:
        text += "Пока никто не работал.\n"
    else:
        for worker, jobs in sorted(all_workers_stats.items()):
            text += f"**{worker}:**\n"

            total_worker = 0
            for job_name, details in jobs.items():
                job_total = sum(item['count'] for item in details)
                total_worker += job_total
                text += f"   {job_name}: {job_total}шт\n"

                # Группируем по партиям
                party_groups = {}
                for item in details:
                    party_key = f"Партия №{item['party']}"
                    if party_key not in party_groups:
                        party_groups[party_key] = []
                    party_groups[party_key].append(item)

                for party_name, party_items in party_groups.items():
                    text += f"      {party_name}:\n"
                    for item in party_items:
                        text += f"         • {item['color']}: {item['count']}шт\n"

                text += "\n"

            text += f"   **Итого: {total_worker}шт**\n\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="back_to_parties")
    builder.adjust(1)

    try:
        await call.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await call.message.answer(text, reply_markup=builder.as_markup())
    await call.answer()