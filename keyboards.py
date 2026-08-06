from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
    from config import COUNTRIES
    keyboard = []
    for name, data in COUNTRIES.items():
        keyboard.append([InlineKeyboardButton(
            text=f"{data['flag']} {name}",
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