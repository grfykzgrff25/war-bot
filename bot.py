import os
import sqlite3
import random
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Optional OpenAI / LLM Integration
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ----------------------------------------------------
# 1. CONFIGURATION & LOGGING
# ----------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DB_NAME = "world_war_master.db"
AI_API_KEY = os.environ.get("OPENAI_API_KEY", None)

if OPENAI_AVAILABLE and AI_API_KEY:
    openai.api_key = AI_API_KEY

# ----------------------------------------------------
# 2. DATABASE INITIALIZATION & SCHEMA EXPANSIO
# ----------------------------------------------------
def init_sqlite():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. USERS & COMMANDERS
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            commander_name TEXT,
            country_code TEXT,
            level INTEGER DEFAULT 1,
            score INTEGER DEFAULT 0,
            approval INTEGER DEFAULT 100,
            is_admin INTEGER DEFAULT 0,
            chat_state TEXT DEFAULT 'NONE',
            alliance_id INTEGER DEFAULT 0,
            tech_era TEXT DEFAULT 'CLASSIC',
            is_sanctioned INTEGER DEFAULT 0,
            in_civil_war INTEGER DEFAULT 0,
            rebel_power INTEGER DEFAULT 0,
            season_wins INTEGER DEFAULT 0
        )
    ''')
    
    # 2. COUNTRIES
    c.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            code TEXT PRIMARY KEY,
            name TEXT,
            flag TEXT,
            population INTEGER,
            money REAL DEFAULT 1000000,
            oil REAL DEFAULT 50000,
            steel REAL DEFAULT 50000,
            food REAL DEFAULT 100000,
            power REAL DEFAULT 50000,
            gold REAL DEFAULT 1000,
            is_ai INTEGER DEFAULT 0,
            has_satellite INTEGER DEFAULT 0,
            has_s400 INTEGER DEFAULT 0,
            chokepoint_control TEXT DEFAULT 'NONE'
        )
    ''')
    
    # 3. PROVINCES
    c.execute('''
        CREATE TABLE IF NOT EXISTS provinces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT,
            name TEXT,
            population INTEGER,
            security INTEGER DEFAULT 100,
            infrastructure INTEGER DEFAULT 1,
            owner_id INTEGER DEFAULT 0,
            is_radioactive INTEGER DEFAULT 0,
            radioactive_until TIMESTAMP,
            weather_condition TEXT DEFAULT 'CLEAR'
        )
    ''')
    
    # 4. ARMIES & HIGH-TECH WEAPONS
    c.execute('''
        CREATE TABLE IF NOT EXISTS armies (
            user_id INTEGER PRIMARY KEY,
            soldiers INTEGER DEFAULT 10000,
            tanks INTEGER DEFAULT 100,
            artillery INTEGER DEFAULT 50,
            spec_ops INTEGER DEFAULT 20,
            fighters INTEGER DEFAULT 20,
            bombers INTEGER DEFAULT 10,
            drones INTEGER DEFAULT 30,
            warships INTEGER DEFAULT 5,
            submarines INTEGER DEFAULT 2,
            carriers INTEGER DEFAULT 0,
            missiles_short INTEGER DEFAULT 10,
            missiles_mid INTEGER DEFAULT 5,
            missiles_long INTEGER DEFAULT 1,
            nukes INTEGER DEFAULT 0,
            cyber_level INTEGER DEFAULT 1,
            laser_turrets INTEGER DEFAULT 0,
            hypersonic_missiles INTEGER DEFAULT 0,
            ai_drones INTEGER DEFAULT 0
        )
    ''')
    
    # 5. WARS & TACTICS
    c.execute('''
        CREATE TABLE IF NOT EXISTS wars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER,
            defender_id INTEGER,
            province_id INTEGER,
            end_time TIMESTAMP,
            attacker_tactic TEXT DEFAULT 'STANDARD',
            is_false_flag INTEGER DEFAULT 0,
            framed_user_id INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ACTIVE'
        )
    ''')
    
    # 6. ALLIANCES & UN
    c.execute('''
        CREATE TABLE IF NOT EXISTS alliances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            leader_id INTEGER,
            treasury REAL DEFAULT 0
        )
    ''')

    # 7. GENERALS
    c.execute('''
        CREATE TABLE IF NOT EXISTS generals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            type TEXT,
            level INTEGER DEFAULT 1,
            is_alive INTEGER DEFAULT 1
        )
    ''')

    # 8. MARKET PRICES
    c.execute('''
        CREATE TABLE IF NOT EXISTS market (
            resource TEXT PRIMARY KEY,
            price REAL,
            trend TEXT DEFAULT 'STABLE'
        )
    ''')

    # 9. WORLD NEWS
    c.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 10. UN RESOLUTIONS
    c.execute('''
        CREATE TABLE IF NOT EXISTS un_resolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_user_id INTEGER,
            reason TEXT,
            votes_for INTEGER DEFAULT 0,
            votes_against INTEGER DEFAULT 0,
            status TEXT DEFAULT 'PENDING'
        )
    ''')

    # Seed Default Countries & Market
    c.execute("SELECT COUNT(*) FROM countries")
    if c.fetchone()[0] == 0:
        default_countries = [
            ("IRN", "ایران", "🇮🇷", 85000000, 1),
            ("USA", "آمریکا", "🇺🇸", 330000000, 1),
            ("RUS", "روسیه", "🇷🇺", 144000000, 1),
            ("CHN", "چین", "🇨🇳", 1400000000, 1),
            ("DEU", "آلمان", "🇩🇪", 83000000, 1),
            ("FRA", "فرانسه", "🇫🇷", 67000000, 1),
            ("GBR", "انگلیس", "🇬🇧", 67000000, 1),
            ("JPN", "ژاپن", "🇯🇵", 125000000, 1),
            ("TUR", "ترکیه", "🇹🇷", 84000000, 1),
            ("IND", "هند", "🇮🇳", 1380000000, 1),
        ]
        for code, name, flag, pop, is_ai in default_countries:
            c.execute("INSERT INTO countries (code, name, flag, population, is_ai) VALUES (?, ?, ?, ?, ?)",
                      (code, name, flag, pop, is_ai))
            provs = [f"استان مرکز {name}", f"استان شمالی {name}", f"استان جنوبی {name}"]
            for p in provs:
                c.execute("INSERT INTO provinces (country_code, name, population) VALUES (?, ?, ?)",
                          (code, p, random.randint(1000000, 10000000)))

    c.execute("SELECT COUNT(*) FROM market")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO market (resource, price) VALUES ('oil', 75.0)")
        c.execute("INSERT INTO market (resource, price) VALUES ('steel', 120.0)")
        c.execute("INSERT INTO market (resource, price) VALUES ('food', 40.0)")
        c.execute("INSERT INTO market (resource, price) VALUES ('gold', 1800.0)")

    conn.commit()
    conn.close()

