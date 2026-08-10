import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ----------------------------------------------------
# LOGGING & DATABASE SETUP
# ----------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DB_NAME = "bot_database.db"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_admin INTEGER DEFAULT 0,
            chat_state TEXT DEFAULT 'NONE'
        )
    ''')
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

# ----------------------------------------------------
# 🔘 ساخت کیبورد شیشه‌ای دقیقاً مطابق تصویر شما
# ----------------------------------------------------
def get_inline_main_menu():
    # دقیقاً متن‌ها و ایموجی‌های داخل تصویر شما در ۲ ستون
    keyboard = [
        [
            InlineKeyboardButton("مشاهده و مدیریت آرشیو 📚", callback_data="btn_archive_manage"),
            InlineKeyboardButton("بررسی خبر جدید 🔍", callback_data="btn_check_news")
        ],
        [
            InlineKeyboardButton("وضعیت هوش مصنوعی 🧠", callback_data="btn_ai_status"),
            InlineKeyboardButton("آمار آرشیو 📊", callback_data="btn_archive_stats")
        ],
        [
            InlineKeyboardButton("لیست مدیران 👥", callback_data="btn_admin_list"),
            InlineKeyboardButton("تنظیمات سیستم ⚙️", callback_data="btn_system_settings")
        ],
        [
            InlineKeyboardButton("پاکسازی کامل آرشیو 🗑️", callback_data="btn_clear_archive"),
            InlineKeyboardButton("راهنما 📋", callback_data="btn_help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ----------------------------------------------------
# COMMAND HANDLERS
# ----------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # ثبت کاربر
    is_admin_val = 1 if (ADMIN_ID != 0 and user_id == ADMIN_ID) else 0
    db_query("INSERT OR IGNORE INTO users (user_id, username, is_admin) VALUES (?, ?, ?)",
             (user_id, user.username or user.first_name, is_admin_val), commit=True)

    text = "👋 **به پنل مدیریت سیستم خوش آمدید!**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    
    await update.message.reply_text(text, reply_markup=get_inline_main_menu(), parse_mode="Markdown")

# ----------------------------------------------------
# 🎯 اجرای دستور تمام دکمه‌ها (CALLBACK HANDLER)
# ----------------------------------------------------
async def handle_button_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()

    # دکمه بازگشت به منوی اصلی
    if data == "btn_main_menu":
        db_query("UPDATE users SET chat_state = 'NONE' WHERE user_id = ?", (user_id,), commit=True)
        text = "📌 **منوی اصلی سیستم:**\nلطفاً گزینه مورد نظر را انتخاب کنید:"
        await query.edit_message_text(text, reply_markup=get_inline_main_menu(), parse_mode="Markdown")
        return

    # ۱. بررسی خبر جدید 🔍
    if data == "btn_check_news":
        latest = db_query("SELECT title, content, timestamp FROM news ORDER BY id DESC LIMIT 1", fetchone=True)
        if latest:
            text = f"🔎 **آخرین خبر ثبت‌شده:**\n\n📌 **{latest[0]}**\n📝 {latest[1]}\n📅 _{latest[2]}_"
        else:
            text = "🔎 **بررسی خبر جدید:**\nدر حال حاضر هیچ خبر جدیدی در سیستم ثبت نشده است."
        
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="btn_main_menu")]])
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

    # ۲. مشاهده و مدیریت آرشیو 📚
    elif data == "btn_archive_manage":
        news_items = db_query("SELECT id, title, timestamp FROM news ORDER BY id DESC LIMIT 5", fetchall=True)
        if news_items:
            res = "📚 **لیست و مدیریت آرشیو اخبار:**\n\n"
            for item in news_items:
                res += f"🔹 #{item[0]} | {item[1]} ({item[2]})\n"
        else:
            res = "📚 **آرشیو خالی است.** هیچ خبری برای مدیریت وجود ندارد."

        keyboard = [
            [
                InlineKeyboardButton("➕ افزودن خبر جدید", callback_data="btn_add_news"),
                InlineKeyboardButton("🗑️ حذف خبر", callback_data="btn_delete_news")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="btn_main_menu")]
        ]
        await query.edit_message_text(res, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ۳. وضعیت هوش مصنوعی 🧠
    elif data == "btn_ai_status":
        db_query("UPDATE users SET chat_state = 'TALKING_TO_AI' WHERE user_id = ?", (user_id,), commit=True)
        text = (
            "🧠 **وضعیت هوش مصنوعی:**\n"
            "سرویس هوش مصنوعی: **فعال 🟢**\n\n"
            "💬 اکنون می‌توانید سوال، متن یا درخواست خود را ارسال کنید تا هوش مصنوعی به آن پاسخ دهد:"
        )
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="btn_main_menu")]])
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

    # ۴. آمار آرشیو 📊
    elif data == "btn_archive_stats":
        total_news = db_query("SELECT COUNT(*) FROM news", fetchone=True)[0]
        total_users = db_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
        
        text = (
            "📊 **گزارش و آمار دقیق آرشیو سیستم:**\n\n"
            f"📰 تعداد کل اخبار آرشیو شده: **{total_news}**\n"
            f"👥 تعداد کل کاربران سیستم: **{total_users}**\n"
            f"⚡ وضعیت پایگاه داده: **سالم و فعال 🟢**"
        )
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="btn_main_menu")]])
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

    # ۵. تنظیمات سیستم ⚙️
    elif data == "btn_system_settings":
        text = "⚙️ **تنظیمات سیستم:**\nپارامتر مورد نظر برای پیکربندی را انتخاب کنید:"
        keyboard = [
            [
                InlineKeyboardButton("🔔 تنظیمات اعلان‌ها", callback_data="btn_setting_notif"),
                InlineKeyboardButton("🔑 تغییر سطح دسترسی", callback_data="btn_setting_perm")
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="btn_main_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ۶. لیست مدیران 👥
    elif data == "btn_admin_list":
        admins = db_query("SELECT username FROM users WHERE is_admin = 1", fetchall=True)
        admin_str = "\n".join([f"👤 @{a[0]}" for a in admins if a[0]]) if admins else "👤 مدیر ارشد سیستم"
        
        text = f"👥 **لیست مدیران مجاز سیستم:**\n\n{admin_str}\n\nپشتیبانی: @BotFather"
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="btn_main_menu")]])
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

    # ۷. راهنما 📋
    elif data == "btn_help":
        text = (
            "📋 **راهنمای استفاده از ربات:**\n\n"
            "🔹 **بررسی خبر جدید:** دریافت و بررسی آخرین اخبار به‌روزرسانی شده.\n"
            "🔹 **مدیریت آرشیو:** مشاهده، ویرایش و مدیریت اخبار آرشیو شده.\n"
            "🔹 **وضعیت هوش مصنوعی:** چت مستقیم با هوش مصنوعی ربات.\n"
            "🔹 **پاکسازی آرشیو:** حذف کامل گزارشات (مخصوص مدیران)."
        )
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="btn_main_menu")]])
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

    # ۸. پاکسازی کامل آرشیو 🗑️
    elif data == "btn_clear_archive":
        user_data = db_query("SELECT is_admin FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        if user_data and user_data[0] == 1:
            db_query("DELETE FROM news", commit=True)
            text = "🗑️ **آرشیو اخبار سیستم با موفقیت به‌طور کامل پاکسازی شد.**"
        else:
            text = "⚠️ **خطا:** شما دسترسی لازم برای پاکسازی کامل آرشیو را ندارید. فقط مدیران ارشد مجاز هستند."
        
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="btn_main_menu")]])
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

    # افزودن خبر جدید
    elif data == "btn_add_news":
        db_query("UPDATE users SET chat_state = 'WAITING_FOR_NEWS' WHERE user_id = ?", (user_id,), commit=True)
        text = "✏️ **لطفاً عنوان و متن خبر جدید را ارسال کنید:**\n\nفرمت ارسال: `عنوان | متن خبر`"
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="btn_archive_manage")]])
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

# ----------------------------------------------------
# TEXT HANDLER (چت هوش مصنوعی و دریافت اخبار)
# ----------------------------------------------------
async def handle_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    u = db_query("SELECT chat_state FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not u:
        return

    chat_state = u[0]

    # حالت ارسال خبر جدید
    if chat_state == 'WAITING_FOR_NEWS':
        if "|" in text:
            parts = text.split("|", 1)
            title, content = parts[0].strip(), parts[1].strip()
            db_query("INSERT INTO news (title, content) VALUES (?, ?)", (title, content), commit=True)
            db_query("UPDATE users SET chat_state = 'NONE' WHERE user_id = ?", (user_id,), commit=True)
            
            back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("📚 بازگشت به آرشیو", callback_data="btn_archive_manage")]])
            await update.message.reply_text("✅ **خبر جدید با موفقیت در آرشیو ثبت شد!**", reply_markup=back_btn, parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ لطفاً فرمت را رعایت کنید: `عنوان | متن خبر`", parse_mode="Markdown")

    # حالت گفتگو با هوش مصنوعی
    elif chat_state == 'TALKING_TO_AI':
        await update.message.reply_chat_action("typing")
        reply_text = f"🧠 **پاسخ هوش مصنوعی:**\nدرخواست شما ('{text}') دریافت شد و پردازش گردید."
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="btn_main_menu")]])
        await update.message.reply_text(reply_text, reply_markup=back_btn, parse_mode="Markdown")

# ----------------------------------------------------
# MAIN LAUNCHER
# ----------------------------------------------------
def main():
    init_db()
    
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    app = Application.builder().token(TOKEN).build()

    # ثبت دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button_clicks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_text))

    print("Bot is running with Inline Glass Buttons UI...")
    app.run_polling()

if __name__ == "__main__":
    main()
