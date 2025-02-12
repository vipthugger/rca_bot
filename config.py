import os
import logging

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your-bot-token-here')

# Message templates
WELCOME_MESSAGE = """👋 Вітаємо, {username}! Ознайомтеся з правилами, щоб уникнути непорозумінь. Приємного спілкування!"""

RULES_TEXT = """
📜 Правила групи:
1. Поважайте інших учасників
2. Дотримуйтесь тематики групи
3. В темі #resale використовуйте хештеги #продам або #куплю
4. Заборонено спам та рекламу
"""

# Topic monitoring
REQUIRED_HASHTAGS = ['#продам', '#куплю']
MESSAGE_COOLDOWN_MINUTES = 60
MAX_MESSAGES_BEFORE_COOLDOWN = 3
NOTIFICATION_DELETE_DELAY = 10  # seconds
WELCOME_MESSAGE_DELETE_DELAY = 15  # seconds

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO