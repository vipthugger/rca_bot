import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from flask import Flask, request
import logging
import asyncio
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Constants
REQUIRED_HASHTAGS = ['#продам', '#куплю']
MIN_PRICE = 3000  # Minimum price in UAH
MESSAGE_COOLDOWN_MINUTES = 60
MAX_MESSAGES_BEFORE_COOLDOWN = 3
NOTIFICATION_DELETE_DELAY = 10  # seconds
WELCOME_MESSAGE_DELETE_DELAY = 15  # seconds

WELCOME_MESSAGE = """👋 Вітаємо, {username}! Ознайомтеся з правилами, щоб уникнути непорозумінь. Приємного спілкування!"""

# Initialize bot and dispatcher
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("No TELEGRAM_TOKEN found in environment variables")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Store monitored topic ID and user message tracking
resale_topic_id = None
user_last_message_time = {}  # Time of user's last message
user_message_count = {}      # Count of user's messages

def extract_price(text: str) -> int:
    """Extract price from message text"""
    text = text.lower().replace(' ', '')
    k_match = re.search(r'(\d+)[kкК]', text)
    if k_match:
        return int(k_match.group(1)) * 1000
    price_match = re.search(r'(\d+)(?:грн|uah)?', text)
    if price_match:
        return int(price_match.group(1))
    return 0

@dp.message(CommandStart())
async def start_command(message: types.Message):
    """Handle /start command"""
    await message.reply("Привіт! Я бот для модерації чату.")

@dp.message(Command(commands=['resale_topic']))
async def set_resale_topic(message: types.Message):
    """Set topic for monitoring resale messages"""
    global resale_topic_id
    try:
        if not message.message_thread_id:
            notification = await message.reply("Будь ласка, використовуйте цю команду в темі, яку хочете модерувати.")
            await message.delete()
            await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
            await notification.delete()
            return

        chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        await message.delete()

        if chat_member.status not in ['creator', 'administrator']:
            notification = await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Ця команда доступна тільки адміністраторам.",
                message_thread_id=message.message_thread_id
            )
            await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
            await notification.delete()
            return

        resale_topic_id = message.message_thread_id
        notification = await bot.send_message(
            chat_id=message.chat.id,
            text="✅ Бот тепер контролює цю гілку на відповідність правилам.",
            message_thread_id=message.message_thread_id
        )
        await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
        await notification.delete()

    except Exception as e:
        logger.error(f"Error setting resale topic: {e}")
        try:
            notification = await bot.send_message(
                chat_id=message.chat.id,
                text="Виникла помилка при встановленні теми для модерації.",
                message_thread_id=message.message_thread_id
            )
            await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
            await notification.delete()
        except Exception as inner_e:
            logger.error(f"Error sending error notification: {inner_e}")

@dp.message(lambda message: message.new_chat_members is not None)
async def handle_new_member(message: types.Message):
    """Welcome new members"""
    try:
        for new_member in message.new_chat_members:
            if new_member.is_bot:
                continue
            username = f"@{new_member.username}" if new_member.username else "новий учасник"
            welcome_msg = await message.reply(WELCOME_MESSAGE.format(username=username))
            await message.delete()
            await asyncio.sleep(WELCOME_MESSAGE_DELETE_DELAY)
            await welcome_msg.delete()
    except Exception as e:
        logger.error(f"Error handling new member: {e}")

@dp.message(lambda message: message.text and resale_topic_id and message.message_thread_id == resale_topic_id)
async def handle_resale_message(message: types.Message):
    """Handle messages in resale topic"""
    try:
        chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status in ['creator', 'administrator']:
            return

        user_id = message.from_user.id
        current_time = datetime.now()

        if user_id not in user_message_count:
            user_message_count[user_id] = 0
        user_message_count[user_id] += 1

        if user_message_count[user_id] > MAX_MESSAGES_BEFORE_COOLDOWN:
            if user_id in user_last_message_time:
                last_time = user_last_message_time[user_id]
                if current_time - last_time < timedelta(minutes=MESSAGE_COOLDOWN_MINUTES):
                    username = f"@{message.from_user.username}" if message.from_user.username else "користувач"
                    delete_reason = f"{username}, ви можете надсилати повідомлення у цю гілку лише раз на {MESSAGE_COOLDOWN_MINUTES} хвилин!"
                    await message.delete()
                    notification = await bot.send_message(
                        chat_id=message.chat.id,
                        text=delete_reason,
                        message_thread_id=resale_topic_id
                    )
                    await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
                    await notification.delete()
                    return

        user_last_message_time[user_id] = current_time

        if not any(tag.lower() in message.text.lower() for tag in REQUIRED_HASHTAGS):
            username = f"@{message.from_user.username}" if message.from_user.username else "користувач"
            delete_reason = f"{username}, ваше повідомлення було видалено, оскільки воно не містить необхідних хештегів {', '.join(REQUIRED_HASHTAGS)}."
            await message.delete()
            notification = await bot.send_message(
                chat_id=message.chat.id,
                text=delete_reason,
                message_thread_id=resale_topic_id
            )
            await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
            await notification.delete()
            user_message_count[user_id] -= 1
            return

        if '#продам' in message.text.lower():
            price = extract_price(message.text)
            if price < MIN_PRICE:
                username = f"@{message.from_user.username}" if message.from_user.username else "користувач"
                delete_reason = f"{username}, ваше повідомлення було видалено. Мінімальна ціна для продажу - {MIN_PRICE} грн."
                await message.delete()
                notification = await bot.send_message(
                    chat_id=message.chat.id,
                    text=delete_reason,
                    message_thread_id=resale_topic_id
                )
                await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
                await notification.delete()
                user_message_count[user_id] -= 1
                return

    except Exception as e:
        logger.error(f"Error handling resale message: {str(e)}")

# Flask routes
@app.route('/' + TELEGRAM_TOKEN, methods=['POST'])
async def webhook():
    """Process incoming updates via webhook"""
    try:
        if not request.is_json:
            logger.error("Received non-JSON request")
            return 'Error: Invalid Content-Type', 400

        update_data = await request.get_json()
        logger.info(f"Received update: {json.dumps(update_data, indent=2)}")

        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        return 'OK', 200
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        return 'Error', 500

@app.route('/')
def index():
    """Health check endpoint"""
    return 'Bot is running', 200

# Startup function
async def on_startup():
    """Configure webhook on startup"""
    try:
        VERCEL_URL = os.getenv('VERCEL_URL')
        if not VERCEL_URL:
            logger.error("No VERCEL_URL found in environment variables")
            return

        webhook_url = f"https://{VERCEL_URL}/{TELEGRAM_TOKEN}"
        logger.info(f"Setting webhook to: {webhook_url}")

        await bot.delete_webhook()  # Clean up any existing webhook
        await bot.set_webhook(webhook_url)
        logger.info("Webhook set successfully")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        asyncio.run(on_startup())
        port = int(os.getenv('PORT', 3000))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Error starting the bot: {e}", exc_info=True)
        raise