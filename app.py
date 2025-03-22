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

# Директорія для бази даних
# На Render доступні для запису каталоги /tmp та /var/data
# /var/data зберігається між деплоями, а /tmp очищається
DATA_DIR = os.environ.get("DATA_DIR", "/var/data")
if not os.path.exists(DATA_DIR):
    # Якщо ми не на Render або директорія не існує, використовуємо поточний каталог
    DATA_DIR = os.getcwd()
    # Створюємо директорію data, якщо вона не існує
    data_path = os.path.join(DATA_DIR, "data")
    os.makedirs(data_path, exist_ok=True)
    DATA_DIR = data_path

# Максимальна кількість повідомлень для зберігання
MAX_MESSAGES = 50

logger.info(f"Використовуємо директорію для даних: {DATA_DIR}")
logger.info(f"Максимальна кількість повідомлень: {MAX_MESSAGES}")

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
    # Використовуємо постійну директорію на Render
    db_path = os.path.join(DATA_DIR, "messages.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# Функція для видалення найстаріших повідомлень
def enforce_message_limit(conn):
    """Видаляє найстаріші повідомлення, якщо їх кількість перевищує MAX_MESSAGES"""
    cursor = conn.cursor()

    # Отримуємо загальну кількість повідомлень
    cursor.execute("SELECT COUNT(*) FROM messages")
    count = cursor.fetchone()[0]

    # Якщо кількість повідомлень перевищує ліміт
    if count > MAX_MESSAGES:
        # Кількість повідомлень, які потрібно видалити
        to_delete = count - MAX_MESSAGES
        logger.info(f"Видаляємо {to_delete} найстаріших повідомлень для дотримання ліміту в {MAX_MESSAGES}")

        # Видаляємо найстаріші повідомлення (з найменшими id)
        cursor.execute("DELETE FROM messages WHERE id IN (SELECT id FROM messages ORDER BY id ASC LIMIT ?)",
                       (to_delete,))
        conn.commit()

        # Перевіряємо, скільки було видалено
        cursor.execute("SELECT COUNT(*) FROM messages")
        new_count = cursor.fetchone()[0]
        logger.info(f"Після видалення залишилося {new_count} повідомлень")

    cursor.close()


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
        logger.info("База даних порожня, додаємо тестові повідомлення")
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
    else:
        logger.info(f"База даних вже містить {count} повідомлень")

        # Перевіряємо, чи не перевищено ліміт і видаляємо зайві повідомлення
        enforce_message_limit(conn)

    cursor.close()
    conn.close()


# Ініціалізація бази даних при запуску
@app.on_event("startup")
async def startup_event():
    try:
        # Ініціалізуємо базу даних
        init_db()
        logger.info("База даних ініціалізована успішно")

        # Запускаємо keep_alive в фоні
        asyncio.create_task(keep_alive())
        logger.info("Запущено фонове завдання підтримки активності")
    except Exception as e:
        logger.error(f"Помилка при ініціалізації: {e}")


# Проста функція для підтримки активності сервера
async def keep_alive():
    """
    Функція для підтримки активності сервера, яка просто пише в лог кожні 10 хвилин
    """
    # Змінна для зберігання останнього стану повідомлень
    last_message_count = None

    # Завжди чекаємо 30 секунд після старту перед першою перевіркою
    await asyncio.sleep(30)

    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # Отримуємо поточну кількість повідомлень
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM messages")
            current_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            # Перевіряємо чи є зміни
            if last_message_count is None:
                # Перший запуск
                logger.info(f"[{current_time}] Перша перевірка: {current_count} повідомлень в базі")
                last_message_count = current_count
            elif current_count > last_message_count:
                # Є нові повідомлення
                logger.info(f"[{current_time}] Зміни є: +{current_count - last_message_count} нових повідомлень")
                last_message_count = current_count
            else:
                # Змін немає
                logger.info(f"[{current_time}] Змін немає: все ще {current_count} повідомлень")

        except Exception as e:
            # Якщо сталася помилка при перевірці
            logger.error(f"[{current_time}] Помилка при перевірці змін: {str(e)}")

        # Чекаємо 10 хвилин перед наступною перевіркою
        await asyncio.sleep(600)  # 600 секунд = 10 хвилин


@app.head("/")
def head_root():
    """Обробляє HEAD запит до кореневого шляху"""
    return {}  # Повертаємо порожній словник без тіла

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
        message_id = cursor.lastrowid

        # Перевіряємо ліміт повідомлень і видаляємо зайві, якщо потрібно
        enforce_message_limit(conn)

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Додано нове повідомлення від бота (user_id: {user_id})")
        return {"success": True, "message_id": message_id}
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
        message_id = cursor.lastrowid

        # Перевіряємо ліміт повідомлень і видаляємо зайві, якщо потрібно
        enforce_message_limit(conn)

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Додано нове повідомлення з веб-інтерфейсу")
        return {"success": True, "message_id": message_id}
    except Exception as e:
        logger.error(f"Помилка при додаванні повідомлення: {e}")
        return {"success": False, "error": str(e)}


# Ендпоінт для перевірки статусу
@app.get("/health")
def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return {
            "status": "ok",
            "version": "1.0",
            "message_count": count,
            "max_messages": MAX_MESSAGES,
            "data_dir": DATA_DIR
        }
    except Exception as e:
        logger.error(f"Помилка при перевірці статусу: {e}")
        return {"status": "error", "error": str(e)}


# Ручний тригер для пінгу (може використовуватись для тестування)
@app.get("/manual-ping")
async def manual_ping(background_tasks: BackgroundTasks, api_key: str = Depends(verify_api_key)):
    """Ручний тригер для пінгу з аутентифікацією API ключем (для тестування)"""
    background_tasks.add_task(ping_health_once)
    return {"message": "Ping запущено в фоні"}


# Ендпоінт для отримання статистики
@app.get("/stats")
def get_stats(api_key: str = Depends(verify_api_key)):
    """Отримує статистику по повідомленнях (захищено API ключем)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Загальна кількість повідомлень
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_count = cursor.fetchone()[0]

        # Кількість повідомлень за останні 24 години
        cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp > datetime('now', '-1 day')")
        last_24h_count = cursor.fetchone()[0]

        # Кількість унікальних користувачів (якщо є user_id)
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM messages WHERE user_id IS NOT NULL")
        unique_users = cursor.fetchone()[0]

        # Перше і останнє повідомлення
        cursor.execute("SELECT timestamp FROM messages ORDER BY id ASC LIMIT 1")
        first_message = cursor.fetchone()
        first_message_time = first_message[0] if first_message else None

        cursor.execute("SELECT timestamp FROM messages ORDER BY id DESC LIMIT 1")
        last_message = cursor.fetchone()
        last_message_time = last_message[0] if last_message else None

        cursor.close()
        conn.close()

        return {
            "total_messages": total_count,
            "last_24h_messages": last_24h_count,
            "unique_users": unique_users,
            "max_messages": MAX_MESSAGES,
            "first_message_time": first_message_time,
            "last_message_time": last_message_time
        }
    except Exception as e:
        logger.error(f"Помилка при отриманні статистики: {e}")
        return {"status": "error", "error": str(e)}


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