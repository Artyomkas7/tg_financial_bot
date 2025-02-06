import ydb
import ydb.iam

driver = ydb.Driver(
    endpoint="grpcs://your-database-name.ydb.yandexcloud.net:2135",
    database="/ru-central1/b1gXXXXXXXXX/your-db",
    credentials=ydb.iam.ServiceAccountCredentials.from_file("authorized_key.json")
)

driver.wait(timeout=30)
print("✅ Успешное подключение к YDB!")