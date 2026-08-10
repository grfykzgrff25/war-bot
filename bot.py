import os
import sqlite3
import random
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue
)

# ----------------------------------------------------
# 1. LOGGING & DATABASE INITIALIZATION
# ----------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DB_NAME = "world_war.db"

def init_sqlite():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Users / Commanders
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            commander_name TEXT,
            country_code TEXT,
            level INTEGER DEFAULT 1,
            score INTEGER DEFAULT 0,
            approval INTEGER DEFAULT 100,
            is_admin INTEGER DEFAULT 0
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
            is_ai INTEGER DEFAULT 0
        )
    ''')
    
    # Provinces
    c.execute('''
        CREATE TABLE IF NOT EXISTS provinces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT,
            name TEXT,
            population INTEGER,
            security INTEGER DEFAULT 100,
            infrastructure INTEGER DEFAULT 1,
            owner_id INTEGER
        )
    ''')
    
    # Armies
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
            nukes INTEGER DEFAULT 0
        )
    ''')
    
    # Market
    c.execute('''
        CREATE TABLE IF NOT EXISTS market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            resource TEXT,
            amount REAL,
            price_per_unit REAL
        )
    ''')
    
    # Active Timed Wars
    c.execute('''
        CREATE TABLE IF NOT EXISTS wars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER,
            defender_id INTEGER,
            province_id INTEGER,
            end_time TIMESTAMP,
            attacker_tactic TEXT DEFAULT 'standard',
            defender_tactic TEXT DEFAULT 'standard',
            status TEXT DEFAULT 'ACTIVE'
        )
    ''')
    
    # Generals / Commanders
    c.execute('''
        CREATE TABLE IF NOT EXISTS generals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            type TEXT, -- LAND, AIR, SEA
            level INTEGER DEFAULT 1,
            bonus_percent INTEGER DEFAULT 5
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
            
            # Default Provinces for IRN as sample
            if code == "IRN":
                provs = ["تهران", "اصفهان", "فارس", "خوزستان", "کرمان", "گیلان", "مازندران", "آذربایجان شرقی"]
                for p in provs:
                    c.execute("INSERT INTO provinces (country_code, name, population) VALUES (?, ?, ?)",
                              (code, p, random.randint(1000000, 10000000)))

    conn.commit()
    conn.close()

# ----------------------------------------------------
# 2. HELPER DATABASE FUNCTIONS
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

# ----------------------------------------------------
# 3. COMMAND HANDLERS & MENUS
# ----------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    db_user = db_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    
    if not db_user:
        # Registration Step 1: Select Country
        countries = db_query("SELECT code, name, flag FROM countries WHERE is_ai = 1", fetchall=True)
        keyboard = []
        for code, name, flag in countries:
            keyboard.append([InlineKeyboardButton(f"{flag} {name}", callback_data=f"select_country_{code}")])
            
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
    
    # Save User
    commander_name = f"فرمانده {query.from_user.first_name}"
    db_query("INSERT INTO users (user_id, commander_name, country_code) VALUES (?, ?, ?)",
             (user_id, commander_name, country_code), commit=True)
    
    # Initialize Army
    db_query("INSERT INTO armies (user_id) VALUES (?)", (user_id,), commit=True)
    
    # Generate Starting Generals
    db_query("INSERT INTO generals (user_id, name, type) VALUES (?, ?, ?)",
             (user_id, "ژنرال آریا", "LAND"), commit=True)
    
    # Set AI off for chosen country
    db_query("UPDATE countries SET is_ai = 0 WHERE code = ?", (country_code,), commit=True)
    
    add_news(f"👑 فرمانده جدید {commander_name} رهبری کشور {country_code} را بر عهده گرفت!")
    
    await query.edit_message_text(f"✅ انتخاب شما ثبت شد! شما اکنون رهبر کشور {country_code} هستید.\nاز منوی اصلی استفاده کنید.")
    await main_menu(update, context)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👤 پروفایل & کشور", callback_data="menu_profile"), InlineKeyboardButton("🏙 استان‌ها", callback_data="menu_provinces")],
        [InlineKeyboardButton("🪖 ارتش & ژنرال‌ها", callback_data="menu_army"), InlineKeyboardButton("⚔️ اتاق جنگ (تاکتیکی)", callback_data="menu_war")],
        [InlineKeyboardButton("💰 بازار جهانی & اقتصاد", callback_data="menu_market"), InlineKeyboardButton("🤝 دیپلماسی & جاسوسی", callback_data="menu_diplomacy")],
        [InlineKeyboardButton("📰 اخبار جهان & سازمان ملل", callback_data="menu_news"), InlineKeyboardButton("🏆 رتبه‌بندی", callback_data="menu_rankings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🌍 **منوی اصلی فرماندهی WORLD WAR**\nدستور مورد نظر را انتخاب کنید:"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ----------------------------------------------------
# 4. MODULES IMPLEMENTATION
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
        await main_menu(update, context)
        return

    # --- PROFILE ---
    if data == "menu_profile":
        u = db_query("SELECT commander_name, country_code, level, score, approval FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        c = db_query("SELECT name, flag, money, oil, steel, food, power, gold FROM countries WHERE code = ?", (u[1],), fetchone=True)
        
        text = (
            f"👤 **پروفایل فرمانده:** {u[0]}\n"
            f"🚩 **کشور:** {c[1]} {c[0]}\n"
            f"⭐ **سطح:** {u[2]} | **امتیاز:** {u[3]}\n"
            f"📊 **رضایت عمومی:** {u[4]}%\n\n"
            f"💰 **خزانه:** ${c[2]:,.0f}\n"
            f"🛢 **نفت:** {c[3]:,.0f} بشکه | 🔩 **فولاد:** {c[4]:,.0f} تن\n"
            f"🌾 **غذا:** {c[5]:,.0f} تن | ⚡ **برق:** {c[6]:,.0f} MW\n"
            f"💎 **طلا:** {c[7]:,.0f} شمش"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- ARMY ---
    elif data == "menu_army":
        a = db_query("SELECT soldiers, tanks, artillery, spec_ops, fighters, bombers, drones, warships, submarines, carriers, missiles_short, missiles_mid, missiles_long, nukes FROM armies WHERE user_id = ?", (user_id,), fetchone=True)
        g = db_query("SELECT name, type, level, bonus_percent FROM generals WHERE user_id = ?", (user_id,), fetchall=True)
        
        gen_str = "\n".join([f"🎖 {x[0]} ({x[1]}) - سطح {x[2]} [بونس: +{x[3]}%]" for x in g]) if g else "هیچ ژنرالی ندارید."
        
        text = (
            f"🪖 **وضعیت نیروهای نظامی:**\n"
            f"🪖 سرباز: {a[0]:,} | 🛡 تانک: {a[1]:,} | 💥 توپخانه: {a[2]:,}\n"
            f"🎯 نیروی ویژه: {a[3]:,} | ✈️ جنگنده: {a[4]:,} | 💣 بمب‌افکن: {a[5]:,}\n"
            f"🛸 پهپاد: {a[6]:,} | 🚢 ناو: {a[7]:,} | 🌊 زیردریایی: {a[8]:,}\n"
            f"⚓ ناو هواپیمابر: {a[9]:,}\n"
            f"🚀 موشک: کوتاه‌برد ({a[10]}) | میان‌برد ({a[11]}) | دوربرد ({a[12]})\n"
            f"☢️ کلاهک هسته‌ای: {a[13]}\n\n"
            f"👨‍✈️ **کادر فرماندهی:**\n{gen_str}"
        )
        keyboard = [
            [InlineKeyboardButton("➕ خرید/تولید تجهیزات", callback_data="build_army")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- WAR ROOM & TACTICS ---
    elif data == "menu_war":
        wars = db_query("SELECT id, defender_id, end_time, attacker_tactic FROM wars WHERE attacker_id = ? AND status = 'ACTIVE'", (user_id,), fetchall=True)
        war_str = ""
        for w in wars:
            def_user = db_query("SELECT commander_name FROM users WHERE user_id = ?", (w[1],), fetchone=True)
            def_name = def_user[0] if def_user else "کشور AI"
            war_str += f"⚔️ جنگ ID {w[0]} علیه {def_name} | تاکتیک: {w[3]} | پایان: {w[2]}\n"
        
        if not war_str:
            war_str = "هیچ جنگ فعال در حال جریانی ندارید."

        text = (
            f"⚔️ **اتاق فرماندهی جنگ**\n\n"
            f"**جنگ‌های فعال شما:**\n{war_str}\n\n"
            f"برای حمله جدید استان هدف را انتخاب کنید."
        )
        keyboard = [
            [InlineKeyboardButton("🚀 اعلان جنگ & حمله", callback_data="attack_select_target")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "attack_select_target":
        # Launch an instant simulated war / timed war
        provs = db_query("SELECT id, name, country_code FROM provinces LIMIT 5", fetchall=True)
        keyboard = []
        for p_id, p_name, p_code in provs:
            keyboard.append([InlineKeyboardButton(f"حمله به {p_name} ({p_code})", callback_data=f"start_war_{p_id}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_war")])
        
        await query.edit_message_text("یک استان را برای حمله انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("start_war_"):
        prov_id = int(data.split("_")[2])
        end_time = datetime.now() + timedelta(hours=1)
        
        db_query("INSERT INTO wars (attacker_id, defender_id, province_id, end_time) VALUES (?, 0, ?, ?)",
                 (user_id, prov_id, end_time), commit=True)
        
        add_news(f"🔥 جنگ جدیدی برای تصرف استان شماره {prov_id} آغاز شد!")
        
        keyboard = [
            [InlineKeyboardButton("🎯 تنظیم تاکتیک: حمله گازانبری", callback_data=f"tactic_flank_{prov_id}")],
            [InlineKeyboardButton("✈️ پشتیبانی هوایی سنگین", callback_data=f"tactic_air_{prov_id}")],
            [InlineKeyboardButton("🔙 بازگشت به اتاق جنگ", callback_data="menu_war")]
        ]
        await query.edit_message_text("✅ دستور حمله صادر شد! جنگ تا ۱ ساعت آینده ادامه دارد.\nمی‌توانید تاکتیک‌های نبرد را تنظیم کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    # --- GLOBAL MARKET ---
    elif data == "menu_market":
        text = (
            "💰 **بازار آزاد و بورس جهانی منابع**\n\n"
            "نرخ آنلاین عرضه و تقاضا:\n"
            "🛢 نفت: $120 / بشکه\n"
            "🔩 فولاد: $85 / تن\n"
            "🌾 غذا: $40 / تن\n"
            "⚡ برق: $60 / MW"
        )
        keyboard = [
            [InlineKeyboardButton("🛒 خرید منابع", callback_data="market_buy"), InlineKeyboardButton("🏷 فروش منابع", callback_data="market_sell")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- NEWS & UN ---
    elif data == "menu_news":
        news_items = db_query("SELECT content, timestamp FROM news ORDER BY id DESC LIMIT 5", fetchall=True)
        news_str = "\n".join([f"• [{x[1]}] {x[0]}" for x in news_items]) if news_items else "خبری ثبت نشده است."
        
        text = (
            f"📰 **خبرگزاری سراسری جهان & سازمان ملل**\n\n"
            f"{news_str}\n\n"
            f"🇺🇳 **قطعنامه‌های جاری:** هیچ قطعنامه تحریمی فعالی وجود ندارد."
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- RANKINGS ---
    elif data == "menu_rankings":
        top_users = db_query("SELECT commander_name, score FROM users ORDER BY score DESC LIMIT 5", fetchall=True)
        rank_str = "\n".join([f"{i+1}. {x[0]} - {x[1]} امتیاز" for i, x in enumerate(top_users)])
        
        text = f"🏆 **رتبه‌بندی ۵ قدرت برتر جهان:**\n\n{rank_str}"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ----------------------------------------------------
# 5. ADMIN COMMANDS
# ----------------------------------------------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Simple check for Admin
    user = db_query("SELECT is_admin FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    
    if not user or user[0] != 1:
        # Default promote first user to admin if needed or allow command override
        db_query("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,), commit=True)

    text = (
        "👑 **پنل مدیریت ادمین**\n\n"
        "دستورات ادمین:\n"
        "/add_money <amount> - تزریق پول\n"
        "/trigger_disaster - ایجاد بلای طبیعی تصادفی\n"
        "/broadcast <message> - ارسال خبر جهانی"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = " ".join(context.args)
    if msg:
        add_news(f"📢 **بیانیه ادمین:** {msg}")
        await update.message.reply_text("خبر ارسال شد.")

# ----------------------------------------------------
# 6. CRON JOBS & AUTOMATION (EVERY 6H, 24H, WARS, AI)
# ----------------------------------------------------
async def job_economy_tick(context: ContextTypes.DEFAULT_TYPE):
    """ Runs every 6 hours: Resource Production & Economic Decay """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE countries SET money = money + 50000, oil = oil + 2000, steel = steel + 1000, food = food + 3000")
    conn.commit()
    conn.close()
    add_news("📈 چرخه‌های اقتصادی تولید شد! درآمد ۶ ساعته به خزانه کشورها واریز گردید.")

async def job_disaster_and_un(context: ContextTypes.DEFAULT_TYPE):
    """ Runs every 24 hours: Natural Disasters """
    disasters = [
        "🌊 زلزله شدید ۸ ریشتری در آسیا خسارات سنگینی به بار آورد!",
        "🌪 طوفان شدید سهمگین تأسیسات نفتی را مختل کرد!",
        "🌾 خشکسالی بی‌سابقه تولید کشاورزی را ۲ logic٪ کاهش داد!"
    ]
    event = random.choice(disasters)
    add_news(f"🌪 **بلای طبیعی:** {event}")

async def job_ai_turns(context: ContextTypes.DEFAULT_TYPE):
    """ Automated AI decisions """
    ai_countries = db_query("SELECT code, name FROM countries WHERE is_ai = 1", fetchall=True)
    if ai_countries:
        chosen = random.choice(ai_countries)
        actions = [
            f"کشور {chosen[1]} ارتش نیروی زمینی خود را توسعه داد.",
            f"کشور {chosen[1]} مانور نظامی در مرزها برگزار کرد.",
            f"کشور {chosen[1]} بودجه تحقیقات هسته‌ای را افزایش داد."
        ]
        add_news(f"🤖 **هوش مصنوعی:** {random.choice(actions)}")

async def job_war_resolver(context: ContextTypes.DEFAULT_TYPE):
    """ Checks active wars and calculates outcome when ended """
    now = datetime.now()
    active_wars = db_query("SELECT id, attacker_id, defender_id, province_id FROM wars WHERE status = 'ACTIVE' AND end_time <= ?", (now,), fetchall=True)
    
    for w_id, att_id, def_id, prov_id in active_wars:
        # Determine Winner based on random/army formula
        win = random.choice([True, False])
        if win:
            db_query("UPDATE wars SET status = 'ATTACKER_WON' WHERE id = ?", (w_id,), commit=True)
            db_query("UPDATE users SET score = score + 100 WHERE user_id = ?", (att_id,), commit=True)
            add_news(f"🏆 پیروزی بزرگ! نیروهای تحت فرماندهی <{att_id}> موفق به فتح استان {prov_id} شدند!")
        else:
            db_query("UPDATE wars SET status = 'DEFENDER_WON' WHERE id = ?", (w_id,), commit=True)
            add_news(f"💀 شکست! حمله به استان {prov_id} توسط مدافعین سرکوب شد.")

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

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(CallbackQueryHandler(handle_callbacks))

    # Job Queue Setup
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(job_war_resolver, interval=30, first=10)
        job_queue.run_repeating(job_ai_turns, interval=3600, first=60)
        job_queue.run_repeating(job_economy_tick, interval=21600, first=120)
        job_queue.run_repeating(job_disaster_and_un, interval=86400, first=300)

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
