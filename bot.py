import asyncio
import logging
import sqlite3
import json
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= تنظیمات =================
BOT_TOKEN = "8971614267:AAG18ai0KIvaNszLH2aKZQMIZ9XTHodnAwE"
ADMINS = [8974374358]
CHANNEL_ID = "@jsfbkxf"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= دیتابیس SQLite =================
conn = sqlite3.connect("world_war.db", check_same_thread=False)
cur = conn.cursor()

# ایجاد جداول
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    country_id INTEGER,
    president_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    flag TEXT,
    population INTEGER,
    gdp INTEGER,
    oil_reserves INTEGER,
    satisfaction INTEGER,
    nuclear_level INTEGER,
    military_power INTEGER,
    world_rank INTEGER,
    is_active BOOLEAN DEFAULT 1,
    color TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS military (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER,
    soldiers INTEGER DEFAULT 100000,
    tanks INTEGER DEFAULT 100,
    missiles INTEGER DEFAULT 10,
    fighters INTEGER DEFAULT 20,
    drones INTEGER DEFAULT 50,
    warships INTEGER DEFAULT 5,
    nuclear_warheads INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS economy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER,
    gold INTEGER DEFAULT 1000000,
    oil INTEGER DEFAULT 10000,
    steel INTEGER DEFAULT 5000,
    food INTEGER DEFAULT 20000,
    electricity INTEGER DEFAULT 5000,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS diplomacy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country1_id INTEGER,
    country2_id INTEGER,
    status TEXT DEFAULT 'neutral',
    alliance TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS wars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attacker_id INTEGER,
    defender_id INTEGER,
    attacker_forces TEXT,
    defender_forces TEXT,
    winner_id INTEGER,
    loot TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    status TEXT DEFAULT 'active'
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# ================= کشورها =================
COUNTRIES = {
    "ایران": {"flag": "🇮🇷", "population": 89000000, "gdp": 450, "oil": 157, "nuclear_level": 4, "military_power": 91, "world_rank": 7, "color": "#FF6B6B"},
    "آمریکا": {"flag": "🇺🇸", "population": 335000000, "gdp": 25000, "oil": 47, "nuclear_level": 5, "military_power": 98, "world_rank": 1, "color": "#4ECDC4"},
    "روسیه": {"flag": "🇷🇺", "population": 144000000, "gdp": 1800, "oil": 107, "nuclear_level": 5, "military_power": 95, "world_rank": 2, "color": "#45B7D1"},
    "چین": {"flag": "🇨🇳", "population": 1410000000, "gdp": 18000, "oil": 26, "nuclear_level": 4, "military_power": 93, "world_rank": 3, "color": "#96CEB4"},
    "آلمان": {"flag": "🇩🇪", "population": 84000000, "gdp": 4300, "oil": 2, "nuclear_level": 2, "military_power": 85, "world_rank": 4, "color": "#FFEAA7"},
    "انگلیس": {"flag": "🇬🇧", "population": 68000000, "gdp": 3200, "oil": 15, "nuclear_level": 4, "military_power": 88, "world_rank": 5, "color": "#DDA0DD"},
    "فرانسه": {"flag": "🇫🇷", "population": 68000000, "gdp": 3000, "oil": 1, "nuclear_level": 4, "military_power": 87, "world_rank": 6, "color": "#98D8C8"},
    "ژاپن": {"flag": "🇯🇵", "population": 124000000, "gdp": 4900, "oil": 0, "nuclear_level": 1, "military_power": 82, "world_rank": 8, "color": "#F7DC6F"},
    "ترکیه": {"flag": "🇹🇷", "population": 86000000, "gdp": 900, "oil": 0, "nuclear_level": 1, "military_power": 80, "world_rank": 9, "color": "#BB8FCE"},
    "هند": {"flag": "🇮🇳", "population": 1420000000, "gdp": 3700, "oil": 6, "nuclear_level": 3, "military_power": 84, "world_rank": 10, "color": "#F1948A"}
}

# ================= توابع کمکی =================
def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cur.fetchone()

def create_user(user_id, username, first_name, last_name=""):
    cur.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, first_name, last_name))
    conn.commit()