# ----------------------------------------------------
# 3. HELPER FUNCTIONS
# ----------------------------------------------------
def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(query, params)
    res = None
    if fetchone:
        res = c.fetchone()
    elif fetchall:
        res = c.fetchall()
    if commit:
        conn.commit()
    conn.close()
    return res

def add_news(content):
    db_query("INSERT INTO news (content) VALUES (?)", (content,), commit=True)

async def generate_ai_response(prompt: str, context_system: str = "شما یک مشاور استراتژیک نظامی و اقتصادی هستید.") -> str:
    if OPENAI_AVAILABLE and AI_API_KEY:
        try:
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": context_system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI API Error: {e}")
    
    fallback_responses = [
        "جناب فرمانده، طبق اطلاعات هوش مصنوعی، تقویت پدافند سایبری و ذخایر طلا پیشنهاد می‌شود.",
        "پیشنهاد می‌کنم پیش از هرگونه اقدام نظامی، با کشورهای عضو پیمان مشورت کنید.",
        "رضایت عمومی کاهش یافته است؛ بخشی از بودجه ارتش را به رفاه استان‌ها اختصاص دهید.",
        "فرمانده، گزارش‌ها نشان می‌دهد دشمن در حال توسعه موشک‌های هایپرسونیک است؛ پدافند را ارتقا دهید."
    ]
    return random.choice(fallback_responses)

