import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.types import WebAppInfo

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = "7830618724:AAFMhiP-DOV8fAs64Ecm3TUF-Xb-0zexJZI"

# URL вашого додатку на Render
WEBAPP_URL = "https://anonymbot-n1ms.onrender.com"  # Замініть на ваш URL

# URL для API-ендпоінту
API_URL = f"{WEBAPP_URL}/bot/messages"

# API-ключ для доступу до ендпоінту
API_KEY = "AKe5Df9cB7zX2pQr8tYw3mVn6uJh4gLs"  # Замініть на той же ключ, що і в app.py

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
        "👋 Вітаю! Надішліть мені будь яку свою потребу, і я збережу її.\n\nВона обов'язково буде почута.")


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

        await message.answer("📩 Помолитися за потреби можна тут:", reply_markup=keyboard)
        logger.info("Кнопка WebApp надіслана успішно")
    except Exception as e:
        logger.error(f"Помилка при обробці команди /read: {e}")
        await message.answer(f"Сталася помилка: {e}")


# Хендлер для звичайних повідомлень (не команд)
@dp.message()
async def save_message(message: Message):
    """Зберігає анонімне повідомлення на сервер"""
    try:
        user_id = str(message.from_user.id)
        text = message.text

        logger.info(f"Отримано повідомлення від {user_id}: {text[:20]}...")

        # Відправляємо повідомлення на сервер через API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    API_URL,
                    json={"text": text, "user_id": user_id},
                    headers={"X-API-Key": API_KEY}
            ) as response:

                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        await message.answer("✅ Ваше повідомлення збережено анонімно.")
                        logger.info(f"Повідомлення успішно збережено, message_id: {result.get('message_id')}")
                    else:
                        error = result.get("error", "Невідома помилка")
                        await message.answer(f"❌ Помилка при збереженні повідомлення: {error}")
                        logger.error(f"Помилка від сервера: {error}")
                else:
                    await message.answer(f"❌ Сервер повернув помилку: {response.status}")
                    logger.error(f"Сервер повернув статус {response.status}")

    except Exception as e:
        logger.error(f"Помилка при відправці повідомлення на сервер: {e}")
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