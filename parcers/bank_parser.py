import pandas as pd
from datetime import datetime
from utils.helpers import safe_float, parse_date, clean_sum, is_income

class BankStatementParser:
    """Парсер выписок из банков"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.income_operations = []
        self.all_operations = []
        
    def parse(self):
        """Основной метод парсинга"""
        try:
            # Пробуем прочитать Excel
            df = pd.read_excel(self.file_path, header=None)
            df = self._clean_dataframe(df)
            self._extract_operations(df)
            return self.income_operations
        except Exception as e:
            raise Exception(f"Ошибка парсинга файла: {e}")
    
    def _clean_dataframe(self, df):
        """Очистка DataFrame от служебных строк"""
        # Ищем строку с заголовками
        header_row = None
        for idx, row in df.iterrows():
            row_str = ' '.join(str(v) for v in row.values if pd.notna(v)).lower()
            if 'дата' in row_str and ('сумма' in row_str or 'кредит' in row_str):
                header_row = idx
                break
        
        if header_row is None:
            # Если не нашли заголовки, пробуем первый вариант
            return df
        
        # Устанавливаем заголовки
        headers = df.iloc[header_row].values
        df.columns = headers
        df = df.iloc[header_row + 1:].reset_index(drop=True)
        
        return df
    
    def _extract_operations(self, df):
        """Извлечение операций из DataFrame"""
        
        # Определяем названия колонок
        col_date = None
        col_credit = None
        col_debit = None
        col_purpose = None
        
        for col in df.columns:
            col_str = str(col).lower()
            if 'дата' in col_str:
                col_date = col
            elif 'кредит' in col_str or 'поступление' in col_str or 'приход' in col_str:
                col_credit = col
            elif 'дебет' in col_str or 'списание' in col_str or 'расход' in col_str:
                col_debit = col
            elif 'назначение' in col_str or 'содержание' in col_str or 'назначение платежа' in col_str:
                col_purpose = col
        
        if col_date is None or (col_credit is None and col_debit is None):
            # Пробуем альтернативный формат (с колонкой Сумма и направлением)
            if 'сумма' in df.columns:
                # Проверяем знак суммы
                for idx, row in df.iterrows():
                    amount = safe_float(row.get('сумма', 0))
                    purpose = str(row.get('назначение', row.get('назначение платежа', '')))
                    date = parse_date(row.get('дата', ''))
                    
                    if date and amount > 0 and is_income(purpose):
                        self.income_operations.append({
                            'date': date,
                            'amount': amount,
                            'purpose': purpose,
                            'document': row.get('номер', f"п/п {idx+1}"),
                            'counterparty': row.get('контрагент', '')
                        })
            return
        
        # Стандартный парсинг
        for idx, row in df.iterrows():
            date = parse_date(row.get(col_date))
            if not date:
                continue
            
            # Определяем сумму (кредит = доход, дебет = расход)
            amount = safe_float(row.get(col_credit, 0))
            is_credit = True
            
            if amount == 0 and col_debit:
                amount = safe_float(row.get(col_debit, 0))
                is_credit = False
            
            if amount == 0:
                continue
            
            purpose = str(row.get(col_purpose, ''))
            
            # Если это доход (кредит) и подходит по ключевым словам
            if is_credit and amount > 0 and is_income(purpose):
                self.income_operations.append({
                    'date': date,
                    'amount': amount,
                    'purpose': purpose,
                    'document': f"п/п {idx+1}",
                    'counterparty': str(row.get('контрагент', ''))
                })
            
            self.all_operations.append({
                'date': date,
                'amount': amount,
                'is_income': is_credit and amount > 0 and is_income(purpose),
                'purpose': purpose
            })