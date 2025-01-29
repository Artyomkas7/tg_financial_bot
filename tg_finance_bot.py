from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
import requests
import logging

# URL Google Apps Script
GAS_URL = "https://script.google.com/macros/s/AKfycbwFih7SoHRVE2dIVFCgxXoUrQmPDhnnTuQ8rVH9EQ1CvPbZ72b9LDGmnfZH3BMrJ0NN/exec"

# Логирование
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Этапы диалога
SUM, CATEGORY, OPERATION_TYPE = range(3)


# Команда /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Введите сумму:")
    return SUM


# Ввод суммы
async def get_sum(update: Update, context: CallbackContext):
    context.user_data["sum"] = update.message.text
    keyboard = [["Еда", "Транспорт"], ["Развлечения", "Другое"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите категорию:", reply_markup=reply_markup)
    return CATEGORY


# Выбор категории
async def get_category(update: Update, context: CallbackContext):
    context.user_data["category"] = update.message.text
    keyboard = [["Доход", "Расход"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите тип операции:", reply_markup=reply_markup)
    return OPERATION_TYPE


# Запись в Google Таблицу
async def get_operation_type(update: Update, context: CallbackContext):
    context.user_data["operation_type"] = update.message.text

    # Отправляем данные в Google Apps Script
    data = {
        "sum": context.user_data["sum"],
        "category": context.user_data["category"],
        "type": context.user_data["operation_type"]
    }
    response = requests.post(GAS_URL, json=data)

    await update.message.reply_text(response.text, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# Команда /cancel
async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Операция отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# Запуск бота
def main():
    app = Application.builder().token("7697444585:AAGcna4h-eGa-89UCTfG9XL4EGI-ujj0QWs").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sum)],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
            OPERATION_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_operation_type)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()