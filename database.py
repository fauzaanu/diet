from datetime import datetime
from enum import Enum, auto
import os
from dotenv import load_dotenv
from supabase import create_client, Client


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

supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

class UserState:
    def __init__(self, user_id):
        self.user_id = user_id
        self.weight_unit = None
        self.weight = None
        self.goal = None
        self.level = None

    def save_to_db(self):
        data = {
            "user_id": self.user_id,
            "weight_unit": self.weight_unit,
            "weight": self.weight,
            "goal": self.goal.name if self.goal else None,
            "level": self.level,
            "last_updated": datetime.now().isoformat()
        }
        supabase.table("users").upsert(data).execute()

def init_db():
    # Create users table
    supabase.table("users").create({
        "user_id": "int8",
        "weight_unit": "text",
        "weight": "float8",
        "goal": "text",
        "level": "int2",
        "last_updated": "timestamp"
    }, primary_key="user_id")

    # Create payments table
    supabase.table("payments").create({
        "payment_id": "int8",
        "user_id": "int8",
        "amount": "float8",
        "currency": "text",
        "telegram_payment_charge_id": "text",
        "timestamp": "timestamp"
    }, primary_key="payment_id")

def get_user_state(user_id):
    response = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if response.data:
        user_data = response.data[0]
        user_state = UserState(user_id)
        user_state.weight_unit = user_data["weight_unit"]
        user_state.weight = user_data["weight"]
        user_state.goal = Goal[user_data["goal"]] if user_data["goal"] else None
        user_state.level = user_data["level"]
        return user_state
    return None
