import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Папки
DATA_DIR = "data"
OUTPUT_DIR = "output"

# Ключевые слова для определения дохода
INCOME_KEYWORDS = [
    "оплата за товар",
    "оплата по договору",
    "оплата за услуги",
    "интернет решения",
    "озон",
    "по реестру",
    "оплата по контракту",
    "платеж по ден.треб",
    "за товар",
]

# Исключаемые операции
EXCLUDE_KEYWORDS = [
    "собственных средств",
    "перевод собственных",
    "вывод собственных",
    "комиссия",
    "уплата налога",
    "страховые взносы",
]

# КБК страховых взносов
INSURANCE_KBK = "18210202000010000160"