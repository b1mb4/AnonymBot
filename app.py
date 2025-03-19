import os
import sqlite3
import secrets
import asyncio
import aiohttp
from fastapi import FastAPI, Request, HTTPException, Header, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Створення директорії для статичних файлів, якщо її немає
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

API_KEY = os.environ.get("API_KEY", "AKe5Df9cB7zX2pQr8tYw3mVn6uJh4gLs")

# Отримання URL додатку з середовища або встановлення стандартного для локального тестування
APP_URL = os.environ.get("APP_URL", "http://localhost:8000")

# Ініціалізація FastAPI
app = FastAPI()

# Додаємо middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для продакшену слід обмежити дозволені домени
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Підключення статичних файлів
app.mount("/static", StaticFiles(directory="static"), name="static")

# Шаблони
templates = Jinja2Templates(directory="templates")


# Функція для перевірки API ключа
def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Невірний API ключ"
        )
    return x_api_key


# Функція для підключення до бази даних
def get_db_connection():
    # Створюємо базу в тимчасовому каталозі, який доступний для запису на Render
    db_path = os.path.join("/tmp", "messages.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# Ініціалізація бази даних
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        user_id TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

    # Додаємо тестові дані, якщо база порожня
    cursor.execute("SELECT COUNT(*) FROM messages")
    count = cursor.fetchone()[0]

    if count == 0:
        test_messages = [
            "Привіт! Це перше анонімне повідомлення.",
            "Мені дуже подобається цей бот!",
            "Хотів би дізнатися, хто ще користується цим ботом.",
            "Дякую за створення такого корисного інструменту!",
            "Це тестове повідомлення для перевірки функціонування."
        ]

        for msg in test_messages:
            cursor.execute("INSERT INTO messages (text) VALUES (?)", (msg,))

        conn.commit()
        logger.info(f"Додано {len(test_messages)} тестових повідомлень")

    cursor.close()
    conn.close()


# Ініціалізація бази даних при запуску
try:
    init_db()
except Exception as e:
    logger.error(f"Помилка при ініціалізації бази даних: {e}")


# Функція для підтримки активності сервера
async def keep_alive():
    """Функція для підтримки активності сервера, запускається в фоні"""
    while True:
        try:
            # Пінгуємо наш власний /health ендпоінт
            async with aiohttp.ClientSession() as session:
                ping_url = f"{APP_URL}/health"
                async with session.get(ping_url) as response:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if response.status == 200:
                        logger.info(f"[{current_time}] Ping успішний: {ping_url}, статус: {response.status}")
                    else:
                        logger.warning(f"[{current_time}] Ping невдалий: {ping_url}, статус: {response.status}")
        except Exception as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.error(f"[{current_time}] Помилка при виконанні ping: {str(e)}")

        # Чекаємо 10 хвилин перед наступним пінгом
        # Render зазвичай "засинає" після 15 хвилин неактивності
        await asyncio.sleep(600)  # 600 секунд = 10 хвилин


# Запуск фонового завдання при старті додатку
@app.on_event("startup")
async def startup_event():
    # Запускаємо keep_alive в фоні
    asyncio.create_task(keep_alive())
    logger.info("Запущено фонове завдання підтримки активності")


@app.get("/", response_class=HTMLResponse)
def read_messages(request: Request):
    """Повертає HTML-сторінку"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/messages", response_class=JSONResponse)
def get_messages(limit: int = 10):
    """Повертає список повідомлень у JSON"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT text, timestamp FROM messages ORDER BY id DESC LIMIT ?", (limit,))
        messages = [{"text": row["text"], "timestamp": row["timestamp"]} for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        logger.info(f"Успішно отримано {len(messages)} повідомлень")
        return messages
    except Exception as e:
        logger.error(f"Помилка при отриманні повідомлень: {e}")
        return {"error": str(e)}


@app.post("/bot/messages")
async def add_bot_message(message: dict, api_key: str = Depends(verify_api_key)):
    """Ендпоінт для додавання повідомлень від бота (захищений API ключем)"""
    try:
        text = message.get("text", "")
        user_id = message.get("user_id", "")

        if not text:
            return {"success": False, "error": "Порожнє повідомлення"}

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("INSERT INTO messages (text, user_id) VALUES (?, ?)", (text, user_id))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Додано нове повідомлення від бота (user_id: {user_id})")
        return {"success": True, "message_id": cursor.lastrowid}
    except Exception as e:
        logger.error(f"Помилка при додаванні повідомлення від бота: {e}")
        return {"success": False, "error": str(e)}


@app.post("/messages")
async def add_message(message: dict):
    """Додає нове повідомлення через API (для веб-інтерфейсу)"""
    try:
        text = message.get("text", "")
        if not text:
            return {"success": False, "error": "Порожнє повідомлення"}

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("INSERT INTO messages (text) VALUES (?)", (text,))

        conn.commit()
        cursor.close()
        conn.close()

        return {"success": True}
    except Exception as e:
        logger.error(f"Помилка при додаванні повідомлення: {e}")
        return {"success": False, "error": str(e)}


# Ендпоінт для перевірки статусу
@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0"}


# Ручний тригер для пінгу (може використовуватись для тестування)
@app.get("/manual-ping")
async def manual_ping(background_tasks: BackgroundTasks, api_key: str = Depends(verify_api_key)):
    """Ручний тригер для пінгу з аутентифікацією API ключем (для тестування)"""
    background_tasks.add_task(ping_health_once)
    return {"message": "Ping запущено в фоні"}


async def ping_health_once():
    """Виконати один пінг ендпоінту /health"""
    try:
        async with aiohttp.ClientSession() as session:
            ping_url = f"{APP_URL}/health"
            async with session.get(ping_url) as response:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"[{current_time}] Ручний ping: {ping_url}, статус: {response.status}")
                return {"status": response.status}
    except Exception as e:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.error(f"[{current_time}] Помилка ручного ping: {str(e)}")
        return {"error": str(e)}


# Для Render порт буде отримано з системних змінних
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)