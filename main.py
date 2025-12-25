import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
DB_NAME = "bot.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

admin_state = None

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        await db.execute(
            "INSERT OR IGNORE INTO settings VALUES ('card', '0000 0000 0000 0000 | Иванов И.И.')"
        )
        await db.commit()

async def add_user(user):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users VALUES (?, ?)",
            (user.id, user.username or 'без_юза')
        )
        await db.commit()

async def get_card():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM settings WHERE key='card'") as c:
            return (await c.fetchone())[0]

async def set_card(value):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE settings SET value=? WHERE key='card'", (value,))
        await db.commit()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await add_user(message.from_user)
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton('🚀 Начать диалог', callback_data='start_dialog')
    )
    await message.answer(
        '🔷 <b>Добро пожаловать в ChatGPT</b>\n\n'
        '🚀 Начать общение — нажмите «Начать диалог»\n\n'
        '📌 Закрепи бота, чтобы не потерять',
        reply_markup=kb,
        parse_mode='HTML'
    )

@dp.callback_query_handler(lambda c: c.data == 'start_dialog')
async def start_dialog(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton('💳 Оплатить 99 ₽', callback_data='pay')
    )
    await call.message.edit_text(
        '💬 <b>Для начала общения требуется подписка</b>\n\n'
        '💰 Стоимость: <b>99 ₽</b>',
        reply_markup=kb,
        parse_mode='HTML'
    )

@dp.callback_query_handler(lambda c: c.data == 'pay')
async def pay(call: types.CallbackQuery):
    card = await get_card()
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton('📨 Отправить чек менеджеру', url='https://t.me/fepxu')
    )
    await call.message.edit_text(
        f'💳 <b>Оплата подписки</b>\n\n'
        f'🔢 <b>Карта:</b> <code>{card}</code>\n'
        f'💰 <b>Сумма:</b> 99 ₽',
        reply_markup=kb,
        parse_mode='HTML'
    )

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    executor.start_polling(dp, skip_updates=True)
