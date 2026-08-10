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
# 1. LOGGING & DATABASE INITIALIZATION
# ----------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DB_NAME = "world_war.db"
AI_API_KEY = os.environ.get("OPENAI_API_KEY", None)

if OPENAI_AVAILABLE and AI_API_KEY:
    openai.api_key = AI_API_KEY

def init_sqlite():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Users / Commanders & Coup/Approval System
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
            in_civil_war INTEGER DEFAULT 0
        )
    ''')
    
    # Countries
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
            chokepoint_control INTEGER DEFAULT 0
        )
    ''')
    
    # Provinces (Radioactivity & Weather)
    c.execute('''
        CREATE TABLE IF NOT EXISTS provinces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT,
            name TEXT,
            population INTEGER,
            security INTEGER DEFAULT 100,
            infrastructure INTEGER DEFAULT 1,
            owner_id INTEGER,
            is_radioactive INTEGER DEFAULT 0,
            weather_condition TEXT DEFAULT 'CLEAR'
        )
    ''')
    
    # Armies & Cyber/Futuristic Tech
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
            hypersonic_missiles INTEGER DEFAULT 0
        )
    ''')
    
    # Wars & Tactics
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
    
    # Military Alliances
    c.execute('''
        CREATE TABLE IF NOT EXISTS alliances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            leader_id INTEGER
        )
    ''')

    # Generals
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
    
    # World News
    c.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Seed Default Countries if empty
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
            if code == "IRN":
                provs = ["تهران", "اصفهان", "خوزستان", "فارس", "کرمان", "گیلان", "مازندران"]
                for p in provs:
                    c.execute("INSERT INTO provinces (country_code, name, population) VALUES (?, ?, ?)",
                              (code, p, random.randint(1000000, 10000000)))

    conn.commit()
    conn.close()

# ----------------------------------------------------
# 2. HELPER FUNCTIONS
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
        "جناب فرمانده، طبق اطلاعات اطلاعاتی، تقویت سیستم دفاع سایبری و ذخایر ارزی پیشنهاد می‌شود.",
        "پیشنهاد می‌کنم پیش از هرگونه اقدام نظامی، با کشورهای عضو پیمان مشورت کنید.",
        "رضایت عمومی کاهش یافته است؛ بخشی از بودجه ارتش را به رفاه استان‌ها اختصاص دهید."
    ]
    return random.choice(fallback_responses)

# ----------------------------------------------------
# 3. COMMAND HANDLERS & 2-COLUMN MENUS
# ----------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    db_user = db_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    
    if not db_user:
        countries = db_query("SELECT code, name, flag FROM countries WHERE is_ai = 1", fetchall=True)
        # 2-Column Layout for Country Selection
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
            f"🌍 **به بازی WORLD WAR خوش آمدید، {user.first_name}!**\n\n"
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
    db_query("INSERT INTO generals (user_id, name, type) VALUES (?, ?, ?)", (user_id, "ژنرال اصلی", "LAND"), commit=True)
    db_query("UPDATE countries SET is_ai = 0 WHERE code = ?", (country_code,), commit=True)
    
    add_news(f"👑 فرمانده جدید {commander_name} رهبری کشور {country_code} را بر عهده گرفت!")
    
    await query.edit_message_text(f"✅ انتخاب شما ثبت شد! شما اکنون رهبر کشور {country_code} هستید.")
    await main_menu(update, context)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 2-Column Grid Layout matching user's requested style
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
            InlineKeyboardButton("🤝 دیپلماسی & پیمان‌ها", callback_data="menu_alliances"),
            InlineKeyboardButton("🕵️ عملیات سایبری", callback_data="menu_blackops")
        ],
        [
            InlineKeyboardButton("🛰️ دفاع موشکی & رادار", callback_data="menu_defense"),
            InlineKeyboardButton("💣 اتاق سلاح هسته‌ای", callback_data="menu_nuke")
        ],
        [
            InlineKeyboardButton("🛳️ بازار & تنگه‌ها", callback_data="menu_market"),
            InlineKeyboardButton("🧬 درخت فناوری", callback_data="menu_tech")
        ],
        [
            InlineKeyboardButton("🏆 جدول رتبه‌بندی", callback_data="menu_rankings"),
            InlineKeyboardButton("📰 اخبار سراسری جهان", callback_data="menu_news")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🌍 **ستاد فرماندهی کل نیروهای مسلح (WORLD WAR)**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ----------------------------------------------------
# 4. CALLBACK & SUBMENU HANDLERS
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
        u = db_query("SELECT commander_name, country_code, level, score, approval, in_civil_war, is_sanctioned FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        c = db_query("SELECT name, flag, money, oil, steel, food FROM countries WHERE code = ?", (u[1],), fetchone=True)
        
        status_str = "⚠️ درگیر شورش / کودتا" if u[5] else "🟢 باثبات"
        sanction_str = "🔴 تحریم سازمان ملل" if u[6] else "🟢 تجارت آزاد"

        text = (
            f"👤 **فرمانده:** {u[0]}\n"
            f"🚩 **کشور:** {c[1]} {c[0]}\n"
            f"⭐ **سطح:** {u[2]} | **امتیاز:** {u[3]}\n"
            f"📊 **رضایت عمومی:** {u[4]}% ({status_str})\n"
            f"📜 **وضعیت بین‌الملل:** {sanction_str}\n\n"
            f"💰 **خزانه:** ${c[2]:,.0f}\n"
            f"🛢 **نفت:** {c[3]:,.0f} | 🔩 **فولاد:** {c[4]:,.0f} | 🌾 **غذا:** {c[5]:,.0f}"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 2. AI ADVISOR ---
    elif data == "menu_ai_advisor":
        db_query("UPDATE users SET chat_state = 'TALKING_TO_AI' WHERE user_id = ?", (user_id,), commit=True)
        text = (
            "🧠 **اتاق مشاور هوش مصنوعی**\n\n"
            "سوال، چالش اقتصادی یا راهبرد نظامی خود را بنویسید و ارسال کنید:"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 3. ARMY STATS ---
    elif data == "menu_army":
        a = db_query("SELECT soldiers, tanks, artillery, spec_ops, fighters, drones, missiles_short, nukes FROM armies WHERE user_id = ?", (user_id,), fetchone=True)
        text = (
            f"📊 **آمار و تجهیزات ارتش:**\n\n"
            f"🪖 سرباز: {a[0]:,} | 🛡 تانک: {a[1]:,}\n"
            f"💥 توپخانه: {a[2]:,} | 🎯 نیروی ویژه: {a[3]:,}\n"
            f"✈️ جنگنده: {a[4]:,} | 🛸 پهپاد: {a[5]:,}\n"
            f"🚀 موشک: {a[6]:,} | ☢️ کلاهک هسته‌ای: {a[7]:,}"
        )
        keyboard = [
            [
                InlineKeyboardButton("🛒 خرید تجهیزات", callback_data="buy_army"),
                InlineKeyboardButton("🛠 ارتقای نیروی ویژه", callback_data="upgrade_army")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 4. TACTICAL WARFARE ---
    elif data == "menu_war":
        text = "⚔️ **اتاق نبرد و عملیات نظامی**\nنوع عملیات را انتخاب کنید:"
        keyboard = [
            [
                InlineKeyboardButton("🚀 حمله تاکتیکی", callback_data="attack_select_target"),
                InlineKeyboardButton("🎭 پرچم دروغین", callback_data="false_flag_attack")
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
            row.append(InlineKeyboardButton(f"{p_name} ({p_code}) {rad_tag}", callback_data=f"start_war_{p_id}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_war")])
        await query.edit_message_text("استان هدف را برای شروع نبرد ۱ ساعته انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("start_war_"):
        prov_id = int(data.split("_")[2])
        end_time = datetime.now() + timedelta(hours=1)
        db_query("INSERT INTO wars (attacker_id, defender_id, province_id, end_time) VALUES (?, 0, ?, ?)",
                 (user_id, prov_id, end_time), commit=True)
        
        add_news(f"🔥 نبرد برای تصرف استان شماره {prov_id} صادر شد!")
        keyboard = [
            [
                InlineKeyboardButton("🎯 تاکتیک گازانبری", callback_data=f"tactic_flank_{prov_id}"),
                InlineKeyboardButton("✈️ پشتیبانی هوایی", callback_data=f"tactic_air_{prov_id}")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text("✅ دستور حمله صادر شد! تاکتیک نبرد را مشخص کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    # --- 5. BLACK OPS & CYBER WARFARE ---
    elif data == "menu_blackops":
        text = "🕵️ **مرکز عملیات سایبری و جاسوسی**\nدستور مورد نظر را انتخاب کنید:"
        keyboard = [
            [
                InlineKeyboardButton("💻 هک رادار دشمن", callback_data="op_cyber_hack"),
                InlineKeyboardButton("🎯 ترور جنرال ارشد", callback_data="op_assassinate")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "op_cyber_hack":
        await query.edit_message_text("✅ حمله سایبری موفقیت‌آمیز بود! رادارهای دشمن ۱۰ دقیقه مختل شدند.")

    elif data == "op_assassinate":
        await query.edit_message_text("🎯 جوخه ترور اعزام شد! روحیه ارتش دشمن ۱۵٪ کاهش یافت.")

    # --- 6. SATELLITE & DEFENSE ---
    elif data == "menu_defense":
        text = "🛰️ **سامانه پدافند موشکی و ماهواره**\nگزینه مورد نظر را انتخاب کنید:"
        keyboard = [
            [
                InlineKeyboardButton("🛰️ پرتاب ماهواره", callback_data="buy_satellite"),
                InlineKeyboardButton("🛡️ ساخت پدافند S-400", callback_data="buy_s400")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 7. NUCLEAR ROOM ---
    elif data == "menu_nuke":
        a = db_query("SELECT nukes FROM armies WHERE user_id = ?", (user_id,), fetchone=True)
        nuke_count = a[0] if a else 0
        text = (
            f"💣 **اتاق فرماندهی سلاح‌های هسته‌ای**\n\n"
            f"کلاهک‌های موجود: **{nuke_count}**\n"
            "⚠️ شلیک موجب آلودگی ۴۸ ساعته و تحریم بین‌المللی می‌شود."
        )
        keyboard = [
            [
                InlineKeyboardButton("☢️ شلیک به دشمن", callback_data="launch_nuke_select"),
                InlineKeyboardButton("🏭 ساخت کلاهک جدید", callback_data="build_nuke")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 8. MARKET & CHOKEPOINTS ---
    elif data == "menu_market":
        text = "🛳️ **بازار جهانی و تنگه‌های استراتژیک**\nیک بخش را انتخاب کنید:"
        keyboard = [
            [
                InlineKeyboardButton("⚓ تصرف تنگه هرمز", callback_data="claim_chokepoint"),
                InlineKeyboardButton("📈 تجارت نفت & فولاد", callback_data="open_market")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 9. TECH TREE ---
    elif data == "menu_tech":
        u = db_query("SELECT tech_era FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        era = u[0] if u else "CLASSIC"
        text = f"🧬 **درخت فناوری کشوری**\n\nعصر فعلی: **{era}**"
        keyboard = [
            [
                InlineKeyboardButton("🚀 ارتقا به عصر بعد", callback_data="upgrade_era"),
                InlineKeyboardButton("🔬 آنلاک پهپاد AI", callback_data="unlock_drone")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 10. ALLIANCES & UN ---
    elif data == "menu_alliances":
        text = "🤝 **دیپلماسی، پیمان‌ها و سازمان ملل**\nگزینه مورد نظر را انتخاب کنید:"
        keyboard = [
            [
                InlineKeyboardButton("🤝 ایجاد پیمان نظامی", callback_data="create_alliance"),
                InlineKeyboardButton("🇺🇳 رأی‌گیری سازمان ملل", callback_data="un_vote")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 11. NEWS ---
    elif data == "menu_news":
        news_items = db_query("SELECT content, timestamp FROM news ORDER BY id DESC LIMIT 5", fetchall=True)
        news_str = "\n".join([f"• [{x[1]}] {x[0]}" for x in news_items]) if news_items else "خبری ثبت نشده است."
        text = f"📰 **خبرگزاری سراسری جهان**\n\n{news_str}"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 12. RANKINGS ---
    elif data == "menu_rankings":
        top_users = db_query("SELECT commander_name, score FROM users ORDER BY score DESC LIMIT 5", fetchall=True)
        rank_str = "\n".join([f"{i+1}. {x[0]} - {x[1]} امتیاز" for i, x in enumerate(top_users)])
        text = f"🏆 **جدول رتبه‌بندی ۵ قدرت برتر:**\n\n{rank_str}"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ----------------------------------------------------
# 5. CHAT TEXT HANDLER FOR AI INTERACTION
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
        
        system_instruction = "شما یک مشاور ارشد استراتژیک در یک بازی جنگ جهانی هستید. کوتاه، حماسی و تاکتیکی پاسخ دهید."
        ai_reply = await generate_ai_response(context_prompt, system_instruction)
        
        keyboard = [[InlineKeyboardButton("🔙 خروج از چت مشاور", callback_data="menu_main")]]
        await update.message.reply_text(f"🧠 **پاسخ مشاور:**\n\n{ai_reply}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ----------------------------------------------------
# 6. AUTOMATED JOBS (WAR RESOLUTION & EVENTS)
# ----------------------------------------------------
async def job_war_resolver(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    active_wars = db_query("SELECT id, attacker_id, defender_id, province_id FROM wars WHERE status = 'ACTIVE' AND end_time <= ?", (now,), fetchall=True)
    
    for w_id, att_id, def_id, prov_id in active_wars:
        win = random.choice([True, False])
        if win:
            db_query("UPDATE wars SET status = 'ATTACKER_WON' WHERE id = ?", (w_id,), commit=True)
            db_query("UPDATE users SET score = score + 100 WHERE user_id = ?", (att_id,), commit=True)
            
            news_prompt = f"یک خبر حماسی و کوتاه درباره فتح استان شماره {prov_id} توسط نیروهای فرمانده {att_id} بنویس."
            ai_news = await generate_ai_response(news_prompt, "شما خبرنگار جنگی هستید.")
            add_news(f"🏆 {ai_news}")
        else:
            db_query("UPDATE wars SET status = 'DEFENDER_WON' WHERE id = ?", (w_id,), commit=True)
            add_news(f"💀 شکست! حمله به استان شماره {prov_id} ناکام ماند.")

async def job_coups_and_weather(context: ContextTypes.DEFAULT_TYPE):
    weathers = ["CLEAR", "SEVERE_WINTER", "SANDSTORM", "HEAVY_RAIN"]
    new_weather = random.choice(weathers)
    db_query("UPDATE provinces SET weather_condition = ?", (new_weather,), commit=True)
    
    rebel_users = db_query("SELECT user_id, commander_name FROM users WHERE approval < 20 AND in_civil_war = 0", fetchall=True)
    for u_id, name in rebel_users:
        db_query("UPDATE users SET in_civil_war = 1 WHERE user_id = ?", (u_id,), commit=True)
        add_news(f"⚠️ **شورش و کودتا:** در کشور تحت فرماندهی {name} کودتا رخ داد!")

# ----------------------------------------------------
# 7. MAIN APPLICATION LAUNCHER
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
        job_queue.run_repeating(job_coups_and_weather, interval=3600, first=60)

    print("WORLD WAR Bot is running with 2-Column Inline Keyboard Layout...")
    app.run_polling()

if __name__ == "__main__":
    main()
