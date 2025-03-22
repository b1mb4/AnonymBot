// Ініціалізація Telegram WebApp
document.addEventListener('DOMContentLoaded', function() {
    // Ініціалізація Telegram WebApp, якщо доступно
    if (window.Telegram && window.Telegram.WebApp) {
        const tg = window.Telegram.WebApp;

        // Встановлення теми
        document.body.className = 'telegram-theme';

        // Повідомлення Telegram, що додаток готовий
        tg.ready();

        // Розгортання додатку на весь екран
        tg.expand();

        // Отримання кольорів теми, якщо доступно
        applyTelegramTheme();
    }

    // Завантаження повідомлень
    updateMessages();

    // Додаємо анімацію кнопці оновлення
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            this.classList.add('refreshing');
            setTimeout(() => {
                this.classList.remove('refreshing');
            }, 1000);
        });
    }
});

// Застосування теми Telegram
function applyTelegramTheme() {
    if (window.Telegram && window.Telegram.WebApp) {
        const tg = window.Telegram.WebApp;

        // Встановлення CSS-змінних відповідно до кольорів теми Telegram
        document.documentElement.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#f5f5f5');
        document.documentElement.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#333333');
        document.documentElement.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#888888');
        document.documentElement.style.setProperty('--tg-theme-link-color', tg.themeParams.link_color || '#2481cc');
        document.documentElement.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#2481cc');
        document.documentElement.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');
        document.documentElement.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color || '#ffffff');
    }
}

// Форматування дати з врахуванням локального часового поясу користувача
function formatDate(dateString) {
    if (!dateString) return '';

    try {
        // Створюємо об'єкт дати
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return '';

        // Отримуємо поточну дату в локальному часовому поясі
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        // Форматування часу (години:хвилини)
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const timeString = `${hours}:${minutes}`;

        // Якщо сьогодні
        if (date.getDate() === today.getDate() &&
            date.getMonth() === today.getMonth() &&
            date.getFullYear() === today.getFullYear()) {
            return `Сьогодні, ${timeString}`;
        }

        // Якщо вчора
        if (date.getDate() === yesterday.getDate() &&
            date.getMonth() === yesterday.getMonth() &&
            date.getFullYear() === yesterday.getFullYear()) {
            return `Вчора, ${timeString}`;
        }

        // Інакше повна дата
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();

        return `${day}.${month}.${year}, ${timeString}`;
    } catch (e) {
        console.error("Помилка форматування дати:", e);
        return dateString || '';
    }
}

// Оновлення повідомлень
function updateMessages() {
    const messagesContainer = document.getElementById('messages-container');
    const filterSelect = document.getElementById('filter');
    const limit = filterSelect ? filterSelect.value : 10;

    // Додаємо клас animation до кнопки оновлення
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.innerHTML = '🔄 Оновлюється...';
    }

    // Показати індикатор завантаження
    messagesContainer.innerHTML = '<div class="loading">Завантаження...</div>';

    // Отримання повідомлень з API
    fetch(`/messages?limit=${limit}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Сервер повернув помилку: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            // Перевірка на помилку в відповіді
            if (data.error) {
                throw new Error(data.error);
            }

            messagesContainer.innerHTML = '';

            if (!Array.isArray(data) || data.length === 0) {
                messagesContainer.innerHTML = '<div class="empty-message">Повідомлень поки немає</div>';
                return;
            }

            data.forEach(message => {
                const messageElement = document.createElement('div');
                messageElement.className = 'message';

                const messageText = document.createElement('div');
                messageText.className = 'message-text';
                messageText.textContent = message.text;

                messageElement.appendChild(messageText);

                // Додавання часу повідомлення, якщо доступно
                if (message.timestamp) {
                    const messageTime = document.createElement('div');
                    messageTime.className = 'message-time';
                    messageTime.textContent = formatDate(message.timestamp);
                    messageElement.appendChild(messageTime);
                }

                messagesContainer.appendChild(messageElement);
            });

            // Повертаємо текст кнопки
            if (refreshBtn) {
                refreshBtn.innerHTML = '🔄';
            }

            // Оновлюємо статус
            const statusElement = document.querySelector('.status-message');
            if (statusElement) {
                const now = new Date();
                const hours = String(now.getHours()).padStart(2, '0');
                const minutes = String(now.getMinutes()).padStart(2, '0');
                const seconds = String(now.getSeconds()).padStart(2, '0');
                statusElement.textContent = `Оновлено о ${hours}:${minutes}:${seconds}`;
            }
        })
        .catch(error => {
            console.error('Помилка:', error);
            messagesContainer.innerHTML = `
                <div class="error-message">
                    <p>Не вдалося завантажити повідомлення</p>
                    <p class="error-details">${error.message}</p>
                    <button onclick="updateMessages()" class="refresh-button">Спробувати ще раз</button>
                </div>
            `;

            // Повертаємо текст кнопки
            if (refreshBtn) {
                refreshBtn.innerHTML = '🔄';
            }
        });
}

// Додавання періодичного оновлення
setInterval(updateMessages, 30000); // Оновлюємо кожні 30 секунд