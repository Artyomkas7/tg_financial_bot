import logging
import ydb
import ydb.iam
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключение к YDB
def create_ydb_driver():
    driver = ydb.Driver(
        endpoint="grpcs://ydb.serverless.yandexcloud.net:2135",
        database="/ru-central1/b1g86rbv28go73jml91a/etnv8re60doc9qg4iglk",
        credentials=ydb.iam.ServiceAccountCredentials.from_file("authorized_key.json")
    )
    driver.wait(timeout=30)
    return driver

driver = create_ydb_driver()
session = driver.table_client.session().create()

# Этапы диалога
SELECT_TYPE, ENTER_AMOUNT, SELECT_ACCOUNT, SELECT_CATEGORY, ENTER_DESIRABILITY, ENTER_DESCRIPTION = range(6)

# Стартовое сообщение
async def start(update: Update, context):
    keyboard = [["Записать операцию"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Привет! Я ваш финансовый бот. Выберите действие:", reply_markup=reply_markup)

# Начало ввода операции
async def start_transaction(update: Update, context):
    keyboard = [["Доход", "Расход"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите тип операции:", reply_markup=reply_markup)
    return SELECT_TYPE

# Ввод суммы
async def enter_amount(update: Update, context):
    # Получаем тип операции, выбранный пользователем
    user_type = update.message.text
    if user_type not in ["Доход", "Расход"]:
        await update.message.reply_text("Ошибка! Выберите 'Доход' или 'Расход'.")
        return SELECT_TYPE  # Вернуться на выбор типа операции

    # Сохраняем тип операции в данных пользователя
    context.user_data["type"] = user_type

    # Просим ввести сумму
    await update.message.reply_text("Введите сумму:")
    return ENTER_AMOUNT

# Выбор счета списания
async def select_account(update: Update, context):
    try:
        amount = float(update.message.text)
        if context.user_data["type"] == "Расход":
            amount = -amount
        context.user_data["amount"] = amount
    except ValueError:
        await update.message.reply_text("Ошибка! Введите числовое значение суммы.")
        return ENTER_AMOUNT

    # Запрос списка счетов из YDB
    session = driver.table_client.session().create()
    query = "SELECT name FROM accounts"
    result_set = session.transaction().execute(query, commit_tx=True)
    accounts = [row[0] for row in result_set[0].rows]

    keyboard = [[acc] for acc in accounts] + [["Добавить новый счет"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите счет списания:", reply_markup=reply_markup)
    return SELECT_ACCOUNT

# Выбор категории
async def select_category(update: Update, context):
    context.user_data["account"] = update.message.text

    # Запрос категорий из YDB
    session = driver.table_client.session().create()
    query = "SELECT name FROM categories WHERE type = @type"
    result_set = session.transaction().execute(query, {"type": context.user_data["type"]}, commit_tx=True)
    categories = [row[0] for row in result_set[0].rows]

    keyboard = [[cat] for cat in categories] + [["Добавить новую категорию"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите категорию:", reply_markup=reply_markup)
    return SELECT_CATEGORY

# Ввод желательности расхода
async def enter_desirability(update: Update, context):
    context.user_data["category"] = update.message.text
    keyboard = [["Желательный", "Нежелательный"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Этот расход желательный или нежелательный?", reply_markup=reply_markup)
    return ENTER_DESIRABILITY

# Ввод описания
async def enter_description(update: Update, context):
    context.user_data["desirability"] = update.message.text
    await update.message.reply_text("Введите описание или отправьте 'Без описания':")
    return ENTER_DESCRIPTION

# Запись операции в YDB
async def save_transaction(update: Update, context):
    description = update.message.text if update.message.text != "Без описания" else None
    user_data = context.user_data

    session = driver.table_client.session().create()
    query = """
        INSERT INTO transactions (date, amount, account, category, desirability, description)
        VALUES (CurrentUtcDate(), @amount, @account, @category, @desirability, @description)
    """
    session.transaction().execute(query, {
        "amount": user_data["amount"],
        "account": user_data["account"],
        "category": user_data["category"],
        "desirability": user_data["desirability"],
        "description": description
    }, commit_tx=True)

    await update.message.reply_text("✅ Операция успешно записана!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Отмена операции
async def cancel(update: Update, context):
    await update.message.reply_text("Операция отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Создание приложения
app = Application.builder().token("7697444585:AAGcna4h-eGa-89UCTfG9XL4EGI-ujj0QWs").build()

# Добавление обработчиков команд
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("Записать операцию"), start_transaction))

# Обработчик диалога
conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("Записать операцию"), start_transaction)],
    states={
        SELECT_TYPE: [MessageHandler(filters.Regex("^(Доход|Расход)$"), enter_amount)],
        ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_account)],
        SELECT_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_category)],
        SELECT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_desirability)],
        ENTER_DESIRABILITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)],
        ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_transaction)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(conv_handler)

# Запуск бота
app.run_polling()