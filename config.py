import os

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your-bot-token-here')

# Message templates
WELCOME_MESSAGE = """
Вітаємо в нашій групі! 👋
Будь ласка, ознайомтесь з правилами групи перед початком спілкування.
"""

RULES_TEXT = """
📜 Правила групи:
1. Поважайте інших учасників
2. Дотримуйтесь тематики групи
3. В темі #resale використовуйте хештеги #продам або #куплю
4. Заборонено спам та рекламу
"""

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# Topic moderation
REQUIRED_HASHTAGS = ['#продам', '#куплю']