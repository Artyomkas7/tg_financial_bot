from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
import ydb
import ydb.iam
import uuid
from datetime import datetime

# Подключение к YDB
driver_config = ydb.DriverConfig(
        'grpcs://ydb.serverless.yandexcloud.net:2135', '/ru-central1/b1g86rbv28go73jml91a/etnv8re60doc9qg4iglk',
        credentials=ydb.credentials_from_env_variables(),
        root_certificates=ydb.load_ydb_root_certificate(),
    )
print(driver_config)
with ydb.Driver(driver_config) as driver:
    try:
        driver.wait(timeout=15)
    except TimeoutError:
        print("Connect failed to YDB")
        print("Last reported errors by discovery:")
        print(driver.discovery_debug_details())

# Определение состояний для пошагового ввода данных
TYPE, SUM, ACCOUNT, CATEGORY, DESIRABILITY, UNDESIRED_AMOUNT, DESCRIPTION, CONFIRM = range(8)

user_data = {}

# Команда /start с кнопкой "Записать операцию"
def start(update: Update, context: CallbackContext):
    keyboard = [["Записать операцию"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Добро пожаловать! Нажмите кнопку, чтобы начать запись операции.", reply_markup=reply_markup)
    return TYPE

# Выбор дохода или расхода
def get_type(update: Update, context: CallbackContext):
    operation_type = update.message.text
    user_data[update.message.chat_id] = {"type": operation_type}
    update.message.reply_text("Введите сумму:")
    return SUM

# Ввод суммы (с автоматическим знаком)
def get_sum(update: Update, context: CallbackContext):
    try:
        amount = float(update.message.text)
        if user_data[update.message.chat_id]["type"] == "Расход":
            amount = -abs(amount)
        else:
            amount = abs(amount)

        user_data[update.message.chat_id]["amount"] = amount
        update.message.reply_text("Выберите счет списания:", reply_markup=ReplyKeyboardMarkup(
            [["Карта", "Наличные", "Добавить новый"]], one_time_keyboard=True))
        return ACCOUNT
    except ValueError:
        update.message.reply_text("Введите корректную сумму.")
        return SUM

# Выбор счета
def get_account(update: Update, context: CallbackContext):
    account = update.message.text
    if account == "Добавить новый":
        update.message.reply_text("Введите название нового счета:")
        return ACCOUNT
    else:
        user_data[update.message.chat_id]["account"] = account
        update.message.reply_text("Выберите категорию:", reply_markup=ReplyKeyboardMarkup(
            [["Еда", "Транспорт", "Добавить новую"]], one_time_keyboard=True))
        return CATEGORY

# Выбор категории
def get_category(update: Update, context: CallbackContext):
    category = update.message.text
    if category == "Добавить новую":
        update.message.reply_text("Введите название новой категории:")
        return CATEGORY
    else:
        user_data[update.message.chat_id]["category"] = category
        update.message.reply_text("Расход желательный или нежелательный?", reply_markup=ReplyKeyboardMarkup(
            [["Желательный", "Нежелательный"]], one_time_keyboard=True))
        return DESIRABILITY

# Желательность расхода
def get_desirability(update: Update, context: CallbackContext):
    desirability = update.message.text
    user_data[update.message.chat_id]["desirability"] = desirability
    if desirability == "Нежелательный":
        update.message.reply_text("Введите сумму нежелательного расхода:")
        return UNDESIRED_AMOUNT
    else:
        return ask_description(update)

# Ввод нежелательной суммы
def get_undesired_amount(update: Update, context: CallbackContext):
    try:
        undesired_amount = float(update.message.text)
        user_data[update.message.chat_id]["undesired_amount"] = undesired_amount
        return ask_description(update)
    except ValueError:
        update.message.reply_text("Введите корректную сумму.")
        return UNDESIRED_AMOUNT

# Запрос на добавление описания
def ask_description(update: Update):
    update.message.reply_text("Добавить описание или оставить без описания?", reply_markup=ReplyKeyboardMarkup(
        [["Добавить", "Без описания"]], one_time_keyboard=True))
    return DESCRIPTION

# Ввод описания
def get_description(update: Update, context: CallbackContext):
    description = update.message.text
    if description == "Добавить":
        update.message.reply_text("Введите описание:")
        return DESCRIPTION
    else:
        user_data[update.message.chat_id]["description"] = ""
        return confirm_data(update)

# Подтверждение данных
def confirm_data(update: Update):
    chat_id = update.message.chat_id
    data = user_data.get(chat_id, {})

    text = f"""
    Подтвердите данные:
    Сумма: {data['amount']}
    Счет: {data['account']}
    Категория: {data['category']}
    Желательность: {data['desirability']}
    Нежелательная сумма: {data.get('undesired_amount', 0)}
    Описание: {data.get('description', '')}
    """

    update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(
        [["Подтвердить", "Отмена"]], one_time_keyboard=True))
    return CONFIRM

# Сохранение данных в YDB
def save_transaction(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    data = user_data.get(chat_id, {})

    transaction_id = str(uuid.uuid4())
    created_at = int(datetime.utcnow().timestamp() * 1_000_000)

    def execute_query(session):
        session.transaction().execute(
            """
            INSERT INTO transactions (user_id, transaction_id, date, amount, account, category, type, desirability, undesired_amount, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chat_id, transaction_id, created_at, data['amount'], data['account'], data['category'], data['type'],
             data['desirability'], data.get('undesired_amount', 0), data.get('description', '')),
            commit_tx=True
        )

    pool.retry_operation_sync(execute_query)
    update.message.reply_text("Операция сохранена!")
    return ConversationHandler.END

# Определение обработчиков диалогов
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start), MessageHandler(filters.regex("Записать операцию"), start)],
    states={
        TYPE: [MessageHandler(filters.text, get_type)],
        SUM: [MessageHandler(filters.text, get_sum)],
        ACCOUNT: [MessageHandler(filters.text, get_account)],
        CATEGORY: [MessageHandler(filters.text, get_category)],
        DESIRABILITY: [MessageHandler(filters.text, get_desirability)],
        UNDESIRED_AMOUNT: [MessageHandler(filters.text, get_undesired_amount)],
        DESCRIPTION: [MessageHandler(filters.text, get_description)],
        CONFIRM: [MessageHandler(filters.regex("Подтвердить"), save_transaction)],
    },
    fallbacks=[]
)

# Запуск бота
updater = Updater("7697444585:AAGcna4h-eGa-89UCTfG9XL4EGI-ujj0QWs", use_context=True)
dp = updater.dispatcher
dp.add_handler(conv_handler)
updater.start_polling()
updater.idle()