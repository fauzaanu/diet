import logging
import os
from enum import Enum, auto

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, PreCheckoutQueryHandler, ContextTypes, ConversationHandler

# Diet plan constants
WEIGHT_UNIT, WEIGHT, GOAL, LEVEL, RESULT = range(5)

class Goal(Enum):
    EXTREME_WEIGHT_LOSS = auto()
    MODERATE_WEIGHT_LOSS = auto()
    MAINTENANCE = auto()
    MODERATE_WEIGHT_GAIN = auto()
    EXTREME_WEIGHT_GAIN = auto()

GOAL_LEVELS = {
    Goal.EXTREME_WEIGHT_LOSS: [7, 8, 9],
    Goal.MODERATE_WEIGHT_LOSS: [10, 11, 12],
    Goal.MAINTENANCE: [13, 14, 15],
    Goal.MODERATE_WEIGHT_GAIN: [16, 17, 18],
    Goal.EXTREME_WEIGHT_GAIN: [19, 20, 21]
}

class UserState:
    def __init__(self):
        self.weight_unit = None
        self.weight = None
        self.goal = None
        self.level = None

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [['kg', 'lbs']]
    await update.message.reply_text(
        "Welcome to the Diet Plan Bot! Let's create a personalized plan based on Alex Hormozi's method.\n\n"
        "First, please choose your preferred weight unit:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    context.user_data['state'] = UserState()
    return WEIGHT_UNIT

async def weight_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_state = context.user_data['state']
    user_state.weight_unit = update.message.text
    await update.message.reply_text(
        f"Great! Now, please enter your weight in {user_state.weight_unit}:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return WEIGHT

async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_state = context.user_data['state']
    try:
        user_state.weight = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid number for your weight.")
        return WEIGHT

    goals = [goal.name.replace('_', ' ').title() for goal in Goal]
    reply_keyboard = [[goal] for goal in goals]
    await update.message.reply_text(
        "What's your goal?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return GOAL

async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_state = context.user_data['state']
    user_state.goal = Goal[update.message.text.replace(' ', '_').upper()]
    
    levels = GOAL_LEVELS[user_state.goal]
    reply_keyboard = [[str(level)] for level in levels]
    await update.message.reply_text(
        f"Choose a level for {user_state.goal.name.replace('_', ' ').title()}:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return LEVEL

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_state = context.user_data['state']
    user_state.level = int(update.message.text)
    
    # Calculate the diet plan
    weight_in_lbs = user_state.weight if user_state.weight_unit == 'lbs' else user_state.weight * 2.20462
    calories = round(weight_in_lbs * user_state.level)
    protein = round(weight_in_lbs)
    
    result = (
        f"Here's your personalized diet plan:\n\n"
        f"Daily Calorie Target: {calories} calories\n"
        f"Daily Protein Target: {protein}g\n\n"
        f"Remember to distribute your calories and protein throughout the day. "
        f"You can adjust your meals based on your preferences, as long as you meet these targets."
    )
    
    await update.message.reply_text(result, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Diet plan creation cancelled. Type /start to begin again.", 
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def send_invoice(update, context):
    await context.bot.send_invoice(
        chat_id=update.message.chat.id,
        title='Sample Invoice',
        description='This is a sample invoice',
        payload='WPBOT-PYLD',
        currency='XTR',
        prices=[
            LabeledPrice('Basic', 100)
        ],
        provider_token='',
    )


async def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload != 'WPBOT-PYLD':
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)


async def successful_payment_callback(update, context):
    """
    This is recieved on successful payment.
    chargeback id can be found by clicking the service message in the chat. (if you are testing).
    This is a good place to store the charg id in your database and to process your internal balance
    or subscription logic.
    """
    print(update.message.successful_payment)


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
    application = ApplicationBuilder().token(token).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            WEIGHT_UNIT: [MessageHandler(filters.Regex('^(kg|lbs)$'), weight_unit)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal)],
            LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Keep other handlers
    invoice = CommandHandler('invoice', send_invoice)
    refund = CommandHandler('refund', refund_payment)
    successful_payment = MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)

    application.add_handler(invoice)
    application.add_handler(refund)
    application.add_handler(successful_payment)

    # Pre-checkout handler to final check
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    application.run_polling()
