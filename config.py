import os

class Config:
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    DATABASE_FILE = os.getenv('DATABASE_FILE', 'aliases.db')
    MAX_ALIASES_PER_GENERATE = 100
    MAX_DOT_ALIASES = 30
    MAX_CUSTOM_ALIASES = 30
    ADMIN_USER_IDS = [int(x) for x in os.getenv('ADMIN_USER_IDS', '').split(',') if x]
    RATE_LIMIT_WINDOW_SECONDS = 3600
    RATE_LIMIT_MAX_REQUESTS = 100