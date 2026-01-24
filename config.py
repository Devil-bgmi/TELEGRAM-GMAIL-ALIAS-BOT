import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_required_env(var_name: str, default: str = None) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(var_name, default)
    if not value:
        raise ValueError(f"❌ Environment variable '{var_name}' is not set!")
    return value

def get_optional_env(var_name: str, default: str) -> str:
    """Get optional environment variable."""
    return os.getenv(var_name, default)

class Config:
    # Required
    BOT_TOKEN = get_required_env('TELEGRAM_BOT_TOKEN')
    
    # Optional with defaults
    DATABASE_FILE = get_optional_env('DATABASE_FILE', 'aliases.db')
    MAX_ALIASES_PER_USER = int(get_optional_env('MAX_ALIASES_PER_USER', '1000'))
    MAX_DOT_VARIANTS = int(get_optional_env('MAX_DOT_VARIANTS', '100'))
    
    # Admin IDs (comma separated)
    admin_ids = get_optional_env('ADMIN_USER_IDS', '').strip()
    ADMIN_USER_IDS = [int(x.strip()) for x in admin_ids.split(',') if x.strip()] if admin_ids else []
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE = int(get_optional_env('RATE_LIMIT_PER_MINUTE', '30'))
    RATE_LIMIT_PER_HOUR = int(get_optional_env('RATE_LIMIT_PER_HOUR', '200'))
    
    # Gmail-specific
    GMAIL_DOMAINS = ['gmail.com', 'googlemail.com']
    
    def validate(self):
        """Validate configuration."""
        if not self.BOT_TOKEN.startswith(''):
            raise ValueError("Invalid Telegram Bot Token format")
        return True

# Create and validate config instance
try:
    config = Config()
    config.validate()
    print("✅ Configuration loaded successfully!")
except Exception as e:
    print(f"❌ Configuration error: {e}")
    exit(1)
