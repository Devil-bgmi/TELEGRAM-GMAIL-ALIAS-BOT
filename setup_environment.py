#!/usr/bin/env python3
"""
Setup script for Gmail Alias Generator Bot
"""

import os
import sys

def setup_environment():
    """Setup environment for the bot."""
    print("="*50)
    print("🔧 Gmail Alias Generator - Setup")
    print("="*50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    # Check if .env exists
    env_file = '.env'
    if not os.path.exists(env_file):
        print("📝 Creating .env file...")
        
        env_content = """# Telegram Bot Token (get from @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional Settings
DATABASE_FILE=aliases.db
MAX_ALIASES_PER_USER=1000
MAX_DOT_VARIANTS=100
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_PER_HOUR=200

# Admin User IDs (comma separated, optional)
ADMIN_USER_IDS=
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print(f"✅ Created {env_file}")
        print("ℹ️  Please edit this file and add your bot token")
    else:
        print(f"✅ {env_file} already exists")
    
    # Check requirements
    print("\n📦 Checking requirements...")
    try:
        import telegram
        import python_dotenv
        print("✅ All dependencies are installed")
    except ImportError:
        print("❌ Some dependencies are missing")
        print("Run: pip install -r requirements.txt")
    
    print("\n" + "="*50)
    print("🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file and add your bot token")
    print("2. Run: python run_bot.py")
    print("="*50)

if __name__ == '__main__':
    setup_environment()
