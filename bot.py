import os
import asyncio
import tempfile
from datetime import datetime

from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import BOT_TOKEN, DATA_DIR, OUTPUT_DIR
from parsers.bank_parser import BankStatementParser
from parsers.ens_parser import ENSParser
from generators.kudir_generator import KudirGenerator
from generators.declaration_generator import DeclarationGenerator

# Хранилище для сессий пользователей
user_sessions = {}

class UserSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.bank_statements = []
        self.ens_data = None
        self.total_income = 0.0
        self.tax_payable = 0.0
        
    def add_bank_statement(self, file_path, operations):
        self.bank_statements.extend(operations)
        
    def set_ens_data(self, ens_data):
        self.ens_data = ens_data
        
    def reset(self):
        self.bank_statements = []
        self.ens_data = None
        self.total_income = 0.0
        self.tax_payable = 0.0

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id] = UserSession(user_id)
    
    await update.message.reply_text(
        "🤖 *Бот для подготовки отчетности ИП на УСН*\n\n"
        "Я помогу вам:\n"
        "📊 Сформировать КУДиР на основе выписок из банков\n"
        "📝 Заполнить декларацию по УСН\n"
        "💰 Рассчитать налог к уплате\n\n"
        "*Как работать с ботом:*\n"
        "1️⃣ Загрузите выписки с расчетных счетов (Excel)\n"
        "2️⃣ Загрузите выписку с ЕНС (CSV)\n"
        "3️⃣ Получите готовые КУДиР и декларацию\n\n"
        "📌 *Важные сроки за 2025 год:*\n"
        "• Сдать декларацию — до *27 апреля 2026*\n"
        "• Уплатить налог — до *28 апреля 2026*\n\n"
        "⚠️ *Главное*: если не сдать декларацию в срок, налоговая может заблокировать счет. "
        "Просрочка уплаты налога счет не блокирует — только пени.\n\n"
        "Отправьте мне первый файл выписки!",
        parse_mode="Markdown"
    )

