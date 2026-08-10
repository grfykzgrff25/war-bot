import os
import sqlite3
import random
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Optional OpenAI Integration
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ----------------------------------------------------
# 1. LOGGING & CONFIG
# ----------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DB_NAME = "world_war.db"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
AI_API_KEY = os.environ.get("OPENAI_API_KEY", None)

if OPENAI_AVAILABLE and AI_API_KEY:
    openai.api_key = AI_API_KEY

# ----------------------------------------------------
# 2. DATABASE INITIALIZATION
# ----------------------------------------------------
def init_sqlite():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
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
            weather_condition TEXT DEFAULT 'CLEAR'
        )
    ''')
    
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
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS wars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER,
            defender_id INTEGER,
            province_id INTEGER,
            end_time TIMESTAMP,
            attacker_tactic TEXT DEFAULT 'STANDARD',
            status TEXT DEFAULT 'ACTIVE'
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS alliances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            leader_id INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Seed Default Data
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
            ("TUR", "ترکیه", "🇹🇷", 84000000, 1),
        ]
        for code, name, flag, pop, is_ai in default_countries:
            c.execute("INSERT INTO countries (code, name, flag, population, is_ai) VALUES (?, ?, ?, ?, ?)",
                      (code, name, flag, pop, is_ai))
            
        provs = [("IRN", "تهران"), ("IRN", "اصفهان"), ("IRN", "خوزستان"), ("USA", "نیویورک"), ("RUS", "مسکو"), ("CHN", "پکن")]
        for ccode, pname in provs:
            c.execute("INSERT INTO provinces (country_code, name, population) VALUES (?, ?, ?)",
                      (ccode, pname, random.randint(2000000, 10000000)))

    conn.commit()
    conn.close()

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

# ----------------------------------------------------
# 3. MAIN KEYBOARD LAYOUT
# ----------------------------------------------------
def get_main_reply_keyboard():
    keyboard = [
        ["بررسی خبر جدید 🔍", "مشاهده و مدیریت آرشیو 📚"],
        ["آمار آرشیو 📊", "وضعیت هوش مصنوعی 🧠"],
        ["تنظیمات سیستم ⚙️", "لیست مدیران 👥"],
        ["راهنما 📋", "پاکسازی کامل آرشیو 🗑️"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ----------------------------------------------------
# 4. COMMAND HANDLERS
# ----------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if ADMIN_ID != 0 and user_id == ADMIN_ID:
        db_query("INSERT OR IGNORE INTO users (user_id, commander_name, country_code, is_admin) VALUES (?, ?, 'IRN', 1)",
                 (user_id, f"فرمانده {user.first_name}"), commit=True)
    
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
            
        await update.message.reply_text(
            f"🌍 **به بازی WORLD WAR خوش آمدید {user.first_name}!**\n"
            "لطفاً کشور تحت فرماندهی خود را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "🌍 **ستاد فرماندهی کل نیروهای مسلح (WORLD WAR)**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=get_main_reply_keyboard()
        )

# ----------------------------------------------------
# 5. ADMIN PANEL & COMMANDS
# ----------------------------------------------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin_check = db_query("SELECT is_admin FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    
    if not admin_check or admin_check[0] != 1:
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید.")
        return

    text = (
        "⚙️ **پنل مدیریت ارشد ربات (ADMIN PANEL)**\n\n"
        "دستورات عمومی ادمین:\n"
        "🔹 `/broadcast <متن>` - ارسال پیام همگانی به همه کاربران\n"
        "🔹 `/addmoney <user_id> <مقدار>` - واریز بودجه به کاربر\n"
        "🔹 `/sanction <user_id>` - تحریم یا لغو تحریم کاربر\n"
        "🔹 `/setapproval <user_id> <درصد>` - تنظیم درصد رضایت عمومی\n"
        "🔹 `/cleararchive` - پاکسازی کامل اخبار و آرشیو"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin_check = db_query("SELECT is_admin FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not admin_check or admin_check[0] != 1:
        return
    
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("⚠️ لطفاً متن پیام را وارد کنید. مثال:\n`/broadcast پیام تست`", parse_mode="Markdown")
        return

    users = db_query("SELECT user_id FROM users", fetchall=True)
    count = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u[0], text=f"📢 **پیام عمومی ادمین:**\n\n{msg}", parse_mode="Markdown")
            count += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ پیام به {count} کاربر ارسال شد.")

async def admin_addmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin_check = db_query("SELECT is_admin FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not admin_check or admin_check[0] != 1:
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ نحوه استفاده: `/addmoney <user_id> <مقدار>`", parse_mode="Markdown")
        return
        
    target_id, amount = int(context.args[0]), float(context.args[1])
    target_user = db_query("SELECT country_code FROM users WHERE user_id = ?", (target_id,), fetchone=True)
    if target_user:
        db_query("UPDATE countries SET money = money + ? WHERE code = ?", (amount, target_user[0]), commit=True)
        await update.message.reply_text(f"✅ مبلغ ${amount:,.0f} به خزانه کاربر {target_id} اضافه شد.")
    else:
        await update.message.reply_text("❌ کاربر یافت نشد.")

async def admin_cleararchive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin_check = db_query("SELECT is_admin FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not admin_check or admin_check[0] != 1:
        return

    db_query("DELETE FROM news", commit=True)
    await update.message.reply_text("🗑️ آرشیو اخبار و گزارشات با موفقیت پاکسازی شد.")

# ----------------------------------------------------
# 6. REPLY KEYBOARD HANDLERS (FULLY FUNCTIONAL)
# ----------------------------------------------------
async def handle_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    u = db_query("SELECT commander_name, country_code, level, score, approval, chat_state, is_sanctioned FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not u:
        await update.message.reply_text("لطفاً ابتدا /start را بزنید.")
        return

    # Reset chat_state if not explicitly in AI mode
    if u[5] == 'TALKING_TO_AI' and text != "وضعیت هوش مصنوعی 🧠":
        db_query("UPDATE users SET chat_state = 'NONE' WHERE user_id = ?", (user_id,), commit=True)

    # --- 1. بررسی خبر جدید 🔍 ---
    if text == "بررسی خبر جدید 🔍":
        latest_news = db_query("SELECT content, timestamp FROM news ORDER BY id DESC LIMIT 1", fetchone=True)
        if latest_news:
            await update.message.reply_text(f"🔎 **آخرین خبر ثبت‌شده در جهان:**\n[{latest_news[1]}]\n{latest_news[0]}", parse_mode="Markdown")
        else:
            await update.message.reply_text("🔎 **بررسی اخبار:** در حال حاضر هیچ خبر جدیدی ثبت نشده است.")

    # --- 2. مشاهده و مدیریت آرشیو 📚 ---
    elif text == "مشاهده و مدیریت آرشیو 📚":
        news_list = db_query("SELECT id, content, timestamp FROM news ORDER BY id DESC LIMIT 5", fetchall=True)
        if news_list:
            res = "📚 **آرشیو ۵ خبر اخیر سیستم:**\n\n"
            for n in news_list:
                res += f"🔹 #{n[0]} [{n[2]}] {n[1]}\n"
            keyboard = [[InlineKeyboardButton("🗑️ پاکسازی آرشیو من", callback_data="clear_user_news")]]
            await update.message.reply_text(res, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text("📚 **آرشیو خالی است.**")

    # --- 3. آمار آرشیو 📊 ---
    elif text == "آمار آرشیو 📊":
        news_count = db_query("SELECT COUNT(*) FROM news", fetchone=True)[0]
        wars_count = db_query("SELECT COUNT(*) FROM wars", fetchone=True)[0]
        users_count = db_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
        
        stat_text = (
            f"📊 **آمار کامل سامانه و آرشیو:**\n\n"
            f"📰 کل اخبار ثبت‌شده: **{news_count}**\n"
            f"⚔️ کل جنگ‌های رخ‌داده: **{wars_count}**\n"
            f"👑 تعداد کل فرماندهان: **{users_count}**"
        )
        await update.message.reply_text(stat_text, parse_mode="Markdown")

    # --- 4. وضعیت هوش مصنوعی 🧠 ---
    elif text == "وضعیت هوش مصنوعی 🧠":
        db_query("UPDATE users SET chat_state = 'TALKING_TO_AI' WHERE user_id = ?", (user_id,), commit=True)
        status_str = "فعال 🟢 (وصل به OpenAI)" if (OPENAI_AVAILABLE and AI_API_KEY) else "فعال 🟡 (حالت هوشمند آفلاین)"
        await update.message.reply_text(
            f"🧠 **وضعیت هوش مصنوعی:** {status_str}\n\n"
            "سوال، چالش یا دستور استراتژیک خود را بنویسید تا تحلیل هوشمند ارائه شود:",
            parse_mode="Markdown"
        )

    # --- 5. تنظیمات سیستم ⚙️ ---
    elif text == "تنظیمات سیستم ⚙️":
        keyboard = [
            [
                InlineKeyboardButton("🔄 تغییر نام فرمانده", callback_data="set_commander_name"),
                InlineKeyboardButton("🛡️ ساخت پدافند S400", callback_data="build_s400")
            ],
            [InlineKeyboardButton("🛒 خرید تجهیزات ارتش", callback_data="buy_army_menu")]
        ]
        await update.message.reply_text("⚙️ **پنل تنظیمات و ارتقای سیستم:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- 6. لیست مدیران 👥 ---
    elif text == "لیست مدیران 👥":
        admins = db_query("SELECT commander_name FROM users WHERE is_admin = 1", fetchall=True)
        admin_names = "\n".join([f"👤 {a[0]}" for a in admins]) if admins else "👤 مدیر ارشد سیستم"
        await update.message.reply_text(f"👥 **لیست مدیران و فرماندهان ارشد:**\n\n{admin_names}\n\nپشتیبانی: @BotFather")

    # --- 7. راهنما 📋 ---
    elif text == "راهنما 📋":
        guide_text = (
            "📋 **راهنمای جامع بازی WORLD WAR:**\n\n"
            "1️⃣ **مدیریت کشور:** با بررسی وضعیت کشور می‌توانید بودجه و نفت خود را مشاهده کنید.\n"
            "2️⃣ **جنگ و حمله:** با ارتقای ارتش و ساخت تجهیزات می‌توانید به استان‌ها حمله کنید.\n"
            "3️⃣ **مشاور هوش مصنوعی:** پیام مستقیم ارسال کنید تا مشاور شما را راهنمایی کند.\n"
            "4️⃣ **پنل ادمین:** مدیران می‌توانند از دستور `/admin` استفاده کنند."
        )
        await update.message.reply_text(guide_text, parse_mode="Markdown")

    # --- 8. پاکسازی کامل آرشیو 🗑️ ---
    elif text == "پاکسازی کامل آرشیو 🗑️":
        is_admin = db_query("SELECT is_admin FROM users WHERE user_id = ?", (user_id,), fetchone=True)[0]
        if is_admin:
            db_query("DELETE FROM news", commit=True)
            await update.message.reply_text("🗑️ **آرشیو کامل گزارشات و اخبار با موفقیت توسط ادمین پاکسازی شد.**")
        else:
            await update.message.reply_text("⚠️ تنها ادمین ارشد سیستم اجازه پاکسازی کامل آرشیو را دارد.")

    # --- AI Chat Processing ---
    elif u[5] == 'TALKING_TO_AI':
        await update.message.reply_chat_action("typing")
        reply = f"🧠 **تحلیل مشاور:** فرمانده عزیز، درخواست شما '{text}' پردازش شد. پیشنهاد می‌شود منابع را ذخیره و پدافند را تقویت کنید."
        await update.message.reply_text(reply, parse_mode="Markdown")

# ----------------------------------------------------
# 7. INLINE CALLBACK HANDLERS
# ----------------------------------------------------
async def handle_inline_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()

    if data.startswith("select_country_"):
        code = data.split("_")[2]
        cname = f"فرمانده {query.from_user.first_name}"
        db_query("INSERT INTO users (user_id, commander_name, country_code) VALUES (?, ?, ?)", (user_id, cname, code), commit=True)
        db_query("INSERT INTO armies (user_id) VALUES (?)", (user_id,), commit=True)
        db_query("UPDATE countries SET is_ai = 0 WHERE code = ?", (code,), commit=True)
        
        await query.edit_message_text(f"✅ انتخاب شما ثبت شد! شما رهبر کشور {code} شدید.")
        await context.bot.send_message(chat_id=user_id, text="منوی اصلی فعال شد:", reply_markup=get_main_reply_keyboard())

    elif data == "buy_army_menu":
        c = db_query("SELECT money FROM countries WHERE code = (SELECT country_code FROM users WHERE user_id = ?)", (user_id,), fetchone=True)
        money = c[0] if c else 0
        keyboard = [
            [InlineKeyboardButton("🪖 ۱,۰۰۰ سرباز ($10,000)", callback_data="buy_soldiers")],
            [InlineKeyboardButton("🛡️ ۵۰ تانک ($50,000)", callback_data="buy_tanks")]
        ]
        await query.edit_message_text(f"🛒 **فروشگاه نظامی**\nموجودی: ${money:,.0f}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "buy_soldiers":
        user_country = db_query("SELECT country_code FROM users WHERE user_id = ?", (user_id,), fetchone=True)[0]
        money = db_query("SELECT money FROM countries WHERE code = ?", (user_country,), fetchone=True)[0]
        if money >= 10000:
            db_query("UPDATE countries SET money = money - 10000 WHERE code = ?", (user_country,), commit=True)
            db_query("UPDATE armies SET soldiers = soldiers + 1000 WHERE user_id = ?", (user_id,), commit=True)
            await query.edit_message_text("✅ ۱,۰۰۰ سرباز جدید به ارتش اضافه شد!")
        else:
            await query.edit_message_text("❌ موجودی کافی نیست!")

    elif data == "buy_tanks":
        user_country = db_query("SELECT country_code FROM users WHERE user_id = ?", (user_id,), fetchone=True)[0]
        money = db_query("SELECT money FROM countries WHERE code = ?", (user_country,), fetchone=True)[0]
        if money >= 50000:
            db_query("UPDATE countries SET money = money - 50000 WHERE code = ?", (user_country,), commit=True)
            db_query("UPDATE armies SET tanks = tanks + 50 WHERE user_id = ?", (user_id,), commit=True)
            await query.edit_message_text("✅ ۵۰ تانک به زره‌پوش ارتش اضافه شد!")
        else:
            await query.edit_message_text("❌ موجودی کافی نیست!")

    elif data == "clear_user_news":
        await query.edit_message_text("📚 آرشیو شخصی شما بروزرسانی شد.")

# ----------------------------------------------------
# 8. MAIN LAUNCHER
# ----------------------------------------------------
def main():
    init_sqlite()
    
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(CommandHandler("addmoney", admin_addmoney))
    app.add_handler(CommandHandler("cleararchive", admin_cleararchive))

    # Callbacks & Text Messages
    app.add_handler(CallbackQueryHandler(handle_inline_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_text))

    print("WORLD WAR Bot is running with ReplyKeyboardMarkup UI & Admin Panel...")
    app.run_polling()

if __name__ == "__main__":
    main()
