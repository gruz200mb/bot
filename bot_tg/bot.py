import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

# Токен вашего бота
import os
TOKEN = os.getenv("TOKEN")


bot = Bot(token=TOKEN)
dp = Dispatcher()

# Путь к базе данных
DB_PATH = "domains.db"

# Функция для инициализации базы данных
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price INTEGER NOT NULL,
                indexed BOOLEAN NOT NULL DEFAULT 0,
                backlinks INTEGER DEFAULT 0,
                traffic INTEGER DEFAULT 0,
                description TEXT
            )
        ''')
        await db.commit()
        print("✅ Таблица 'domains' создана или уже существует.")

# Функция для получения всех доменов
async def get_all_domains():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT name, price, indexed, backlinks, traffic, description FROM domains')
        rows = await cursor.fetchall()
        return [
            {
                "name": row[0],
                "price": row[1],
                "indexed": bool(row[2]),
                "backlinks": row[3],
                "traffic": row[4],
                "description": row[5]
            }
            for row in rows
        ]

# Функция для поиска доменов по ключевому слову
async def search_domains(query: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            SELECT name, price, indexed, backlinks, traffic, description
            FROM domains
            WHERE name LIKE ?
        ''', (f'%{query}%',))
        rows = await cursor.fetchall()
        return [
            {
                "name": row[0],
                "price": row[1],
                "indexed": bool(row[2]),
                "backlinks": row[3],
                "traffic": row[4],
                "description": row[5]
            }
            for row in rows
        ]

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🤖 Загружаю каталог доменов...")

    domains = await get_all_domains()

    if not domains:
        await message.answer("❌ Каталог пуст.")
        return

    for domain in domains[:10]:
        status = "✅" if domain["indexed"] else "❌"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Купить", callback_data=f"buy_{domain['name']}")]
        ])
        await message.answer(
            f"🔹 <b>{domain['name']}</b>\n"
            f"💰 Цена: {domain['price']} руб.\n"
            f"🔍 Индексация: {status}\n"
            f"🔗 Ссылки: {domain['backlinks']}\n"
            f"📊 Трафик: ~{domain['traffic']} посещений/мес\n"
            f"📝 Описание: {domain['description'] or 'Нет описания'}",
            reply_markup=kb,
            parse_mode="HTML"
        )

    if len(domains) > 10:
        await message.answer(f"Всего в каталоге: {len(domains)} доменов. Используйте /search для поиска.")

# Команда /help — меню с навигацией
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
🤖 <b>Меню навигации бота</b>

🔹 <code>/start</code> — Показать каталог доменов (первые 10)
🔹 <code>/search слово</code> — Найти домены по ключевому слову
🔹 <code>/buy</code> — Инструкция по покупке домена
🔹 <code>/help</code> — Это меню (сейчас вы здесь)

🔍 <b>Как пользоваться:</b>
• Напишите любое слово (например, "крым") — бот найдёт похожие домены
• Нажмите "Купить" под доменом — получите инструкции

💳 <b>Оплата:</b>
После выбора домена свяжитесь с @admin@wwwrent.ru
"""
    await message.answer(help_text, parse_mode="HTML")

# Команда /search
@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    query = message.text.split(maxsplit=1)
    if len(query) < 2:
        await message.answer("🔍 Используйте: /search ключевое_слово")
        return

    query = query[1]
    results = await search_domains(query)

    if not results:
        await message.answer("❌ Ничего не найдено.")
        return

    await message.answer(f"🔍 Найдено {len(results)} доменов по запросу '{query}':")

    for domain in results:
        status = "✅" if domain["indexed"] else "❌"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Купить", callback_data=f"buy_{domain['name']}")]
        ])
        await message.answer(
            f"🔹 <b>{domain['name']}</b>\n"
            f"💰 Цена: {domain['price']} руб.\n"
            f"🔍 Индексация: {status}",
            reply_markup=kb,
            parse_mode="HTML"
        )

# Команда /buy
@dp.message(Command("buy"))
async def cmd_buy(message: types.Message):
    await message.answer(
        "💳 Как купить домен:\n\n"
        "1. Выберите домен из каталога\n"
        "2. Оплатите на наш счёт (уточните у менеджера)\n"
        "3. После оплаты — мы передадим права на домен\n\n"
        "Для связи: @admin@wwwrent.ru"
    )

# Обработчик кнопки "Купить"
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def process_buy(callback_query: types.CallbackQuery):
    domain_name = callback_query.data.split("_", 1)[1]
    await callback_query.answer(f"Вы выбрали: {domain_name}. Свяжитесь с @admin@wwwrent.ru")

# Обработчик текста (для поиска без команды)
@dp.message()
async def handle_text(message: types.Message):
    query = message.text.lower()
    if len(query) < 3:
        return

    results = await search_domains(query)

    if results:
        await message.answer(f"🔍 Найдено {len(results)} доменов по запросу '{query}':")
        for domain in results[:5]:
            status = "✅" if domain["indexed"] else "❌"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Купить", callback_data=f"buy_{domain['name']}")]
            ])
            await message.answer(
                f"🔹 <b>{domain['name']}</b>\n"
                f"💰 Цена: {domain['price']} руб.\n"
                f"🔍 Индексация: {status}",
                reply_markup=kb,
                parse_mode="HTML"
            )
    else:
        await message.answer("❌ Ничего не найдено. Попробуйте другой запрос.")

async def main():
    # Инициализируем базу данных
    await init_db()

    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())