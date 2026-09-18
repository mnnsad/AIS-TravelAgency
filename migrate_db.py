import sqlite3
import os
from datetime import date


def check_and_migrate_database(db_path="global_travel.db"):
    """Проверка и миграция существующей базы данных"""

    if not os.path.exists(db_path):
        print(f"База данных {db_path} не найдена!")
        return False

    print(f"Проверка базы данных: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Проверяем существующие таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Существующие таблицы: {tables}")

        # 2. Создаем недостающие таблицы
        create_queries = [
            '''CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                passport TEXT UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                registration_date DATE NOT NULL
            )''',
            '''CREATE TABLE IF NOT EXISTS tours (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                city TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                price REAL NOT NULL,
                max_persons INTEGER NOT NULL,
                available_slots INTEGER NOT NULL,
                description TEXT
            )''',
            '''CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                tour_id INTEGER NOT NULL,
                booking_date DATE NOT NULL,
                persons_count INTEGER NOT NULL,
                total_price REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed',
                notes TEXT,
                FOREIGN KEY (client_id) REFERENCES clients (id),
                FOREIGN KEY (tour_id) REFERENCES tours (id)
            )''',
            '''CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                position TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                hire_date DATE NOT NULL,
                salary REAL NOT NULL
            )'''
        ]

        for query in create_queries:
            cursor.execute(query)

        # 3. Проверяем и обновляем структуру таблиц
        # (добавляем недостающие колонки, если нужно)

        # 4. Проверяем данные
        print("\nСтатистика базы данных:")
        for table in ['clients', 'tours', 'bookings', 'employees']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} записей")

        conn.commit()
        conn.close()

        print(f"\nБаза данных {db_path} готова к использованию!")
        return True

    except Exception as e:
        print(f"Ошибка при проверке базы данных: {e}")
        return False


def backup_database(db_path="global_travel.db"):
    """Создание резервной копии базы данных"""
    import shutil
    from datetime import datetime

    if os.path.exists(db_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.backup_{timestamp}"
        shutil.copy2(db_path, backup_path)
        print(f"Создана резервная копия: {backup_path}")
        return backup_path
    return None


if __name__ == "__main__":
    # Создаем резервную копию перед любыми изменениями
    backup = backup_database()

    # Проверяем и мигрируем базу данных
    success = check_and_migrate_database()

    if success:
        print("\nМиграция завершена успешно!")
        if backup:
            print(f"Резервная копия сохранена в: {backup}")
    else:
        print("\nВо время миграции возникли ошибки!")