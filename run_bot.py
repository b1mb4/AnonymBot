import os
import sys
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Виведення інформації про середовище Python
logger.info(f"Python version: {sys.version}")
logger.info(f"Python path: {sys.path}")

# Токен бота (з змінної середовища або напряму)
TOKEN = os.environ.get("BOT_TOKEN", "7830618724:AAFMhiP-DOV8fAs64Ecm3TUF-Xb-0zexJZI")


# Спрощена версія бота для тестування
async def main():
    try:
        # Створення об'єктів бота і диспетчера
        bot = Bot(token=TOKEN)
        dp = Dispatcher()

        # Команда /start
        @dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            logger.info(f"Отримано команду /start від {message.from_user.id}")
            await message.answer("Бот працює на сервері!")

        # Хендлер для всіх текстових повідомлень
        @dp.message()
        async def echo(message: types.Message):
            logger.info(f"Отримано повідомлення від {message.from_user.id}: {message.text}")
            await message.answer(f"Отримано повідомлення: {message.text}")

        # Запуск бота
        logger.info("Запускаємо бота...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Виникла помилка при запуску бота: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинено")
    except Exception as e:
        logger.critical(f"Критична помилка: {e}", exc_info=True)