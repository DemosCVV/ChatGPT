import asyncio
import os

import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

print("=== RUNNING main.py (with webhook delete + diag) ===")

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
DB_NAME = "bot.db"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

if not ADMIN_ID_RAW:
    raise RuntimeError("ADMIN_ID не задан в переменных окружения")

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    raise RuntimeError("ADMIN_ID должен быть числом (telegram user id)")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


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


async def add_user(user: types.User):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users VALUES (?, ?)",
            (user.id, user.username or "без_юза")
        )
        await db.commit()


async def get_card() -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM settings WHERE key='card'") as c:
            row = await c.fetchone()
            return row[0] if row else "не задано"


async def set_card(value: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE settings SET value=? WHERE key='card'", (value,))
        await db.commit()


def is_admin(message: types.Message) -> bool:
    return bool(message.from_user) and message.from_user.id == ADMIN_ID


# --- DIAG ---
@dp.message_handler(commands=["ping"])
async def ping(message: types.Message):
    await message.reply("pong ✅")


@dp.message_handler(commands=["whoami"])
async def whoami(message: types.Message):
    await message.reply(
        "DIAG 🔎\n"
        f"your id: {message.from_user.id}\n"
        f"chat id: {message.chat.id}\n"
        f"ADMIN_ID env: {os.getenv('ADMIN_ID')}\n"
        f"parsed ADMIN_ID: {ADMIN_ID}\n"
        f"text: {message.text}"
    )


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await add_user(message.from_user)
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🚀 Начать диалог", callback_data="start_dialog")
    )
    await message.answer(
        "🔷 <b>Добро пожаловать в ChatGPT</b>\n\n"
        "🚀 Начать общение — нажмите «Начать диалог»\n\n"
        "📌 Закрепи бота, чтобы не потерять",
        reply_markup=kb,
        parse_mode="HTML",
    )


@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
    if not is_admin(message):
        await message.reply(
            "⛔️ Нет доступа.\n\n"
            f"Твой id: {message.from_user.id}\n"
            f"ADMIN_ID в env: {os.getenv('ADMIN_ID')}\n"
            "Поставь ADMIN_ID равным твоему id (см. /whoami) и перезапусти."
        )
        return

    card = await get_card()
    await message.reply(
        "🛠 <b>Админ-панель</b>\n\n"
        f"💳 Текущая карта:\n<code>{card}</code>\n\n"
        "Команды:\n"
        "• /setcard <номер | ФИО>\n"
        "• /users\n",
        parse_mode="HTML",
    )


@dp.message_handler(commands=["setcard"])
async def admin_setcard(message: types.Message):
    if not is_admin(message):
        await message.reply("⛔️ Нет доступа. Смотри /whoami")
        return

    text = message.get_args().strip()
    if not text:
        await message.reply("Пример:\n/setcard 0000 0000 0000 0000 | Иванов И.И.")
        return

    await set_card(text)
    await message.reply("✅ Карта обновлена.")


@dp.message_handler(commands=["users"])
async def admin_users(message: types.Message):
    if not is_admin(message):
        await message.reply("⛔️ Нет доступа. Смотри /whoami")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            count = (await c.fetchone())[0]

    await message.reply(f"👥 Пользователей в базе: {count}")


@dp.callback_query_handler(lambda c: c.data == "start_dialog")
async def start_dialog(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("💳 Оплатить 99 ₽", callback_data="pay")
    )
    await call.message.edit_text(
        "💬 <b>Для начала общения требуется подписка</b>\n\n"
        "💰 Стоимость: <b>99 ₽</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )


@dp.callback_query_handler(lambda c: c.data == "pay")
async def pay(call: types.CallbackQuery):
    card = await get_card()
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("📨 Отправить чек менеджеру", url="https://t.me/fepxu")
    )
    await call.message.edit_text(
        f"💳 <b>Оплата подписки</b>\n\n"
        f"🔢 <b>Карта:</b> <code>{card}</code>\n"
        f"💰 <b>Сумма:</b> 99 ₽",
        reply_markup=kb,
        parse_mode="HTML",
    )


async def on_startup(dp: Dispatcher):
    # ключевой фикс: удаляем webhook, иначе polling часто "молчит"
    await bot.delete_webhook(drop_pending_updates=True)
    print("WEBHOOK DELETED ✅")
    print("BOT STARTED ✅")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
