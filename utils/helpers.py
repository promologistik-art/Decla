import pandas as pd
import re
from datetime import datetime

def safe_float(value):
    """Безопасное преобразование в float"""
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except:
        return 0.0

def parse_date(date_str):
    """Парсинг даты из разных форматов"""
    if isinstance(date_str, datetime):
        return date_str
    if isinstance(date_str, str):
        # Поддерживаемые форматы
        formats = ["%d.%m.%Y", "%Y-%m-%d", "%d.%m.%Y %H:%M:%S", "%Y%m%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
    return None

def clean_sum(sum_str):
    """Очистка суммы от пробелов и замена запятой"""
    if isinstance(sum_str, (int, float)):
        return float(sum_str)
    if isinstance(sum_str, str):
        cleaned = sum_str.replace(" ", "").replace(",", ".")
        try:
            return float(cleaned)
        except:
            return 0.0
    return 0.0

def is_income(purpose):
    """Определяет, является ли операция доходом"""
    purpose_lower = str(purpose).lower()
    
    # Исключаем явно
    for word in EXCLUDE_KEYWORDS:
        if word in purpose_lower:
            return False
    
    # Проверяем на доход
    for word in INCOME_KEYWORDS:
        if word in purpose_lower:
            return True
    
    return False

def format_currency(amount):
    """Форматирование суммы"""
    return f"{amount:,.2f}".replace(",", " ")

def get_quarter(date_obj):
    """Возвращает номер квартала"""
    month = date_obj.month
    if month <= 3:
        return 1
    elif month <= 6:
        return 2
    elif month <= 9:
        return 3
    else:
        return 4