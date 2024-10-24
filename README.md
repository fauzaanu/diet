# Alex Hormozi Diet Bot 🥗💪

This Telegram bot implements the diet plan based on Alex Hormozi's method, as explained in his [video](https://youtu.be/fxyhIXZ6Yog). It provides personalized diet recommendations and meal plans based on user input. The meals are simply a query to chatgpt to keep it simple and 100% cost free for anyone to run it locally.

## Features

- Personalized calorie and protein targets based on user's weight and goals
- Support for both metric (kg) and imperial (lbs) weight units
- Five different goal options: from extreme weight loss to extreme weight gain
- Three intensity levels for each goal
- Customized meal plan suggestions based on user's favorite foods
- Integration with ChatGPT for generating meal ideas

## How It Works

1. The bot asks for the user's weight unit preference (kg or lbs)
2. User inputs their current weight
3. User selects their goal (weight loss, maintenance, or weight gain)
4. User chooses an intensity level
5. The bot calculates personalized calorie and protein targets based on the calculation done on the video

The bot is complete as of now but I thought of adding some more stuff

6. User inputs their favorite foods
7. The bot generates a ChatGPT prompt for meal planning based on his calculated calories and favourite foods
8. A link button is sent with the prompt in the query string. (clicking it starts the chat and sends the preloaded message to chatgpt)

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up your environment variables:
   - Create a `.env` file in the project root
   - Add your Telegram Bot Token: `TELEGRAM_BOT_TOKEN=your_token_here`
4. Run the bot:
   ```
   python bot.py
   ```

## Usage

1. Start a chat with the bot on Telegram
2. Use the `/start` command to begin the diet plan creation process
3. Follow the bot's prompts to input your information and preferences
4. Receive your personalized diet plan and meal suggestions
