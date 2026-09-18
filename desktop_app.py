import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import sqlite3
import os
import csv

from database import Database

"""Класс для генерации отчетов"""
class ReportGenerator:

    def __init__(self, db: Database):
        self.db = db

    def generate_sales_report(self, start_date: date, end_date: date) -> list:
        """Генерация отчета по продажам за период"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 
                    b.booking_date,
                    c.full_name as client_name,
                    t.name as tour_name,
                    t.country,
                    t.city,
                    b.persons_count,
                    b.total_price,
                    b.status
                FROM bookings b
                JOIN clients c ON b.client_id = c.id
                JOIN tours t ON b.tour_id = t.id
                WHERE b.booking_date BETWEEN ? AND ?
                ORDER BY b.booking_date DESC
            ''', (start_date, end_date))

            return cursor.fetchall()

    def generate_tours_report(self) -> list:
        """Генерация отчета по турам"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 
                    name,
                    country,
                    city,
                    start_date,
                    end_date,
                    price,
                    max_persons,
                    available_slots,
                    (max_persons - available_slots) as booked_slots,
                    ROUND((max_persons - available_slots) * 100.0 / max_persons, 2) as occupancy_rate
                FROM tours
                ORDER BY start_date
            ''')

            return cursor.fetchall()

    def generate_client_bookings_report(self, client_id: int) -> list:
        """Генерация отчета по бронированиям клиента"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 
                    b.booking_date,
                    t.name as tour_name,
                    t.country,
                    t.city,
                    t.start_date,
                    t.end_date,
                    b.persons_count,
                    b.total_price,
                    b.status,
                    b.notes
                FROM bookings b
                JOIN tours t ON b.tour_id = t.id
                WHERE b.client_id = ?
                ORDER BY b.booking_date DESC
            ''', (client_id,))

            return cursor.fetchall()

    def export_to_csv(self, data: list, filename: str, headers: list = None):
        """Экспорт данных в CSV файл"""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            if headers:
                writer.writerow(headers)

            for row in data:
                writer.writerow(row)

        return filename

    def generate_financial_report(self, year: int, month: int = None) -> dict:
        """Генерация финансового отчета"""
        from datetime import timedelta

        report = {
            'total_revenue': 0,
            'confirmed_bookings': 0,
            'cancelled_bookings': 0,
            'monthly_data': []
        }

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            if month:
                # Отчет за конкретный месяц
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(year, month + 1, 1) - timedelta(days=1)

                cursor.execute('''
                    SELECT 
                        SUM(total_price) as revenue,
                        COUNT(*) as total_bookings,
                        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                    FROM bookings
                    WHERE booking_date BETWEEN ? AND ?
                ''', (start_date, end_date))

                result = cursor.fetchone()
                if result and result[0]:
                    report['total_revenue'] = result[0]
                    report['total_bookings'] = result[1]
                    report['cancelled_bookings'] = result[2]
                    report['confirmed_bookings'] = result[1] - result[2]
            else:
                # Отчет за весь год по месяцам
                for m in range(1, 13):
                    start_date = date(year, m, 1)
                    if m == 12:
                        end_date = date(year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_date = date(year, m + 1, 1) - timedelta(days=1)

                    cursor.execute('''
                        SELECT 
                            SUM(total_price) as revenue,
                            COUNT(*) as total_bookings
                        FROM bookings
                        WHERE booking_date BETWEEN ? AND ? AND status != 'cancelled'
                    ''', (start_date, end_date))

                    result = cursor.fetchone()
                    monthly_revenue = result[0] if result and result[0] else 0
                    monthly_bookings = result[1] if result and result[1] else 0

                    report['monthly_data'].append({
                        'month': m,
                        'revenue': monthly_revenue,
                        'bookings': monthly_bookings
                    })

                    report['total_revenue'] += monthly_revenue
                    report['confirmed_bookings'] += monthly_bookings

            return report

class GlobalTravelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🏝️ GLOBAL Travel - Автоматизированная информационная система")
        self.root.geometry("1400x800")

        self.primary_color = '#2A9D8F',      # Бирюзовый
        self.secondary_color = '#264653',    # Темно-синий
        self.accent_color = '#E9C46A',       # Золотой
        self.light_color = 'white',          # Белый
        self.light_bg = '#F8F9FA',           # Светлый фон
        self.light_blue = '#E3F2FD'          # Светло-синий

        # Инициализация базы данных
        self.db = Database()
        self.reports = ReportGenerator(self.db)

        # Стили
        self.setup_styles()

        # Главный контейнер
        self.main_container = tk.Frame(root, bg=self.light_blue)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Панель навигации слева
        self.setup_sidebar()
        # Основная область справа
        self.setup_main_area()
        # Загрузка данных при старте
        self.load_initial_data()
        # Центрирование окна
        self.center_window()

    def center_window(self):
        """Центрирование окна на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_styles(self):
        """Настройка стилей приложения"""
        style = ttk.Style()
        style.theme_use('clam')

        # Настройка цветов
        style.configure('TLabel', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10))
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))

    def setup_sidebar(self):
        """Стилизованная боковая панель"""
        sidebar = tk.Frame(
            self.main_container,
            bg='#264653',  # Темно-синий
            width=280,
            highlightthickness=0
        )
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        sidebar.pack_propagate(False)

        # Логотип
        logo_frame = tk.Frame(sidebar, bg='#264653')
        logo_frame.pack(fill=tk.X, padx=20, pady=(30, 20))

        title_label = tk.Label(
            logo_frame,
            text="🏝️ GLOBAL Travel",
            font=('Arial', 16, 'bold'),
            fg='white',
            bg='#264653'
        )
        title_label.pack()

        subtitle_label = tk.Label(
            logo_frame,
            text="Туристическое агентство",
            font=('Arial', 10),
            fg='#E9C46A',
            bg='#264653'
        )
        subtitle_label.pack(pady=(5, 0))

        # Разделитель
        separator = tk.Frame(sidebar, height=2, bg='#2A9D8F')
        separator.pack(fill=tk.X, padx=20, pady=10)

        nav_buttons = [
            ("🏠 Главная", self.show_dashboard),
            ("👥 Клиенты", self.show_clients),
            ("🌍 Туры", self.show_tours),
            ("📅 Бронирования", self.show_bookings),
            ("👨‍💼 Сотрудники", self.show_employees),
            ("📊 Отчеты", self.show_reports),
            ("📈 Статистика", self.show_statistics),
            ("🗃️ База данных", self.show_database_info)
        ]

        for text, command in nav_buttons:
            btn = tk.Button(
                sidebar,
                text=text,
                font=('Arial', 11),
                anchor='w',
                bg='#264653',
                fg='white',
                activebackground='#2A9D8F',
                activeforeground='white',
                relief='flat',
                borderwidth=0,
                padx=20,
                pady=12,
                cursor='hand2',
                command=command
            )
            btn.pack(fill=tk.X, padx=10, pady=2)

            btn.bind("<Enter>", lambda e, b=btn: b.config(bg='#2A9D8F'))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg='#264653'))

        # Разделитель перед кнопкой выхода
        separator2 = tk.Frame(sidebar, height=2, bg='#2A9D8F')
        separator2.pack(fill=tk.X, padx=20, pady=(30, 20))

        # Кнопка выхода
        exit_btn = tk.Button(
            sidebar,
            text="🚪 Выход",
            font=('Arial', 11, 'bold'),
            bg='#CD5C5C',
            fg='white',
            activebackground='#B3372C',
            activeforeground='white',
            relief='flat',
            borderwidth=0,
            padx=20,
            pady=12,
            cursor='hand2',
            command=self.root.quit
        )
        exit_btn.pack(fill=tk.X, padx=10, pady=10)

        exit_btn.bind("<Enter>", lambda e: exit_btn.config(bg='#B3372C'))
        exit_btn.bind("<Leave>", lambda e: exit_btn.config(bg='#C73E1D'))

    def setup_main_area(self):
        """Настройка основной области"""
        main_bg = '#E3F2FD'

        self.main_area = tk.Frame(self.main_container, bg=main_bg)
        self.main_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Панель заголовка
        self.header_frame = tk.Frame(self.main_area, bg=main_bg, height=80, relief='flat')
        self.header_frame.pack(fill=tk.X, pady=(0, 20))
        self.header_frame.pack_propagate(False)

        self.header_label = tk.Label(self.header_frame, text="Главная панель", font=('Arial', 18, 'bold'), fg='#264653', bg=main_bg)
        self.header_label.pack(side=tk.LEFT, padx=30, pady=25)

        current_time = datetime.now().strftime("%d.%m.%Y | %H:%M")
        self.time_label = tk.Label(self.header_frame, text=current_time,
                                   font=('Arial', 10), fg='#6C757D', bg=main_bg)
        self.time_label.pack(side=tk.RIGHT, padx=30, pady=25)

        def update_time():
            current_time = datetime.now().strftime("%d.%m.%Y | %H:%M")
            self.time_label.config(text=current_time)
            self.root.after(1000, update_time)

        update_time()

        # Область контента
        self.content_frame = tk.Frame(self.main_area, bg=main_bg)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Показываем дашборд при запуске
        self.show_dashboard()

    def show_dashboard(self):
        """Отображение главной панели"""
        self.clear_content()
        self.header_label.config(text="Главная панель")

        stats = self.db.get_statistics()

        # Карточки статистики
        cards_frame = tk.Frame(self.content_frame, bg='#E3F2FD')
        cards_frame.pack(fill=tk.X, pady=(0, 20))

        stats_data = [
            ("👥 Клиенты", stats['total_clients'], '#2A9D8F'),
            ("🌍 Туры", stats['total_tours'], '#264653'),
            ("📅 Бронирования", stats['total_bookings'], '#18A558'),
            ("💰 Выручка", f"{stats['total_revenue']:,.2f} ₽", '#F18F01'),
            ("✅ Активные", stats['active_bookings'], '#2A9D8F'),
        ]

        for i, (title, value, color) in enumerate(stats_data):
            card = self.create_stat_card(cards_frame, title, value, color)
            card.grid(row=0, column=i, padx=5, pady=5, sticky='nsew')
            cards_frame.columnconfigure(i, weight=1)

        # Быстрые действия
        frame_bg = '#E3F2FD'

        actions_frame = tk.Frame(self.content_frame, bg=frame_bg, relief='flat')
        actions_frame.pack(fill=tk.X, pady=(0, 20))

        actions_label = tk.Label(actions_frame, text="Быстрые действия", font=('Arial', 12, 'bold'),
            fg='#264653', bg=frame_bg, anchor='w')
        actions_label.pack(fill=tk.X, padx=20, pady=(15, 10))

        quick_actions = [
            ("➕ Добавить клиента", self.show_clients),
            ("➕ Добавить тур", self.show_tours),
            ("➕ Новое бронирование", self.show_bookings),
            ("📊 Создать отчет", self.show_reports)
        ]

        actions_buttons_frame = tk.Frame(self.content_frame, bg=frame_bg)
        actions_buttons_frame.pack(fill=tk.X, padx=20, pady=(0, 15))

        button_colors = ['#2A9D8F', '#18A558', '#F18F01', '#264653']

        for i, (text, command) in enumerate(quick_actions):
            btn_color = button_colors[i]

            btn = tk.Button(actions_buttons_frame, text=text, font=('Arial', 10), bg=btn_color, fg='white',
                            activebackground=btn_color, activeforeground='white', relief='flat', borderwidth=0,
                            padx=20, pady=10, cursor='hand2', command=command)
            btn.grid(row=0, column=i, padx=10, pady=10, sticky='nsew')
            actions_buttons_frame.columnconfigure(i, weight=1)

            btn.bind("<Enter>", lambda e, b=btn: b.config(bg='#343A40'))
            btn.bind("<Leave>", lambda e, b=btn, c=btn_color: b.config(bg=c))

        # Последние бронирования
        bookings_frame = tk.Frame(self.content_frame, bg=frame_bg, relief='flat')
        bookings_frame.pack(fill=tk.BOTH, expand=True)

        bookings_label = tk.Label(bookings_frame, text="Последние бронирования", font=('Arial', 12, 'bold'),
            fg='#264653', bg=frame_bg, anchor='w')
        bookings_label.pack(fill=tk.X, padx=20, pady=(15, 10))

        # Таблица бронирований
        table_card = tk.Frame(bookings_frame, bg='#E3F2FD')
        table_card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        table_frame = tk.Frame(table_card, bg='#FFFFFF')
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('ID', 'Дата', 'Клиент', 'Тур', 'Стоимость', 'Статус')

        style = ttk.Style()
        style.configure('Booking.Treeview', background='white', fieldbackground='white', foreground='#264653',
                        rowheight=30, font=('Segoe UI', 10))
        style.configure('Booking.Treeview.Heading', background='#2A9D8F', foreground='white',
                        relief='flat', font=('Segoe UI', 11, 'bold'))
        style.map('Booking.Treeview.Heading', background=[('active', '#1F7A6D')])

        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10, style='Booking.Treeview')

        # Настройка колонок
        col_widths = [50, 100, 200, 200, 100, 100]
        for col, width in zip(columns, col_widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor='center')

        tree.tag_configure('oddrow', background='#F8F9FA')
        tree.tag_configure('evenrow', background='white')

        # Полосы прокрутки
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # Размещение
        tree.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
        scrollbar_y.grid(row=0, column=1, sticky='ns', padx=0, pady=0)
        scrollbar_x.grid(row=1, column=0, sticky='ew', padx=0, pady=0)

        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Загрузка данных
        bookings = self.db.get_bookings()
        for i, booking in enumerate(bookings[:10]):  # Последние 10 бронирований
            row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'

            tree.insert('', tk.END, values=(
                booking[0], booking[3], booking[8], booking[9],
                f"{booking[5]:,.2f} ₽", booking[6]
            ), tags=(row_tag,))

        self.bookings_tree = tree

    def create_stat_card(self, parent, title, value, color):
        """Создание карточки статистики"""
        card_bg = '#E3F2FD'

        card = tk.Frame(parent, bg=card_bg, relief='flat', highlightbackground='#E9ECEF', highlightthickness=1)

        # Верхняя полоска
        top_strip = tk.Frame(card, bg=color, height=5)
        top_strip.pack(fill=tk.X)

        content = tk.Frame(card, bg=card_bg, padx=15, pady=15)
        content.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(content, text=title, font=('Arial', 10),
                                fg='#6C757D', bg=card_bg, anchor='w')
        title_label.pack(fill=tk.X, pady=(0, 5))

        # Значение
        value_label = tk.Label(content, text=str(value), font=('Arial', 18, 'bold'),
                                fg='#343A40', bg=card_bg,anchor='w')
        value_label.pack(fill=tk.X)

        return card

    def show_clients(self):
        """Отображение раздела клиентов"""
        self.clear_content()
        self.header_label.config(text="Управление клиентами", font=('Segoe UI', 18, 'bold'), foreground='#264653')

        content_container = tk.Frame(self.content_frame, bg='#E3F2FD')
        content_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Верхняя панель с кнопками
        top_frame = tk.Frame(content_container, bg='#E3F2FD', height=80)
        top_frame.pack(fill=tk.X, pady=(0, 20))
        top_frame.pack_propagate(False)

        tk.Label(top_frame, text="Действия с клиентами", font=('Segoe UI', 12, 'bold'),
                 bg='#E3F2FD', fg='#264653').pack(side=tk.LEFT, padx=20, pady=25)

        button_style = {
            'font': ('Segoe UI', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 15,
            'pady': 8
        }

        add_btn = tk.Button(top_frame, text="➕ Добавить клиента", bg='#2A9D8F', fg='white', activebackground='#2A9D8F',
                    activeforeground='white', borderwidth=0, **button_style, command=self.open_add_client_dialog)
        add_btn.pack(side=tk.LEFT, padx=5)
        add_btn.bind('<Enter>', lambda e: add_btn.config(bg='#343A40'))
        add_btn.bind('<Leave>', lambda e: add_btn.config(bg='#2A9D8F'))

        search_btn = tk.Button(top_frame, text="🔍 Поиск", bg='#F18F01', fg='white', activebackground='#F18F01',
                    activeforeground='white', borderwidth=0, **button_style, command=self.search_clients)
        search_btn.pack(side=tk.LEFT, padx=5)
        search_btn.bind('<Enter>', lambda e: search_btn.config(bg='#343A40'))
        search_btn.bind('<Leave>', lambda e: search_btn.config(bg='#F18F01'))

        refresh_btn = tk.Button(top_frame, text="🔄 Обновить", bg='#27AE60', fg='white', activebackground='#27AE60',
                    activeforeground='white', borderwidth=0, **button_style, command=self.load_clients)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        refresh_btn.bind('<Enter>', lambda e: refresh_btn.config(bg='#343A40'))
        refresh_btn.bind('<Leave>', lambda e: refresh_btn.config(bg='#27AE60'))

        table_card = tk.Frame(content_container, bg='#E3F2FD')
        table_card.pack(fill=tk.BOTH, expand=True)

        # Таблица клиентов
        table_frame = tk.Frame(table_card, bg='#F8FAFC')
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('ID', 'ФИО', 'Паспорт', 'Телефон', 'Email', 'Дата регистрации')

        style = ttk.Style()
        style.configure('Client.Treeview', background='white', fieldbackground='white', foreground='#264653',
                        rowheight=30, font=('Segoe UI', 10))
        style.configure('Client.Treeview.Heading', font=('Segoe UI', 11, 'bold'),
                        background='#2A9D8F', foreground='white', relief='flat')
        style.map('Client.Treeview.Heading', background=[('active', '#1F7A6D')])

        self.clients_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10, style='Client.Treeview')

        # Настройка колонок
        col_widths = [50, 250, 120, 120, 180, 120]
        for col, width in zip(columns, col_widths):
            self.clients_tree.heading(col, text=col)
            self.clients_tree.column(col, width=width, anchor='center')

        self.clients_tree.tag_configure('oddrow', background='#F8F9FA')
        self.clients_tree.tag_configure('evenrow', background='white')

        # Полосы прокрутки
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.clients_tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.clients_tree.xview)
        self.clients_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # Размещение
        self.clients_tree.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
        scrollbar_y.grid(row=0, column=1, sticky='ns', padx=0, pady=0)
        scrollbar_x.grid(row=1, column=0, sticky='ew', padx=0, pady=0)

        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Контекстное меню
        self.setup_context_menu(self.clients_tree, self.edit_client, self.delete_client)

        # Загрузка данных
        self.load_clients()

    def load_clients(self):
        """Загрузка клиентов в таблицу"""
        # Очищаем таблицу
        for item in self.clients_tree.get_children():
            self.clients_tree.delete(item)

        # Загружаем данные
        clients = self.db.get_clients()
        for client in clients:
            self.clients_tree.insert('', tk.END, values=client)

    def open_add_client_dialog(self, client_id=None):
        """Открытие диалога добавления/редактирования клиента"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить клиента" if not client_id else "Редактировать клиента")
        dialog.geometry("600x450")
        dialog.configure(background='#F8FAFC')
        dialog.transient(self.root)
        dialog.grab_set()

        # Данные клиента для редактирования
        client_data = None
        if client_id:
            clients = self.db.get_clients()
            for client in clients:
                if client[0] == client_id:
                    client_data = client
                    break

        # Заголовок
        header_frame = tk.Frame(dialog, bg='#264653', height=80, relief='flat')
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        header_label = tk.Label(header_frame,
                                text="Добавление клиента" if not client_id else "Редактирование клиента",
                                font=('Arial', 14, 'bold'),
                                fg='white',
                                bg='#264653',
                                anchor='w')
        header_label.pack(side=tk.LEFT, padx=30, pady=25)

        # Основная форма
        form_frame = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=30)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # ФИО
        tk.Label(form_frame, text="ФИО *:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        name_entry = tk.Entry(form_frame, font=('Arial', 11),
                              bg='white', fg='#333', relief='solid', borderwidth=1,
                              width=40)
        name_entry.grid(row=0, column=1, pady=(0, 15), padx=(10, 0))

        # Паспорт
        tk.Label(form_frame, text="Паспорт *:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        passport_entry = tk.Entry(form_frame, font=('Arial', 11),
                                  bg='white', fg='#333', relief='solid', borderwidth=1,
                                  width=40)
        passport_entry.grid(row=1, column=1, pady=(0, 15), padx=(10, 0))

        # Телефон
        tk.Label(form_frame, text="Телефон *:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        phone_entry = tk.Entry(form_frame, font=('Arial', 11),
                               bg='white', fg='#333', relief='solid', borderwidth=1,
                               width=40)
        phone_entry.grid(row=2, column=1, pady=(0, 15), padx=(10, 0))

        # Email
        tk.Label(form_frame, text="Email:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        email_entry = tk.Entry(form_frame, font=('Arial', 11),
                               bg='white', fg='#333', relief='solid', borderwidth=1,
                               width=40)
        email_entry.grid(row=3, column=1, pady=(0, 15), padx=(10, 0))

        # Заполняем данные при редактировании
        if client_data:
            name_entry.insert(0, client_data[1])
            passport_entry.insert(0, client_data[2])
            phone_entry.insert(0, client_data[3])
            email_entry.insert(0, client_data[4])

        # Кнопки
        buttons_frame = tk.Frame(dialog, bg='#F8FAFC', pady=20)
        buttons_frame.pack(fill=tk.X, padx=30)

        def save_client():
            """Сохранение клиента"""
            name = name_entry.get().strip()
            passport = passport_entry.get().strip()
            phone = phone_entry.get().strip()
            email = email_entry.get().strip()

            if not name or not passport or not phone:
                messagebox.showerror("Ошибка", "Заполните обязательные поля (отмечены *)")
                return

            try:
                if client_id:
                    # Редактирование существующего клиента
                    success = self.db.update_client(client_id, name, passport, phone, email)
                    if success:
                        message = "Клиент обновлен успешно!"
                    else:
                        message = "Клиент не найден"
                else:
                    # Добавление нового клиента
                    self.db.add_client(name, passport, phone, email)
                    message = "Клиент добавлен успешно!"

                dialog.destroy()
                self.load_clients()
                messagebox.showinfo("Успех", message)

            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Клиент с таким паспортом уже существует")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")

        button_style = {
            'font': ('Arial', 10, 'bold'),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 25,
            'pady': 10,
            'borderwidth': 0
        }

        save_btn = tk.Button(buttons_frame, text="Сохранить",
                             bg='#2A9D8F', fg='white', activebackground='#2A9D8F',
                             activeforeground='white', **button_style, command=save_client)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg='#1F7A6D'))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg='#2A9D8F'))

        cancel_btn = tk.Button(buttons_frame, text="Отмена",
                               bg='#C73E1D', fg='white', activebackground='#C73E1D',
                               activeforeground='white', **button_style, command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg='#B3372C'))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg='#C73E1D'))

        # Фокус на первое поле
        name_entry.focus_set()

    def edit_client(self):
        """Редактирование выбранного клиента"""
        selection = self.clients_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите клиента для редактирования")
            return

        item = self.clients_tree.item(selection[0])
        client_id = item['values'][0]
        self.open_add_client_dialog(client_id)

    def delete_client(self):
        """Удаление выбранного клиента"""
        selection = self.clients_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите клиента для удаления")
            return

        item = self.clients_tree.item(selection[0])
        client_id = item['values'][0]
        client_name = item['values'][1]

        if messagebox.askyesno("Подтверждение",
                               f"Удалить клиента {client_name}? Данное действие нельзя отменить."):
            try:
                success = self.db.delete_client(client_id)

                if success:
                    self.load_clients()
                    messagebox.showinfo("Успех", "Клиент удален успешно!")
                else:
                    messagebox.showerror("Ошибка", "Не удалось удалить клиента")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при удалении: {str(e)}")

    def search_clients(self):
        """Поиск клиентов"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Поиск клиентов")
        dialog.geometry("400x250")
        dialog.configure(bg='#F8FAFC')
        dialog.transient(self.root)

        # Заголовок
        header_frame = tk.Frame(dialog, bg='#264653', height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="Поиск клиентов", font=('Arial', 14, 'bold'),
                 bg='#264653', fg='white').pack(pady=20)

        # Основная форма
        form_frame = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=30)
        form_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(form_frame, text="Введите текст для поиска:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653').pack(anchor='w', pady=(0, 10))

        search_entry = tk.Entry(form_frame, font=('Arial', 11), width=35,
                                bg='white', fg='#333', relief='solid', borderwidth=1)
        search_entry.pack(pady=(0, 20))
        search_entry.focus_set()

        def perform_search():
            search_text = search_entry.get().strip()
            if not search_text:
                return

            # Очищаем таблицу
            for item in self.clients_tree.get_children():
                self.clients_tree.delete(item)

            # Выполняем поиск
            clients = self.db.get_clients(search_text)
            for client in clients:
                self.clients_tree.insert('', tk.END, values=client)

            dialog.destroy()
            messagebox.showinfo("Поиск", f"Найдено клиентов: {len(clients)}")

        # Кнопки
        button_style = {
            'font': ('Arial', 10, 'bold'),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 20,
            'pady': 8,
            'borderwidth': 0
        }

        search_btn = tk.Button(form_frame, text="Искать",
                    bg='#2A9D8F', fg='white', activebackground='#2A9D8F',
                       activeforeground='white', **button_style, command=perform_search)
        search_btn.pack(side=tk.LEFT, padx=(0, 10))
        search_btn.bind('<Enter>', lambda e: search_btn.config(bg='#1F7A6D'))
        search_btn.bind('<Leave>', lambda e: search_btn.config(bg='#2A9D8F'))

        cancel_btn = tk.Button(form_frame, text="Отмена",
                    bg='#C73E1D', fg='white', activebackground='#C73E1D',
                        activeforeground='white', **button_style, command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg='#B3372C'))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg='#C73E1D'))

    def show_tours(self):
        """Отображение раздела туров"""
        self.clear_content()
        self.header_label.config(text="Управление турами", font=('Segoe UI', 18, 'bold'), fg='#264653')

        content_container = tk.Frame(self.content_frame, bg='#E3F2FD')
        content_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        top_frame = tk.Frame(content_container, bg='#E3F2FD', height=80)
        top_frame.pack(fill=tk.X, pady=(0, 20))
        top_frame.pack_propagate(False)

        tk.Label(top_frame, text="Действия с турами", font=('Segoe UI', 12, 'bold'),
                 bg='#E3F2FD', fg='#264653').pack(side=tk.LEFT, padx=20, pady=25)

        button_style = {
            'font': ('Segoe UI', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 15,
            'pady': 8
        }

        add_btn = tk.Button(top_frame, text="➕ Добавить тур", bg='#2A9D8F', fg='white', activebackground='#2A9D8F',
                            activeforeground='white', borderwidth=0, **button_style, command=self.open_add_tour_dialog)
        add_btn.pack(side=tk.LEFT, padx=5)
        add_btn.bind('<Enter>', lambda e: add_btn.config(bg='#343A40'))
        add_btn.bind('<Leave>', lambda e: add_btn.config(bg='#2A9D8F'))

        filter_btn = tk.Button(top_frame, text="🔍 Фильтр по стране", bg='#F18F01', fg='white', activebackground='#F18F01',
                               activeforeground='white', borderwidth=0, **button_style, command=self.filter_tours_by_country)
        filter_btn.pack(side=tk.LEFT, padx=5)
        filter_btn.bind('<Enter>', lambda e: filter_btn.config(bg='#343A40'))
        filter_btn.bind('<Leave>', lambda e: filter_btn.config(bg='#F18F01'))

        refresh_btn = tk.Button(top_frame, text="🔄 Обновить", bg='#27AE60', fg='white', activebackground='#27AE60',
                                activeforeground='white', borderwidth=0, **button_style, command=self.load_tours)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        refresh_btn.bind('<Enter>', lambda e: refresh_btn.config(bg='#343A40'))
        refresh_btn.bind('<Leave>', lambda e: refresh_btn.config(bg='#27AE60'))

        table_card = tk.Frame(content_container, bg='#E3F2FD')
        table_card.pack(fill=tk.BOTH, expand=True)

        # Таблица туров
        table_frame = tk.Frame(table_card, bg='#F8FAFC')
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('ID', 'Название', 'Страна', 'Город', 'Начало', 'Окончание',
                   'Цена', 'Макс. мест', 'Свободно', 'Описание')

        style = ttk.Style()
        style.configure('Tour.Treeview', background='white', fieldbackground='white', foreground='#264653',
                        rowheight=30, font=('Segoe UI', 10))
        style.configure('Tour.Treeview.Heading', font=('Segoe UI', 11, 'bold'),
                        background='#2A9D8F', foreground='white', relief='flat')
        style.map('Tour.Treeview.Heading', background=[('active', '#1F7A6D')])

        self.tours_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10,
                                         style='Tour.Treeview')

        # Настройка колонок
        col_widths = [50, 150, 100, 100, 100, 100, 80, 90, 80, 200]
        for col, width in zip(columns, col_widths):
            self.tours_tree.heading(col, text=col)
            self.tours_tree.column(col, width=width, anchor='center')

        # Полосы прокрутки
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tours_tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tours_tree.xview)
        self.tours_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # Размещение
        self.tours_tree.grid(row=0, column=0, sticky='nsew', pady=0, padx=0)
        scrollbar_y.grid(row=0, column=1, sticky='ns', pady=0, padx=0)
        scrollbar_x.grid(row=1, column=0, sticky='ew', pady=0, padx=0)

        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Контекстное меню
        self.setup_context_menu(self.tours_tree, self.edit_tour, self.delete_tour)

        # Загрузка данных
        self.load_tours()

    def load_tours(self, country_filter=""):
        """Загрузка туров в таблицу"""
        # Очищаем таблицу
        for item in self.tours_tree.get_children():
            self.tours_tree.delete(item)

        # Загружаем данные
        tours = self.db.get_tours(country_filter)
        for tour in tours:
            self.tours_tree.insert('', tk.END, values=tour)

    def open_add_tour_dialog(self, tour_id=None):
        """Открытие диалога добавления/редактирования тура"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить тур" if not tour_id else "Редактировать тур")
        dialog.geometry("600x600")
        dialog.configure(background='#F8FAFC')
        dialog.transient(self.root)
        dialog.grab_set()

        # Данные тура для редактирования
        tour_data = None
        if tour_id:
            tours = self.db.get_tours()
            for tour in tours:
                if tour[0] == tour_id:
                    tour_data = tour
                    break

        # Заголовок в стиле приложения
        header_frame = tk.Frame(dialog, bg='#264653', height=80, relief='flat')
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        header_label = tk.Label(header_frame,
                                text="Добавление тура" if not tour_id else "Редактирование тура",
                                font=('Arial', 14, 'bold'),
                                fg='white',
                                bg='#264653',
                                anchor='w')
        header_label.pack(side=tk.LEFT, padx=30, pady=25)

        # Основная форма
        form_frame = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=30)
        form_frame.pack(fill=tk.BOTH, expand=True)

        row = 0

        # Название
        tk.Label(form_frame, text="Название *:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=row, column=0, sticky=tk.W, pady=(0, 5))
        name_entry = tk.Entry(form_frame, font=('Arial', 11),
                              bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        name_entry.grid(row=row, column=1, pady=(0, 15), padx=(10, 0))
        row += 1

        # Страна
        tk.Label(form_frame, text="Страна *:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=row, column=0, sticky=tk.W, pady=(0, 5))
        country_entry = tk.Entry(form_frame, font=('Arial', 11),
                              bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        country_entry.grid(row=row, column=1, pady=(0, 15), padx=(10, 0))
        row += 1

        # Город
        tk.Label(form_frame, text="Город *:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=row, column=0, sticky=tk.W, pady=(0, 5))
        city_entry = tk.Entry(form_frame, font=('Arial', 11),
                              bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        city_entry.grid(row=row, column=1, pady=(0, 15), padx=(10, 0))
        row += 1

        # Дата начала
        tk.Label(form_frame, text="Дата начала (ГГГГ-ММ-ДД) *:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=row, column=0, sticky=tk.W, pady=(0, 5))
        start_date_entry = tk.Entry(form_frame, font=('Arial', 11),
                              bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        start_date_entry.grid(row=row, column=1, pady=(0, 15), padx=(10, 0))
        row += 1

        # Дата окончания
        tk.Label(form_frame, text="Дата окончания (ГГГГ-ММ-ДД) *:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=row, column=0, sticky=tk.W, pady=(0, 5))
        end_date_entry = tk.Entry(form_frame, font=('Arial', 11),
                                   bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        end_date_entry.grid(row=row, column=1, pady=(0, 15), padx=(10, 0))
        row += 1

        # Цена
        tk.Label(form_frame, text="Цена *:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=row, column=0, sticky=tk.W, pady=(0, 5))
        price_entry = tk.Entry(form_frame, font=('Arial', 11),
                                   bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        price_entry.grid(row=row, column=1, pady=(0, 15), padx=(10, 0))
        row += 1

        # Максимальное количество мест
        tk.Label(form_frame, text="Максимальное количество мест *:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=row, column=0, sticky=tk.W, pady=(0, 5))
        max_persons_entry = tk.Entry(form_frame, font=('Arial', 11),
                                   bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        max_persons_entry.grid(row=row, column=1, pady=(0, 15), padx=(10, 0))
        row += 1

        # Описание
        tk.Label(form_frame, text="Описание *:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=row, column=0, sticky=tk.W, pady=(0, 5))
        description_text = tk.Text(form_frame, font=('Arial', 11),
                                   bg='white', fg='#333', relief='solid', borderwidth=1, width=40, height=5)
        description_text.grid(row=row, column=1, pady=(0, 15), padx=(10, 0))
        row += 1

        # Заполняем данные при редактировании
        if tour_data:
            name_entry.insert(0, tour_data[1])
            country_entry.insert(0, tour_data[2])
            city_entry.insert(0, tour_data[3])
            start_date_entry.insert(0, tour_data[4])
            end_date_entry.insert(0, tour_data[5])
            price_entry.insert(0, tour_data[6])
            max_persons_entry.insert(0, tour_data[7])
            description_text.insert('1.0', tour_data[9] if len(tour_data) > 9 else "")

        # Кнопки
        buttons_frame = tk.Frame(dialog, bg='#F8FAFC', pady=20)
        buttons_frame.pack(fill=tk.X, padx=30)

        def save_tour():
            """Сохранение тура"""
            name = name_entry.get().strip()
            country = country_entry.get().strip()
            city = city_entry.get().strip()
            start_date_str = start_date_entry.get().strip()
            end_date_str = end_date_entry.get().strip()
            price_str = price_entry.get().strip()
            max_persons_str = max_persons_entry.get().strip()
            description = description_text.get('1.0', tk.END).strip()

            # Проверка обязательных полей
            if not all([name, country, city, start_date_str, end_date_str, price_str, max_persons_str]):
                messagebox.showerror("Ошибка", "Заполните все обязательные поля (отмечены *)")
                return

            try:
                # Парсинг данных
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str)
                price = float(price_str)
                max_persons = int(max_persons_str)

                if price <= 0 or max_persons <= 0:
                    messagebox.showerror("Ошибка", "Цена и количество мест должны быть положительными числами")
                    return

                if start_date >= end_date:
                    messagebox.showerror("Ошибка", "Дата начала должна быть раньше даты окончания")
                    return

                if tour_id:
                    # Редактирование существующего тура
                    success = self.db.update_tour(tour_id, name, country, city, start_date,
                                                  end_date, price, max_persons, description)
                    if success:
                        message = "Тур обновлен успешно!"
                    else:
                        message = "Тур не найден"
                else:
                    # Добавление нового тура
                    self.db.add_tour(name, country, city, start_date, end_date,
                                     price, max_persons, description)
                    message = "Тур добавлен успешно!"

                dialog.destroy()
                self.load_tours()
                messagebox.showinfo("Успех", message)

            except ValueError as e:
                messagebox.showerror("Ошибка", f"Ошибка в формате данных: {str(e)}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")

        button_style = {
            'font': ('Arial', 10, 'bold'),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 25,
            'pady': 10,
            'borderwidth': 0
        }

        # Кнопки
        save_btn = tk.Button(buttons_frame, text="Сохранить", bg='#2A9D8F', fg='white', activebackground='#2A9D8F', activeforeground='white', **button_style, command=save_tour)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg='#1F7A6D'))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg='#2A9D8F'))

        cancel_btn = tk.Button(buttons_frame, text="Отмена", bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg='#B3372C'))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg='#C73E1D'))

    def edit_tour(self):
        """Редактирование выбранного тура"""
        selection = self.tours_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите тур для редактирования")
            return

        item = self.tours_tree.item(selection[0])
        tour_id = item['values'][0]
        self.open_add_tour_dialog(tour_id)

    def delete_tour(self):
        """Удаление выбранного тура"""
        selection = self.tours_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите тур для удаления")
            return

        item = self.tours_tree.item(selection[0])
        tour_id = item['values'][0]
        tour_name = item['values'][1]

        if messagebox.askyesno("Подтверждение",
                               f"Удалить тур '{tour_name}'? Данное действие нельзя отменить."):
            try:
                success = self.db.delete_tour(tour_id)

                if success:
                    self.load_tours()
                    messagebox.showinfo("Успех", "Тур удален успешно!")
                else:
                    messagebox.showerror("Ошибка", "Не удалось удалить тур")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при удалении: {str(e)}")

    def filter_tours_by_country(self):
        """Фильтрация туров по стране"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Фильтр по стране")
        dialog.geometry("450x250")
        dialog.configure(bg='#F8FAFC')
        dialog.transient(self.root)

        # Заголовок
        header_frame = tk.Frame(dialog, bg='#264653', height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="Фильтр по стране", font=('Arial', 14, 'bold'),
                 bg='#264653', fg='white').pack(pady=20)

        # Основная форма
        form_frame = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=30)
        form_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(form_frame, text="Введите название страны (оставьте пустым для всех туров):",
                 font=('Arial', 10), bg='#F8FAFC', fg='#264653').pack(anchor='w', pady=(0, 10))

        country_entry = tk.Entry(form_frame, font=('Arial', 11), width=35,
                                 bg='white', fg='#333', relief='solid', borderwidth=1)
        country_entry.pack(pady=(0, 20))
        country_entry.focus_set()

        def apply_filter():
            country = country_entry.get().strip()
            self.load_tours(country)
            dialog.destroy()

            if country:
                messagebox.showinfo("Фильтр", f"Показаны туры в стране: {country}")
            else:
                messagebox.showinfo("Фильтр", "Показаны все туры")

        buttons_frame = tk.Frame(form_frame, bg='#E3F2FD')
        buttons_frame.pack(pady=10)

        button_style = {
            'font': ('Arial', 10, 'bold'),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 20,
            'pady': 8,
            'borderwidth': 0
        }

        filter_btn = tk.Button(buttons_frame, text="Применить фильтр", bg='#2A9D8F', fg='white', activebackground='#2A9D8F', activeforeground='white', **button_style, command=apply_filter)
        filter_btn.pack(side=tk.LEFT, padx=(0, 10))
        filter_btn.bind('<Enter>', lambda e: filter_btn.config(bg='#1F7A6D'))
        filter_btn.bind('<Leave>', lambda e: filter_btn.config(bg='#2A9D8F'))

        cancel_btn = tk.Button(buttons_frame, text="Отмена", bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg='#B3372C'))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg='#C73E1D'))

    def show_bookings(self):
        """Отображение раздела бронирований"""
        self.clear_content()
        self.header_label.config(text="Управление бронированиями", font=('Segoe UI', 18, 'bold'), fg='#264653')

        content_container = tk.Frame(self.content_frame, bg='#E3F2FD')
        content_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Верхняя панель с кнопками
        top_frame = tk.Frame(content_container, bg='#E3F2FD', height=80)
        top_frame.pack(fill=tk.X, pady=(0, 20))
        top_frame.pack_propagate(False)

        tk.Label(top_frame, text="Управление бронированиями", font=('Segoe UI', 12, 'bold'),
                 bg='#E3F2FD', fg='#264653').pack(side=tk.LEFT, padx=20, pady=25)

        button_style = {
            'font': ('Segoe UI', 10),
            'cursor': 'hand2',
            'padx': 15,
            'pady': 8
        }

        add_btn = tk.Button(top_frame, text="➕ Новое бронирование", bg='#2A9D8F', fg='white', activebackground='#2A9D8F',
                activeforeground='white', borderwidth=0, **button_style, command=self.open_add_booking_dialog)
        add_btn.pack(side=tk.LEFT, padx=5)
        add_btn.bind('<Enter>', lambda e: add_btn.config(bg='#343A40'))
        add_btn.bind('<Leave>', lambda e: add_btn.config(bg='#2A9D8F'))

        confirmed_btn = tk.Button(top_frame, text="✅ Подтвержденные", bg='#27AE60', fg='white', activebackground='#27AE60',
                activeforeground='white', borderwidth=0, **button_style, command=lambda: self.load_bookings("confirmed"))
        confirmed_btn.pack(side=tk.LEFT, padx=5)
        confirmed_btn.bind('<Enter>', lambda e: confirmed_btn.config(bg='#343A40'))
        confirmed_btn.bind('<Leave>', lambda e: confirmed_btn.config(bg='#27AE60'))

        cancelled_btn = tk.Button(top_frame, text="❌ Отмененные", bg='#C73E1D', fg='white', activebackground='#C73E1D',
                activeforeground='white', borderwidth=0, **button_style, command=lambda: self.load_bookings("cancelled"))
        cancelled_btn.pack(side=tk.LEFT, padx=5)
        cancelled_btn.bind('<Enter>', lambda e: cancelled_btn.config(bg='#343A40'))
        cancelled_btn.bind('<Leave>', lambda e: cancelled_btn.config(bg='#C73E1D'))

        refresh_btn = tk.Button(top_frame, text="🔄 Обновить", bg='#F18F01', fg='white', activebackground='#F18F01',
                activeforeground='white', borderwidth=0, **button_style, command=self.load_bookings)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        refresh_btn.bind('<Enter>', lambda e: refresh_btn.config(bg='#343A40'))
        refresh_btn.bind('<Leave>', lambda e: refresh_btn.config(bg='#F18F01'))

        table_card = tk.Frame(content_container, bg='#E3F2FD')
        table_card.pack(fill=tk.BOTH, expand=True)

        # Таблица бронирований
        table_frame = tk.Frame(table_card, bg='#F8FAFC')
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('ID', 'Дата', 'Клиент', 'Тур', 'Кол-во чел.', 'Стоимость', 'Статус', 'Примечания')

        style = ttk.Style()
        style.configure('Booking.Treeview', background='white', fieldbackground='white', foreground='#264653',
                        rowheight=30, font=('Segoe UI', 10))
        style.configure('Booking.Treeview.Heading', font=('Segoe UI', 11, 'bold'),
                        background='#2A9D8F', foreground='white', relief='flat')
        style.map('Booking.Treeview.Heading', background=[('active', '#1F7A6D')])

        self.bookings_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10, style='Booking.Treeview')

        # Настройка колонок
        col_widths = [50, 100, 150, 150, 100, 100, 100, 200]
        for col, width in zip(columns, col_widths):
            self.bookings_tree.heading(col, text=col)
            self.bookings_tree.column(col, width=width, anchor='center')

        # Полосы прокрутки
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.bookings_tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.bookings_tree.xview)
        self.bookings_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # Размещение
        self.bookings_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')

        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Контекстное меню
        self.setup_context_menu(self.bookings_tree, self.edit_booking_status, self.delete_booking)

        # Загрузка данных
        self.load_bookings()

    def load_bookings(self, status_filter=""):
        """Загрузка бронирований в таблицу"""
        # Очищаем таблицу
        for item in self.bookings_tree.get_children():
            self.bookings_tree.delete(item)

        # Загружаем данные
        bookings = self.db.get_bookings(status_filter)
        for booking in bookings:
            self.bookings_tree.insert('', tk.END, values=(
                booking[0], booking[3], booking[8], booking[9],
                booking[4], f"{booking[5]:,.2f} ₽", booking[6], booking[7]
            ))

    def open_add_booking_dialog(self):
        """Открытие диалога добавления бронирования"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Новое бронирование")
        dialog.geometry("600x450")
        dialog.configure(background='#F8FAFC')
        dialog.transient(self.root)
        dialog.grab_set()

        # Получаем списки клиентов и туров
        clients = self.db.get_clients()
        tours = self.db.get_tours()

        if not clients or not tours:
            messagebox.showerror("Ошибка", "Для создания бронирования нужны клиенты и туры")
            dialog.destroy()
            return

        # Заголовок
        header_frame = tk.Frame(dialog, bg='#264653', height=80, relief='flat')
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        header_label = tk.Label(header_frame,
                                text="Добавление бронирования",
                                font=('Arial', 14, 'bold'),
                                fg='white',
                                bg='#264653',
                                anchor='w')
        header_label.pack(side=tk.LEFT, padx=30, pady=25)

        # Основная форма
        form_frame = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=30)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Клиент
        tk.Label(form_frame, text="Клиент *:", font=('Arial', 10), bg='#F8FAFC', fg='#264653', anchor='w').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        client_var = tk.StringVar()
        client_combo = ttk.Combobox(form_frame, textvariable=client_var, font=('Arial', 11), width=38, state='readonly')
        client_combo.grid(row=0, column=1, pady=(0, 15), padx=(10, 0))

        # Заполняем клиентов
        client_dict = {}
        client_list = []
        for client in clients:
            display_text = f"{client[0]}: {client[1]}"
            client_list.append(display_text)
            client_dict[display_text] = client[0]

        client_combo['values'] = client_list

        # Тур
        tk.Label(form_frame, text="Тур *:", font=('Arial', 10), bg='#F8FAFC', fg='#264653', anchor='w').grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        tour_var = tk.StringVar()
        tour_combo = ttk.Combobox(form_frame, textvariable=tour_var, font=('Arial', 11), width=38, state='readonly')
        tour_combo.grid(row=1, column=1, pady=(0, 15), padx=(10, 0))

        # Заполняем туры
        tour_dict = {}
        tour_list = []
        for tour in tours:
            if tour[8] > 0:  # Только доступные туры
                display_text = f"{tour[0]}: {tour[1]} ({tour[2]}, {tour[3]}) - свободно: {tour[8]}"
                tour_list.append(display_text)
                tour_dict[display_text] = tour[0]

        tour_combo['values'] = tour_list

        # Количество человек
        tk.Label(form_frame, text="Количество человек *:", font=('Arial', 10), bg='#F8FAFC', fg='#264653', anchor='w').grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        persons_spinbox = tk.Spinbox(form_frame, from_=1, to=20, font=('Arial', 11), width=37, bg='white', fg='#333')
        persons_spinbox.grid(row=2, column=1, pady=(0, 15), padx=(10, 0))

        # Примечания
        tk.Label(form_frame, text="Примечания:", font=('Arial', 10), bg='#F8FAFC', fg='#264653', anchor='w').grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        notes_text = tk.Text(form_frame, font=('Arial', 11), width=38, height=4, bg='white', fg='#333', relief='solid', borderwidth=1)
        notes_text.grid(row=3, column=1, pady=(0, 15), padx=(10, 0))

        # Кнопки
        buttons_frame = tk.Frame(dialog, bg='#F8FAFC', pady=20)
        buttons_frame.pack(fill=tk.X, padx=30)

        def create_booking():
            """Создание бронирования"""
            client_text = client_var.get()
            tour_text = tour_var.get()
            persons_str = persons_spinbox.get()
            notes = notes_text.get('1.0', tk.END).strip()

            if not client_text or not tour_text or not persons_str:
                messagebox.showerror("Ошибка", "Заполните обязательные поля (отмечены *)")
                return

            try:
                client_id = client_dict[client_text]
                tour_id = tour_dict[tour_text]
                persons_count = int(persons_str)

                success, message, booking_id = self.db.add_booking(
                    client_id, tour_id, persons_count, notes
                )

                if success:
                    dialog.destroy()
                    self.load_bookings()
                    messagebox.showinfo("Успех", f"Бронирование создано! ID: {booking_id}")
                else:
                    messagebox.showerror("Ошибка", message)

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при создании бронирования: {str(e)}")

        button_style = {
            'font': ('Arial', 10, 'bold'),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 25,
            'pady': 10,
            'borderwidth': 0
        }

        save_btn = tk.Button(buttons_frame, text="Сохранить",
                             bg='#2A9D8F', fg='white', activebackground='#2A9D8F',
                             activeforeground='white', **button_style, command=create_booking)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg='#1F7A6D'))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg='#2A9D8F'))

        cancel_btn = tk.Button(buttons_frame, text="Отмена",
                               bg='#C73E1D', fg='white', activebackground='#C73E1D',
                               activeforeground='white', **button_style, command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg='#B3372C'))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg='#C73E1D'))

    def edit_booking_status(self):
        """Изменение статуса бронирования"""
        selection = self.bookings_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите бронирование для редактирования")
            return

        item = self.bookings_tree.item(selection[0])
        booking_id = item['values'][0]
        current_status = item['values'][6]

        dialog = tk.Toplevel(self.root)
        dialog.title("Изменение статуса бронирования")
        dialog.geometry("400x350")
        dialog.configure(bg='#F8FAFC')
        dialog.transient(self.root)
        dialog.grab_set()

        # Заголовок
        header_frame = tk.Frame(dialog, bg='#264653', height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="Изменение статуса", font=('Arial', 14, 'bold'),
                 bg='#264653', fg='white').pack(pady=20)

        # Основная форма
        form_frame = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=30)
        form_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(form_frame, text=f"Бронирование ID: {booking_id}", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653').pack(anchor='w', pady=(0, 5))
        tk.Label(form_frame, text=f"Текущий статус: {current_status}", font=('Arial', 10, 'bold'),
                 bg='#F8FAFC', fg='#2A9D8F').pack(anchor='w', pady=(0, 15))

        tk.Label(form_frame, text="Новый статус:", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653').pack(anchor='w', pady=(0, 5))

        status_var = tk.StringVar(value=current_status)
        status_combo = ttk.Combobox(form_frame, textvariable=status_var,
                                    font=('Arial', 11),
                                    values=["confirmed", "cancelled", "completed"],
                                    state='readonly', width=20)
        status_combo.pack(anchor='w', pady=(0, 20))

        def update_status():
            new_status = status_var.get()
            if new_status == current_status:
                messagebox.showwarning("Предупреждение", "Статус не изменился")
                return

            try:
                success = self.db.update_booking_status(booking_id, new_status)
                if success:
                    dialog.destroy()
                    self.load_bookings()
                    messagebox.showinfo("Успех", f"Статус изменен на '{new_status}'")
                else:
                    messagebox.showerror("Ошибка", "Не удалось изменить статус")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при изменении статуса: {str(e)}")

        buttons_frame = tk.Frame(form_frame, bg='#F8FAFC')
        buttons_frame.pack(pady=10)

        button_style = {
            'font': ('Arial', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 20,
            'pady': 8,
            'borderwidth': 0
        }

        save_btn = tk.Button(buttons_frame, text="Сохранить", bg='#2A9D8F', fg='white', activebackground='#2A9D8F', activeforeground='white', **button_style, command=update_status)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg='#1F7A6D'))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg='#2A9D8F'))

        cancel_btn = tk.Button(buttons_frame, text="Отмена", bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg='#B3372C'))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg='#C73E1D'))

    def delete_booking(self):
        """Удаление выбранного бронирования"""
        selection = self.bookings_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите бронирование для удаления")
            return

        item = self.bookings_tree.item(selection[0])
        booking_id = item['values'][0]

        if messagebox.askyesno("Подтверждение",
                               f"Удалить бронирование #{booking_id}? Данное действие нельзя отменить."):
            try:
                success = self.db.delete_booking(booking_id)

                if success:
                    self.load_bookings()
                    messagebox.showinfo("Успех", "Бронирование удалено успешно!")
                else:
                    messagebox.showerror("Ошибка", "Не удалось удалить бронирование")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при удалении: {str(e)}")

    def show_employees(self):
        """Отображение раздела сотрудников"""
        self.clear_content()
        self.header_label.config(text="Управление сотрудниками", font=('Segoe UI', 18, 'bold'), fg='#264653')

        content_container = tk.Frame(self.content_frame, bg='#E3F2FD')
        content_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Верхняя панель с кнопками
        top_frame = tk.Frame(content_container, bg='#E3F2FD', height=80)
        top_frame.pack(fill=tk.X, pady=(0, 20))
        top_frame.pack_propagate(False)

        tk.Label(top_frame, text="Управление сотрудниками", font=('Segoe UI', 12, 'bold'),
                 bg='#E3F2FD', fg='#264653').pack(side=tk.LEFT, padx=20, pady=25)

        button_style = {
            'font': ('Segoe UI', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'borderwidth': 0,
            'padx': 15,
            'pady': 8
        }

        add_btn = tk.Button(top_frame, text="➕ Добавить сотрудника", bg='#2A9D8F', fg='white', activebackground='#2A9D8F',
                            activeforeground='white', **button_style, command=self.open_add_employee_dialog)
        add_btn.pack(side=tk.LEFT, padx=5)
        add_btn.bind('<Enter>', lambda e: add_btn.config(bg='#1F7A6D'))
        add_btn.bind('<Leave>', lambda e: add_btn.config(bg='#2A9D8F'))

        refresh_btn = tk.Button(top_frame, text="🔄 Обновить", bg='#F18F01', fg='white', activebackground='#F18F01',
                                activeforeground='white', **button_style, command=self.load_employees)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        refresh_btn.bind('<Enter>', lambda e: refresh_btn.config(bg='#D97B0D'))
        refresh_btn.bind('<Leave>', lambda e: refresh_btn.config(bg='#F18F01'))

        table_card = tk.Frame(content_container, bg='#E3F2FD')
        table_card.pack(fill=tk.BOTH, expand=True)

        # Таблица сотрудников
        table_frame = tk.Frame(table_card, bg='#F8FAFC')
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('ID', 'ФИО', 'Должность', 'Телефон', 'Email', 'Дата приема', 'Зарплата')

        style = ttk.Style()
        style.configure('Employee.Treeview', background='white', fieldbackground='white', foreground='#264653',
                        rowheight=30, font=('Segoe UI', 10))
        style.configure('Employee.Treeview.Heading', font=('Segoe UI', 11, 'bold'),
                        background='#2A9D8F', foreground='white', relief='flat')
        style.map('Employee.Treeview.Heading', background=[('active', '#1F7A6D')])

        self.employees_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10,
                                       style='Employee.Treeview')

        # Настройка колонок
        col_widths = [20, 250, 300, 90, 140, 80, 80]
        for col, width in zip(columns, col_widths):
            self.employees_tree.heading(col, text=col)
            self.employees_tree.column(col, width=width, anchor='center')

        # Полосы прокрутки
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.employees_tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.employees_tree.xview)
        self.employees_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # Размещение
        self.employees_tree.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
        scrollbar_y.grid(row=0, column=1, sticky='ns', padx=0, pady=0)
        scrollbar_x.grid(row=1, column=0, sticky='ew', padx=0, pady=0)

        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Контекстное меню
        self.setup_context_menu(self.employees_tree, self.edit_employee, self.delete_employee)

        # Загрузка данных
        self.load_employees()

    def load_employees(self):
        """Загрузка сотрудников в таблицу"""
        # Очищаем таблицу
        for item in self.employees_tree.get_children():
            self.employees_tree.delete(item)

        # Загружаем данные
        employees = self.db.get_employees()
        for employee in employees:
            self.employees_tree.insert('', tk.END, values=employee)

    def open_add_employee_dialog(self, employee_id=None):
        """Открытие диалога добавления/редактирования сотрудника"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить сотрудника" if not employee_id else "Редактировать сотрудника")
        dialog.geometry("500x450")
        dialog.configure(background='#F8FAFC')
        dialog.transient(self.root)
        dialog.grab_set()

        # Данные сотрудника для редактирования
        employee_data = None
        if employee_id:
            employees = self.db.get_employees()
            for emp in employees:
                if emp[0] == employee_id:
                    employee_data = emp
                    break

        # Заголовок
        header_frame = tk.Frame(dialog, bg='#264653', height=80, relief='flat')
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        header_label = tk.Label(header_frame,
                                text="Добавление сотрудника" if not employee_id else "Редактирование сотрудника",
                                font=('Arial', 14, 'bold'),
                                fg='white',
                                bg='#264653',
                                anchor='w')
        header_label.pack(side=tk.LEFT, padx=30, pady=25)

        # Основная форма
        form_frame = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=30)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # ФИО
        tk.Label(form_frame, text="ФИО *:", font=('Arial', 10), bg='#F8FAFC', fg='#264653', anchor='w').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        name_entry = tk.Entry(form_frame, font=('Arial', 11), bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        name_entry.grid(row=0, column=1, pady=(0, 15), padx=(10, 0))

        # Должность
        tk.Label(form_frame, text="Должность *:", font=('Arial', 10), bg='#F8FAFC', fg='#264653', anchor='w').grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        position_entry = tk.Entry(form_frame, font=('Arial', 11), bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        position_entry.grid(row=1, column=1, pady=(0, 15), padx=(10, 0))

        # Телефон
        tk.Label(form_frame, text="Телефон *:", font=('Arial', 10), bg='#F8FAFC', fg='#264653', anchor='w').grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        phone_entry = tk.Entry(form_frame, font=('Arial', 11), bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        phone_entry.grid(row=2, column=1, pady=(0, 15), padx=(10, 0))

        # Email
        tk.Label(form_frame, text="Email *:", font=('Arial', 10), bg='#F8FAFC', fg='#264653', anchor='w').grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        email_entry = tk.Entry(form_frame, font=('Arial', 11), bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        email_entry.grid(row=3, column=1, pady=(0, 15), padx=(10, 0))

        # Зарплата
        tk.Label(form_frame, text="Зарплата *:", font=('Arial', 10), bg='#F8FAFC', fg='#264653', anchor='w').grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        salary_entry = tk.Entry(form_frame, font=('Arial', 11), bg='white', fg='#333', relief='solid', borderwidth=1, width=40)
        salary_entry.grid(row=4, column=1, pady=(0, 15), padx=(10, 0))

        # Заполняем данные при редактировании
        if employee_data:
            name_entry.insert(0, employee_data[1])
            position_entry.insert(0, employee_data[2])
            phone_entry.insert(0, employee_data[3])
            email_entry.insert(0, employee_data[4])
            salary_entry.insert(0, employee_data[6])

        # Кнопки (в стиле основного приложения)
        buttons_frame = tk.Frame(dialog, bg='#F8FAFC', pady=20)
        buttons_frame.pack(fill=tk.X, padx=30)

        def save_employee():
            """Сохранение сотрудника"""
            name = name_entry.get().strip()
            position = position_entry.get().strip()
            phone = phone_entry.get().strip()
            email = email_entry.get().strip()
            salary_str = salary_entry.get().strip()

            if not all([name, position, phone, email, salary_str]):
                messagebox.showerror("Ошибка", "Заполните все поля")
                return

            try:
                salary = float(salary_str)

                if salary <= 0:
                    messagebox.showerror("Ошибка", "Зарплата должна быть положительным числом")
                    return

                if employee_id:
                    # Редактирование существующего сотрудника
                    success = self.db.update_employee(employee_id, name, position, phone, email, salary)
                    if success:
                        message = "Сотрудник обновлен успешно!"
                    else:
                        message = "Сотрудник не найден"
                else:
                    # Добавление нового сотрудника
                    self.db.add_employee(name, position, phone, email, salary)
                    message = "Сотрудник добавлен успешно!"

                dialog.destroy()
                self.load_employees()
                messagebox.showinfo("Успех", message)

            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат зарплаты")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")

        button_style = {
            'font': ('Arial', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 25,
            'pady': 10,
            'borderwidth': 0
        }

        save_btn = tk.Button(buttons_frame, text="Сохранить", bg='#2A9D8F', fg='white', activebackground='#2A9D8F', activeforeground='white', **button_style, command=save_employee)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg='#1F7A6D'))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg='#2A9D8F'))

        cancel_btn = tk.Button(buttons_frame, text="Отмена", bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg='#B3372C'))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg='#C73E1D'))

        # Фокус на первое поле
        name_entry.focus_set()

    def edit_employee(self):
        """Редактирование выбранного сотрудника"""
        selection = self.employees_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите сотрудника для редактирования")
            return

        item = self.employees_tree.item(selection[0])
        employee_id = item['values'][0]
        self.open_add_employee_dialog(employee_id)

    def delete_employee(self):
        """Удаление выбранного сотрудника"""
        selection = self.employees_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите сотрудника для удаления")
            return

        item = self.employees_tree.item(selection[0])
        employee_id = item['values'][0]
        employee_name = item['values'][1]

        if messagebox.askyesno("Подтверждение",
                               f"Удалить сотрудника {employee_name}? Данное действие нельзя отменить."):
            try:
                success = self.db.delete_employee(employee_id)

                if success:
                    self.load_employees()
                    messagebox.showinfo("Успех", "Сотрудник удален успешно!")
                else:
                    messagebox.showerror("Ошибка", "Не удалось удалить сотрудника")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при удалении: {str(e)}")

    def show_reports(self):
        """Отображение раздела отчетов"""
        self.clear_content()
        self.header_label.config(text="Отчеты и аналитика", font=('Segoe UI', 18, 'bold'), fg='#264653')

        content_container = tk.Frame(self.content_frame, bg='#E3F2FD')
        content_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Заголовок
        header_frame = tk.Frame(content_container, bg='#E3F2FD', height=80)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="Генерация отчетов", font=('Segoe UI', 12, 'bold'),
                 bg='#E3F2FD', fg='#264653').pack(side=tk.LEFT, padx=20, pady=25)

        # Кнопки отчетов
        reports_frame = tk.Frame(content_container, bg='#E3F2FD')
        reports_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=20)

        reports = [
            ("📊 Отчет по продажам", self.generate_sales_report_dialog, '#2A9D8F'),
            ("🌍 Отчет по турам", self.generate_tours_report_dialog, '#264653'),
            ("👤 Отчет по клиенту", self.generate_client_report_dialog, '#18A558'),
            ("💰 Финансовый отчет", self.generate_financial_report_dialog, '#F18F01'),
            ("📈 Экспорт данных", self.export_data_dialog, '#9B59B6')
        ]

        button_style = {
            'font': ('Segoe UI', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'borderwidth': 0,
            'padx': 30,
            'pady': 15,
            'width': 25
        }

        for i, (text, command, color) in enumerate(reports):
            row = i // 2
            col = i % 2

            btn = tk.Button(reports_frame, text=text, bg=color, fg='white', activebackground=color, activeforeground='white', **button_style, command=command)
            btn.grid(row=row, column=col, padx=20, pady=20, sticky='nsew')

            btn.bind("<Enter>", lambda e, b=btn, c=color: b.config(bg='#343A40'))
            btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(bg=c))

        reports_frame.columnconfigure(0, weight=1)
        reports_frame.columnconfigure(1, weight=1)
        reports_frame.rowconfigure(0, weight=1)
        reports_frame.rowconfigure(1, weight=1)
        reports_frame.rowconfigure(2, weight=1)

    def generate_sales_report_dialog(self):
        """Диалог генерации отчета по продажам"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Отчет по продажам")
        dialog.geometry("450x350")
        dialog.configure(background='#F8FAFC')
        dialog.transient(self.root)

        # Заголовок
        header_frame = tk.Frame(dialog, bg='#264653', height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="Отчет по продажам", font=('Arial', 14, 'bold'),
                 bg='#264653', fg='white').pack(pady=20)

        # Основная форма
        form_frame = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=30)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Дата начала
        tk.Label(form_frame, text="Дата начала (ГГГГ-ММ-ДД):", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        start_entry = tk.Entry(form_frame, font=('Arial', 11), width=25,
                               bg='white', fg='#333', relief='solid', borderwidth=1)
        start_entry.grid(row=0, column=1, pady=(0, 15), padx=(10, 0))
        start_entry.insert(0, date.today().replace(day=1).isoformat())

        # Дата окончания
        tk.Label(form_frame, text="Дата окончания (ГГГГ-ММ-ДД):", font=('Arial', 10),
                 bg='#F8FAFC', fg='#264653', anchor='w').grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        end_entry = tk.Entry(form_frame, font=('Arial', 11), width=25,
                             bg='white', fg='#333', relief='solid', borderwidth=1)
        end_entry.grid(row=1, column=1, pady=(0, 15), padx=(10, 0))
        end_entry.insert(0, date.today().isoformat())

        def generate():
            """Генерация отчета"""
            start_date_str = start_entry.get().strip()
            end_date_str = end_entry.get().strip()

            try:
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str)

                data = self.reports.generate_sales_report(start_date, end_date)

                if not data:
                    messagebox.showinfo("Отчет", "Нет данных за указанный период")
                    return

                # Отображение результатов
                result_dialog = tk.Toplevel(dialog)
                result_dialog.title("Результаты отчета по продажам")
                result_dialog.geometry("800x600")
                result_dialog.configure(background='#F8FAFC')

                # Заголовок
                result_header = tk.Frame(result_dialog, bg='#264653', height=70)
                result_header.pack(fill=tk.X)
                result_header.pack_propagate(False)

                tk.Label(result_header, text="Результаты отчета по продажам", font=('Arial', 14, 'bold'), bg='#264653', fg='white').pack(pady=20)

                # Текстовое поле с результатами
                text_frame = tk.Frame(result_dialog, bg='#F8FAFC', padx=10, pady=10)
                text_frame.pack(fill=tk.BOTH, expand=True)

                text_widget = tk.Text(text_frame, wrap=tk.NONE, font=('Courier', 10),
                                      bg='white', fg='#333', relief='solid', borderwidth=1)

                scrollbar_y = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
                scrollbar_x = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text_widget.xview)
                text_widget.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

                text_widget.grid(row=0, column=0, sticky='nsew')
                scrollbar_y.grid(row=0, column=1, sticky='ns')
                scrollbar_x.grid(row=1, column=0, sticky='ew')

                text_frame.columnconfigure(0, weight=1)
                text_frame.rowconfigure(0, weight=1)

                # Добавляем данные
                headers = ['Дата', 'Клиент', 'Тур', 'Страна', 'Город', 'Человек', 'Стоимость', 'Статус']
                text_widget.insert(tk.END, "\t".join(headers) + "\n")
                text_widget.insert(tk.END, "-" * 100 + "\n")

                total_revenue = 0
                for row in data:
                    text_widget.insert(tk.END, "\t".join(str(x) for x in row) + "\n")
                    if row[7] != "cancelled":
                        total_revenue += row[6]

                text_widget.insert(tk.END, "\n" + "=" * 100 + "\n")
                text_widget.insert(tk.END, f"Общая выручка: {total_revenue:,.2f} ₽\n")
                text_widget.insert(tk.END, f"Всего записей: {len(data)}\n")

                # Кнопки
                buttons_frame = tk.Frame(result_dialog, bg='#F8FAFC', pady=10)
                buttons_frame.pack(fill=tk.X, padx=30)

                # Кнопка экспорта
                def export_csv():
                    filename = filedialog.asksaveasfilename(
                        defaultextension=".csv",
                        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
                    )
                    if filename:
                        headers = ['Дата', 'Клиент', 'Тур', 'Страна', 'Город', 'Человек', 'Стоимость', 'Статус']
                        self.reports.export_to_csv(data, filename, headers)
                        messagebox.showinfo("Экспорт", f"Отчет сохранен в {filename}")

                button_style = {
                    'font': ('Arial', 10, 'bold'),
                    'relief': 'flat',
                    'cursor': 'hand2',
                    'padx': 20,
                    'pady': 8,
                    'borderwidth': 0
                }

                export_btn = tk.Button(buttons_frame, text="Экспорт в CSV", bg='#2A9D8F', fg='white', activebackground='#2A9D8F', activeforeground='white', **button_style, command=export_csv)
                export_btn.pack(side=tk.LEFT, padx=(0, 10))
                export_btn.bind('<Enter>', lambda e: export_btn.config(bg='#1F7A6D'))
                export_btn.bind('<Leave>', lambda e: export_btn.config(bg='#2A9D8F'))

                close_btn = tk.Button(buttons_frame, text="Закрыть", bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=result_dialog.destroy)
                close_btn.pack(side=tk.LEFT)
                close_btn.bind('<Enter>', lambda e: close_btn.config(bg='#B3372C'))
                close_btn.bind('<Leave>', lambda e: close_btn.config(bg='#C73E1D'))

            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат даты")

        # Кнопки
        buttons_frame = tk.Frame(dialog, bg='#F8FAFC', pady=20)
        buttons_frame.pack(fill=tk.X, padx=30)

        button_style = {
            'font': ('Arial', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 20,
            'pady': 8,
            'borderwidth': 0
        }

        generate_btn = tk.Button(buttons_frame, text="Сгенерировать", bg='#2A9D8F', fg='white', activebackground='#2A9D8F', activeforeground='white', **button_style, command=generate)
        generate_btn.pack(side=tk.LEFT, padx=(0, 10))
        generate_btn.bind('<Enter>', lambda e: generate_btn.config(bg='#1F7A6D'))
        generate_btn.bind('<Leave>', lambda e: generate_btn.config(bg='#2A9D8F'))

        close_btn = tk.Button(buttons_frame, text="Закрыть", bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=dialog.destroy)
        close_btn.pack(side=tk.LEFT)
        close_btn.bind('<Enter>', lambda e: close_btn.config(bg='#B3372C'))
        close_btn.bind('<Leave>', lambda e: close_btn.config(bg='#C73E1D'))

    def generate_tours_report_dialog(self):
        """Генерация отчета по турам"""
        try:
            data = self.reports.generate_tours_report()

            if not data:
                messagebox.showinfo("Отчет", "Нет данных по турам")
                return

            # Отображение результатов
            dialog = tk.Toplevel(self.root)
            dialog.title("Отчет по турам")
            dialog.geometry("900x600")
            dialog.configure(background='#F8FAFC')

            # Заголовок
            header_frame = tk.Frame(dialog, bg='#264653', height=70)
            header_frame.pack(fill=tk.X)
            header_frame.pack_propagate(False)

            tk.Label(header_frame, text="Отчет по турам", font=('Arial', 14, 'bold'), bg='#264653', fg='white').pack(pady=20)

            # Текстовое поле с результатами
            text_frame = tk.Frame(dialog, bg='#F8FAFC', padx=10, pady=10)
            text_frame.pack(fill=tk.BOTH, expand=True)

            text_widget = tk.Text(text_frame, wrap=tk.NONE, font=('Courier', 9), bg='white', fg='#333', relief='solid', borderwidth=1)

            scrollbar_y = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            scrollbar_x = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text_widget.xview)
            text_widget.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

            text_widget.grid(row=0, column=0, sticky='nsew')
            scrollbar_y.grid(row=0, column=1, sticky='ns')
            scrollbar_x.grid(row=1, column=0, sticky='ew')

            text_frame.columnconfigure(0, weight=1)
            text_frame.rowconfigure(0, weight=1)

            # Добавляем данные
            headers = ['Название', 'Страна', 'Город', 'Начало', 'Окончание',
                       'Цена', 'Всего мест', 'Свободно', 'Занято', 'Загруженность %']
            text_widget.insert(tk.END, "\t".join(headers) + "\n")
            text_widget.insert(tk.END, "-" * 120 + "\n")

            total_tours = 0
            total_occupied = 0
            total_capacity = 0

            for row in data:
                text_widget.insert(tk.END, "\t".join(str(x) for x in row) + "\n")
                total_tours += 1
                if len(row) > 8:
                    total_capacity += row[6] if row[6] else 0
                    total_occupied += row[8] if row[8] else 0

            text_widget.insert(tk.END, "\n" + "=" * 120 + "\n")
            text_widget.insert(tk.END, f"Всего туров: {total_tours}\n")
            if total_capacity > 0:
                occupancy_rate = (total_occupied / total_capacity) * 100
                text_widget.insert(tk.END, f"Общая загруженность: {occupancy_rate:.2f}%\n")

            # Кнопки
            buttons_frame = tk.Frame(dialog, bg='#F8FAFC', pady=10)
            buttons_frame.pack(fill=tk.X, padx=30)

            # Кнопка экспорта
            def export_csv():
                filename = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
                )
                if filename:
                    self.reports.export_to_csv(data, filename, headers)
                    messagebox.showinfo("Экспорт", f"Отчет сохранен в {filename}")

            button_style = {
                'font': ('Arial', 10),
                'relief': 'flat',
                'cursor': 'hand2',
                'padx': 20,
                'pady': 8,
                'borderwidth': 0
            }

            export_btn = tk.Button(buttons_frame, text="📥 Экспорт в CSV", bg='#2A9D8F', fg='white', activebackground='#2A9D8F', activeforeground='white', **button_style, command=export_csv)
            export_btn.pack(side=tk.LEFT, padx=(0, 10))
            export_btn.bind('<Enter>', lambda e: export_btn.config(bg='#1F7A6D'))
            export_btn.bind('<Leave>', lambda e: export_btn.config(bg='#2A9D8F'))

            close_btn = tk.Button(buttons_frame, text="Закрыть", bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=dialog.destroy)
            close_btn.pack(side=tk.LEFT)
            close_btn.bind('<Enter>', lambda e: close_btn.config(bg='#B3372C'))
            close_btn.bind('<Leave>', lambda e: close_btn.config(bg='#C73E1D'))

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при генерации отчета: {str(e)}")

    def generate_client_report_dialog(self):
        """Диалог генерации отчета по клиенту"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Отчет по клиенту")
        dialog.geometry("450x300")
        dialog.configure(background='#F8FAFC')
        dialog.transient(self.root)

        # Заголовок
        header_frame = tk.Frame(dialog, bg='#264653', height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="Отчет по клиенту", font=('Arial', 14, 'bold'), bg='#264653', fg='white').pack(pady=20)

        # Основная форма
        form_frame = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=30)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Получаем список клиентов
        clients = self.db.get_clients()
        client_dict = {}
        client_list = []

        for client in clients:
            display_text = f"{client[0]}: {client[1]}"
            client_list.append(display_text)
            client_dict[display_text] = client[0]

        tk.Label(form_frame, text="Выберите клиента:", font=('Arial', 10, 'bold'), bg='#F8FAFC', fg='#264653', anchor='center').pack(anchor='center', pady=(0, 10))

        client_var = tk.StringVar()
        client_combo = ttk.Combobox(dialog, textvariable=client_var, font=('Arial', 11), values=client_list, width=38, state='readonly')
        client_combo.pack(pady=(0, 20))
        client_combo.focus_set()

        def generate():
            """Генерация отчета"""
            client_text = client_var.get()
            if not client_text:
                messagebox.showwarning("Предупреждение", "Выберите клиента")
                return

            client_id = client_dict[client_text]
            data = self.reports.generate_client_bookings_report(client_id)

            if not data:
                messagebox.showinfo("Отчет", "У клиента нет бронирований")
                return

            # Отображение результатов
            result_dialog = tk.Toplevel(dialog)
            result_dialog.title(f"Отчет по клиенту {client_text}")
            result_dialog.geometry("900x550")
            result_dialog.configure(background='#F8FAFC')

            # Заголовок
            result_header = tk.Frame(result_dialog, bg='#264653', height=70)
            result_header.pack(fill=tk.X)
            result_header.pack_propagate(False)

            tk.Label(result_header, text=f"Отчет по клиенту: {client_text}", font=('Arial', 14, 'bold'), bg='#264653', fg='white').pack(pady=20)

            # Текстовое поле с результатами
            text_frame = tk.Frame(result_dialog, bg='#F8FAFC', padx=10, pady=10)
            text_frame.pack(fill=tk.BOTH, expand=True)

            text_widget = tk.Text(text_frame, wrap=tk.NONE, font=('Courier', 9), bg='white', fg='#333', relief='solid', borderwidth=1)

            scrollbar_y = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            scrollbar_x = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text_widget.xview)
            text_widget.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

            text_widget.grid(row=0, column=0, sticky='nsew')
            scrollbar_y.grid(row=0, column=1, sticky='ns')
            scrollbar_x.grid(row=1, column=0, sticky='ew')

            text_frame.columnconfigure(0, weight=1)
            text_frame.rowconfigure(0, weight=1)

            # Добавляем данные
            headers = ['Дата брони', 'Тур', 'Страна', 'Город', 'Начало',
                       'Окончание', 'Человек', 'Стоимость', 'Статус', 'Примечания']
            text_widget.insert(tk.END, "\t".join(headers) + "\n")
            text_widget.insert(tk.END, "-" * 120 + "\n")

            total_spent = 0
            confirmed_bookings = 0

            for row in data:
                text_widget.insert(tk.END, "\t".join(str(x) for x in row) + "\n")
                if row[8] != "cancelled":
                    total_spent += row[7]
                    confirmed_bookings += 1

            text_widget.insert(tk.END, "\n" + "=" * 100 + "\n")
            text_widget.insert(tk.END, f"Общая сумма покупок: {total_spent:,.2f} ₽\n")
            text_widget.insert(tk.END, f"Всего бронирований: {len(data)}\n")
            text_widget.insert(tk.END, f"Подтвержденных бронирований: {confirmed_bookings}\n")

            if len(data) > 0:
                avg_check = total_spent / confirmed_bookings if confirmed_bookings > 0 else 0
                text_widget.insert(tk.END, f"Средний чек: {avg_check:,.2f} ₽\n")

            # Кнопки
            buttons_frame = tk.Frame(result_dialog, bg='#F8FAFC', pady=10)
            buttons_frame.pack(fill=tk.X, padx=30)

            # Кнопка экспорта
            def export_csv():
                filename = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
                )
                if filename:
                    self.reports.export_to_csv(data, filename, headers)
                    messagebox.showinfo("Экспорт", f"Отчет сохранен в {filename}")

            button_style = {
                'font': ('Arial', 10),
                'relief': 'flat',
                'cursor': 'hand2',
                'padx': 20,
                'pady': 8,
                'borderwidth': 0
            }

            export_btn = tk.Button(buttons_frame, text="Экспорт в CSV", bg='#2A9D8F', fg='white', activebackground='#2A9D8F', activeforeground='white', **button_style, command=export_csv)
            export_btn.pack(side=tk.LEFT, padx=(0, 10))
            export_btn.bind('<Enter>', lambda e: export_btn.config(bg='#1F7A6D'))
            export_btn.bind('<Leave>', lambda e: export_btn.config(bg='#2A9D8F'))

            close_btn = tk.Button(buttons_frame, text="Закрыть", bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=result_dialog.destroy)
            close_btn.pack(side=tk.LEFT)
            close_btn.bind('<Enter>', lambda e: close_btn.config(bg='#B3372C'))
            close_btn.bind('<Leave>', lambda e: close_btn.config(bg='#C73E1D'))

        # Кнопки
        buttons_frame = tk.Frame(dialog, bg='#F8FAFC', pady=20)
        buttons_frame.pack(fill=tk.X, padx=30)

        button_style = {
            'font': ('Arial', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 20,
            'pady': 8,
            'borderwidth': 0
        }

        generate_btn = tk.Button(buttons_frame, text="Сгенерировать отчет", bg='#2A9D8F', fg='white', activebackground='#2A9D8F', activeforeground='white', **button_style, command=generate)
        generate_btn.pack(side=tk.LEFT, padx=(0, 10))
        generate_btn.bind('<Enter>', lambda e: generate_btn.config(bg='#1F7A6D'))
        generate_btn.bind('<Leave>', lambda e: generate_btn.config(bg='#2A9D8F'))

        close_btn = tk.Button(buttons_frame, text="Закрыть",bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=dialog.destroy)
        close_btn.pack(side=tk.LEFT)
        close_btn.bind('<Enter>', lambda e: close_btn.config(bg='#B3372C'))
        close_btn.bind('<Leave>', lambda e: close_btn.config(bg='#C73E1D'))

    def generate_financial_report_dialog(self):
        """Диалог генерации финансового отчета"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Финансовый отчет")
        dialog.geometry("450x350")
        dialog.configure(background='#F8FAFC')
        dialog.transient(self.root)

        # Заголовок
        header_frame = tk.Frame(dialog, bg='#264653', height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="Финансовый отчет", font=('Arial', 14, 'bold'),
                 bg='#264653', fg='white').pack(pady=20)

        # Основная форма
        form_frame = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=30)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Год
        tk.Label(form_frame, text="Год:", font=('Arial', 10), bg='#F8FAFC', fg='#264653', anchor='w').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        year_var = tk.StringVar(value=str(date.today().year))
        year_spinbox = tk.Spinbox(form_frame, from_=2000, to=2100, textvariable=year_var, font=('Arial', 11), width=20, bg='white', fg='#333')
        year_spinbox.grid(row=0, column=1, pady=(0, 15), padx=(10, 0))

        # Месяц
        tk.Label(form_frame, text="Месяц (0 = годовой отчет):", font=('Arial', 10), bg='#F8FAFC', fg='#264653', anchor='w').grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        month_var = tk.StringVar(value="0")
        month_spinbox = tk.Spinbox(form_frame, from_=0, to=12, textvariable=month_var, font=('Arial', 11), width=20, bg='white', fg='#333')
        month_spinbox.grid(row=1, column=1, pady=(0, 15), padx=(10, 0))

        def generate():
            """Генерация отчета"""
            try:
                year = int(year_var.get())
                month = int(month_var.get())

                if month == 0:
                    report = self.reports.generate_financial_report(year)

                    # Отображение годового отчета
                    result_dialog = tk.Toplevel(dialog)
                    result_dialog.title(f"Финансовый отчет за {year} год")
                    result_dialog.geometry("600x600")
                    result_dialog.configure(background='#F8FAFC')

                    # Заголовок
                    result_header = tk.Frame(result_dialog, bg='#264653', height=70)
                    result_header.pack(fill=tk.X)
                    result_header.pack_propagate(False)

                    tk.Label(result_header, text=f"Финансовый отчет за {year} год", font=('Arial', 14, 'bold'),
                             bg='#264653', fg='white').pack(pady=20)

                    # Текстовое поле с результатами
                    text_frame = tk.Frame(result_dialog, bg='#F8FAFC', padx=10, pady=10)
                    text_frame.pack(fill=tk.BOTH, expand=True)

                    text_widget = tk.Text(text_frame, wrap=tk.NONE, font=('Courier', 10),
                                          bg='white', fg='#333', relief='solid', borderwidth=1)

                    scrollbar_y = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
                    text_widget.configure(yscrollcommand=scrollbar_y.set)

                    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                    scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

                    text_widget.insert(tk.END, f"Финансовый отчет за {year} год\n")
                    text_widget.insert(tk.END, "=" * 50 + "\n\n")
                    text_widget.insert(tk.END, f"Общая выручка: {report['total_revenue']:,.2f} ₽\n")
                    text_widget.insert(tk.END, f"Подтвержденных бронирований: {report['confirmed_bookings']}\n\n")

                    text_widget.insert(tk.END, "Помесячная статистика:\n")
                    text_widget.insert(tk.END, "-" * 50 + "\n")
                    text_widget.insert(tk.END, f"{'Месяц':<15} {'Выручка':<20} {'Бронирования':<15}\n")
                    text_widget.insert(tk.END, "-" * 50 + "\n")

                    month_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

                    for month_data in report['monthly_data']:
                        month_idx = month_data['month'] - 1
                        month_name = month_names[month_idx] if month_idx < len(
                            month_names) else f"Месяц {month_data['month']}"
                        text_widget.insert(tk.END,
                                           f"{month_name:<15} {month_data['revenue']:<20,.2f} {month_data['bookings']:<15}\n")

                else:
                    report = self.reports.generate_financial_report(year, month)
                    month_name = date(2000, month, 1).strftime('%B')

                    # Отображение месячного отчета
                    result_dialog = tk.Toplevel(dialog)
                    result_dialog.title(f"Финансовый отчет за {month_name} {year}")
                    result_dialog.geometry("600x350")
                    result_dialog.configure(background='#F8FAFC')

                    # Заголовок
                    result_header = tk.Frame(result_dialog, bg='#264653', height=70)
                    result_header.pack(fill=tk.X)
                    result_header.pack_propagate(False)

                    tk.Label(result_header, text=f"Финансовый отчет за {month_name} {year}",
                             font=('Arial', 14, 'bold'), bg='#264653', fg='white').pack(pady=20)

                    # Текстовое поле с результатами
                    text_frame = tk.Frame(result_dialog, bg='#F8FAFC', padx=20, pady=20)
                    text_frame.pack(fill=tk.BOTH, expand=True)

                    text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Arial', 11),
                                          bg='white', fg='#333', relief='solid', borderwidth=1,
                                          height=10)
                    text_widget.pack(fill=tk.BOTH, expand=True)

                    text_widget.insert(tk.END, f"Финансовый отчет за {month_name} {year}\n")
                    text_widget.insert(tk.END, "=" * 40 + "\n\n")
                    text_widget.insert(tk.END, f"Выручка: {report['total_revenue']:,.2f} ₽\n")
                    text_widget.insert(tk.END, f"Всего бронирований: {report.get('total_bookings', 0)}\n")
                    text_widget.insert(tk.END, f"Подтвержденных: {report.get('confirmed_bookings', 0)}\n")
                    text_widget.insert(tk.END, f"Отмененных: {report.get('cancelled_bookings', 0)}\n")

                    if report.get('total_bookings', 0) > 0:
                        cancellation_rate = (report.get('cancelled_bookings', 0) / report.get('total_bookings',
                                                                                              0)) * 100
                        text_widget.insert(tk.END, f"Процент отмен: {cancellation_rate:.2f}%\n")

                # Кнопка закрытия для обоих вариантов
                buttons_frame = tk.Frame(result_dialog, bg='#F8FAFC', pady=10)
                buttons_frame.pack(fill=tk.X, padx=30)

                button_style = {
                    'font': ('Arial', 10),
                    'relief': 'flat',
                    'cursor': 'hand2',
                    'padx': 20,
                    'pady': 8,
                    'borderwidth': 0
                }

                close_btn = tk.Button(buttons_frame, text="Закрыть", bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=result_dialog.destroy)
                close_btn.pack()
                close_btn.bind('<Enter>', lambda e: close_btn.config(bg='#B3372C'))
                close_btn.bind('<Leave>', lambda e: close_btn.config(bg='#C73E1D'))

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при генерации отчета: {str(e)}")

        # Кнопки
        buttons_frame = tk.Frame(dialog, bg='#F8FAFC', pady=20)
        buttons_frame.pack(fill=tk.X, padx=30)

        button_style = {
            'font': ('Arial', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 20,
            'pady': 8,
            'borderwidth': 0
        }

        generate_btn = tk.Button(buttons_frame, text="Сгенерировать", bg='#2A9D8F', fg='white', activebackground='#2A9D8F', activeforeground='white', **button_style, command=generate)
        generate_btn.pack(side=tk.LEFT, padx=(0, 10))
        generate_btn.bind('<Enter>', lambda e: generate_btn.config(bg='#1F7A6D'))
        generate_btn.bind('<Leave>', lambda e: generate_btn.config(bg='#2A9D8F'))

        close_btn = tk.Button(buttons_frame, text="Закрыть", bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=dialog.destroy)
        close_btn.pack(side=tk.LEFT)
        close_btn.bind('<Enter>', lambda e: close_btn.config(bg='#B3372C'))
        close_btn.bind('<Leave>', lambda e: close_btn.config(bg='#C73E1D'))

    def export_data_dialog(self):
        """Диалог экспорта данных"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Экспорт данных")
        dialog.geometry("400x500")
        dialog.configure(background='#F8FAFC')
        dialog.transient(self.root)

        # Заголовок
        header_frame = tk.Frame(dialog, bg='#264653', height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="Экспорт данных", font=('Arial', 14, 'bold'),
                 bg='#264653', fg='white').pack(pady=20)

        # Основная форма
        form_frame = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=30)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Варианты экспорта
        export_options = [
            ("Клиенты", self.export_clients, '#2A9D8F'),
            ("Туры", self.export_tours, '#264653'),
            ("Бронирования", self.export_bookings, '#18A558'),
            ("Сотрудники", self.export_employees, '#F18F01')
        ]

        button_style = {
            'font': ('Arial', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'borderwidth': 0,
            'padx': 20,
            'pady': 10,
            'width': 25
        }

        for i, (text, command, color) in enumerate(export_options):
            btn = tk.Button(form_frame, text=text, bg=color, fg='white', activebackground=color, activeforeground='white', **button_style, command=command)
            btn.pack(pady=10)

            btn.bind('<Enter>', lambda e, b=btn, c=color: b.config(bg='#343A40'))
            btn.bind('<Leave>', lambda e, b=btn, c=color: b.config(bg=c))

        # Кнопка закрытия
        buttons_frame = tk.Frame(dialog, bg='#F8FAFC', pady=20)
        buttons_frame.pack(fill=tk.X, padx=30)

        close_btn = tk.Button(buttons_frame, text="Закрыть", bg='#C73E1D', fg='white', activebackground='#C73E1D', activeforeground='white', **button_style, command=dialog.destroy)
        close_btn.pack()
        close_btn.bind('<Enter>', lambda e: close_btn.config(bg='#B3372C'))
        close_btn.bind('<Leave>', lambda e: close_btn.config(bg='#C73E1D'))

    def export_clients(self):
        """Экспорт клиентов в CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile="clients_export.csv"
            )
            if filename:
                clients = self.db.get_clients()
                headers = ['ID', 'ФИО', 'Паспорт', 'Телефон', 'Email', 'Дата регистрации']
                self.reports.export_to_csv(clients, filename, headers)
                messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {str(e)}")

    def export_tours(self):
        """Экспорт туров в CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile="tours_export.csv"
            )
            if filename:
                tours = self.db.get_tours()
                headers = ['ID', 'Название', 'Страна', 'Город', 'Дата начала', 'Дата окончания',
                           'Цена', 'Макс. мест', 'Свободно', 'Описание']
                self.reports.export_to_csv(tours, filename, headers)
                messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {str(e)}")

    def export_bookings(self):
        """Экспорт бронирований в CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile="bookings_export.csv"
            )
            if filename:
                bookings = self.db.get_bookings()
                headers = ['ID', 'ID клиента', 'ID тура', 'Дата брони', 'Кол-во человек',
                           'Общая стоимость', 'Статус', 'Примечания']
                self.reports.export_to_csv(bookings, filename, headers)
                messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {str(e)}")

    def export_employees(self):
        """Экспорт сотрудников в CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile="employees_export.csv"
            )
            if filename:
                employees = self.db.get_employees()
                headers = ['ID', 'ФИО', 'Должность', 'Телефон', 'Email', 'Дата приема', 'Зарплата']
                self.reports.export_to_csv(employees, filename, headers)
                messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {str(e)}")

    def show_statistics(self):
        """Отображение статистики"""
        self.clear_content()
        self.header_label.config(text="Статистика системы", font=('Segoe UI', 18, 'bold'), fg='#264653')

        # Получаем статистику
        stats = self.db.get_statistics()

        # Контейнер для всего контента
        content_container = tk.Frame(self.content_frame, bg='#E3F2FD')
        content_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Заголовок раздела
        stats_header = tk.Label(content_container,
                                text="Детальная статистика",
                                font=('Segoe UI', 14, 'bold'),
                                bg='#E3F2FD',
                                fg='#264653',
                                anchor='w')
        stats_header.pack(fill=tk.X, pady=(0, 15))

        # Карточка для таблицы статистики
        stats_card = tk.Frame(content_container,
                              bg='#FFFFFF',
                              relief='solid',
                              borderwidth=1,
                              highlightbackground='#DEE2E6',
                              highlightthickness=1)
        stats_card.pack(fill=tk.BOTH, expand=True)

        # Основная статистика
        stats_frame = tk.Frame(stats_card, bg='#FFFFFF')
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)

        detailed_stats = [
            ("Общее количество клиентов:", stats.get('total_clients', 0), '#2A9D8F'),
            ("Общее количество туров:", stats.get('total_tours', 0), '#264653'),
            ("Всего бронирований:", stats.get('total_bookings', 0), '#18A558'),
            ("Активных бронирований:", stats.get('active_bookings', 0), '#2A9D8F'),
            ("Подтвержденных бронирований:", stats.get('confirmed_bookings', 0), '#18A558'),
            ("Отмененных бронирований:", stats.get('cancelled_bookings', 0), '#C73E1D'),
            ("Общая выручка:", f"{stats.get('total_revenue', 0):,.2f} ₽", '#F18F01'),
            ("Средний чек:", f"{stats.get('avg_check', 0):,.2f} ₽" if stats.get('avg_check') else "Н/Д", '#E9C46A'),
        ]

        for i, (label, value, color) in enumerate(detailed_stats):
            # Метка
            label_widget = tk.Label(stats_frame,
                                    text=label,
                                    font=('Segoe UI', 11),
                                    bg='#FFFFFF',
                                    fg='#495057',
                                    anchor='w')
            label_widget.grid(row=i, column=0, sticky='w', pady=10, padx=(0, 20))

            # Значение с цветным акцентом
            value_widget = tk.Label(stats_frame,
                                    text=str(value),
                                    font=('Segoe UI', 11, 'bold'),
                                    bg='#FFFFFF',
                                    fg=color,
                                    anchor='e')
            value_widget.grid(row=i, column=1, sticky='e', pady=10)

        # Настраиваем колонки
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=0)

            # Разделитель
        separator2 = tk.Frame(content_container, height=2, bg='#DEE2E6')
        separator2.pack(fill=tk.X, pady=30)

        # Кнопка обновления статистики
        refresh_frame = tk.Frame(content_container, bg='#E3F2FD', pady=20)
        refresh_frame.pack(fill=tk.X)

        refresh_btn = tk.Button(refresh_frame, text="🔄 Обновить статистику", font=('Segoe UI', 10, 'bold'), bg='#2A9D8F', fg='white',
                                cursor='hand2', padx=20, pady=10, activebackground='#2A9D8F', activeforeground='white', borderwidth=0, command=lambda: self.show_statistics())
        refresh_btn.pack()

        # Эффект при наведении
        refresh_btn.bind('<Enter>', lambda e: refresh_btn.config(bg='#1F7A6D'))
        refresh_btn.bind('<Leave>', lambda e: refresh_btn.config(bg='#2A9D8F'))

    def show_database_info(self):
        """Показать информацию о базе данных"""
        try:
            info = self.db.get_table_info()

            dialog = tk.Toplevel(self.root)
            dialog.title("Информация о базе данных")
            dialog.geometry("600x400")

            text_widget = tk.Text(dialog, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            text_widget.insert(tk.END, f"База данных: {self.db.db_name}\n")
            text_widget.insert(tk.END, "=" * 50 + "\n\n")

            for table_name, table_info in info.items():
                text_widget.insert(tk.END, f"Таблица: {table_name}\n")
                text_widget.insert(tk.END, f"  Количество записей: {table_info['count']}\n")
                text_widget.insert(tk.END, f"  Колонки: {', '.join(table_info['columns'])}\n")
                text_widget.insert(tk.END, "-" * 40 + "\n")

            # Кнопка закрытия
            ttk.Button(dialog, text="Закрыть",
                       command=dialog.destroy).pack(pady=10)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось получить информацию о БД: {str(e)}")

    def clear_content(self):
        """Очистка области контента"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def setup_context_menu(self, tree, edit_command, delete_command):
        """Настройка контекстного меню для дерева"""
        context_menu = tk.Menu(tree, tearoff=0, bg='#F8FAFC', fg='#264653', activebackground='#E3F2FD', activeforeground='#264653', bd=1, relief='solid')

        context_menu.add_command(label="✏️ Редактировать", font=('Arial', 10), command=edit_command)
        context_menu.add_command(label="🗑️ Удалить", font=('Arial', 10), command=delete_command)

        def show_context_menu(event):
            """Показать контекстное меню"""
            item = tree.identify_row(event.y)
            if item:
                tree.selection_set(item)
                context_menu.tk_popup(event.x_root, event.y_root)

        tree.bind("<Button-3>", show_context_menu)

    def load_initial_data(self):
        """Загрузка начальных данных"""
        pass

def main():
    """Основная функция запуска приложения"""
    root = tk.Tk()
    app = GlobalTravelApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()