import sqlite3
from datetime import datetime
from enum import Enum, auto


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


class UserState:
    def __init__(self, user_id):
        self.user_id = user_id
        self.weight_unit = None
        self.weight = None
        self.goal = None
        self.level = None

    def save_to_db(self):
        conn = sqlite3.connect("diet_bot.db")
        c = conn.cursor()
        c.execute(
            """INSERT OR REPLACE INTO users
                     (user_id, weight_unit, weight, goal, level, last_updated)
                     VALUES (?, ?, ?, ?, ?, ?)""",
            (
                self.user_id,
                self.weight_unit,
                self.weight,
                self.goal.name if self.goal else None,
                self.level,
                datetime.now(),
            ),
        )
        conn.commit()
        conn.close()


def init_db():
    conn = sqlite3.connect("diet_bot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  weight_unit TEXT,
                  weight REAL,
                  goal TEXT,
                  level INTEGER,
                  last_updated TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS payments
                 (payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  amount REAL,
                  currency TEXT,
                  telegram_payment_charge_id TEXT,
                  timestamp TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id))""")
    conn.commit()
    conn.close()
