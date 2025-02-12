import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from config import BOT_TOKEN, WELCOME_MESSAGE, RULES_TEXT, REQUIRED_HASHTAGS
from logger import logger

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Store monitored topic ID
resale_topic_id = None

@dp.message(CommandStart())
async def start_command(message: types.Message):
    """Handle /start command"""
    await message.reply("Привіт! Я бот для модерації групи та управління новими учасниками.")

@dp.message(Command(commands=['resale_topic']))
async def set_resale_topic(message: types.Message):
    """Set topic for monitoring resale messages"""
    global resale_topic_id

    # Check admin rights
    chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ['creator', 'administrator']:
        await message.reply("Ця команда доступна тільки для адміністраторів.")
        return

    try:
        # Get topic ID from command message
        if not message.message_thread_id:
            await message.reply("Будь ласка, використовуйте цю команду в темі, яку хочете модерувати.")
            return

        resale_topic_id = message.message_thread_id
        await message.reply(f"Тема з ID {resale_topic_id} тепер відслідковується для модерації.")
        logger.info(f"Resale topic set to {resale_topic_id}")
    except Exception as e:
        logger.error(f"Error setting resale topic: {e}")
        await message.reply("Виникла помилка при встановленні теми для модерації.")

@dp.message(lambda message: message.new_chat_members is not None)
async def handle_new_member(message: types.Message):
    """Welcome new members and restrict their permissions"""
    try:
        for new_member in message.new_chat_members:
            if new_member.is_bot:
                continue

            # Restrict member
            await bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=new_member.id,
                permissions=types.ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                )
            )

            # Send welcome message with inline button
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="Так, я прочитав(-ла) правила",
                    callback_data="rules_accepted"
                )
            ]])

            await message.reply(
                WELCOME_MESSAGE + "\n" + RULES_TEXT,
                reply_markup=keyboard
            )
            logger.info(f"New member welcomed: {new_member.id}")
    except Exception as e:
        logger.error(f"Error handling new member: {e}")

@dp.callback_query(lambda c: c.data == "rules_accepted")
async def handle_rules_acceptance(callback_query: types.CallbackQuery):
    """Handle rules acceptance button click"""
    try:
        # Remove restrictions
        await bot.restrict_chat_member(
            chat_id=callback_query.message.chat.id,
            user_id=callback_query.from_user.id,
            permissions=types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )

        # Answer callback query and edit message
        await callback_query.answer("Дякуємо! Тепер ви можете писати повідомлення.")
        await callback_query.message.edit_reply_markup(reply_markup=None)
        logger.info(f"User {callback_query.from_user.id} accepted rules")
    except Exception as e:
        logger.error(f"Error handling rules acceptance: {e}")

@dp.message(lambda message: message.text and resale_topic_id and message.message_thread_id == resale_topic_id)
async def handle_resale_message(message: types.Message):
    """Handle messages in resale topic"""
    try:
        # Skip admin messages
        chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status in ['creator', 'administrator']:
            return

        # Check for required hashtags
        if not any(tag.lower() in message.text.lower() for tag in REQUIRED_HASHTAGS):
            await message.delete()
            await message.answer(
                "Ваше повідомлення було видалено, оскільки воно не містить необхідних хештегів (#продам або #куплю).",
                message_thread_id=resale_topic_id
            )
            logger.info(f"Deleted message without required hashtags from user {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error handling resale message: {e}")

async def main():
    """Start the bot"""
    try:
        logger.info("Bot started")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == '__main__':
    asyncio.run(main())