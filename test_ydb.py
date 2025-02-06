import ydb
import ydb.iam

ENDPOINT = "grpcs://your-database-name.ydb.yandexcloud.net:2135"
DATABASE = "/ru-central1/b1gXXXXXXXXX/your-db"

driver = ydb.Driver(endpoint=ENDPOINT, database=DATABASE, credentials=ydb.iam.MetadataUrlCredentials())

try:
    driver.wait(timeout=30)
    print("✅ Успешное подключение к YDB!")
except Exception as e:
    print("❌ Ошибка подключения:", e)