from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from config import WELCOME_MESSAGE, RULES_TEXT
from logger import logger
from utils import (
    check_admin_rights,
    create_rules_keyboard,
    check_required_hashtags,
    restrict_new_member,
    remove_restrictions
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if update.message:
        await update.message.reply_text(
            "Привіт! Я бот для модерації групи та управління новими учасниками."
        )

async def resale_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resale_topic command for setting up topic monitoring"""
    if not update.message:
        return

    # Check admin rights
    is_admin = await check_admin_rights(update, context)
    if not is_admin:
        await update.message.reply_text(
            "Ця команда доступна тільки для адміністраторів."
        )
        return

    # Get topic ID from command arguments
    if not context.args:
        await update.message.reply_text(
            "Будь ласка, вкажіть ID теми після команди."
        )
        return

    try:
        topic_id = int(context.args[0])
        # Store topic ID in bot data
        context.bot_data['resale_topic_id'] = topic_id
        await update.message.reply_text(
            f"Тема з ID {topic_id} тепер відслідковується для модерації."
        )
    except ValueError:
        await update.message.reply_text(
            "Невірний формат ID теми. Будь ласка, вкажіть числове значення."
        )

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new member joins"""
    if not update.message or not update.message.new_chat_members:
        return

    for new_member in update.message.new_chat_members:
        if new_member.is_bot:
            continue

        # Restrict new member
        await restrict_new_member(update, context)

        # Send welcome message with rules
        try:
            await update.message.reply_text(
                WELCOME_MESSAGE + "\n" + RULES_TEXT,
                reply_markup=create_rules_keyboard()
            )
            logger.info(f"New member welcomed: {new_member.id}")
        except TelegramError as e:
            logger.error(f"Error welcoming new member: {e}")

async def handle_rules_acceptance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rules acceptance button click"""
    query = update.callback_query
    if not query:
        return

    if query.data != "rules_accepted":
        return

    try:
        # Remove restrictions
        await remove_restrictions(update, context)
        
        # Answer callback query
        await query.answer("Дякуємо! Тепер ви можете писати повідомлення.")
        
        # Edit original message to remove button
        await query.edit_message_reply_markup(reply_markup=None)
        
        logger.info(f"User {query.from_user.id} accepted rules")
    except TelegramError as e:
        logger.error(f"Error handling rules acceptance: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in resale topic"""
    if not update.message or not update.message.text:
        return

    # Check if message is in monitored topic
    topic_id = context.bot_data.get('resale_topic_id')
    if not topic_id or update.message.message_thread_id != topic_id:
        return

    # Check for required hashtags
    if not check_required_hashtags(update.message.text):
        try:
            await update.message.delete()
            await update.message.reply_text(
                "Ваше повідомлення було видалено, оскільки воно не містить необхідних хештегів (#продам або #куплю).",
                message_thread_id=topic_id
            )
            logger.info(f"Deleted message without required hashtags from user {update.message.from_user.id}")
        except TelegramError as e:
            logger.error(f"Error deleting message: {e}")
