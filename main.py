import asyncio
import os

from aiogram import Dispatcher, Bot, types
from aiogram.filters import CommandStart, Command
from dotenv import load_dotenv

from keyboards import reply_main_menu

load_dotenv()
TOKEN = os.getenv('TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer('Здраствуйте! Это бот чтобы записывать данные своей работы в швейном цеху.Выберите опции:',
                         reply_markup=reply_main_menu)

@dp.message()
async def text_handler(message: types.Message):
    if message.text == 'Регистрация':



async def main():
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())