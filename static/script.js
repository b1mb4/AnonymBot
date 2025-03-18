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

// Оновлення повідомлень
function updateMessages() {
    const messagesContainer = document.getElementById('messages-container');
    const filterSelect = document.getElementById('filter');
    const limit = filterSelect ? filterSelect.value : 10;

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
                messagesContainer.appendChild(messageElement);
            });
        })
        .catch(error => {
            console.error('Помилка:', error);
            messagesContainer.innerHTML = `
                <div class="error-message">
                    <p>Не вдалося завантажити повідомлення</p>
                    <p class="error-details">${error.message}</p>
                    <button onclick="updateMessages()" class="retry-button">Спробувати ще раз</button>
                </div>
            `;
        });
}

// Додавання періодичного оновлення
setInterval(updateMessages, 10000);