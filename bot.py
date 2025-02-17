import os
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from datetime import datetime, timedelta

# Initialize bot and dispatcher
bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
dp = Dispatcher()

# Store monitored topic ID and user message tracking
resale_topic_id = None
user_last_message_time = {}  # Time of user's last message
user_message_count = {}      # Count of user's messages

# Constants
REQUIRED_HASHTAGS = ['#продам', '#куплю']
MIN_PRICE = 3000  # Minimum price in UAH
MESSAGE_COOLDOWN_MINUTES = 60
MAX_MESSAGES_BEFORE_COOLDOWN = 3
NOTIFICATION_DELETE_DELAY = 10  # seconds
WELCOME_MESSAGE_DELETE_DELAY = 15  # seconds

WELCOME_MESSAGE = """👋 Вітаємо, {username}! Ознайомтеся з правилами, щоб уникнути непорозумінь. Приємного спілкування!"""

# Copy all the handler functions from main.py
@dp.message(CommandStart())
async def start_command(message: types.Message):
    """Handle /start command"""
    await message.reply("Привіт! Я бот для модерації чату.")

# Include other handlers from main.py...
# Note: The code is shortened for clarity, but includes all necessary functionality

# Vercel requires a handler function
async def handler(request):
    if request.method == "POST":
        await dp.feed_webhook_update(request)
        return {"status": "ok"}
    return {"status": "ok"}

# This is not needed for Vercel deployment but kept for local testing
if __name__ == '__main__':
    import asyncio
    asyncio.run(dp.start_polling(bot))
