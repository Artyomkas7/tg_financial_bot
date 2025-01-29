import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
# URL Google Apps Script
GAS_URL = "https://script.google.com/macros/s/AKfycbzp_nqb_UuGN2gV6f_QhWP0O4AFEa9g_MQWneFt4icDd8zf9-i6-AlQbUFi0XMxyWZg/exec"
# Логирование
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
# Этапы диалога
SUM, CATEGORY, OPERATION_TYPE = range(3)
# Команда /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Введите сумму:")
    return SUM
# Ввод суммы
def get_sum(update: Update, context: CallbackContext):
    context.user_data["sum"] = update.message.text
    keyboard = [["Еда", "Транспорт"], ["Развлечения", "Другое"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Выберите категорию:", reply_markup=reply_markup)
    return CATEGORY
# Выбор категории
def get_category(update: Update, context: CallbackContext):
    context.user_data["category"] = update.message.text
    keyboard = [["Доход", "Расход"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Выберите тип операции:", reply_markup=reply_markup)
    return OPERATION_TYPE
# Запись в Google Таблицу
def get_operation_type(update: Update, context: CallbackContext):
    context.user_data["operation_type"] = update.message.text
    # Отправляем данные в Google Apps Script
    data = {
        "sum": context.user_data["sum"],
        "category": context.user_data["category"],
        "type": context.user_data["operation_type"]
    }
    response = requests.post(GAS_URL, json=data)
    update.message.reply_text(response.text, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
# Команда /cancel
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Операция отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
# Запуск бота
def main():
    updater = Updater("7697444585:AAGcna4h-eGa-89UCTfG9XL4EGI-ujj0QWs", use_context=True)
    dp = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SUM: [MessageHandler(Filters.text & ~Filters.command, get_sum)],
            CATEGORY: [MessageHandler(Filters.text & ~Filters.command, get_category)],
            OPERATION_TYPE: [MessageHandler(Filters.text & ~Filters.command, get_operation_type)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()
if __name__ == "__main__":
    main()