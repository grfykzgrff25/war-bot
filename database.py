import asyncpg
from config import DATABASE_URL

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        await self.create_tables()
        return self.pool

    async def create_tables(self):
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(100),
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                country_id INTEGER,
                president_name VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS countries (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE,
                flag VARCHAR(10),
                population BIGINT DEFAULT 5000000,
                gdp BIGINT DEFAULT 100000000,
                oil_reserves BIGINT DEFAULT 10000000,
                satisfaction INTEGER DEFAULT 70,
                nuclear_level INTEGER DEFAULT 0,
                military_power INTEGER DEFAULT 50,
                world_rank INTEGER DEFAULT 50,
                is_active BOOLEAN DEFAULT TRUE,
                color VARCHAR(20) DEFAULT '#808080'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS military (
                id SERIAL PRIMARY KEY,
                country_id INTEGER REFERENCES countries(id),
                soldiers INTEGER DEFAULT 100000,
                tanks INTEGER DEFAULT 100,
                missiles INTEGER DEFAULT 10,
                fighters INTEGER DEFAULT 20,
                drones INTEGER DEFAULT 50,
                warships INTEGER DEFAULT 5,
                nuclear_warheads INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS economy (
                id SERIAL PRIMARY KEY,
                country_id INTEGER REFERENCES countries(id),
                gold BIGINT DEFAULT 1000000,
                oil BIGINT DEFAULT 10000,
                steel BIGINT DEFAULT 5000,
                food BIGINT DEFAULT 20000,
                electricity BIGINT DEFAULT 5000,
                last_updated TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS diplomacy (
                id SERIAL PRIMARY KEY,
                country1_id INTEGER REFERENCES countries(id),
                country2_id INTEGER REFERENCES countries(id),
                status VARCHAR(20) DEFAULT 'neutral',
                alliance VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS wars (
                id SERIAL PRIMARY KEY,
                attacker_id INTEGER REFERENCES countries(id),
                defender_id INTEGER REFERENCES countries(id),
                attacker_forces JSONB,
                defender_forces JSONB,
                winner_id INTEGER REFERENCES countries(id),
                loot JSONB,
                started_at TIMESTAMP DEFAULT NOW(),
                ended_at TIMESTAMP,
                status VARCHAR(20) DEFAULT 'active'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS news (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200),
                content TEXT,
                image_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS world_map (
                id SERIAL PRIMARY KEY,
                map_image_url VARCHAR(500),
                country_positions JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        ]
        async with self.pool.acquire() as conn:
            for query in queries:
                await conn.execute(query)

    async def get_user(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)

    async def create_user(self, user_id, username, first_name, last_name=""):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "INSERT INTO users (user_id, username, first_name, last_name) VALUES ($1, $2, $3, $4) RETURNING *",
                user_id, username, first_name, last_name
            )

    async def update_user_country(self, user_id, country_id, president_name):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "UPDATE users SET country_id = $1, president_name = $2 WHERE user_id = $3 RETURNING *",
                country_id, president_name, user_id
            )

db = Database()