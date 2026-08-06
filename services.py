import random
import json
from datetime import datetime, timedelta
from models import CountryModel, MilitaryModel, EconomyModel, DiplomacyModel, WarModel
from database import db
from config import CHANNEL_ID

class WarService:
    async def calculate_war(self, attacker_id, defender_id, forces):
        attacker_military = await MilitaryModel().get_military(attacker_id)
        defender_military = await MilitaryModel().get_military(defender_id)

        # محاسبه قدرت
        attacker_power = sum([
            forces.get("soldiers", 0) * 1,
            forces.get("tanks", 0) * 5,
            forces.get("missiles", 0) * 10,
            forces.get("fighters", 0) * 8,
            forces.get("drones", 0) * 3,
            forces.get("warships", 0) * 15
        ])

        defender_power = sum([
            defender_military["soldiers"] * 1,
            defender_military["tanks"] * 5,
            defender_military["missiles"] * 10,
            defender_military["fighters"] * 8,
            defender_military["drones"] * 3,
            defender_military["warships"] * 15
        ])

        # شانس پیروزی
        total_power = attacker_power + defender_power
        win_chance = (attacker_power / total_power * 100) if total_power > 0 else 50
        win_chance = max(5, min(95, win_chance))

        is_winner = random.randint(1, 100) <= win_chance

        # تلفات
        if is_winner:
            attacker_loss = random.randint(5, 20)
            defender_loss = random.randint(20, 50)
            loot = {
                "gold": random.randint(100000, 500000),
                "oil": random.randint(1000, 5000),
                "steel": random.randint(500, 2000)
            }
        else:
            attacker_loss = random.randint(20, 50)
            defender_loss = random.randint(5, 20)
            loot = {"gold": 0, "oil": 0, "steel": 0}

        # اعمال تلفات
        for key, value in forces.items():
            loss = int(value * attacker_loss / 100)
            await MilitaryModel().update_military(attacker_id, key, -loss)

        await MilitaryModel().update_military(defender_id, "soldiers", -int(defender_military["soldiers"] * defender_loss / 100))

        # اعمال غنیمت
        if loot["gold"] > 0:
            await EconomyModel().update_economy(attacker_id, "gold", loot["gold"])
            await EconomyModel().update_economy(defender_id, "gold", -loot["gold"])

        return {
            "winner": attacker_id if is_winner else defender_id,
            "attacker_loss": attacker_loss,
            "defender_loss": defender_loss,
            "loot": loot,
            "attacker_power": attacker_power,
            "defender_power": defender_power
        }

class NewsService:
    async def create_news(self, title, content, image_url=None):
        async with db.pool.acquire() as conn:
            return await conn.fetchrow(
                "INSERT INTO news (title, content, image_url) VALUES ($1, $2, $3) RETURNING *",
                title, content, image_url
            )

    async def send_war_news(self, attacker, defender, result):
        if result["winner"] == attacker:
            text = f"""
⚔️ **جنگ پایان یافت!**

🇺🇳 {attacker} پیروز شد!

💥 تلفات:
• {attacker}: {result['attacker_loss']}%
• {defender}: {result['defender_loss']}%

💰 غنیمت:
• طلا: {result['loot']['gold']:,}
• نفت: {result['loot']['oil']:,}
• فولاد: {result['loot']['steel']:,}
"""
        else:
            text = f"""
⚔️ **جنگ پایان یافت!**

🇺🇳 {defender} از کشور خود دفاع کرد!

💥 تلفات:
• {attacker}: {result['attacker_loss']}%
• {defender}: {result['defender_loss']}%
"""
        await self.create_news("⚔️ جنگ", text)

    async def send_diplomacy_news(self, country1, country2, action):
        texts = {
            "war": f"⚔️ {country1} به {country2} اعلان جنگ داد!",
            "peace": f"🕊️ {country1} و {country2} صلح کردند!",
            "alliance": f"🤝 {country1} و {country2} اتحاد تشکیل دادند!"
        }
        await self.create_news(action, texts.get(action, ""))

class MapService:
    async def generate_map(self):
        # این یک نمونه ساده است - با PIL می‌توان نقشه واقعی ساخت
        countries = await CountryModel().get_all_countries()
        positions = {}
        for i, country in enumerate(countries):
            positions[country["name"]] = {
                "x": random.randint(50, 900),
                "y": random.randint(50, 600),
                "color": country["color"]
            }
        return positions