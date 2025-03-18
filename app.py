import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Створення директорії для статичних файлів, якщо її немає
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

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


# Функція для підключення до бази даних
def get_db_connection():
    # Для локального тестування можна використовувати SQLite
    if os.environ.get("DATABASE_URL") is None:
        import sqlite3
        conn = sqlite3.connect("messages.db", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # На Render використовуємо PostgreSQL
    conn = psycopg2.connect(
        os.environ.get("DATABASE_URL", ""),
        cursor_factory=RealDictCursor
    )
    return conn


# Ініціалізація бази даних
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Перевіряємо, чи працюємо з SQLite або PostgreSQL
    if isinstance(conn, psycopg2.extensions.connection):
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL
        )
        """)
    else:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL
        )
        """)

    conn.commit()

    # Додаємо тестові дані, якщо база порожня
    cursor.execute("SELECT COUNT(*) FROM messages")
    count = cursor.fetchone()
    count_value = count["count"] if isinstance(count, dict) else count[0]

    if count_value == 0:
        test_messages = [
            "Привіт! Це перше анонімне повідомлення.",
            "Мені дуже подобається цей бот!",
            "Хотів би дізнатися, хто ще користується цим ботом.",
            "Дякую за створення такого корисного інструменту!",
            "Це тестове повідомлення для перевірки функціонування."
        ]

        for msg in test_messages:
            if isinstance(conn, psycopg2.extensions.connection):
                cursor.execute("INSERT INTO messages (text) VALUES (%s)", (msg,))
            else:
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

        if isinstance(conn, psycopg2.extensions.connection):
            cursor.execute("SELECT text FROM messages ORDER BY id DESC LIMIT %s", (limit,))
            messages = [{"text": row["text"]} for row in cursor.fetchall()]
        else:
            cursor.execute("SELECT text FROM messages ORDER BY id DESC LIMIT ?", (limit,))
            messages = [{"text": row[0]} for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        logger.info(f"Успішно отримано {len(messages)} повідомлень")
        return messages
    except Exception as e:
        logger.error(f"Помилка при отриманні повідомлень: {e}")
        return {"error": str(e)}


@app.post("/messages")
async def add_message(message: dict):
    """Додає нове повідомлення через API"""
    try:
        text = message.get("text", "")
        if not text:
            return {"success": False, "error": "Порожнє повідомлення"}

        conn = get_db_connection()
        cursor = conn.cursor()

        if isinstance(conn, psycopg2.extensions.connection):
            cursor.execute("INSERT INTO messages (text) VALUES (%s)", (text,))
        else:
            cursor.execute("INSERT INTO messages (text) VALUES (?)", (text,))

        conn.commit()
        cursor.close()
        conn.close()

        return {"success": True}
    except Exception as e:
        logger.error(f"Помилка при додаванні повідомлення: {e}")
        return {"success": False, "error": str(e)}


# Для Render порт буде отримано з системних змінних
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)