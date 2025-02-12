from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import REQUIRED_HASHTAGS
import re

async def check_admin_rights(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has admin rights"""
    if not update.effective_chat:
        return False
    
    try:
        user = await context.bot.get_chat_member(
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id
        )
        return user.status in ['creator', 'administrator']
    except Exception as e:
        return False

def create_rules_keyboard():
    """Create keyboard with rules acknowledgment button"""
    keyboard = [[InlineKeyboardButton(
        "Так, я прочитав(-ла) правила",
        callback_data="rules_accepted"
    )]]
    return InlineKeyboardMarkup(keyboard)

def check_required_hashtags(message_text: str) -> bool:
    """Check if message contains required hashtags"""
    if not message_text:
        return False
    
    message_hashtags = set(re.findall(r'#\w+', message_text.lower()))
    return any(hashtag.lower() in message_hashtags for hashtag in REQUIRED_HASHTAGS)

async def restrict_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restrict new member's ability to send messages"""
    if not update.effective_chat:
        return
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
            permissions={
                'can_send_messages': False,
                'can_send_media_messages': False,
                'can_send_other_messages': False,
                'can_add_web_page_previews': False
            }
        )
    except Exception as e:
        # Log error but don't raise it
        pass

async def remove_restrictions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove restrictions from user after accepting rules"""
    if not update.effective_chat:
        return
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
            permissions={
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True
            }
        )
    except Exception as e:
        # Log error but don't raise it
        pass
