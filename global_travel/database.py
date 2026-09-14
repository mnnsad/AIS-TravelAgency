# database.py
import sqlite3
from datetime import date
from typing import List, Tuple, Dict, Any, Optional
import os


class Database:
    """Класс для работы с базой данных SQLite"""

    def __init__(self, db_name: str = "global_travel.db"):
        """Инициализация базы данных"""
        # Проверяем, есть ли база данных в разных возможных местах
        possible_paths = [
            db_name,  # В текущей директории
            f"data/{db_name}",  # В папке data
            f"../{db_name}",  # На уровень выше
            f"../data/{db_name}"  # В папке data на уровень выше
        ]

        # Ищем существующую базу данных
        self.db_name = None
        for path in possible_paths:
            if os.path.exists(path):
                self.db_name = path
                print(f"Найдена база данных: {path}")
                break

        # Если не нашли существующую БД, создаем новую
        if self.db_name is None:
            self.db_name = "global_travel.db"
            print("Создана новая база данных")

        # Проверяем структуру базы данных
        self.check_database_structure()

    def get_connection(self):
        """Создание подключения к базе данных"""
        return sqlite3.connect(self.db_name)

    def check_database_structure(self):
        """Проверка и обновление структуры базы данных при необходимости"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Проверяем существование таблиц
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]

            # Список необходимых таблиц
            required_tables = ['clients', 'tours', 'bookings', 'employees']

            # Создаем недостающие таблицы
            for table in required_tables:
                if table not in existing_tables:
                    print(f"Создание таблицы: {table}")
                    self.create_table(table, cursor)

            conn.commit()

    def create_table(self, table_name, cursor):
        """Создание таблицы по имени"""
        if table_name == 'clients':
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    passport TEXT UNIQUE NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT,
                    registration_date DATE NOT NULL
                )
            ''')

            # Добавляем тестовых клиентов
            try:
                test_clients = [
                    ("Иванов Иван Иванович", "4011123456", "+79161234567", "ivanov@example.com"),
                    ("Петрова Анна Сергеевна", "4011987654", "+79169876543", "petrova@example.com"),
                    ("Сидоров Алексей Владимирович", "4011567890", "+79165678901", "sidorov@example.com")
                ]

                for client in test_clients:
                    cursor.execute('''
                        INSERT OR IGNORE INTO clients (full_name, passport, phone, email, registration_date)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (*client, date.today()))
            except:
                pass

        elif table_name == 'tours':
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tours (
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
                )
            ''')

            # Добавляем тестовые туры
            try:
                test_tours = [
                    ("Отдых в Турции", "Турция", "Анталья", date(2024, 7, 15),
                     date(2024, 7, 25), 50000.0, 20, "Пляжный отдых в отеле 5*"),
                    ("Экскурсия по Италии", "Италия", "Рим", date(2024, 8, 1),
                     date(2024, 8, 10), 75000.0, 15, "Экскурсионный тур по историческим местам"),
                    ("Горнолыжный курорт", "Австрия", "Инсбрук", date(2024, 12, 20),
                     date(2024, 12, 30), 60000.0, 25, "Горнолыжный отдых с инструктором")
                ]

                for tour in test_tours:
                    cursor.execute('''
                        INSERT OR IGNORE INTO tours (name, country, city, start_date, end_date, 
                                                    price, max_persons, available_slots, description)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (*tour[:6], tour[6], tour[6], tour[7]))
            except:
                pass

        elif table_name == 'bookings':
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
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
                )
            ''')

        elif table_name == 'employees':
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    hire_date DATE NOT NULL,
                    salary REAL NOT NULL
                )
            ''')

            # Добавляем тестовых сотрудников
            try:
                test_employees = [
                    ("Смирнова Ольга Петровна", "Менеджер по продажам", "+79161112233",
                     "smirnova@globaltravel.com", date(2023, 1, 15), 85000.0),
                    ("Козлов Дмитрий Сергеевич", "Туроператор", "+79162223344",
                     "kozlov@globaltravel.com", date(2023, 3, 20), 75000.0),
                    ("Волкова Екатерина Игоревна", "Администратор", "+79163334455",
                     "volkova@globaltravel.com", date(2022, 11, 10), 65000.0)
                ]

                for emp in test_employees:
                    cursor.execute('''
                        INSERT OR IGNORE INTO employees (full_name, position, phone, email, hire_date, salary)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', emp)
            except:
                pass

    # ========== МЕТОДЫ ДЛЯ КЛИЕНТОВ ==========

    def add_client(self, full_name: str, passport: str, phone: str, email: str = "") -> int:
        """Добавление нового клиента"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO clients (full_name, passport, phone, email, registration_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (full_name, passport, phone, email, date.today()))
            conn.commit()
            return cursor.lastrowid

    def get_clients(self, search_query: str = "") -> List[Tuple]:
        """Получение списка клиентов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if search_query:
                search_query = f"%{search_query}%"
                cursor.execute('''
                    SELECT * FROM clients 
                    WHERE full_name LIKE ? OR passport LIKE ? OR phone LIKE ? OR email LIKE ?
                    ORDER BY full_name
                ''', (search_query, search_query, search_query, search_query))
            else:
                cursor.execute('SELECT * FROM clients ORDER BY full_name')

            return cursor.fetchall()

    def update_client(self, client_id: int, name: str, passport: str, phone: str, email: str) -> bool:
        """Обновление клиента в базе данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE clients 
                SET full_name = ?, passport = ?, phone = ?, email = ?
                WHERE id = ?
            ''', (name, passport, phone, email, client_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_client(self, client_id: int) -> bool:
        """Удаление клиента"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ========== МЕТОДЫ ДЛЯ ТУРОВ ==========

    def add_tour(self, name: str, country: str, city: str, start_date: date,
                 end_date: date, price: float, max_persons: int, description: str = "") -> int:
        """Добавление нового тура"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tours (name, country, city, start_date, end_date, 
                                  price, max_persons, available_slots, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, country, city, start_date, end_date, price,
                  max_persons, max_persons, description))
            conn.commit()
            return cursor.lastrowid

    def get_tours(self, country_filter: str = "") -> List[Tuple]:
        """Получение списка туров"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if country_filter:
                cursor.execute('''
                    SELECT * FROM tours 
                    WHERE country LIKE ? 
                    ORDER BY start_date, country, city
                ''', (f"%{country_filter}%",))
            else:
                cursor.execute('SELECT * FROM tours ORDER BY start_date, country, city')

            return cursor.fetchall()

    def update_tour(self, tour_id: int, name: str, country: str, city: str,
                    start_date: date, end_date: date, price: float,
                    max_persons: int, description: str) -> bool:
        """Обновление тура в базе данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tours 
                SET name = ?, country = ?, city = ?, start_date = ?, end_date = ?,
                    price = ?, max_persons = ?, description = ?
                WHERE id = ?
            ''', (name, country, city, start_date, end_date, price,
                  max_persons, description, tour_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_tour(self, tour_id: int) -> bool:
        """Удаление тура"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tours WHERE id = ?', (tour_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ========== МЕТОДЫ ДЛЯ БРОНИРОВАНИЙ ==========

    def add_booking(self, client_id: int, tour_id: int, persons_count: int,
                    notes: str = "") -> Tuple[bool, str, int]:
        """Добавление нового бронирования"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Проверяем доступность тура
            cursor.execute('SELECT available_slots, price FROM tours WHERE id = ?', (tour_id,))
            tour = cursor.fetchone()

            if not tour:
                return False, "Тур не найден", 0

            available_slots, price = tour

            if available_slots < persons_count:
                return False, f"Недостаточно свободных мест. Доступно: {available_slots}", 0

            # Вычисляем общую стоимость
            total_price = price * persons_count

            # Создаем бронирование
            cursor.execute('''
                INSERT INTO bookings (client_id, tour_id, booking_date, persons_count, 
                                     total_price, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (client_id, tour_id, date.today(), persons_count,
                  total_price, "confirmed", notes))

            booking_id = cursor.lastrowid

            # Обновляем количество доступных мест
            cursor.execute('''
                UPDATE tours 
                SET available_slots = available_slots - ? 
                WHERE id = ?
            ''', (persons_count, tour_id))

            conn.commit()
            return True, "Бронирование успешно создано", booking_id

    def get_bookings(self, status_filter: str = "") -> List[Tuple]:
        """Получение списка бронирований"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = '''
                SELECT b.*, c.full_name, t.name 
                FROM bookings b
                JOIN clients c ON b.client_id = c.id
                JOIN tours t ON b.tour_id = t.id
            '''
            params = []

            if status_filter:
                query += " WHERE b.status = ?"
                params.append(status_filter)

            query += " ORDER BY b.booking_date DESC"

            cursor.execute(query, params)
            return cursor.fetchall()

    def update_booking_status(self, booking_id: int, new_status: str) -> bool:
        """Обновление статуса бронирования"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Получаем информацию о бронировании для возврата мест при отмене
            if new_status == "cancelled":
                cursor.execute('SELECT tour_id, persons_count FROM bookings WHERE id = ?', (booking_id,))
                booking = cursor.fetchone()

                if booking:
                    tour_id, persons_count = booking
                    # Возвращаем места
                    cursor.execute('''
                        UPDATE tours 
                        SET available_slots = available_slots + ? 
                        WHERE id = ?
                    ''', (persons_count, tour_id))

            cursor.execute('''
                UPDATE bookings 
                SET status = ? 
                WHERE id = ?
            ''', (new_status, booking_id))

            conn.commit()
            return cursor.rowcount > 0

    def delete_booking(self, booking_id: int) -> bool:
        """Удаление бронирования"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Сначала отменяем бронирование, чтобы вернуть места
            self.update_booking_status(booking_id, "cancelled")
            cursor.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ========== МЕТОДЫ ДЛЯ СОТРУДНИКОВ ==========

    def add_employee(self, full_name: str, position: str, phone: str,
                     email: str, salary: float) -> int:
        """Добавление нового сотрудника"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO employees (full_name, position, phone, email, hire_date, salary)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (full_name, position, phone, email, date.today(), salary))
            conn.commit()
            return cursor.lastrowid

    def get_employees(self) -> List[Tuple]:
        """Получение списка сотрудников"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM employees ORDER BY full_name')
            return cursor.fetchall()

    def update_employee(self, employee_id: int, name: str, position: str,
                        phone: str, email: str, salary: float) -> bool:
        """Обновление сотрудника в базе данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE employees 
                SET full_name = ?, position = ?, phone = ?, email = ?, salary = ?
                WHERE id = ?
            ''', (name, position, phone, email, salary, employee_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_employee(self, employee_id: int) -> bool:
        """Удаление сотрудника"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM employees WHERE id = ?', (employee_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ========== МЕТОДЫ ДЛЯ СТАТИСТИКИ ==========

    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Общее количество клиентов
            try:
                cursor.execute('SELECT COUNT(*) FROM clients')
                stats['total_clients'] = cursor.fetchone()[0]
            except:
                stats['total_clients'] = 0

            # Общее количество туров
            try:
                cursor.execute('SELECT COUNT(*) FROM tours')
                stats['total_tours'] = cursor.fetchone()[0]
            except:
                stats['total_tours'] = 0

            # Общее количество бронирований
            try:
                cursor.execute('SELECT COUNT(*) FROM bookings')
                stats['total_bookings'] = cursor.fetchone()[0]
            except:
                stats['total_bookings'] = 0

            # Общая выручка
            try:
                cursor.execute('SELECT SUM(total_price) FROM bookings WHERE status != "cancelled"')
                total_revenue = cursor.fetchone()[0]
                stats['total_revenue'] = total_revenue if total_revenue else 0.0
            except:
                stats['total_revenue'] = 0.0

            # Количество активных бронирований
            try:
                cursor.execute('SELECT COUNT(*) FROM bookings WHERE status = "confirmed"')
                stats['active_bookings'] = cursor.fetchone()[0]
            except:
                stats['active_bookings'] = 0

            # Популярные направления
            try:
                cursor.execute('''
                    SELECT t.country, COUNT(b.id) as booking_count
                    FROM tours t
                    JOIN bookings b ON t.id = b.tour_id
                    WHERE b.status != "cancelled"
                    GROUP BY t.country
                    ORDER BY booking_count DESC
                    LIMIT 5
                ''')
                stats['popular_countries'] = cursor.fetchall()
            except:
                stats['popular_countries'] = []

            return stats

    def get_table_info(self):
        """Получение информации о структуре базы данных"""
        info = {}
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Получаем список таблиц
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]

                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()

                info[table_name] = {
                    'count': count,
                    'columns': [col[1] for col in columns]
                }

        return info