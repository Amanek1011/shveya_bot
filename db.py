import asyncpg
from config import DATABASE_URL


class Database:
    def __init__(self):
        self.pool = None

    async def create_pool(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        print("Подключение к базе данных установлено")

    # === Методы для пользователей ===
    async def get_user(self, tg_id: int):
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM users WHERE tg_id = $1",
                tg_id
            )

    async def add_user(self, tg_id: int, name: str, job: str, machine_number: str = None):
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            try:
                print(f"📝 Добавление пользователя: {name} как {job}, машинка: {machine_number}")

                await conn.execute(
                    """
                    INSERT INTO users (tg_id, name, job, machine_number) 
                    VALUES ($1, $2, $3, $4)
                    """,
                    tg_id, name, job, machine_number
                )
                return True
            except asyncpg.UniqueViolationError:
                # Пользователь уже существует
                print(f"⚠️ Пользователь {tg_id} уже существует")
                return False
            except Exception as e:
                print(f"❌ Ошибка при добавлении пользователя: {e}")
                return False

    async def get_all_users(self):
        """Получить всех пользователей"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            return await conn.fetch(
                "SELECT * FROM users ORDER BY name"
            )

    async def delete_user(self, user_id: int):
        """Удалить пользователя по ID"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM users WHERE id = $1",
                user_id
            )
            return True

    async def get_user_by_id(self, user_id: int):
        """Получить пользователя по ID"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                user_id
            )


    # === Методы для партий ===
    async def get_all_parties(self):
        """Получить все партии"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            return await conn.fetch(
                "SELECT * FROM parties ORDER BY batch_number"
            )

    async def get_party_by_id(self, party_id: int):
        """Получить партию по ID"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM parties WHERE id = $1",
                party_id
            )

    async def get_party_by_number(self, batch_number: str):
        """Получить партию по номеру"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM parties WHERE batch_number = $1",
                batch_number
            )

    async def add_party(self, batch_number: str):
        """Добавить новую партию"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO parties (batch_number) 
                    VALUES ($1)
                    """,
                    batch_number
                )
                return True
            except asyncpg.UniqueViolationError:
                return False  # Партия уже существует
            except Exception as e:
                print(f"Ошибка при добавлении партии: {e}")
                return False

    # === Методы для материалов (цветов) в партии ===
    async def get_materials_by_party(self, party_id: int):
        """Получить все материалы в партии"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT * FROM materials 
                WHERE party_id = $1 
                ORDER BY id
                """,
                party_id
            )

    async def get_material_by_party_and_color(self, party_id: int, color: str):
        """Получить материал по партии и цвету"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT * FROM materials 
                WHERE party_id = $1 AND color = $2
                """,
                party_id, color
            )

    async def delete_party(self, batch_number: str):
        """Удалить партию по номеру (каскадно удалит и материалы)"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            try:
                # Находим ID партии
                party = await conn.fetchrow(
                    "SELECT id FROM parties WHERE batch_number = $1",
                    batch_number
                )

                if not party:
                    return False

                # Удаляем партию (каскадно удалятся все связанные материалы)
                await conn.execute(
                    "DELETE FROM parties WHERE batch_number = $1",
                    batch_number
                )
                return True
            except Exception as e:
                print(f"❌ Ошибка при удалении партии: {e}")
                return False

    async def get_materials_count_by_party(self, party_id: int):
        """Получить количество материалов в партии"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM materials WHERE party_id = $1",
                party_id
            )
        
    async def add_material(self, party_id: int, color: str, quantity_line: int, tshirt_count: int):
        """Добавить материал в партию (для закройщика)"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO materials 
                    (party_id, color, quantity_line, tshirt_count) 
                    VALUES ($1, $2, $3, $4)
                    """,
                    party_id, color, quantity_line, tshirt_count
                )
                return True
            except Exception as e:
                print(f"Ошибка при добавлении материала: {e}")
                return False

    async def delete_material(self, material_id: int):
        """Удалить материал по ID"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    "DELETE FROM materials WHERE id = $1",
                    material_id
                )
                return True
            except Exception as e:
                print(f"❌ Ошибка при удалении материала: {e}")
                return False

    async def get_material_by_id(self, material_id: int):
        """Получить материал по ID"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM materials WHERE id = $1",
                material_id
            )

    # === Методы для обновления данных по операциям ===
    async def update_fourx(self, material_id: int, four_x: str, four_x_count: int):
        """Обновить данные по 4-х оператору"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE materials 
                SET four_x = $1, four_x_count = $2 
                WHERE id = $3
                """,
                four_x, four_x_count, material_id
            )

    async def update_raspash(self, material_id: int, raspash: str, raspash_count: int):
        """Обновить данные по распаш"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE materials 
                SET raspash = $1, raspash_count = $2 
                WHERE id = $3
                """,
                raspash, raspash_count, material_id
            )

    async def update_beika(self, material_id: int, beika: str, beika_count: int):
        """Обновить данные по бейке"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE materials 
                SET beika = $1, beika_count = $2 
                WHERE id = $3
                """,
                beika, beika_count, material_id
            )

    async def update_strochka(self, material_id: int, strochka: str, strochka_count: int):
        """Обновить данные по строчке"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE materials 
                SET strochka = $1, strochka_count = $2 
                WHERE id = $3
                """,
                strochka, strochka_count, material_id
            )

    async def update_gorlo(self, material_id: int, gorlo: str, gorlo_count: int):
        """Обновить данные по горлу"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE materials 
                SET gorlo = $1, gorlo_count = $2 
                WHERE id = $3
                """,
                gorlo, gorlo_count, material_id
            )

    async def update_ytyg(self, material_id: int, ytyg: str, ytyg_count: int):
        """Обновить данные по утюгу"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE materials 
                SET ytyg = $1, ytyg_count = $2 
                WHERE id = $3
                """,
                ytyg, ytyg_count, material_id
            )

    async def update_otk(self, material_id: int, otk: str, otk_count: int):
        """Обновить данные по ОТК"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE materials 
                SET otk = $1, otk_count = $2 
                WHERE id = $3
                """,
                otk, otk_count, material_id
            )

    async def update_ypakovka(self, material_id: int, ypakovka: str, ypakovka_count: int):
        """Обновить данные по упаковке"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE materials 
                SET ypakovka = $1, ypakovka_count = $2 
                WHERE id = $3
                """,
                ypakovka, ypakovka_count, material_id
            )

    async def check_tables(self):
        """Проверка существования таблиц"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            tables = await conn.fetch(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            return [table['table_name'] for table in tables]

    async def create_tables_if_not_exist(self):
        """Создание таблиц если они не существуют"""
        if not self.pool:
            await self.create_pool()

        async with self.pool.acquire() as conn:
            # Таблица users
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    tg_id BIGINT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    job VARCHAR(50),
                    machine_number VARCHAR(50),
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица parties
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS parties (
                    id SERIAL PRIMARY KEY,
                    batch_number VARCHAR(50) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица materials
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS materials (
                    id SERIAL PRIMARY KEY,
                    party_id INTEGER NOT NULL REFERENCES parties(id) ON DELETE CASCADE,
                    color VARCHAR(100),
                    quantity_line INTEGER,
                    tshirt_count INTEGER,
                    four_x VARCHAR(100),
                    four_x_count INTEGER,
                    raspash VARCHAR(100),
                    raspash_count INTEGER,
                    beika VARCHAR(100),
                    beika_count INTEGER,
                    strochka VARCHAR(100),
                    strochka_count INTEGER,
                    gorlo VARCHAR(100),
                    gorlo_count INTEGER,
                    ytyg VARCHAR(100),
                    ytyg_count INTEGER,
                    otk VARCHAR(100),
                    otk_count INTEGER,
                    ypakovka VARCHAR(100),
                    ypakovka_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            print("Таблицы созданы/проверены")


db = Database()
