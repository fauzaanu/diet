import logging
import os
import sqlite3
from enum import Enum, auto
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, Poll
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, PreCheckoutQueryHandler, ContextTypes, ConversationHandler, CallbackQueryHandler, PollHandler
import urllib.parse

# Diet plan constants
WEIGHT_UNIT, WEIGHT, GOAL, LEVEL, MEAL_SUGGESTION, PROCESS_POLL, RESULT = range(7)

# Poll timeout in seconds
POLL_TIMEOUT = 60

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
    Goal.EXTREME_WEIGHT_GAIN: [1, 2, 3]
}

LEVEL_MULTIPLIERS = {
    Goal.EXTREME_WEIGHT_LOSS: {1: 7, 2: 8, 3: 9},
    Goal.MODERATE_WEIGHT_LOSS: {1: 10, 2: 11, 3: 12},
    Goal.MAINTENANCE: {1: 13, 2: 14, 3: 15},
    Goal.MODERATE_WEIGHT_GAIN: {1: 16, 2: 17, 3: 18},
    Goal.EXTREME_WEIGHT_GAIN: {1: 19, 2: 20, 3: 21}
}

class UserState:
    def __init__(self, user_id):
        self.user_id = user_id
        self.weight_unit = None
        self.weight = None
        self.goal = None
        self.level = None

    def save_to_db(self):
        conn = sqlite3.connect('diet_bot.db')
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO users
                     (user_id, weight_unit, weight, goal, level, last_updated)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (self.user_id, self.weight_unit, self.weight,
                   self.goal.name if self.goal else None, self.level,
                   datetime.now()))
        conn.commit()
        conn.close()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def init_db():
    conn = sqlite3.connect('diet_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  weight_unit TEXT,
                  weight REAL,
                  goal TEXT,
                  level INTEGER,
                  last_updated TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments
                 (payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  amount REAL,
                  currency TEXT,
                  telegram_payment_charge_id TEXT,
                  timestamp TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    conn.commit()
    conn.close()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("kg 🇪🇺", callback_data="kg"),
         InlineKeyboardButton("lbs 🇺🇸", callback_data="lbs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to the Diet Plan Bot! 🥗💪\n\n"
        "Let's create a personalized plan based on Alex Hormozi's method.\n\n"
        "First, please choose your preferred weight unit:",
        reply_markup=reply_markup,
    )
    context.user_data['state'] = UserState(user_id)
    return WEIGHT_UNIT

async def weight_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_state = context.user_data['state']
    user_state.weight_unit = query.data
    await query.edit_message_text(
        f"Great! 👍 Now, please enter your weight in {user_state.weight_unit}:"
    )
    return WEIGHT

async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_state = context.user_data['state']
    try:
        user_state.weight = float(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid number for your weight.")
        return WEIGHT

    goals = [
        ("Extreme Weight Loss 🏋️‍♂️", "EXTREME_WEIGHT_LOSS"),
        ("Moderate Weight Loss 🚶‍♂️", "MODERATE_WEIGHT_LOSS"),
        ("Maintenance 🧘‍♂️", "MAINTENANCE"),
        ("Moderate Weight Gain 🍽️", "MODERATE_WEIGHT_GAIN"),
        ("Extreme Weight Gain 💪", "EXTREME_WEIGHT_GAIN")
    ]
    keyboard = [[InlineKeyboardButton(goal[0], callback_data=goal[1])] for goal in goals]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Great! 🎯 What's your goal?",
        reply_markup=reply_markup,
    )
    return GOAL

async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_state = context.user_data['state']
    user_state.goal = Goal[query.data]
    
    levels = GOAL_LEVELS[user_state.goal]
    keyboard = [[InlineKeyboardButton(f"Level {level} {'🔥' * level}", callback_data=str(level)) for level in levels]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Awesome choice! 🌟 Now, choose an intensity level for {user_state.goal.name.replace('_', ' ').title()}:",
        reply_markup=reply_markup,
    )
    return LEVEL

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_state = context.user_data['state']
    user_state.level = int(query.data)
    
    # Save user data to the database
    user_state.save_to_db()
    
    # Calculate the diet plan
    weight_in_lbs = user_state.weight if user_state.weight_unit == 'lbs' else user_state.weight * 2.20462
    multiplier = LEVEL_MULTIPLIERS[user_state.goal][user_state.level]
    calories = round(weight_in_lbs * multiplier)
    protein = round(weight_in_lbs)
    
    result = (
        f"🎉 Congratulations! Here's your personalized diet plan:\n\n"
        f"🍽️ Daily Calorie Target: {calories} calories\n"
        f"🥩 Daily Protein Target: {protein}g\n\n"
        f"💡 Remember to distribute your calories and protein throughout the day. "
        f"You can adjust your meals based on your preferences, as long as you meet these targets.\n\n"
        f"Good luck on your journey! 💪🌟"
    )
    
    await query.edit_message_text(result)
    
    # Move to meal suggestion poll
    protein_sources = [
        "Chicken 🍗",
        "Beef 🥩",
        "Fish 🐟",
        "Eggs 🥚",
        "Tofu 🧊",
        "Beans 🫘",
    ]
    sent_poll = await context.bot.send_poll(
        chat_id=query.message.chat_id,
        question="Now, let's find some meal ideas! 🍽️\nWhat are your favorite protein sources? (You can choose multiple)",
        options=protein_sources,
        is_anonymous=False,
        allows_multiple_answers=True,
        type=Poll.REGULAR,
    )
    
    # Store the poll message id and chat id for later use
    context.user_data['poll_message_id'] = sent_poll.message_id
    context.user_data['chat_id'] = query.message.chat_id
    
    # Set up a job to stop the poll after the timeout
    context.job_queue.run_once(stop_poll, POLL_TIMEOUT, context=context.user_data)
    
    # Send a "Continue" button
    keyboard = [[InlineKeyboardButton("Continue ➡️", callback_data="continue_after_poll")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"After you've made your selections, click 'Continue' to proceed. The poll will automatically close in {POLL_TIMEOUT} seconds.",
        reply_markup=reply_markup
    )
    
    return MEAL_SUGGESTION

async def process_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    try:
        # Try to stop the poll if it's still active
        await context.bot.stop_poll(
            chat_id=context.user_data['chat_id'],
            message_id=context.user_data['poll_message_id']
        )
    except Exception as e:
        logging.info(f"Poll already closed or error occurred: {e}")
    
    # Get the poll results
    try:
        poll_message = await context.bot.get_poll(
            chat_id=context.user_data['chat_id'],
            message_id=context.user_data['poll_message_id']
        )
        
        selected_options = [option.text for option in poll_message.options if option.voter_count > 0]
        
        if not selected_options:
            await query.edit_message_text("It seems you haven't selected any protein sources. Let's try again!")
            return MEAL_SUGGESTION
        
        # Create search query
        search_query = f"{' '.join(selected_options)} recipes for {context.user_data['state'].goal.name.lower().replace('_', ' ')}"
        encoded_query = urllib.parse.quote(search_query)
        search_url = f"https://www.google.com/search?q={encoded_query}"
        
        keyboard = [[InlineKeyboardButton("Find Recipes 🔍", url=search_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"Great choices! 👨‍🍳 I've prepared a search for recipes with {', '.join(selected_options)} that match your goals.\n"
                 f"Click the button below to find delicious meal ideas:",
            reply_markup=reply_markup,
        )
        return ConversationHandler.END
    except Exception as e:
        logging.error(f"Error processing poll results: {e}")
        await query.edit_message_text("Sorry, there was an error processing your selections. Please try again later.")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Diet plan creation cancelled. 😔 Type /start to begin again when you're ready! 🚀"
    )
    return ConversationHandler.END


async def send_donate_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_invoice(
        chat_id=update.message.chat.id,
        title='Donate to Diet Plan Bot',
        description='Support the development of the Diet Plan Bot',
        payload='DIETBOT-DONATE',
        currency='USD',
        prices=[
            LabeledPrice('Donation', 500)  # $5.00
        ],
        provider_token=os.environ['PAYMENT_PROVIDER_TOKEN'],
    )


async def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload != 'WPBOT-PYLD':
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    amount = payment.total_amount / 100  # Convert from cents to dollars
    currency = payment.currency
    charge_id = payment.telegram_payment_charge_id

    conn = sqlite3.connect('diet_bot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO payments
                 (user_id, amount, currency, telegram_payment_charge_id, timestamp)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, amount, currency, charge_id, datetime.now()))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"Thank you for your donation of {amount} {currency}!")


async def refund_payment(update, context):
    """
    This is a sample refund function.
    """
    db = "LETS SAY THIS IS YOUR DB AND YOU HAVE PAYMENTS STORED HERE"  # just an example, dont be insane
    status = await context.bot.refund_star_payment(
        user_id=update.message.chat.id,
        telegram_payment_charge_id=db.telegram_charge_id
    )
    if status:
        await context.bot.send_message(
            chat_id=update.message.chat.id,
            text=f'Your payment {db.telegram_charge_id} has been refunded successfully.'
        )


if __name__ == '__main__':
    load_dotenv()
    token = os.environ['TELEGRAM_BOT_TOKEN']
    init_db()
    application = ApplicationBuilder().token(token).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            WEIGHT_UNIT: [CallbackQueryHandler(weight_unit, pattern='^(kg|lbs)$')],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
            GOAL: [CallbackQueryHandler(goal)],
            LEVEL: [CallbackQueryHandler(level)],
            MEAL_SUGGESTION: [CallbackQueryHandler(process_poll, pattern='^continue_after_poll$')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Store protein sources in bot_data for easy access
    application.bot_data['protein_sources'] = [
        "Chicken 🍗",
        "Beef 🥩",
        "Fish 🐟",
        "Eggs 🥚",
        "Tofu 🧊",
        "Beans 🫘",
    ]

    # Keep other handlers
    donate = CommandHandler('donate', send_donate_invoice)
    refund = CommandHandler('refund', refund_payment)
    successful_payment = MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)

    application.add_handler(donate)
    application.add_handler(refund)
    application.add_handler(successful_payment)

    # Pre-checkout handler to final check
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    application.run_polling()
async def stop_poll(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.context['chat_id']
    poll_message_id = job.context['poll_message_id']
    
    try:
        poll = await context.bot.stop_poll(
            chat_id=chat_id,
            message_id=poll_message_id
        )
        logging.info(f"Poll stopped: {poll}")
    except Exception as e:
        logging.error(f"Error stopping poll: {e}")