# Обработка документов
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id)
    
    session = user_sessions[user_id]
    document = update.message.document
    
    # Скачиваем файл
    file = await context.bot.get_file(document.file_id)
    
    # Определяем тип файла
    filename = document.file_name.lower()
    
    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        # Выписка с расчетного счета
        await update.message.reply_text("📥 Получил выписку с расчетного счета. Обрабатываю...")
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            tmp_path = tmp.name
        
        try:
            parser = BankStatementParser(tmp_path)
            income_ops = parser.parse()
            
            if income_ops:
                session.add_bank_statement(tmp_path, income_ops)
                total = sum(op['amount'] for op in income_ops)
                await update.message.reply_text(
                    f"✅ Обработано!\n"
                    f"📊 Найдено доходов: {len(income_ops)} операций\n"
                    f"💰 Сумма доходов: {total:,.2f} ₽\n\n"
                    f"Продолжайте загружать выписки. Когда все загружены, пришлите файл выписки с ЕНС.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    "⚠️ В выписке не найдено операций, которые можно идентифицировать как доходы.\n\n"
                    "Проверьте, что в файле есть:\n"
                    "• Колонки с датой, суммой и назначением платежа\n"
                    "• Поступления от покупателей с пометкой 'оплата'"
                )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при обработке файла: {str(e)}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    elif filename.endswith('.csv'):
        # Выписка с ЕНС
        await update.message.reply_text("📥 Получил выписку с ЕНС. Обрабатываю...")
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            tmp_path = tmp.name
        
        try:
            parser = ENSParser(tmp_path)
            ens_data = parser.parse()
            session.set_ens_data(ens_data)
            
            # Формируем итоговую информацию
            insurance_paid = ens_data.get('insurance_paid', 0)
            paid_in_2025 = sum(1 for d in ens_data.get('insurance_paid_dates', []) if d and d.year == 2025)
            
            await update.message.reply_text(
                f"✅ Выписка ЕНС обработана!\n\n"
                f"📌 Данные по страховым взносам:\n"
                f"• Начислено за 2025: {ens_data.get('insurance_accrued', 0):,.2f} ₽\n"
                f"• Уплачено: {insurance_paid:,.2f} ₽\n"
                f"• Уплачено в 2025 году: {'Да' if paid_in_2025 > 0 else 'Нет'}\n\n"
                f"📌 Пени: {ens_data.get('penalties', 0):,.2f} ₽\n\n"
                f"Теперь я готов сформировать КУДиР и декларацию!\n"
                f"Введите /report, чтобы получить отчетность."
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при обработке файла ЕНС: {str(e)}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    else:
        await update.message.reply_text(
            "❌ Неподдерживаемый формат файла.\n"
            "Пожалуйста, загрузите:\n"
            "• Выписки с расчетных счетов — Excel (.xlsx, .xls)\n"
            "• Выписку с ЕНС — CSV (.csv)"
        )

# Команда /report
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await update.message.reply_text("Сначала загрузите выписки с помощью команды /start")
        return
    
    session = user_sessions[user_id]
    
    if not session.bank_statements:
        await update.message.reply_text("⚠️ Сначала загрузите выписки с расчетных счетов")
        return
    
    if not session.ens_data:
        await update.message.reply_text("⚠️ Сначала загрузите выписку с ЕНС")
        return
    
    await update.message.reply_text("🔄 Формирую отчетность... Это может занять несколько секунд.")
    
    try:
        # Сортируем все операции по дате
        all_ops = []
        for stmt in session.bank_statements:
            all_ops.extend(stmt)
        all_ops.sort(key=lambda x: x['date'])
        
        # Генерируем КУДиР
        kudir_gen = KudirGenerator(all_ops)
        kudir_data = kudir_gen.generate()
        quarterly_totals = kudir_gen.get_quarterly_totals()
        
        # Сохраняем КУДиР
        kudir_excel = os.path.join(OUTPUT_DIR, f"kudir_{user_id}.xlsx")
        total_income = kudir_gen.export_to_excel(kudir_excel)
        
        # Генерируем декларацию
        decl_gen = DeclarationGenerator(all_ops, session.ens_data)
        tax_payable = decl_gen.generate_excel(os.path.join(OUTPUT_DIR, f"declaration_{user_id}.xlsx"))
        decl_gen.generate_xml(os.path.join(OUTPUT_DIR, f"declaration_{user_id}.xml"))
        
        # Отправляем результат
        await update.message.reply_text(
            f"✅ *Отчетность готова!*\n\n"
            f"📊 *Итого доходов за 2025 год:* {total_income:,.2f} ₽\n"
            f"💰 *Налог к уплате:* {tax_payable:,.2f} ₽\n\n"
            f"📌 *Сроки:*\n"
            f"• Декларацию сдать до *27 апреля 2026*\n"
            f"• Налог уплатить до *28 апреля 2026*\n\n"
            f"⚠️ *Важно:* если не сдать декларацию в срок — налоговая может заблокировать счет. "
            f"Просрочка уплаты налога счет не блокирует, только пени.\n\n"
            f"📎 Отправляю готовые файлы...",
            parse_mode="Markdown"
        )
        
        # Отправляем КУДиР
        with open(kudir_excel, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f"КУДиР_2025_{user_id}.xlsx",
                caption="📘 Книга учета доходов и расходов (КУДиР) за 2025 год"
            )
        
        # Отправляем декларацию Excel
        with open(os.path.join(OUTPUT_DIR, f"declaration_{user_id}.xlsx"), 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f"Декларация_УСН_2025_{user_id}.xlsx",
                caption="📝 Декларация по УСН (Excel) — для проверки и печати"
            )
        
        # Отправляем XML для ЛК ФНС
        with open(os.path.join(OUTPUT_DIR, f"declaration_{user_id}.xml"), 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f"declaration_usn_2025.xml",
                caption="📎 XML-файл декларации — для загрузки в Личный кабинет ФНС"
            )
        
        await update.message.reply_text(
            "🎉 *Готово!*\n\n"
            "Что делать дальше:\n"
            "1. Проверьте декларацию в Excel\n"
            "2. Загрузите XML-файл в Личный кабинет ИП на сайте ФНС\n"
            "3. Подпишите электронной подписью и отправьте\n"
            "4. Уплатите налог до 28 апреля 2026\n\n"
            "Если нужна помощь — обращайтесь!",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при формировании отчетности: {str(e)}")
        import traceback
        traceback.print_exc()

# Команда /reset
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions[user_id].reset()
        await update.message.reply_text("🔄 Данные сброшены. Можете начать заново с команды /start")
    else:
        await update.message.reply_text("Нет активной сессии. Используйте /start")

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Помощь по боту*\n\n"
        "*Команды:*\n"
        "/start — начать работу\n"
        "/report — сформировать отчетность\n"
        "/reset — сбросить все данные\n"
        "/help — эта справка\n\n"
        "*Как загружать файлы:*\n"
        "1. Сначала загрузите выписки с расчетных счетов (Excel)\n"
        "2. Затем загрузите выписку с ЕНС (CSV)\n"
        "3. Введите /report\n\n"
        "*Какие файлы нужны:*\n"
        "• Выписки из банков (ВБ Банк, ОЗОН Банк и др.) в формате Excel\n"
        "• Выписка с Единого налогового счета (ЕНС) в формате CSV\n\n"
        "*Сроки за 2025 год:*\n"
        "• Декларация: до 27 апреля 2026\n"
        "• Уплата налога: до 28 апреля 2026\n\n"
        "⚠️ *Блокировка счета* — только за несдачу декларации. "
        "Просрочка уплаты налога счет не блокирует.",
        parse_mode="Markdown"
    )

def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("help", help_command))
    
    # Обработка документов
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()