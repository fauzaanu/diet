from datetime import datetime
from enum import Enum, auto
import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

class Goal(Enum):
    EXTREME_WEIGHT_LOSS = auto()
    MODERATE_WEIGHT_LOSS = auto()
    MAINTENANCE = auto()
    MODERATE_WEIGHT_GAIN = auto()
    EXTREME_WEIGHT_GAIN = auto()

GOAL_LEVELS = {
    Goal.EXTREME_WEIGHT_LOSS: [1, 2, 3],
    Goal.MODERATE_WEIGHT_LOSS: [1, 2, 3],
    Goal.MAINTENANCE: [1, 2, 3],
    Goal.MODERATE_WEIGHT_GAIN: [1, 2, 3],
    Goal.EXTREME_WEIGHT_GAIN: [1, 2, 3],
}

LEVEL_MULTIPLIERS = {
    Goal.EXTREME_WEIGHT_LOSS: {1: 7, 2: 8, 3: 9},
    Goal.MODERATE_WEIGHT_LOSS: {1: 10, 2: 11, 3: 12},
    Goal.MAINTENANCE: {1: 13, 2: 14, 3: 15},
    Goal.MODERATE_WEIGHT_GAIN: {1: 16, 2: 17, 3: 18},
    Goal.EXTREME_WEIGHT_GAIN: {1: 19, 2: 20, 3: 21},
}

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD")
    )

class UserState:
    def __init__(self, user_id):
        self.user_id = user_id
        self.weight_unit = None
        self.weight = None
        self.goal = None
        self.level = None

    def save_to_db(self):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (user_id, weight_unit, weight, goal, level, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE
                    SET weight_unit = EXCLUDED.weight_unit,
                        weight = EXCLUDED.weight,
                        goal = EXCLUDED.goal,
                        level = EXCLUDED.level,
                        last_updated = EXCLUDED.last_updated
                """, (
                    self.user_id,
                    self.weight_unit,
                    self.weight,
                    self.goal.name if self.goal else None,
                    self.level,
                    datetime.now()
                ))
                conn.commit()

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    weight_unit TEXT,
                    weight DOUBLE PRECISION,
                    goal TEXT,
                    level SMALLINT,
                    last_updated TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    amount DOUBLE PRECISION,
                    currency TEXT,
                    telegram_payment_charge_id TEXT,
                    timestamp TIMESTAMP
                )
            """)
            conn.commit()

def get_user_state(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user_data = cur.fetchone()
            if user_data:
                user_state = UserState(user_id)
                user_state.weight_unit = user_data[1]
                user_state.weight = user_data[2]
                user_state.goal = Goal[user_data[3]] if user_data[3] else None
                user_state.level = user_data[4]
                return user_state
    return None

def save_payment(user_id, amount, currency, charge_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO payments (user_id, amount, currency, telegram_payment_charge_id, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, amount, currency, charge_id, datetime.now()))
            conn.commit()
