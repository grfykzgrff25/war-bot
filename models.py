from config import COUNTRIES, CHANNEL_ID
from database import db
import random
import json
from datetime import datetime, timedelta

class CountryModel:
    async def get_all_countries(self):
        async with db.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM countries ORDER BY world_rank")

    async def get_country_by_id(self, country_id):
        async with db.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM countries WHERE id = $1", country_id)

    async def get_country_by_name(self, name):
        async with db.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM countries WHERE name = $1", name)

    async def get_country_by_user(self, user_id):
        user = await db.get_user(user_id)
        if not user or not user["country_id"]:
            return None
        return await self.get_country_by_id(user["country_id"])

    async def create_countries(self):
        async with db.pool.acquire() as conn:
            colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F"]
            for i, (name, data) in enumerate(COUNTRIES.items()):
                color = colors[i % len(colors)]
                await conn.execute("""
                    INSERT INTO countries (name, flag, population, gdp, oil_reserves, 
                                         nuclear_level, military_power, world_rank, color)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (name) DO NOTHING
                """, name, data["flag"], data["population"], data["gdp"], 
                   data["oil"], data["nuclear_level"], data["military_power"], data["world_rank"], color)

    async def get_country_info(self, country_name):
        country = await self.get_country_by_name(country_name)
        if not country:
            return None

        async with db.pool.acquire() as conn:
            military = await conn.fetchrow("SELECT * FROM military WHERE country_id = $1", country["id"])
            economy = await conn.fetchrow("SELECT * FROM economy WHERE country_id = $1", country["id"])

        return {"country": country, "military": military, "economy": economy}

    async def update_world_rank(self, country_id, new_rank):
        async with db.pool.acquire() as conn:
            await conn.execute("UPDATE countries SET world_rank = $1 WHERE id = $2", new_rank, country_id)

class MilitaryModel:
    async def get_military(self, country_id):
        async with db.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM military WHERE country_id = $1", country_id)

    async def update_military(self, country_id, field, value):
        async with db.pool.acquire() as conn:
            await conn.execute(f"UPDATE military SET {field} = {field} + $1, last_updated = NOW() WHERE country_id = $2", value, country_id)

    async def buy_equipment(self, country_id, equipment, quantity, price):
        economy = await EconomyModel().get_economy(country_id)
        if not economy or economy["gold"] < price * quantity:
            return False, "پول کافی نیست!"

        async with db.pool.acquire() as conn:
            await conn.execute("UPDATE economy SET gold = gold - $1 WHERE country_id = $2", price * quantity, country_id)
            await conn.execute(f"UPDATE military SET {equipment} = {equipment} + $1 WHERE country_id = $2", quantity, country_id)

        return True, f"{quantity} عدد {equipment} خریداری شد!"

class EconomyModel:
    async def get_economy(self, country_id):
        async with db.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM economy WHERE country_id = $1", country_id)

    async def update_economy(self, country_id, field, value):
        async with db.pool.acquire() as conn:
            await conn.execute(f"UPDATE economy SET {field} = {field} + $1 WHERE country_id = $2", value, country_id)

class DiplomacyModel:
    async def get_relation(self, country1_id, country2_id):
        async with db.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM diplomacy WHERE (country1_id = $1 AND country2_id = $2) OR (country1_id = $2 AND country2_id = $1)",
                country1_id, country2_id
            )

    async def set_relation(self, country1_id, country2_id, status, alliance=None):
        async with db.pool.acquire() as conn:
            existing = await self.get_relation(country1_id, country2_id)
            if existing:
                await conn.execute(
                    "UPDATE diplomacy SET status = $1, alliance = $2 WHERE id = $3",
                    status, alliance, existing["id"]
                )
            else:
                await conn.execute(
                    "INSERT INTO diplomacy (country1_id, country2_id, status, alliance) VALUES ($1, $2, $3, $4)",
                    country1_id, country2_id, status, alliance
                )

class WarModel:
    async def start_war(self, attacker_id, defender_id, forces):
        async with db.pool.acquire() as conn:
            return await conn.fetchrow(
                "INSERT INTO wars (attacker_id, defender_id, attacker_forces, defender_forces, status) VALUES ($1, $2, $3, $4, 'active') RETURNING *",
                attacker_id, defender_id, json.dumps(forces), "{}"
            )

    async def end_war(self, war_id, winner_id, loot):
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE wars SET winner_id = $1, loot = $2, status = 'ended', ended_at = NOW() WHERE id = $3",
                winner_id, json.dumps(loot), war_id
            )