import os
import sys

def setup_environment():
    required_vars = ['TELEGRAM_BOT_TOKEN']
    
    print("🔧 Email Alias Bot - Environment Setup")
    print("=" * 50)
    
    if not os.path.exists('.env'):
        create_env_file()
    else:
        print("✅ .env file already exists")
    
    check_environment_variables(required_vars)
    print("\n🎉 Setup completed! You can now run the bot.")
    print("👉 Run: python alias_bot.py")

def create_env_file():
    env_content = """TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_FILE=aliases.db
MAX_ALIASES_PER_GENERATE=10
ADMIN_USER_IDS=123456789,987654321
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    print("✅ Created .env file")
    print("📝 Please edit .env file and add your Telegram Bot Token")

def check_environment_variables(required_vars):
    print("\n🔍 Checking environment variables...")
    
    for var in required_vars:
        value = os.getenv(var)
        if value and value != 'your_bot_token_here':
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Not set or using default value")

if __name__ == '__main__':
    setup_environment()