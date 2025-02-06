import ydb
import ydb.iam

driver = ydb.Driver(
    endpoint="grpcs://ydb.serverless.yandexcloud.net:2135",
    database="/ru-central1/b1g86rbv28go73jml91a/etnv8re60doc9qg4iglk",
    credentials=ydb.iam.ServiceAccountCredentials.from_file("authorized_key.json")
)

driver.wait(timeout=30)
print("✅ Успешное подключение к YDB!")