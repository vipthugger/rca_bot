import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from config import (
    BOT_TOKEN, RULES_TEXT, WELCOME_MESSAGE, REQUIRED_HASHTAGS,
    MESSAGE_COOLDOWN_MINUTES, MAX_MESSAGES_BEFORE_COOLDOWN,
    NOTIFICATION_DELETE_DELAY, WELCOME_MESSAGE_DELETE_DELAY,
    MIN_PRICE
)
from logger import logger
from datetime import datetime, timedelta

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Store monitored topic ID and user message tracking
resale_topic_id = None
user_last_message_time = {}  # Time of user's last message
user_message_count = {}      # Count of user's messages

def extract_price(text: str) -> int:
    """
    Extract price from message text, handling different formats:
    - Plain numbers: 3000, 3 000
    - With currency: 3000грн, 3000 грн
    - Short format: 3k, 3К, 3к
    Returns 0 if no valid price found
    """
    # Remove spaces from text for easier processing
    text = text.lower().replace(' ', '')

    # Try to find price in format "3k" or "3к" (both cyrillic and latin)
    k_match = re.search(r'(\d+)[kкК]', text)
    if k_match:
        return int(k_match.group(1)) * 1000

    # Try to find regular price, handling optional currency
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
        logger.info(f"Processing /resale_topic command from user {message.from_user.id}")

        # Get topic ID from command message
        if not message.message_thread_id:
            logger.info("Command used outside of topic")
            notification = await message.reply("Будь ласка, використовуйте цю команду в темі, яку хочете модерувати.")
            await message.delete()
            await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
            await notification.delete()
            return

        # Check admin rights
        chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        logger.info(f"User status: {chat_member.status}")

        # Delete command message first
        await message.delete()

        if chat_member.status not in ['creator', 'administrator']:
            logger.info("Non-admin user attempted to use /resale_topic command")
            notification = await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Ця команда доступна тільки адміністраторам.",
                message_thread_id=message.message_thread_id
            )
            await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
            await notification.delete()
            return

        resale_topic_id = message.message_thread_id
        logger.info(f"Admin user set resale_topic_id to {resale_topic_id}")

        # Send success notification for admins
        notification = await bot.send_message(
            chat_id=message.chat.id,
            text="✅ Бот тепер контролює цю гілку на відповідність правилам.",
            message_thread_id=message.message_thread_id
        )

        # Delete success notification after delay
        await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
        await notification.delete()

        logger.info(f"Resale topic set to {resale_topic_id}")
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

            # If username exists, use username, otherwise use "новий учасник"
            username = f"@{new_member.username}" if new_member.username else "новий учасник"
            welcome_msg = await message.reply(
                WELCOME_MESSAGE.format(username=username)
            )

            # Delete the system message about user joining
            await message.delete()

            # Delete welcome message after some time
            await asyncio.sleep(WELCOME_MESSAGE_DELETE_DELAY)
            await welcome_msg.delete()

            logger.info(f"New member welcomed: {new_member.id}")
    except Exception as e:
        logger.error(f"Error handling new member: {e}")

@dp.message(lambda message: message.text and resale_topic_id and message.message_thread_id == resale_topic_id)
async def handle_resale_message(message: types.Message):
    """Handle messages in resale topic"""
    try:
        # Skip admin messages
        chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status in ['creator', 'administrator']:
            logger.info(f"Admin message allowed: user_id={message.from_user.id}")
            return

        user_id = message.from_user.id
        current_time = datetime.now()

        logger.info(f"Processing message in resale topic: user_id={user_id}, message_id={message.message_id}")

        # Initialize message count for new users
        if user_id not in user_message_count:
            user_message_count[user_id] = 0
        user_message_count[user_id] += 1

        # Check cooldown period after max messages
        if user_message_count[user_id] > MAX_MESSAGES_BEFORE_COOLDOWN:
            if user_id in user_last_message_time:
                last_time = user_last_message_time[user_id]
                if current_time - last_time < timedelta(minutes=MESSAGE_COOLDOWN_MINUTES):
                    username = f"@{message.from_user.username}" if message.from_user.username else "користувач"
                    delete_reason = f"{username}, ви можете надсилати повідомлення у цю гілку лише раз на {MESSAGE_COOLDOWN_MINUTES} хвилин!"

                    await message.delete()
                    logger.info(f"Cooldown triggered: user_id={user_id}, message_count={user_message_count[user_id]}")

                    notification = await bot.send_message(
                        chat_id=message.chat.id,
                        text=delete_reason,
                        message_thread_id=resale_topic_id
                    )
                    await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
                    await notification.delete()
                    return

        # Update last message time
        user_last_message_time[user_id] = current_time

        # Check for required hashtags
        if not any(tag.lower() in message.text.lower() for tag in REQUIRED_HASHTAGS):
            username = f"@{message.from_user.username}" if message.from_user.username else "користувач"
            delete_reason = f"{username}, ваше повідомлення було видалено, оскільки воно не містить необхідних хештегів {', '.join(REQUIRED_HASHTAGS)}."

            await message.delete()
            logger.info(f"Message deleted - missing hashtags: user_id={user_id}, message_id={message.message_id}")

            notification = await bot.send_message(
                chat_id=message.chat.id,
                text=delete_reason,
                message_thread_id=resale_topic_id
            )
            await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
            await notification.delete()

            # Decrease message count for deleted messages
            user_message_count[user_id] -= 1
            return

        # Check minimum price for sale posts
        if '#продам' in message.text.lower():
            price = extract_price(message.text)
            if price < MIN_PRICE:
                username = f"@{message.from_user.username}" if message.from_user.username else "користувач"
                delete_reason = f"{username}, ваше повідомлення було видалено. Мінімальна ціна для продажу - {MIN_PRICE} грн."

                await message.delete()
                logger.info(f"Message deleted - price too low: user_id={user_id}, price={price}")

                notification = await bot.send_message(
                    chat_id=message.chat.id,
                    text=delete_reason,
                    message_thread_id=resale_topic_id
                )
                await asyncio.sleep(NOTIFICATION_DELETE_DELAY)
                await notification.delete()

                # Decrease message count for deleted messages
                user_message_count[user_id] -= 1
                return

    except Exception as e:
        logger.error(f"Error handling resale message: {str(e)}, user_id={message.from_user.id if message.from_user else 'unknown'}")

async def main():
    """Start the bot"""
    try:
        logger.info("Bot started")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == '__main__':
    asyncio.run(main())