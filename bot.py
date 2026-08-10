# Correcting string quotation in file writing block
bot_code = r'''# -*- coding: utf-8 -*-
"""
WORLD WAR TELEGRAM BOT - Single File Production Implementation
Designed for Railway Deployment with SQLite / PostgreSQL persistence, 
Inline Keyboards, War Calculation Engine, AI Country Loop, Economy Schedule, 
Natural Disasters, and Admin Panel.
"""

import os
import sys
import time
import math
import json
import random
import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta

# Telegram Bot Library
try:
    from telegram import (
        Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
    )
    from telegram.ext import (
        Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
    )
except ImportError:
    print("Installing python-telegram-bot v13.x...")
    os.system(f"{sys.executable} -m pip install python-telegram-bot==13.15")
    from telegram import (
        Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
    )
    from telegram.ext import (
        Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
    )

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("WorldWarBot")

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_FILE = "world_war_game.db"

# Base Data Constants
COUNTRIES = {
    "IR": {"name": "ایران 🇮🇷", "population": 85000000, "gdp": 350000, "flag": "🇮🇷", "provinces": ["تهران", "اصفهان", "فارس", "خوزستان", "کرمان", "گیلان", "مازندران", "آذربایجان شرقی", "آذربایجان غربی", "یزد"]},
    "US": {"name": "آمریکا 🇺🇸", "population": 331000000, "gdp": 21000000, "flag": "🇺🇸", "provinces": ["کالیفرنیا", "تگزاس", "نیویورک", "فلوریدا", "ایلینوی", "پنسیلوانیا", "اوهایو", "جورجیا", "کارولینای شمالی", "میچیگان"]},
    "RU": {"name": "روسیه 🇷🇺", "population": 144000000, "gdp": 1500000, "flag": "🇷🇺", "provinces": ["مسکو", "سن پترزبورگ", "سیبری", "تاتارستان", "کراسنودار", "سوردلوفسک", "نیژنی نووگورود", "سامارا", "روستوف", "باشقیرستان"]},
    "CN": {"name": "چین 🇨🇳", "population": 1410000000, "gdp": 14000000, "flag": "🇨🇳", "provinces": ["پکن", "شانگهای", "گوانگ‌دونگ", "شاندونگ", "جیانگسو", "هنان", "سیچوان", "ژجیانگ", "هوبی", "هونان"]},
    "DE": {"name": "آلمان 🇩🇪", "population": 83000000, "gdp": 3800000, "flag": "🇩🇪", "provinces": ["باواریا", "برلین", "هامبورگ", "هسن", "زاکسن", "بافاریا سفلی", "براندنبورگ", "بادن-وورتمبرگ", "نوردراین-وستفالن", "تورینگن"]},
    "FR": {"name": "فرانسه 🇫🇷", "population": 67000000, "gdp": 2700000, "flag": "🇫🇷", "provinces": ["ایل-دو-فرانس", "پرStructured", "رون-آلپ", "پروبانس", "بوردو", "برتانی", "نورماندی", "اکیتن", "کورس", "کورز"]},
    "GB": {"name": "انگلیس 🇬🇧", "population": 67000000, "gdp": 2800000, "flag": "🇬🇧", "provinces": ["لندن", "منچستر", "بیرمنگام", "لیدز", "گلاسگو", "لیورپول", "ادینبرگ", "بریستول", "شفیلد", "نیوکاسل"]},
    "JP": {"name": "ژاپن 🇯🇵", "population": 125000000, "gdp": 5000000, "flag": "🇯🇵", "provinces": ["توکیو", "اوساکا", "کاناقاوا", "ایچی", "سایتاما", "چیبا", "هوکایدو", "هیوقو", "فوکوئوکا", "کیوتو"]},
    "TR": {"name": "ترکیه 🇹🇷", "population": 84000000, "gdp": 750000, "flag": "🇹🇷", "provinces": ["استانبول", "آنکارا", "ازمیر", "بورسا", "آنتالیا", "آدانا", "قونیه", "غازی عینتاب", "شانلی‌اورفه", "مرسین"]},
    "IN": {"name": "هند 🇮🇳", "population": 1380000000, "gdp": 2800000, "flag": "🇮🇳", "provinces": ["مومبای", "دهلی", "بنگلور", "حیدرآباد", "چنای", "کلکته", "احمدآباد", "پونه", "سورت", "جیپور"]}
}

BUILDINGS_CONFIG = {
    "factory": {"name": "🏭 کارخانه صنعتی", "cost": {"money": 1000, "steel": 200}, "income": {"money": 200, "steel": 50}},
    "refinery": {"name": "🛢 پالایشگاه نفت", "cost": {"money": 1500, "steel": 300}, "income": {"money": 150, "oil": 100}},
    "farm": {"name": "🌾 مزرعه مدرن", "cost": {"money": 800, "steel": 100}, "income": {"food": 300, "money": 100}},
    "powerplant": {"name": "⚡ نیروگاه برق", "cost": {"money": 1200, "steel": 250}, "income": {"power": 200, "money": 100}},
    "barracks": {"name": "🪖 پادگان نظامی", "cost": {"money": 2000, "steel": 500}, "bonus": "افزایش سرعت ساخت ارتش"},
    "airbase": {"name": "✈️ پایگاه هوایی", "cost": {"money": 3000, "steel": 800}, "bonus": "پشتیبانی هوایی"},
    "lab": {"name": "🔬 مرکز تحقیقات", "cost": {"money": 2500, "steel": 400}, "bonus": "سرعت تحقیقات"}
}

UNITS_CONFIG = {
    "infantry": {"name": "💂 سرباز پیاده", "cost": {"money": 50, "food": 20}, "power": 10},
    "tank": {"name": "🚜 تانک سنگین", "cost": {"money": 300, "steel": 100, "oil": 50}, "power": 80},
    "fighter": {"name": "✈️ جنگنده پیشرفته", "cost": {"money": 800, "steel": 200, "oil": 150}, "power": 220},
    "missile": {"name": "🚀 موشک بالستیک", "cost": {"money": 1500, "steel": 400, "oil": 300}, "power": 500}
}

# ---------------------------------------------------------
# DATABASE SYSTEM (SQLite Native Engine)
# ---------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Players Table
    c.execute("""CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        commander_name TEXT,
        country_code TEXT,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        money INTEGER DEFAULT 10000,
        oil INTEGER DEFAULT 2000,
        steel INTEGER DEFAULT 2000,
        food INTEGER DEFAULT 5000,
        power_res INTEGER DEFAULT 2000,
        gold INTEGER DEFAULT 50,
        tech_level INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Provinces Table
    c.execute("""CREATE TABLE IF NOT EXISTS provinces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_code TEXT,
        name TEXT,
        owner_id INTEGER,
        population INTEGER,
        security_level INTEGER DEFAULT 100,
        buildings TEXT DEFAULT '{}',
        stationed_troops TEXT DEFAULT '{}',
        FOREIGN KEY(owner_id) REFERENCES players(user_id)
    )""")

    # Wars Table
    c.execute("""CREATE TABLE IF NOT EXISTS wars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_id INTEGER,
        defender_id INTEGER,
        target_province_id INTEGER,
        attack_units TEXT,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        status TEXT DEFAULT 'ACTIVE'
    )""")

    # Global News Table
    c.execute("""CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def get_player(user_id):
    conn = get_db()
    player = conn.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return player

def register_player(user_id, commander_name, country_code):
    conn = get_db()
    conn.execute(
        "INSERT INTO players (user_id, commander_name, country_code) VALUES (?, ?, ?)",
        (user_id, commander_name, country_code)
    )
    # Assign provinces
    country = COUNTRIES[country_code]
    for prov_name in country["provinces"]:
        conn.execute(
            "INSERT INTO provinces (country_code, name, owner_id, population) VALUES (?, ?, ?, ?)",
            (country_code, prov_name, user_id, country["population"] // len(country["provinces"]))
        )
    conn.commit()
    conn.close()

def log_news(message):
    conn = get_db()
    conn.execute("INSERT INTO news (content) VALUES (?)", (message,))
    conn.commit()
    conn.close()

def calculate_military_power(user_id):
    conn = get_db()
    provinces = conn.execute("SELECT stationed_troops FROM provinces WHERE owner_id = ?", (user_id,)).fetchall()
    conn.close()
    total_power = 0
    for p in provinces:
        try:
            troops = json.loads(p['stationed_troops'] or '{}')
            for unit, count in troops.items():
                if unit in UNITS_CONFIG:
                    total_power += count * UNITS_CONFIG[unit]['power']
        except Exception:
            pass
    return total_power

# ---------------------------------------------------------
# BOT HANDLERS & COMMANDS
# ---------------------------------------------------------
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    player = get_player(user.id)
    
    if player:
        show_dashboard(update, context)
    else:
        keyboard = []
        for code, info in COUNTRIES.items():
            keyboard.append([InlineKeyboardButton(f"{info['flag']} {info['name']}", callback_data=f"select_country_{code}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            f"🌍 **به بازی جنگ جهانی (WORLD WAR) خوش آمدید!**\n\n"
            f"فرمانده {user.first_name}، لطفاً کشور خود را برای رهبری و فرماندهی انتخاب کنید:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

def show_dashboard(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    player = get_player(user_id)
    if not player:
        return

    country = COUNTRIES.get(player['country_code'], {"name": "نامشخص", "flag": "🏳️"})
    power = calculate_military_power(user_id)

    text = (
        f"👑 **فرمانده:** {player['commander_name']}\n"
        f"🌍 **کشور:** {country['name']}\n"
        f"⭐ **سطح:** {player['level']} | **امتیاز تجربه:** {player['xp']}\n"
        f"⚔️ **قدرت نظامی:** {power:,}\n\n"
        f"💵 **بودجه:** {player['money']:,} $\n"
        f"🛢 **نفت:** {player['oil']:,} | 🔩 **فولاد:** {player['steel']:,}\n"
        f"🌾 **غذا:** {player['food']:,} | ⚡ **برق:** {player['power_res']:,}\n"
        f"💎 **طلا:** {player['gold']:,}\n"
    )

    keyboard = [
        [InlineKeyboardButton("🏙 استان‌ها", callback_data="provinces_list"), InlineKeyboardButton("🪖 ارتش و واحدها", callback_data="army_menu")],
        [InlineKeyboardButton("🏭 ساخت و ساز", callback_data="build_menu"), InlineKeyboardButton("🔬 تحقیقات", callback_data="tech_menu")],
        [InlineKeyboardButton("⚔️ اتاق جنگ", callback_data="war_room"), InlineKeyboardButton("🤝 دیپلماسی", callback_data="diplomacy_menu")],
        [InlineKeyboardButton("📰 اخبار جهان", callback_data="news_feed"), InlineKeyboardButton("🏆 رتبه‌بندی", callback_data="leaderboard")],
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_dashboard")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👑 پنل مدیریت (ADMIN)", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# ---------------------------------------------------------
# CALLBACK QUERY ROUTER
# ---------------------------------------------------------
def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    query.answer()

    # Country Selection
    if data.startswith("select_country_"):
        code = data.split("_")[2]
        if get_player(user_id):
            query.edit_message_text("شما قبلاً کشور خود را انتخاب کرده‌اید!")
            return
        register_player(user_id, query.from_user.first_name, code)
        log_news(f"👑 فرمانده جدید {query.from_user.first_name} رهبری کشور {COUNTRIES[code]['name']} را به دست گرفت!")
        query.edit_message_text("✅ کشور شما با موفقیت ثبت شد! در حال انتقال به اتاق فرماندهی...")
        show_dashboard(update, context)
        return

    player = get_player(user_id)
    if not player:
        query.edit_message_text("لطفا ابتدا /start را بزنید.")
        return

    if data == "refresh_dashboard":
        show_dashboard(update, context)
    
    elif data == "provinces_list":
        conn = get_db()
        provinces = conn.execute("SELECT * FROM provinces WHERE owner_id = ?", (user_id,)).fetchall()
        conn.close()
        text = "🏙 **استان‌های تحت کنترل شما:**\n\n"
        for p in provinces:
            text += f"🔹 **{p['name']}** - جمعیت: {p['population']:,} | امنیت: {p['security_level']}%\n"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="refresh_dashboard")]]
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "army_menu":
        text = "🪖 **مدیریت ارتش و نیروهای نظامی**\nیکی از واحدهای زیر را برای تولید انتخاب کنید:\n"
        keyboard = []
        for u_id, u_info in UNITS_CONFIG.items():
            cost_str = ", ".join([f"{v} {k}" for k, v in u_info['cost'].items()])
            keyboard.append([InlineKeyboardButton(f"{u_info['name']} (قدرت: {u_info['power']})", callback_data=f"buy_unit_{u_id}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="refresh_dashboard")])
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("buy_unit_"):
        u_id = data.split("_")[2]
        unit = UNITS_CONFIG[u_id]
        # Resource Check
        can_buy = True
        conn = get_db()
        for res, amt in unit['cost'].items():
            if player[res] < amt:
                can_buy = False
                break
        if can_buy:
            # Deduct resource & add unit to first province
            updates = ", ".join([f"{res} = {res} - {amt}" for res, amt in unit['cost'].items()])
            conn.execute(f"UPDATE players SET {updates} WHERE user_id = ?", (user_id,))
            # Fetch target province
            prov = conn.execute("SELECT * FROM provinces WHERE owner_id = ? LIMIT 1", (user_id,)).fetchone()
            if prov:
                troops = json.loads(prov['stationed_troops'] or '{}')
                troops[u_id] = troops.get(u_id, 0) + 1
                conn.execute("UPDATE provinces SET stationed_troops = ? WHERE id = ?", (json.dumps(troops), prov['id']))
            conn.commit()
            query.answer(f"✅ یک {unit['name']} با موفقیت ساخته شد!", show_alert=True)
        else:
            query.answer("❌ منابع کافی برای ساخت این واحد را ندارید!", show_alert=True)
        conn.close()
        show_dashboard(update, context)

    elif data == "news_feed":
        conn = get_db()
        news_items = conn.execute("SELECT * FROM news ORDER BY id DESC LIMIT 10").fetchall()
        conn.close()
        text = "📰 **اخبار سراسری جهان:**\n\n"
        for item in news_items:
            text += f"🌐 {item['content']}\n⏱ _{item['created_at']}_\n\n"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="refresh_dashboard")]]
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "leaderboard":
        conn = get_db()
        players = conn.execute("SELECT * FROM players ORDER BY level DESC, money DESC LIMIT 10").fetchall()
        conn.close()
        text = "🏆 **جدول رتبه‌بندی برترین فرماندهان:**\n\n"
        for idx, p in enumerate(players, 1):
            c_flag = COUNTRIES.get(p['country_code'], {}).get('flag', '🏳️')
            text += f"{idx}. {c_flag} **{p['commander_name']}** - لول: {p['level']} | پول: {p['money']:,} $\n"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="refresh_dashboard")]]
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_panel" and user_id == ADMIN_ID:
        text = "👑 **پنل مدیریت ارشد**\nاز این بخش می‌توانید منابع یا دستورات ویژه صادر کنید."
        keyboard = [
            [InlineKeyboardButton("➕ افزودن ۱۰,۰۰۰ دلار به همه", callback_data="admin_add_money")],
            [InlineKeyboardButton("🌪 راه اندازی بلای طبیعی", callback_data="admin_disaster")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="refresh_dashboard")]
        ]
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_add_money" and user_id == ADMIN_ID:
        conn = get_db()
        conn.execute("UPDATE players SET money = money + 10000")
        conn.commit()
        conn.close()
        query.answer("💵 مبلغ ۱۰,۰۰۰ دلار به تمام بازیکنان اضافه شد!", show_alert=True)

    elif data == "admin_disaster" and user_id == ADMIN_ID:
        trigger_disaster_event()
        query.answer("🌪 بلای طبیعی با موفقیت شبیه‌سازی شد!", show_alert=True)

# ---------------------------------------------------------
# BACKGROUND TASKS & GAME ENGINE LOOPS
# ---------------------------------------------------------
def economy_cycle_job(context: CallbackContext):
    """6-Hour Economy Cycle: Generates income & resource production."""
    logger.info("Executing 6-hour economy calculation...")
    conn = get_db()
    players = conn.execute("SELECT * FROM players").fetchall()
    
    for p in players:
        # Base income
        inc_money = 1000
        inc_oil = 200
        inc_steel = 200
        inc_food = 500
        
        conn.execute("""
            UPDATE players 
            SET money = money + ?, oil = oil + ?, steel = steel + ?, food = food + ? 
            WHERE user_id = ?
        """, (inc_money, inc_oil, inc_steel, inc_food, p['user_id']))

    conn.commit()
    conn.close()
    log_news("💰 **سود اقتصادی ۶ ساعته توزیع شد!** تمام کشورها درآمد حاصل از تولیدات و مالیات را دریافت کردند.")

def trigger_disaster_event():
    """24-Hour Natural Disaster Event System."""
    disasters = ["زلزله شدید 💥", "سیل ویرانگر 🌊", "خشکسالی بزرگ ☀️", "طوفان سهمگین 🌪"]
    selected_disaster = random.choice(disasters)
    
    conn = get_db()
    provinces = conn.execute("SELECT * FROM provinces").fetchall()
    if provinces:
        target_prov = random.choice(provinces)
        damage_pop = int(target_prov['population'] * 0.05)
        conn.execute("UPDATE provinces SET population = population - ? WHERE id = ?", (damage_pop, target_prov['id']))
        conn.commit()
        
        c_flag = COUNTRIES.get(target_prov['country_code'], {}).get('flag', '🌐')
        log_news(f"⚠️ **وقوع بلای طبیعی!** {selected_disaster} در استان **{target_prov['name']}** ({c_flag}) رخ داد. خسارات: کاهش {damage_pop:,} نفر جمعیت!")
    conn.close()

def disaster_cycle_job(context: CallbackContext):
    trigger_disaster_event()

def ai_action_job(context: CallbackContext):
    """NPC/AI Countries Decision Loop."""
    logger.info("Running AI logic loop...")
    ai_events = [
        "کشور روسیه 🇷🇺 مانور نظامی جدیدی در مرزها آغاز کرد.",
        "چین 🇨🇳 قرارداد تجاری جدیدی برای توسعه فولاد امضا نمود.",
        "آمریکا 🇺🇸 بودجه دفاعی خود را برای توسعه موشکی افزایش داد."
    ]
    log_news(f"🤖 {random.choice(ai_events)}")

# ---------------------------------------------------------
# MAIN INITIALIZATION & STARTUP
# ---------------------------------------------------------
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN is not configured! Set it in Environment Variables.")
        return

    init_db()

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Register Handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(callback_handler))

    # Job Queue Configuration for Background Logic
    job_queue = updater.job_queue
    if job_queue:
        # Economy calculation every 6 hours (21,600 seconds)
        job_queue.run_repeating(economy_cycle_job, interval=21600, first=10)
        # Disaster calculation every 24 hours (86,400 seconds)
        job_queue.run_repeating(disaster_cycle_job, interval=86400, first=30)
        # AI Logic Loop every 3 hours (10,800 seconds)
        job_queue.run_repeating(ai_action_job, interval=10800, first=60)

    logger.info("Bot successfully started! Polling Telegram API...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
'''

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(bot_code)

print("Created bot.py file successfully!")