# ----------------------------------------------------
# 4. COMMAND HANDLERS & NAVIGATION
# ----------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    db_user = db_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    
    if not db_user:
        countries = db_query("SELECT code, name, flag FROM countries WHERE is_ai = 1", fetchall=True)
        keyboard = []
        row = []
        for code, name, flag in countries:
            row.append(InlineKeyboardButton(f"{flag} {name}", callback_data=f"select_country_{code}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"🌍 **به بازی WORLD WAR MASTER خوش آمدید، {user.first_name}!**\n\n"
            "لطفاً کشور تحت فرماندهی خود را انتخاب کنید:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await main_menu(update, context)

async def select_country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    country_code = query.data.split("_")[2]
    
    commander_name = f"فرمانده {query.from_user.first_name}"
    db_query("INSERT INTO users (user_id, commander_name, country_code) VALUES (?, ?, ?)",
             (user_id, commander_name, country_code), commit=True)
    
    db_query("INSERT INTO armies (user_id) VALUES (?)", (user_id,), commit=True)
    db_query("INSERT INTO generals (user_id, name, type) VALUES (?, ?, ?)", (user_id, "ژنرال اصلی ارتش", "LAND"), commit=True)
    db_query("UPDATE countries SET is_ai = 0 WHERE code = ?", (country_code,), commit=True)
    
    add_news(f"👑 فرمانده جدید {commander_name} رهبری کشور {country_code} را بر عهده گرفت!")
    
    await query.edit_message_text(f"✅ انتخاب شما ثبت شد! شما اکنون رهبر کشور {country_code} هستید.")
    await main_menu(update, context)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🔍 بررسی وضعیت کشور", callback_data="menu_profile"),
            InlineKeyboardButton("🧠 مشاور هوش مصنوعی", callback_data="menu_ai_advisor")
        ],
        [
            InlineKeyboardButton("📊 آمار ارتش & نیروها", callback_data="menu_army"),
            InlineKeyboardButton("⚔️ اتاق جنگ تاکتیکی", callback_data="menu_war")
        ],
        [
            InlineKeyboardButton("🤝 دیپلماسی & سازمان ملل", callback_data="menu_alliances"),
            InlineKeyboardButton("🕵️ عملیات پرچم دروغین & سایبری", callback_data="menu_blackops")
        ],
        [
            InlineKeyboardButton("🛰️ پدافند & سامانه‌های لیزری", callback_data="menu_defense"),
            InlineKeyboardButton("☢️ اتاق شلیک هسته‌ای & آلودگی", callback_data="menu_nuke")
        ],
        [
            InlineKeyboardButton("🛳️ بورس جهانی & کنترل تنگه‌ها", callback_data="menu_market"),
            InlineKeyboardButton("🧬 درخت فناوری ۴ عصری", callback_data="menu_tech")
        ],
        [
            InlineKeyboardButton("👑 مدیریت شورش & کودتا", callback_data="menu_civil_war"),
            InlineKeyboardButton("🎯 ترور ژنرال‌های دشمن", callback_data="menu_assassinate")
        ],
        [
            InlineKeyboardButton("🏆 تالار افتخارات & رتبه‌بندی", callback_data="menu_rankings"),
            InlineKeyboardButton("📰 اخبار سراسری جهان", callback_data="menu_news")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🌍 **ستاد فرماندهی کل نیروهای مسلح (WORLD WAR MASTER)**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ----------------------------------------------------
# 5. DETAILED CALLBACK HANDLERS
# ----------------------------------------------------
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()

    if data.startswith("select_country_"):
        await select_country_callback(update, context)
        return

    if data == "menu_main":
        db_query("UPDATE users SET chat_state = 'NONE' WHERE user_id = ?", (user_id,), commit=True)
        await main_menu(update, context)
        return

    # --- 1. PROFILE ---
    if data == "menu_profile":
        u = db_query("SELECT commander_name, country_code, level, score, approval, in_civil_war, is_sanctioned, tech_era FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        c = db_query("SELECT name, flag, money, oil, steel, food, gold, chokepoint_control FROM countries WHERE code = ?", (u[1],), fetchone=True)
        
        status_str = "⚠️ درگیر شورش / کودتا" if u[5] else "🟢 باثبات"
        sanction_str = "🔴 تحریم سازمان ملل" if u[6] else "🟢 تجارت آزاد"

        text = (
            f"👤 **فرمانده:** {u[0]}\n"
            f"🚩 **کشور:** {c[1]} {c[0]}\n"
            f"⭐ **سطح:** {u[2]} | **امتیاز:** {u[3]} | **عصر:** {u[7]}\n"
            f"📊 **رضایت عمومی:** {u[4]}% ({status_str})\n"
            f"📜 **وضعیت بین‌الملل:** {sanction_str}\n"
            f"⚓ **تنگه تحت کنترل:** {c[7]}\n\n"
            f"💰 **خزانه:** ${c[2]:,.0f} | 🪙 **طلا:** {c[6]:,.0f} شمش\n"
            f"🛢 **نفت:** {c[3]:,.0f} | 🔩 **فولاد:** {c[4]:,.0f} | 🌾 **غذا:** {c[5]:,.0f}"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 2. AI ADVISOR ---
    elif data == "menu_ai_advisor":
        db_query("UPDATE users SET chat_state = 'TALKING_TO_AI' WHERE user_id = ?", (user_id,), commit=True)
        text = (
            "🧠 **اتاق مشاور هوش مصنوعی**\n\n"
            "سوال، چالش اقتصادی، یا راهبرد نظامی خود را بنویسید و ارسال کنید:"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 3. ARMY STATS & SHOP ---
    elif data == "menu_army":
        a = db_query("SELECT soldiers, tanks, artillery, spec_ops, fighters, drones, missiles_short, nukes, laser_turrets, hypersonic_missiles, ai_drones FROM armies WHERE user_id = ?", (user_id,), fetchone=True)
        text = (
            f"📊 **آمار و تجهیزات ارتش:**\n\n"
            f"🪖 سرباز: {a[0]:,} | 🛡 تانک: {a[1]:,}\n"
            f"💥 توپخانه: {a[2]:,} | 🎯 نیروی ویژه: {a[3]:,}\n"
            f"✈️ جنگنده: {a[4]:,} | 🛸 پهپاد عادی: {a[5]:,}\n"
            f"🤖 پهپاد AI: {a[10]:,} | ⚡ برجک لیزری: {a[8]:,}\n"
            f"🚀 موشک بالستیک: {a[6]:,} | 🌀 موشک هایپرسونیک: {a[9]:,}\n"
            f"☢️ کلاهک هسته‌ای: {a[7]:,}"
        )
        keyboard = [
            [
                InlineKeyboardButton("🛒 خرید نیروی زمینی", callback_data="buy_land_army"),
                InlineKeyboardButton("✈️ خرید تجهیزات مدرن", callback_data="buy_tech_army")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "buy_land_army":
        u = db_query("SELECT country_code FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        c = db_query("SELECT money FROM countries WHERE code = ?", (u[0],), fetchone=True)
        if c[0] >= 50000:
            db_query("UPDATE countries SET money = money - 50000 WHERE code = ?", (u[0],), commit=True)
            db_query("UPDATE armies SET soldiers = soldiers + 2000, tanks = tanks + 20 WHERE user_id = ?", (user_id,), commit=True)
            await query.edit_message_text("✅ تعداد ۲۰۰۰ سرباز و ۲۰ تانک جدید به ارتش شما اضافه شد!")
        else:
            await query.edit_message_text("❌ بودجه کافی برای خرید نیرو ندارید! (نیاز به $50,000)")

    elif data == "buy_tech_army":
        u = db_query("SELECT country_code FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        c = db_query("SELECT money, steel FROM countries WHERE code = ?", (u[0],), fetchone=True)
        if c[0] >= 150000 and c[1] >= 5000:
            db_query("UPDATE countries SET money = money - 150000, steel = steel - 5000 WHERE code = ?", (u[0],), commit=True)
            db_query("UPDATE armies SET fighters = fighters + 5, drones = drones + 10 WHERE user_id = ?", (user_id,), commit=True)
            await query.edit_message_text("✅ تعداد ۵ جنگنده و ۱۰ پهپاد جدید خریداری شد!")
        else:
            await query.edit_message_text("❌ منابع کافی ندارید! (نیاز به $150,000 و 5,000 فولاد)")

    # --- 4. TACTICAL WARFARE & FALSE FLAG ---
    elif data == "menu_war":
        text = "⚔️ **اتاق نبرد و عملیات نظامی**\nنوع عملیات نبرد را انتخاب کنید:"
        keyboard = [
            [
                InlineKeyboardButton("🚀 حمله مستعمراتی مستقیم", callback_data="attack_select_target"),
                InlineKeyboardButton("🎭 عملیات پرچم دروغین", callback_data="false_flag_attack")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "attack_select_target":
        provs = db_query("SELECT id, name, country_code, is_radioactive, weather_condition FROM provinces LIMIT 6", fetchall=True)
        keyboard = []
        row = []
        for p_id, p_name, p_code, p_rad, p_weather in provs:
            rad_tag = "☢️" if p_rad else ""
            w_tag = "❄️" if p_weather == "SEVERE_WINTER" else ("🌪️" if p_weather == "SANDSTORM" else "")
            row.append(InlineKeyboardButton(f"{p_name} ({p_code}) {rad_tag}{w_tag}", callback_data=f"start_war_{p_id}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_war")])
        await query.edit_message_text("استان هدف را انتخاب کنید (علامت ☢️ نشان‌دهنده آلودگی هسته‌ای است):", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("start_war_"):
        prov_id = int(data.split("_")[2])
        end_time = datetime.now() + timedelta(minutes=30)
        db_query("INSERT INTO wars (attacker_id, defender_id, province_id, end_time) VALUES (?, 0, ?, ?)",
                 (user_id, prov_id, end_time), commit=True)
        
        add_news(f"🔥 نبرد برای تصرف استان شماره {prov_id} آغاز شد!")
        keyboard = [
            [
                InlineKeyboardButton("🎯 تاکتیک گازانبری", callback_data=f"tactic_flank_{prov_id}"),
                InlineKeyboardButton("✈️ پشتیبانی سنگین هوایی", callback_data=f"tactic_air_{prov_id}")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text("✅ دستور حمله صادر شد! تاکتیک ارتش را مشخص کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    # --- 5. BLACK OPS & FALSE FLAG ---
    elif data == "menu_blackops":
        text = "🕵️ **مرکز عملیات پرچم دروغین و حملات سایبری**\nدستور را انتخاب کنید:"
        keyboard = [
            [
                InlineKeyboardButton("🎭 شبیه‌سازی حمله پرچم دروغین", callback_data="exec_false_flag"),
                InlineKeyboardButton("💻 هک سایبری پدافند دشمن", callback_data="op_cyber_hack")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "exec_false_flag":
        other_users = db_query("SELECT user_id, commander_name FROM users WHERE user_id != ? LIMIT 2", (user_id,), fetchall=True)
        if len(other_users) >= 1:
            framed_id = other_users[0][0]
            add_news(f"⚠️ **گزارش فوری:** نیروهای انتصابی به {other_users[0][1]} به مرزهای بین‌المللی حمله کردند! (عملیات مشکوک)")
            await query.edit_message_text(f"🎭 عملیات پرچم دروغین اجرا شد! حمله به نام فرمانده {other_users[0][1]} ثبت گردید.")
        else:
            await query.edit_message_text("❌ بازیکن دیگری برای جعل هویت در سیستم یافت نشد.")

    elif data == "op_cyber_hack":
        await query.edit_message_text("✅ حمله سایبری موفقیت‌آمیز بود! سامانه‌های پدافندی کشور هدف تا ۱۰ دقیقه از کار افتادند.")

    # --- 6. SATELLITE & DEFENSE ---
    elif data == "menu_defense":
        text = "🛰️ **سامانه پدافند موشکی، رادار و سلاح‌های لیزری**\nگزینه مورد نظر را انتخاب کنید:"
        keyboard = [
            [
                InlineKeyboardButton("🛰️ پرتاب ماهواره جاسوسی", callback_data="buy_satellite"),
                InlineKeyboardButton("🛡️ ساخت پدافند S-400", callback_data="buy_s400")
            ],
            [
                InlineKeyboardButton("⚡ ساخت برجک لیزری ضدموشک", callback_data="buy_laser")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "buy_laser":
        u = db_query("SELECT country_code FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        c = db_query("SELECT money, gold FROM countries WHERE code = ?", (u[0],), fetchone=True)
        if c[0] >= 300000 and c[1] >= 100:
            db_query("UPDATE countries SET money = money - 300000, gold = gold - 100 WHERE code = ?", (u[0],), commit=True)
            db_query("UPDATE armies SET laser_turrets = laser_turrets + 1 WHERE user_id = ?", (user_id,), commit=True)
            await query.edit_message_text("⚡ یک برجک لیزری پیشرفته نابودکننده موشک‌های هایپرسونیک ساخته شد!")
        else:
            await query.edit_message_text("❌ منابع کافی ندارید! (نیاز به $300,000 و 100 شمش طلا)")

    # --- 7. NUCLEAR ROOM & FALLOUT ---
    elif data == "menu_nuke":
        a = db_query("SELECT nukes FROM armies WHERE user_id = ?", (user_id,), fetchone=True)
        nuke_count = a[0] if a else 0
        text = (
            f"☢️ **اتاق فرماندهی سلاح‌های هسته‌ای و آلودگی رادیواکتیو**\n\n"
            f"کلاهک‌های موجود: **{nuke_count}**\n\n"
            "⚠️ **هشدار:** شلیک موشک هسته‌ای، استان هدف را تا ۴۸ ساعت دچار «آلودگی کامل رادیواکتیو» کرده، تولید منابع را صفر می‌کند و موجب تحریم فوری سازمان ملل می‌شود."
        )
        keyboard = [
            [
                InlineKeyboardButton("☢️ شلیک موشک هسته‌ای به استان target", callback_data="launch_nuke_target"),
                InlineKeyboardButton("🏭 ساخت کلاهک هسته‌ای جدید", callback_data="build_nuke")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "launch_nuke_target":
        a = db_query("SELECT nukes FROM armies WHERE user_id = ?", (user_id,), fetchone=True)
        if a and a[0] >= 1:
            db_query("UPDATE armies SET nukes = nukes - 1 WHERE user_id = ?", (user_id,), commit=True)
            db_query("UPDATE users SET is_sanctioned = 1 WHERE user_id = ?", (user_id,), commit=True)
            
            # آلوده کردن اولین استان
            rad_until = datetime.now() + timedelta(hours=48)
            db_query("UPDATE provinces SET is_radioactive = 1, radioactive_until = ? WHERE id = 1", (rad_until,), commit=True)
            
            u = db_query("SELECT commander_name FROM users WHERE user_id = ?", (user_id,), fetchone=True)
            add_news(f"☢️ **فاجعه هسته‌ای:** کشور {u[0]} یک موشک هسته‌ای شلیک کرد! استان target دچار آلودگی شدید شد!")
            await query.edit_message_text("🚀 موشک هسته‌ای با موفقیت شلیک شد! منطقه هدف نابود و آلوده به رادیواکتیو شد.")
        else:
            await query.edit_message_text("❌ شما هیچ کلاهک هسته‌ای آماده‌ای در اختیار ندارید!")

    elif data == "build_nuke":
        u = db_query("SELECT country_code FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        c = db_query("SELECT money, gold FROM countries WHERE code = ?", (u[0],), fetchone=True)
        if c[0] >= 1000000 and c[1] >= 500:
            db_query("UPDATE countries SET money = money - 1000000, gold = gold - 500 WHERE code = ?", (u[0],), commit=True)
            db_query("UPDATE armies SET nukes = nukes + 1 WHERE user_id = ?", (user_id,), commit=True)
            await query.edit_message_text("☢️ یک کلاهک هسته‌ای جدید با موفقیت مونتاژ و آماده شلیک شد!")
        else:
            await query.edit_message_text("❌ بودجه ساخت کلاهک هسته‌ای کافی نیست! ($1,000,000 و 500 طلا)")

    # --- 8. MARKET & CHOKEPOINTS ---
    elif data == "menu_market":
        mk = db_query("SELECT resource, price FROM market", fetchall=True)
        m_str = "\n".join([f"• {x[0].upper()}: ${x[1]:,.1f}" for x in mk])
        
        text = (
            f"🛳️ **بورس جهانی منابع & کنترل تنگه‌های استراتژیک**\n\n"
            f"📈 **قیمت‌های لحظه‌ای بازار:**\n{m_str}\n\n"
            "با تسلط بر تنگه‌ها (هرمز، سوئز) می‌توانید ۵٪ عوارض از تجارت تمام کشورها بگیرید."
        )
        keyboard = [
            [
                InlineKeyboardButton("⚓ تصرف تنگه هرمز", callback_data="claim_hormuz"),
                InlineKeyboardButton("⚓ تصرف کانال سوئز", callback_data="claim_suez")
            ],
            [
                InlineKeyboardButton("🛢 فروش ۱,۰۰۰ نفت", callback_data="sell_oil"),
                InlineKeyboardButton("🔩 خرید ۱,۰۰۰ فولاد", callback_data="buy_steel")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "claim_hormuz":
        u = db_query("SELECT country_code FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        db_query("UPDATE countries SET chokepoint_control = 'HORMUZ' WHERE code = ?", (u[0],), commit=True)
        add_news(f"⚓ کشور {u[0]} کنترل تنگه هرمز را به دست گرفت و عوارض گمرکی تعیین کرد!")
        await query.edit_message_text("⚓ شما موفق به تصرف و اعمال کنترل بر تنگه هرمز شدید!")

    # --- 9. TECH TREE ---
    elif data == "menu_tech":
        u = db_query("SELECT tech_era FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        era = u[0] if u else "CLASSIC"
        text = (
            f"🧬 **درخت فناوری و عصر توسعه**\n\n"
            f"عصر فعلی شما: **{era}**\n\n"
            "ارتقا به اعصارهای بالاتر باعث باز شدن سلاح‌های هایپرسونیک، سامانه‌های سایبری و پهپادهای خودکار می‌شود."
        )
        keyboard = [
            [
                InlineKeyboardButton("🚀 ارتقا به عصر بعد (CYBER / HYPERSONIC)", callback_data="upgrade_tech_era"),
                InlineKeyboardButton("🤖 ساخت پهپاد انتحاری AI", callback_data="build_ai_drone")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "upgrade_tech_era":
        u = db_query("SELECT tech_era, country_code FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        c = db_query("SELECT money FROM countries WHERE code = ?", (u[1],), fetchone=True)
        
        if c[0] >= 500000:
            next_era = "CYBER" if u[0] == "CLASSIC" else "HYPERSONIC"
            db_query("UPDATE countries SET money = money - 500000 WHERE code = ?", (u[1],), commit=True)
            db_query("UPDATE users SET tech_era = ? WHERE user_id = ?", (next_era, user_id), commit=True)
            await query.edit_message_text(f"🚀 فناوری کشور شما با موفقیت به عصر **{next_era}** ارتقا یافت!")
        else:
            await query.edit_message_text("❌ بودجه تحقیقاتی کافی نیست! (نیاز به $500,000)")

    # --- 10. COUP & CIVIL WAR ---
    elif data == "menu_civil_war":
        u = db_query("SELECT approval, in_civil_war, rebel_power FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        
        if u[1] == 1:
            text = (
                f"🚨 **هشدار بحران: جنگ داخلی و کودتا!**\n\n"
                f"قدرت نیروهای شورشی: **{u[2]}%**\n"
                "شورشیان مسلح به بخش‌هایی از کشور تسلط یافته‌اند. باید فوراً نیروهای ویژه اعزام کنید یا سرکوب سراسری انجام دهید!"
            )
            keyboard = [
                [
                    InlineKeyboardButton("🪖 سرکوب نظامی شورشیان", callback_data="suppress_rebels"),
                    InlineKeyboardButton("💰 اعطای یارانه و اصلاحات", callback_data="bribe_rebels")
                ],
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
            ]
        else:
            text = f"🟢 **وضعیت داخلی باثبات است.**\nدرصد رضایت عمومی مردم: **{u[0]}%**"
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]]
            
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "suppress_rebels":
        db_query("UPDATE users SET in_civil_war = 0, approval = 50, rebel_power = 0 WHERE user_id = ?", (user_id,), commit=True)
        await query.edit_message_text("🪖 ارتش با موفقیت شورش داخلی را سرکوب کرد و امنیت بازگشت!")

    # --- 11. GENERAL ASSASSINATION ---
    elif data == "menu_assassinate":
        text = "🎯 **اتاق ترور ژنرال‌های برجسته دشمن**\n\nبا ترور ژنرال ارشد کشور هدف، توان رزمی نیروهای آن کشور تا ۳۰٪ کاهش می‌یابد."
        keyboard = [
            [
                InlineKeyboardButton("🎯 اعزام جوخه ترور Spec-Ops", callback_data="exec_assassination")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "exec_assassination":
        a = db_query("SELECT spec_ops FROM armies WHERE user_id = ?", (user_id,), fetchone=True)
        if a and a[0] >= 5:
            db_query("UPDATE armies SET spec_ops = spec_ops - 5 WHERE user_id = ?", (user_id,), commit=True)
            succ = random.choice([True, False])
            if succ:
                add_news("🎯 **گزارش ترور:** ژنرال ارشد یکی از قدرت‌های منطقه در یک عملیات پیچیده ترور شد!")
                await query.edit_message_text("🎯 عملیات ترور با موفقیت انجام شد! روحیه دشمن تضعیف گردید.")
            else:
                await query.edit_message_text("❌ عملیات ترور لو رفت و نیروهای شما کشته شدند!")
        else:
            await query.edit_message_text("❌ برای این عملیات به حداقل ۵ نیروی ویژه (Spec-Ops) نیاز دارید.")

    # --- 12. UN & ALLIANCES ---
    elif data == "menu_alliances":
        text = "🤝 **دیپلماسی، پیمان‌های بین‌المللی و شورای امنیت سازمان ملل**"
        keyboard = [
            [
                InlineKeyboardButton("🇺🇳 پیشنهاد تحریم یک کشور", callback_data="propose_un_sanction"),
                InlineKeyboardButton("🤝 تشکیل پیمان جدید", callback_data="create_alliance")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 13. RANKINGS & HALL OF FAME ---
    elif data == "menu_rankings":
        top_users = db_query("SELECT commander_name, score, season_wins FROM users ORDER BY score DESC LIMIT 5", fetchall=True)
        rank_str = "\n".join([f"{i+1}. {x[0]} - {x[1]} امتیاز (🥇 {x[2]} برد فصلی)" for i, x in enumerate(top_users)])
        
        text = f"🏆 **تالار افتخارات و جدول ۵ قدرت برتر:**\n\n{rank_str}"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 14. NEWS ---
    elif data == "menu_news":
        news_items = db_query("SELECT content, timestamp FROM news ORDER BY id DESC LIMIT 5", fetchall=True)
        news_str = "\n".join([f"• [{x[1]}] {x[0]}" for x in news_items]) if news_items else "خبری ثبت نشده است."
        
        text = f"📰 **خبرگزاری سراسری جهان**\n\n{news_str}"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ----------------------------------------------------
# 6. TEXT MESSAGE HANDLER (AI CHAT)
# ----------------------------------------------------
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    u = db_query("SELECT chat_state, country_code FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not u:
        return

    chat_state, country_code = u[0], u[1]

    if chat_state == 'TALKING_TO_AI':
        await update.message.reply_chat_action("typing")
        
        c = db_query("SELECT money, oil, steel, food FROM countries WHERE code = ?", (country_code,), fetchone=True)
        a = db_query("SELECT soldiers, tanks, fighters FROM armies WHERE user_id = ?", (user_id,), fetchone=True)
        
        context_prompt = (
            f"اطلاعات کشور بازیکن:\n"
            f"کشور: {country_code} | خزانه: ${c[0]} | نفت: {c[1]} | ارتش: {a[0]} سرباز\n"
            f"سوال فرمانده: {user_text}"
        )
        
        system_instruction = "شما یک مشاور ارشد استراتژیک در یک بازی جنگ جهانی هستید. پاسخ‌های شما باید حماسی، تکنیکی و کوتاه باشد."
        ai_reply = await generate_ai_response(context_prompt, system_instruction)
        
        keyboard = [[InlineKeyboardButton("🔙 خروج از چت مشاور", callback_data="menu_main")]]
        await update.message.reply_text(f"🧠 **پاسخ مشاور:**\n\n{ai_reply}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ----------------------------------------------------
# 7. AUTOMATED BACKGROUND JOBS
# ----------------------------------------------------
async def job_war_resolver(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    active_wars = db_query("SELECT id, attacker_id, defender_id, province_id FROM wars WHERE status = 'ACTIVE' AND end_time <= ?", (now,), fetchall=True)
    
    for w_id, att_id, def_id, prov_id in active_wars:
        win = random.choice([True, False])
        if win:
            db_query("UPDATE wars SET status = 'ATTACKER_WON' WHERE id = ?", (w_id,), commit=True)
            db_query("UPDATE users SET score = score + 150 WHERE user_id = ?", (att_id,), commit=True)
            add_news(f"🏆 **فتح جدید:** استان شماره {prov_id} پس از نبردی سنگین به تصرف نیروهای فرمانده {att_id} درآمد!")
        else:
            db_query("UPDATE wars SET status = 'DEFENDER_WON' WHERE id = ?", (w_id,), commit=True)
            add_news(f"💀 **شکست:** نیروهای مهاجم در استان شماره {prov_id} به طور کامل عقب‌رانی شدند.")

async def job_coups_weather_and_market(context: ContextTypes.DEFAULT_TYPE):
    # Update weather
    weathers = ["CLEAR", "SEVERE_WINTER", "SANDSTORM", "HEAVY_RAIN"]
    new_weather = random.choice(weathers)
    db_query("UPDATE provinces SET weather_condition = ?", (new_weather,), commit=True)
    
    # Check Coups / Civil Wars
    rebel_users = db_query("SELECT user_id, commander_name FROM users WHERE approval < 20 AND in_civil_war = 0", fetchall=True)
    for u_id, name in rebel_users:
        db_query("UPDATE users SET in_civil_war = 1, rebel_power = 60 WHERE user_id = ?", (u_id,), commit=True)
        add_news(f"⚠️ **شورش و کودتای نظامی:** در کشور تحت فرماندهی {name} شورش مسلحانه رخ داد!")

    # Market Price Fluctuation
    db_query("UPDATE market SET price = price * 1.05 WHERE resource = 'oil'", commit=True)
    db_query("UPDATE market SET price = price * 0.98 WHERE resource = 'steel'", commit=True)

# ----------------------------------------------------
# 8. LAUNCHER
# ----------------------------------------------------
def main():
    init_sqlite()
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(job_war_resolver, interval=30, first=10)
        job_queue.run_repeating(job_coups_weather_and_market, interval=1800, first=30)

    print("WORLD WAR MASTER Bot is running successfully...")
    app.run_polling()

if __name__ == "__main__":
    main()
