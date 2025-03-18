import sqlite3
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.types import WebAppInfo

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = "7830618724:AAFMhiP-DOV8fAs64Ecm3TUF-Xb-0zexJZI"

# Підключення до бази
conn = sqlite3.connect("messages.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# Домен для WebApp
# ВАЖЛИВО: Змініть цей URL на ваш реальний HTTPS-домен
WEBAPP_URL = "https://your-domain.com"  # Змініть на адресу вашого хостингу

# Ініціалізація бота
bot = Bot(token=TOKEN)
dp = Dispatcher()


# === ОБРОБНИКИ БОТА ===

# Команда /start
@dp.message(CommandStart())
async def command_start(message: Message):
    """Обробник команди /start"""
    logger.info(f"Отримано команду /start від {message.from_user.id}")
    await message.answer(
        "👋 Вітаю! Надішліть мені анонімне повідомлення, і я збережу його.\n\nВикористовуйте /read щоб переглянути повідомлення.")


# Команда /read
@dp.message(Command("read"))
async def command_read(message: Message):
    """Обробник команди /read"""
    logger.info(f"Отримано команду /read від {message.from_user.id}")

    try:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📖 Відкрити повідомлення", web_app=WebAppInfo(url=WEBAPP_URL))]
            ]
        )

        await message.answer("📩 Ось ваші анонімні повідомлення:", reply_markup=keyboard)
        logger.info("Кнопка WebApp надіслана успішно")
    except Exception as e:
        logger.error(f"Помилка при обробці команди /read: {e}")
        await message.answer(f"Сталася помилка: {e}")


# Хендлер для звичайних повідомлень (не команд)
@dp.message()
async def save_message(message: Message):
    """Зберігає анонімне повідомлення в базу"""
    try:
        logger.info(f"Отримано повідомлення від {message.from_user.id}: {message.text[:20]}...")
        cursor.execute("INSERT INTO messages (text) VALUES (?)", (message.text,))
        conn.commit()
        await message.answer("✅ Ваше повідомлення збережено анонімно.")
    except Exception as e:
        logger.error(f"Помилка при збереженні повідомлення: {e}")
        await message.answer("❌ Виникла помилка при збереженні повідомлення.")


async def main():
    """Запуск бота"""
    logger.info("Запускаємо бота...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Помилка при запуску бота: {e}")


if __name__ == "__main__":
    asyncio.run(main())