def update_user_country(user_id, country_id, president_name):
    cur.execute("""
        UPDATE users SET country_id = ?, president_name = ? WHERE user_id = ?
    """, (country_id, president_name, user_id))
    conn.commit()

def get_country_by_id(country_id):
    cur.execute("SELECT * FROM countries WHERE id = ?", (country_id,))
    return cur.fetchone()

def get_country_by_name(name):
    cur.execute("SELECT * FROM countries WHERE name = ?", (name,))
    return cur.fetchone()

def get_all_countries():
    cur.execute("SELECT * FROM countries ORDER BY world_rank")
    return cur.fetchall()

def get_military(country_id):
    cur.execute("SELECT * FROM military WHERE country_id = ?", (country_id,))
    return cur.fetchone()

def get_economy(country_id):
    cur.execute("SELECT * FROM economy WHERE country_id = ?", (country_id,))
    return cur.fetchone()

def create_countries():
    for name, data in COUNTRIES.items():
        cur.execute("""
            INSERT OR IGNORE INTO countries (name, flag, population, gdp, oil_reserves, 
                                           nuclear_level, military_power, world_rank, color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, data["flag"], data["population"], data["gdp"], data["oil"], 
              data["nuclear_level"], data["military_power"], data["world_rank"], data["color"]))
        # گرفتن country_id
        country = get_country_by_name(name)
        if country:
            # چک کن military وجود داره
            if not get_military(country[0]):
                cur.execute("INSERT INTO military (country_id) VALUES (?)", (country[0],))
            if not get_economy(country[0]):
                cur.execute("INSERT INTO economy (country_id) VALUES (?)", (country[0],))
    conn.commit()

# ================= منوها =================
def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌍 کشور من", callback_data="my_country")],
            [InlineKeyboardButton(text="💰 اقتصاد", callback_data="economy")],
            [InlineKeyboardButton(text="⚔️ ارتش", callback_data="military")],
            [InlineKeyboardButton(text="🤝 دیپلماسی", callback_data="diplomacy")],
            [InlineKeyboardButton(text="🕵️ جاسوسی", callback_data="espionage")],
            [InlineKeyboardButton(text="☢️ هسته‌ای", callback_data="nuclear")],
            [InlineKeyboardButton(text="🗺️ نقشه جهان", callback_data="world_map")],
            [InlineKeyboardButton(text="📰 اخبار جهان", callback_data="news")],
            [InlineKeyboardButton(text="🏆 رتبه‌بندی", callback_data="leaderboard")],
            [InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="settings")]
        ]
    )

def country_select_menu():
    keyboard = []
    for name, data in COUNTRIES.items():
        country = get_country_by_name(name)
        if country:
            # چک کن کشور گرفته شده یا نه
            cur.execute("SELECT user_id FROM users WHERE country_id = ?", (country[0],))
            taken = cur.fetchone()
            status = "❌" if taken else "✅"
            keyboard.append([InlineKeyboardButton(
                text=f"{status} {data['flag']} {name}",
                callback_data=f"select_country_{name}"
            )])
    keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def military_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 وضعیت ارتش", callback_data="military_status")],
            [InlineKeyboardButton(text="🛒 خرید تجهیزات", callback_data="buy_equipment")],
            [InlineKeyboardButton(text="🎯 حمله", callback_data="attack_menu")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
        ]
    )

def diplomacy_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ اعلان جنگ", callback_data="declare_war")],
            [InlineKeyboardButton(text="🕊️ پیشنهاد صلح", callback_data="peace_offer")],
            [InlineKeyboardButton(text="🤝 تشکیل اتحادیه", callback_data="create_alliance")],
            [InlineKeyboardButton(text="📋 لیست اتحادیه‌ها", callback_data="alliance_list")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
        ]
    )

def buy_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👨‍✈️ سرباز (۱۰ دلار)", callback_data="buy_soldiers")],
            [InlineKeyboardButton(text="🛡 تانک (۵۰ دلار)", callback_data="buy_tanks")],
            [InlineKeyboardButton(text="🚀 موشک (۱۰۰ دلار)", callback_data="buy_missiles")],
            [InlineKeyboardButton(text="✈️ جنگنده (۲۰۰ دلار)", callback_data="buy_fighters")],
            [InlineKeyboardButton(text="🛸 پهپاد (۷۵ دلار)", callback_data="buy_drones")],
            [InlineKeyboardButton(text="🚢 ناو (۵۰۰ دلار)", callback_data="buy_warships")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_military")]
        ]
    )

# ================= هندلر استارت =================
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        create_user(
            message.from_user.id,
            message.from_user.username or "",
            message.from_user.first_name,
            message.from_user.last_name or ""
        )
        await message.answer(
            "🌍 **به WORLD WAR خوش آمدید!**\n\n"
            "لطفاً کشور خود را انتخاب کنید:",
            reply_markup=country_select_menu()
        )
    else:
        if not user[4]:  # country_id
            await message.answer(
                "🌍 **کشور خود را انتخاب کنید:**",
                reply_markup=country_select_menu()
            )
        else:
            country = get_country_by_id(user[4])
            country_name = country[1] if country else "نامشخص"
            await message.answer(
                f"🌍 **خوش آمدید {user[2]}!**\n"
                f"کشور شما: {country_name}",
                reply_markup=main_menu()
            )

# ================= انتخاب کشور =================
@dp.callback_query(lambda c: c.data.startswith("select_country_"))
async def select_country(callback: types.CallbackQuery):
    country_name = callback.data.replace("select_country_", "")
    country = get_country_by_name(country_name)
    if not country:
        await callback.answer("❌ کشور یافت نشد!")
        return

    user = get_user(callback.from_user.id)
    if user and user[4]:
        await callback.answer("❌ شما قبلاً کشور انتخاب کرده‌اید!")
        return

    await callback.message.answer("👤 **نام رئیس جمهور را وارد کنید:**")
    # ذخیره موقت country_id در استپ
    cur.execute("UPDATE users SET step = ? WHERE user_id = ?", (f"waiting_president_{country[0]}", callback.from_user.id))
    conn.commit()
    await callback.answer()

# ================= دریافت نام رئیس جمهور =================
@dp.message()
async def handle_text(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        return

    step = user[12] if len(user) > 12 else None
    if step and step.startswith("waiting_president_"):
        country_id = int(step.replace("waiting_president_", ""))
        president_name = message.text
        update_user_country(message.from_user.id, country_id, president_name)
        cur.execute("UPDATE users SET step = NULL WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
        await message.answer(
            f"✅ **کشور شما ثبت شد!**\n"
            f"👤 رئیس جمهور: {president_name}",
            reply_markup=main_menu()
        )

# ================= کشور من =================
@dp.callback_query(lambda c: c.data == "my_country")
async def my_country(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user[4]:
        await callback.answer("❌ شما کشوری انتخاب نکرده‌اید!")
        return

    country = get_country_by_id(user[4])
    if not country:
        await callback.answer("❌ کشور یافت نشد!")
        return

    text = f"""
{country[2]} **{country[1]}**

👤 رئیس جمهور: {user[5] or 'تعیین نشده'}
👥 جمعیت: {country[3]:,}
💰 GDP: {country[4]:,} میلیارد دلار
😊 رضایت مردم: {country[6]}%
🛢 نفت: {country[5]:,} میلیارد بشکه
☢️ فناوری هسته‌ای: سطح {country[7]}
⚔️ قدرت نظامی: {country[8]}/100
🏅 رتبه جهانی: {country[9]}
"""
    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()

# ================= اقتصاد =================
@dp.callback_query(lambda c: c.data == "economy")
async def economy(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user[4]:
        await callback.answer("❌ شما کشوری انتخاب نکرده‌اید!")
        return

    economy = get_economy(user[4])
    if not economy:
        await callback.answer("❌ اطلاعات اقتصادی یافت نشد!")
        return

    text = f"""
💰 **اقتصاد کشور شما**

💵 طلا: {economy[2]:,}
🛢 نفت: {economy[3]:,}
🔩 فولاد: {economy[4]:,}
🍗 غذا: {economy[5]:,}
⚡ برق: {economy[6]:,}
"""
    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()

# ================= ارتش =================
@dp.callback_query(lambda c: c.data == "military")
async def military_menu_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("⚔️ **پنل ارتش**", reply_markup=military_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "military_status")
async def military_status(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user[4]:
        await callback.answer("❌ شما کشوری انتخاب نکرده‌اید!")
        return

    military = get_military(user[4])
    if not military:
        await callback.answer("❌ اطلاعات نظامی یافت نشد!")
        return

    text = f"""
⚔️ **ارتش کشور شما**

👨‍✈️ سرباز: {military[2]:,}
🛡 تانک: {military[3]:,}
🚀 موشک: {military[4]:,}
✈️ جنگنده: {military[5]:,}
🛸 پهپاد: {military[6]:,}
🚢 ناو: {military[7]:,}
⚛️ کلاهک هسته‌ای: {military[8]:,}
"""
    await callback.message.edit_text(text, reply_markup=military_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "buy_equipment")
async def buy_equipment_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("🛒 **فروشگاه تجهیزات**", reply_markup=buy_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_equipment(callback: types.CallbackQuery):
    equipment = callback.data.replace("buy_", "")
    prices = {
        "soldiers": 10, "tanks": 50, "missiles": 100,
        "fighters": 200, "drones": 75, "warships": 500
    }
    
    user = get_user(callback.from_user.id)
    if not user or not user[4]:
        await callback.answer("❌ شما کشوری انتخاب نکرده‌اید!")
        return

    economy = get_economy(user[4])
    if not economy:
        await callback.answer("❌ اطلاعات اقتصادی یافت نشد!")
        return

    price = prices.get(equipment, 0)
    if economy[2] < price:
        await callback.answer(f"❌ پول کافی نیست! نیاز: {price} دلار")
        return

    # خرید
    field_map = {
        "soldiers": "soldiers", "tanks": "tanks", "missiles": "missiles",
        "fighters": "fighters", "drones": "drones", "warships": "warships"
    }
    field = field_map.get(equipment)
    if field:
        cur.execute(f"UPDATE military SET {field} = {field} + 1 WHERE country_id = ?", (user[4],))
        cur.execute("UPDATE economy SET gold = gold - ? WHERE country_id = ?", (price, user[4]))
        conn.commit()
        await callback.answer(f"✅ ۱ عدد {equipment} خریداری شد!")

# ================= دیپلماسی =================
@dp.callback_query(lambda c: c.data == "diplomacy")
async def diplomacy_menu_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("🤝 **پنل دیپلماسی**", reply_markup=diplomacy_menu())
    await callback.answer()

# ================= جاسوسی =================
@dp.callback_query(lambda c: c.data == "espionage")
async def espionage(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user[4]:
        await callback.answer("❌ شما کشوری انتخاب نکرده‌اید!")
        return

    countries = get_all_countries()
    text = "🕵️ **اطلاعات جاسوسی**\n\n"
    for c in countries:
        if c[0] != user[4]:
            military = get_military(c[0])
            if military:
                text += f"{c[2]} {c[1]}: 🪖 {military[2]:,} سرباز | 💰 {c[4]} میلیارد\n"
    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()

# ================= هسته‌ای =================
@dp.callback_query(lambda c: c.data == "nuclear")
async def nuclear(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user[4]:
        await callback.answer("❌ شما کشوری انتخاب نکرده‌اید!")
        return

    military = get_military(user[4])
    country = get_country_by_id(user[4])
    if not military or not country:
        await callback.answer("❌ اطلاعات یافت نشد!")
        return

    text = f"""
☢️ **برنامه هسته‌ای**

⚛️ کلاهک هسته‌ای: {military[8]}
🔬 فناوری هسته‌ای: سطح {country[7]}
⏳ تولید هر کلاهک: ۲۴ ساعت
💰 هزینه تولید: ۱,۰۰۰,۰۰۰ دلار
"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚛️ تولید کلاهک جدید", callback_data="build_nuke")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "build_nuke")
async def build_nuke(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user[4]:
        await callback.answer("❌ شما کشوری انتخاب نکرده‌اید!")
        return

    economy = get_economy(user[4])
    if not economy:
        await callback.answer("❌ اطلاعات اقتصادی یافت نشد!")
        return

    if economy[2] < 1000000:
        await callback.answer("❌ پول کافی نیست! نیاز: ۱,۰۰۰,۰۰۰ دلار")
        return

    cur.execute("UPDATE economy SET gold = gold - 1000000 WHERE country_id = ?", (user[4],))
    cur.execute("UPDATE military SET nuclear_warheads = nuclear_warheads + 1 WHERE country_id = ?", (user[4],))
    conn.commit()
    await callback.answer("✅ کلاهک هسته‌ای تولید شد!")

# ================= نقشه جهان =================
@dp.callback_query(lambda c: c.data == "world_map")
async def world_map(callback: types.CallbackQuery):
    countries = get_all_countries()
    text = "🗺️ **نقشه جهان**\n\n"
    for c in countries:
        cur.execute("SELECT user_id FROM users WHERE country_id = ?", (c[0],))
        owner = cur.fetchone()
        status = "👤 گرفته شده" if owner else "✅ آزاد"
        text += f"{c[2]} {c[1]}: {status}\n"
    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()

# ================= اخبار =================
@dp.callback_query(lambda c: c.data == "news")
async def news(callback: types.CallbackQuery):
    cur.execute("SELECT * FROM news ORDER BY created_at DESC LIMIT 10")
    news_list = cur.fetchall()

    text = "📰 **اخبار جهان**\n\n"
    if not news_list:
        text += "هنوز اخباری وجود ندارد!"
    else:
        for n in news_list:
            text += f"📌 {n[1]}\n{n[2]}\n\n"

    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()

# ================= رتبه‌بندی =================
@dp.callback_query(lambda c: c.data == "leaderboard")
async def leaderboard(callback: types.CallbackQuery):
    countries = get_all_countries()
    text = "🏆 **رتبه‌بندی جهانی**\n\n"
    for i, c in enumerate(countries[:10], 1):
        medals = ["🥇", "🥈", "🥉"]
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {c[2]} {c[1]} | قدرت: {c[8]} | رتبه: {c[9]}\n"
    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()

# ================= برگشت =================
@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("🌍 **منوی اصلی**", reply_markup=main_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_military")
async def back_to_military(callback: types.CallbackQuery):
    await callback.message.edit_text("⚔️ **پنل ارتش**", reply_markup=military_menu())
    await callback.answer()

# ================= راه‌اندازی =================
async def main():
    create_countries()
    print("🌍 WORLD WAR - نسخه نهایی")
    print("=" * 40)
    print(f"✅ توکن: {BOT_TOKEN[:10]}...")
    print(f"✅ ادمین: {ADMINS[0]}")
    print(f"✅ کانال: {CHANNEL_ID}")
    print("🚀 ربات در حال اجراست...")
    print("=" * 40)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())