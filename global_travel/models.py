# models.py
from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class Client:
    """Класс для хранения информации о клиентах"""
    id: Optional[int] = None
    full_name: str = ""
    passport: str = ""
    phone: str = ""
    email: str = ""
    registration_date: date = date.today()

@dataclass
class Tour:
    """Класс для хранения информации о турах"""
    id: Optional[int] = None
    name: str = ""
    country: str = ""
    city: str = ""
    start_date: date = date.today()
    end_date: date = date.today()
    price: float = 0.0
    max_persons: int = 0
    available_slots: int = 0
    description: str = ""

@dataclass
class Booking:
    """Класс для хранения информации о бронированиях"""
    id: Optional[int] = None
    client_id: int = 0
    tour_id: int = 0
    booking_date: date = date.today()
    persons_count: int = 1
    total_price: float = 0.0
    status: str = "confirmed"  # confirmed, cancelled, completed
    notes: str = ""

@dataclass
class Employee:
    """Класс для хранения информации о сотрудниках"""
    id: Optional[int] = None
    full_name: str = ""
    position: str = ""
    phone: str = ""
    email: str = ""
    hire_date: date = date.today()
    salary: float = 0.0