from database import Database
from datetime import date, datetime, timedelta
import csv


class ReportGenerator:
    """Класс для генерации отчетов"""

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
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            report = {
                'total_revenue': 0,
                'confirmed_bookings': 0,
                'cancelled_bookings': 0,
                'monthly_data': []
            }

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
                if result[0]:
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
                    monthly_revenue = result[0] if result[0] else 0
                    monthly_bookings = result[1] if result[1] else 0

                    report['monthly_data'].append({
                        'month': m,
                        'revenue': monthly_revenue,
                        'bookings': monthly_bookings
                    })

                    report['total_revenue'] += monthly_revenue
                    report['confirmed_bookings'] += monthly_bookings

            return report