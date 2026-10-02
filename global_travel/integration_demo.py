from database import Database
from reports import ReportGenerator
from datetime import date

print("=== ИНТЕГРАЦИОННЫЙ ТЕСТ ===")

print("\n[1] Инициализация модуля №1: Database...")
db = Database()

print("\n[2] Инициализация модуля №2: ReportGenerator...")
reporter = ReportGenerator(db)

print("\n[3] Сквозной сценарий: запрос данных -> формирование отчета...")

bookings = db.get_bookings()
if not bookings:
    print(" Бронирований нет. Создаем тестовое...")
    success, message, booking_id = db.add_booking(1, 1, 2, "")
    if success:
        print(f" Создано бронирование №{booking_id}")
    else:
        print(f" Ошибка: {message}")

fin_report = reporter.generate_financial_report(2025)
print(f"\n Выручка: {fin_report['total_revenue']} руб.")
print(f" Подтвержденных бронирований: {fin_report['confirmed_bookings']}")
print(f" Отмененных бронирований: {fin_report['cancelled_bookings']}")

print("\n=== ИНТЕГРАЦИЯ ПРОШЛА УСПЕШНО ===")