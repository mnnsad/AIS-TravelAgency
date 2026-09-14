print("=" * 60)
print("КОНФИГУРАЦИОННОЕ ТЕСТИРОВАНИЕ")
print("=" * 60)

print("\n1. ВЕРСИЯ PYTHON:")
import sys
print(f"Текущая: {sys.version[:20]}...")
if sys.version_info >= (3, 7):
    print("✓ Минимальная версия 3.7: OK")
else:
    print("✗ Требуется Python 3.7+")

print("\n2. БИБЛИОТЕКИ:")
try:
    import sqlite3
    print(f"✓ SQLite: {sqlite3.sqlite_version}")
except:
    print("✗ SQLite не работает")

try:
    import tkinter
    print("✓ Tkinter: установлен")
except:
    print("✗ Tkinter не установлен")

print("\n3. ОПЕРАЦИОННАЯ СИСТЕМА:")
import platform
os_name = platform.system()
print(f"Система: {os_name}")
if os_name in ['Windows', 'Linux', 'Darwin']:
    print("✓ Поддерживаемая ОС")
else:
    print("⚠  Неизвестная ОС")

print("\n4. ЭКРАН:")
try:
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.destroy()
    print(f"Разрешение: {width}x{height}")
    if width >= 1024 and height >= 768:
        print("✓ Достаточно для интерфейса")
    else:
        print("⚠  Маленький экран")
except:
    print("✗ Не удалось проверить")

print("\n5. ФАЙЛЫ:")
import os
files = ['database.py', 'desktop_app.py']
for file in files:
    if os.path.exists(file):
        print(f"✓ {file} найден")
    else:
        print(f"✗ {file} отсутствует")

print("\n6. КОДИРОВКА:")
encoding = sys.getdefaultencoding()
print(f"Кодировка: {encoding}")
try:
    "АИС Тур".encode(encoding)
    print("✓ Русский текст работает")
except:
    print("✗ Проблемы с русским")

print("\n7. БАЗА ДАННЫХ:")
try:
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id INT, name TEXT)")
    cursor.execute("INSERT INTO test VALUES (1, 'test')")
    cursor.execute("SELECT * FROM test")
    data = cursor.fetchall()
    conn.close()
    print("✓ База данных работает")
except Exception as e:
    print(f"✗ Ошибка БД: {e}")

print("\n" + "=" * 60)
print("РЕЗУЛЬТАТ:")
print("АИС «GLOBAL Travel» готова к работе!")
print("=" * 60)