import logging
import os
from supabase import create_client, Client
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    CommandHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
import urllib.parse

from database import UserState, Goal, GOAL_LEVELS, LEVEL_MULTIPLIERS, init_db, get_user_state, supabase

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Diet plan constants
WEIGHT_UNIT, WEIGHT, GOAL, LEVEL, FAVORITE_FOODS, RESULT = range(6)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_state = get_user_state(user_id)
    
    if user_state:
        # User exists, ask if they want to start over
        keyboard = [
            [InlineKeyboardButton("Start Over", callback_data="start_over")],
            [InlineKeyboardButton("Continue", callback_data="continue")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Welcome back! 👋 Do you want to start over or continue with your existing plan?",
            reply_markup=reply_markup
        )
        return WEIGHT_UNIT
    else:
        # New user, start from the beginning
        keyboard = [
            [
                InlineKeyboardButton("kg 🇪🇺", callback_data="kg"),
                InlineKeyboardButton("lbs 🇺🇸", callback_data="lbs"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👋 Welcome to the Diet Plan Bot! 🥗💪\n\n"
            "Let's create a personalized plan based on Alex Hormozi's method.\n\n"
            "First, please choose your preferred weight unit:",
            reply_markup=reply_markup,
        )
        context.user_data["state"] = UserState(user_id)
        return WEIGHT_UNIT


async def weight_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_state = context.user_data["state"]
    user_state.weight_unit = query.data
    await query.edit_message_text(
        f"Great! 👍 Now, please enter your weight in {user_state.weight_unit}:"
    )
    return WEIGHT


async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_state = context.user_data["state"]
    try:
        user_state.weight = float(update.message.text)
    except ValueError:
        await update.message.reply_text(
            "⚠️ Please enter a valid number for your weight."
        )
        return WEIGHT

    goals = [
        ("Extreme Weight Loss 🏋️‍♂️", "EXTREME_WEIGHT_LOSS"),
        ("Moderate Weight Loss 🚶‍♂️", "MODERATE_WEIGHT_LOSS"),
        ("Maintenance 🧘‍♂️", "MAINTENANCE"),
        ("Moderate Weight Gain 🍽️", "MODERATE_WEIGHT_GAIN"),
        ("Extreme Weight Gain 💪", "EXTREME_WEIGHT_GAIN"),
    ]
    keyboard = [
        [InlineKeyboardButton(goal[0], callback_data=goal[1])] for goal in goals
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Great! 🎯 What's your goal?",
        reply_markup=reply_markup,
    )
    return GOAL


async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_state = context.user_data["state"]
    user_state.goal = Goal[query.data]

    levels = GOAL_LEVELS[user_state.goal]
    keyboard = [
        [
            InlineKeyboardButton(
                f"Level {level} {'🔥' * level}", callback_data=str(level)
            )
            for level in levels
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Awesome choice! 🌟 Now, choose an intensity level for {user_state.goal.name.replace('_', ' ').title()}:",
        reply_markup=reply_markup,
    )
    return LEVEL


async def level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_state = context.user_data["state"]
    user_state.level = int(query.data)

    # Save user data to the database
    user_state.save_to_db()

    # Calculate the diet plan
    weight_in_lbs = (
        user_state.weight
        if user_state.weight_unit == "lbs"
        else user_state.weight * 2.20462
    )
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

    # Ask for favorite foods
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Now, let's personalize your meal ideas! 🍽️\n"
        "Please send me a list of foods you love eating, separated by commas.\n"
        "For example: fish,chicken,cheese,hot chocolate,",
    )

    return FAVORITE_FOODS


async def process_favorite_foods(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_state = context.user_data["state"]
    favorite_foods = [
        food.strip() for food in update.message.text.split(",") if food.strip()
    ]

    if not favorite_foods:
        await update.message.reply_text(
            "It seems you haven't entered any foods. Please try again!"
        )
        return FAVORITE_FOODS

    # Calculate calories and protein targets
    weight_in_lbs = (
        user_state.weight
        if user_state.weight_unit == "lbs"
        else user_state.weight * 2.20462
    )
    multiplier = LEVEL_MULTIPLIERS[user_state.goal][user_state.level]
    calories = round(weight_in_lbs * multiplier)
    protein = round(weight_in_lbs)

    # Create ChatGPT prompt
    prompt = f"Here is a list of my favorite foods:\n{', '.join(favorite_foods)}\n\n"
    prompt += "Please help me plan meals for my day based on these foods. "
    prompt += f"I have the following constraint: {user_state.goal.name.lower().replace('_', ' ')}. "
    prompt += f"My daily calorie target is {calories} calories and my daily protein target is {protein}g. "
    prompt += ("Please suggest a full day's meal plan including breakfast, lunch, dinner, and snacks."
               "Please ensure that the total calorie goal is met and only the foods listed are used.")

    encoded_prompt = urllib.parse.quote(prompt)
    chat_url = f"https://www.chatgpt.com/?q={encoded_prompt}"

    keyboard = [[InlineKeyboardButton("Get Meal Plan 🍽️", url=chat_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text="Great choices! 👨‍🍳 I've prepared a prompt for ChatGPT to create a personalized meal plan based on your favorite foods and goals.\n"
        "Click the button below to get your custom meal plan:",
        reply_markup=reply_markup,
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Diet plan creation cancelled. 😔 Type /start to begin again when you're ready! 🚀"
    )
    return ConversationHandler.END


async def send_donate_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_invoice(
        chat_id=update.message.chat.id,
        title="Donate to Diet Plan Bot",
        description="Help us keep this bot alive on a server",
        payload="DIETBOT-DONATE",
        currency="XTR",
        prices=[
            LabeledPrice("Donation", 100)  # $5.00
        ],
        provider_token="",
    )


async def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload != "WPBOT-PYLD":
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)


async def successful_payment_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    amount = payment.total_amount / 100  # Convert from cents to dollars
    currency = payment.currency
    charge_id = payment.telegram_payment_charge_id

    data = {
        "user_id": user_id,
        "amount": amount,
        "currency": currency,
        "telegram_payment_charge_id": charge_id,
        "timestamp": datetime.now().isoformat()
    }
    supabase.table("payments").insert(data).execute()

    await update.message.reply_text(
        f"Thank you for your donation of {amount} {currency}!"
    )


if __name__ == "__main__":
    load_dotenv()
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    init_db()
    application = ApplicationBuilder().token(token).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            WEIGHT_UNIT: [CallbackQueryHandler(weight_unit, pattern="^(kg|lbs)$")],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
            GOAL: [CallbackQueryHandler(goal)],
            LEVEL: [CallbackQueryHandler(level)],
            FAVORITE_FOODS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_favorite_foods)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Keep other handlers
    donate = CommandHandler("donate", send_donate_invoice)
    successful_payment = MessageHandler(
        filters.SUCCESSFUL_PAYMENT, successful_payment_callback
    )

    application.add_handler(donate)
    application.add_handler(successful_payment)

    # Pre-checkout handler to final check
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    application.run_polling()
