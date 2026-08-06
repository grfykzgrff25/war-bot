import os
from dotenv import load_dotenv

load_dotenv()

# ================= توکن =================
BOT_TOKEN = "8971614267:AAG18ai0KIvaNszLH2aKZQMIZ9XTHodnAwE"

# ================= ادمین =================
ADMINS = [8974374358]  # آیدی عددی شما

# ================= کانال خبری =================
CHANNEL_ID = "@jsfbkxf"  # کانال خبری

# ================= دیتابیس (اختیاری - از Railway می‌گیرد) =================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///world_war.db")

# ================= تنظیمات بازی =================
WAR_DURATION = 7200  # ۲ ساعت
NUCLEAR_COOLDOWN = 86400  # ۲۴ ساعت
ESPIONAGE_COOLDOWN = 3600  # ۱ ساعت
MAX_PLAYERS = 30