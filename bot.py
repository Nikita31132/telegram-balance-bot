import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
from collections import Counter

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Путь к файлу с ключом
CREDENTIALS_PATH = '/Users/nikitaeliseev/Desktop/telegram_balance_bot/credentials.json'
SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive.readonly"]

# Проверка существования файла
if not os.path.exists(CREDENTIALS_PATH):
    logger.error(f"Файл {CREDENTIALS_PATH} не найден!")
    raise FileNotFoundError(f"Файл {CREDENTIALS_PATH} не найден! Убедитесь, что он существует.")

# ID таблицы
SPREADSHEET_ID = '158X45Ng-LK4JVdBFsBPIYA-J9aTzCs-uHsQDri43zXU'
RANGE_NAME = 'E:G'

def get_google_sheet_data():
    """Получаем данные из Google Sheets"""
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet('Основа')
        data = sheet.get(RANGE_NAME)
        logger.info("Данные успешно получены из Google Sheets.")
        
        if not data or len(data) < 1:
            raise ValueError("Таблица пуста или не содержит данных в диапазоне E:G")
        
        headers = data[0]
        result = []
        for row in data[1:]:
            balance = row[0] if len(row) > 0 else 'Не указано'
            campaign = row[1] if len(row) > 1 else 'Не указано'
            personal_cabinet = row[2] if len(row) > 2 else 'Не указано'
            if str(balance) != "9964476":
                result.append({
                    'Кампания': campaign,
                    'Баланс': balance,
                    'Личный кабинет': personal_cabinet
                })
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {e}")
        raise

def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start для показа клавиатуры"""
    keyboard = [[KeyboardButton("/balance")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    update.message.reply_text("Привет! Нажми кнопку ниже, чтобы увидеть баланс.", 
                              reply_markup=reply_markup, 
                              disable_notification=True)

def balance_callback(update: Update, context: CallbackContext) -> None:
    """Функция для обработки команды /balance"""
    try:
        data = get_google_sheet_data()

        # Сортируем данные по балансу от большего к меньшему
        data.sort(key=lambda x: float(x['Баланс']) if str(x['Баланс']).replace('.', '').isdigit() else 0, reverse=True)

        # Получаем текущую дату и время
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        # Подсчитываем дубликаты кампаний
        campaign_counts = Counter(row['Кампания'] for row in data)
        
        # Структурируем ответ без Markdown
        message_lines = [f"Запрос от {current_time}\n"]
        
        for i, row in enumerate(data, start=1):
            campaign = row.get('Кампания', 'Не указано')
            balance = row.get('Баланс', 'Не указано')
            personal_cabinet = row.get('Личный кабинет', 'Не указано')
            # Если кампания повторяется, добавляем уточнение из "Личного кабинета"
            if campaign_counts[campaign] > 1:
                line = f"{i}. {campaign} ({personal_cabinet}) | {balance}"
            else:
                line = f"{i}. {campaign} | {balance}"
            message_lines.append(line)
            logger.info(f"Строка {i}: {line}")
        
        # Собираем сообщение
        max_length = 4096
        messages = []
        current_message = ""
        
        for line in message_lines:
            if len(current_message) + len(line) + 1 > max_length:
                messages.append(current_message)
                current_message = line
            else:
                if current_message:
                    current_message += "\n" + line
                else:
                    current_message = line
        
        if current_message:
            messages.append(current_message)
        
        # Создаем клавиатуру с кнопкой /balance
        keyboard = [[KeyboardButton("/balance")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        # Отправляем сообщения без Markdown
        for part in messages:
            logger.info(f"Отправляем часть сообщения: {len(part)} символов")
            update.message.reply_text(part, reply_markup=reply_markup, disable_notification=True)
        
    except Exception as e:
        update.message.reply_text(f"Произошла ошибка: {str(e)}. Попробуйте позже.")
        logger.error(f"Ошибка в обработке команды balance: {e}")

def main():
    """Основная функция для запуска бота"""
    bot_token = "8181411445:AAEUXyRdVe90etjMB5CX1gNT7G5vNLnQank"
    updater = Updater(token=bot_token, use_context=True)
    dispatcher = updater.dispatcher

    # Устанавливаем команды в меню бота
    updater.bot.set_my_commands([
        ("start", "Запустить бота"),
        ("balance", "Показать баланс")
    ])

    # Добавляем обработчики только для команд
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('balance', balance_callback))

    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()