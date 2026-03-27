import pandas as pd
from datetime import datetime
from utils.helpers import safe_float

class ENSParser:
    """Парсер выписки с Единого налогового счета"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.insurance_accrued = 0.0
        self.insurance_paid = 0.0
        self.insurance_paid_dates = []
        self.penalties = 0.0
        self.usn_payments = []
        
    def parse(self):
        """Парсинг CSV выписки ЕНС"""
        try:
            # Читаем CSV с разделителем ;
            df = pd.read_csv(self.file_path, sep=';', encoding='utf-8')
            self._parse_dataframe(df)
            return {
                'insurance_accrued': self.insurance_accrued,
                'insurance_paid': self.insurance_paid,
                'insurance_paid_dates': self.insurance_paid_dates,
                'penalties': self.penalties,
                'usn_payments': self.usn_payments
            }
        except Exception as e:
            raise Exception(f"Ошибка парсинга файла ЕНС: {e}")
    
    def _parse_dataframe(self, df):
        """Парсинг DataFrame"""
        for idx, row in df.iterrows():
            operation = str(row.get('Наименование операции', ''))
            kbk = str(row.get('КБК', ''))
            amount = safe_float(row.get('Сумма операции', 0))
            date = row.get('Дата записи', '')
            
            # Парсим дату
            try:
                date_obj = datetime.strptime(str(date), '%Y-%m-%d')
            except:
                date_obj = None
            
            # Начисление страховых взносов
            if 'Начислено' in operation and 'Страховые взносы' in str(row.get('Наименование обязательства', '')):
                self.insurance_accrued += abs(amount)
            
            # Пени
            elif 'пеня' in operation.lower():
                self.penalties += abs(amount)
            
            # Уплата
            elif 'Уплата' in operation:
                if kbk == '18201061201010000510':  # ЕНП
                    # Это может быть уплата взносов или налога
                    # Определяем по дате и сумме
                    self.usn_payments.append({
                        'date': date_obj,
                        'amount': amount
                    })
                    
                    # Проверяем, не уплата ли это взносов
                    # Если дата > 31.12.2025, то это взносы за 2025, уплаченные в 2026
                    if date_obj and date_obj.year == 2026:
                        self.insurance_paid += amount
                        self.insurance_paid_dates.append(date_obj)
    
    def can_deduct_insurance_for_year(self, year):
        """Можно ли вычесть взносы за указанный год"""
        # Для 2025 года: вычет только если взносы уплачены до 31.12.2025
        if year == 2025:
            for date in self.insurance_paid_dates:
                if date and date.year == 2025:
                    return True
            return False
        return True
    
    def get_insurance_deductible(self, year):
        """Сумма взносов, подлежащая вычету за указанный год"""
        if year == 2025:
            if self.can_deduct_insurance_for_year(2025):
                return self.insurance_paid
            return 0.0
        return self.insurance_paid