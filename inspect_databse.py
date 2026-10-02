# inspect_database.py
import inspect
from global_travel.database import Database

print("=== ИНСПЕКЦИЯ КЛАССА DATABASE ===")
print()

# Создаем экземпляр
db = Database()

print("1. Все публичные методы Database:")
print("-" * 40)

methods = []
for attr_name in dir(db):
    if not attr_name.startswith('_'):  # Только публичные
        attr = getattr(db, attr_name)
        if callable(attr):  # Только методы
            methods.append(attr_name)
            print(f"  - {attr_name}")

print()
print("2. Тестируем основные методы:")
print("-" * 40)

# Тестируем подключение
try:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        print("✅ get_connection() - работает")

        # Проверяем таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   Таблицы в БД: {tables}")
except Exception as e:
    print(f"❌ get_connection() - ошибка: {e}")

print()
print("3. Сигнатуры методов:")
print("-" * 40)

# Показываем сигнатуры
test_methods = ['add_client', 'add_tour', 'add_booking', 'get_clients', 'get_statistics']
for method_name in test_methods:
    if hasattr(db, method_name):
        try:
            method = getattr(db, method_name)
            sig = inspect.signature(method)
            print(f"  - {method_name}{sig}")
        except:
            print(f"  - {method_name} (сигнатура недоступна)")
    else:
        print(f"  - {method_name} (метод не найден)")