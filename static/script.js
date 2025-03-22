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

// Форматування дати з врахуванням часового поясу України (GMT+2)
function formatDate(dateString) {
    if (!dateString) return '';

    try {
        // Створюємо об'єкт дати
        const utcDate = new Date(dateString);
        if (isNaN(utcDate.getTime())) return '';

        // Конвертуємо UTC в GMT+2 (додаємо 2 години)
        const localDate = new Date(utcDate.getTime() + (2 * 60 * 60 * 1000));

        // Поточна дата у GMT+2
        const now = new Date();
        const nowGmt2 = new Date(now.getTime() + (2 * 60 * 60 * 1000));
        const today = new Date(nowGmt2.getFullYear(), nowGmt2.getMonth(), nowGmt2.getDate());
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        // Форматування часу (години:хвилини)
        const hours = String(localDate.getUTCHours()).padStart(2, '0');
        const minutes = String(localDate.getUTCMinutes()).padStart(2, '0');
        const timeString = `${hours}:${minutes}`;

        // Якщо сьогодні
        if (localDate >= today) {
            return `Сьогодні, ${timeString}`;
        }

        // Якщо вчора
        if (localDate >= yesterday) {
            return `Вчора, ${timeString}`;
        }

        // Інакше повна дата
        const day = String(localDate.getUTCDate()).padStart(2, '0');
        const month = String(localDate.getUTCMonth() + 1).padStart(2, '0');
        const year = localDate.getUTCFullYear();

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
                // Додаємо 2 години для GMT+2
                const localNow = new Date(now.getTime() + (2 * 60 * 60 * 1000));
                const hours = String(localNow.getUTCHours()).padStart(2, '0');
                const minutes = String(localNow.getUTCMinutes()).padStart(2, '0');
                const seconds = String(localNow.getUTCSeconds()).padStart(2, '0');
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