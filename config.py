import os
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv('TOKEN')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

# Формируем DSN для asyncpg
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ID закройщика
ZAKROISHCHIK_ID = int(os.getenv('ZAKROISHCHIK_ID'))