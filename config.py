import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Папки
DATA_DIR = "data"
OUTPUT_DIR = "output"

# Создаем папки если их нет
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Ключевые слова для определения дохода (можно расширять)
INCOME_KEYWORDS = [
    "оплата за товар",
    "оплата по договору",
    "оплата за услуги",
    "интернет решения",
    "озон",
    "по реестру",
    "оплата по контракту",
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