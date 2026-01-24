#!/usr/bin/env python3
"""
Install dependencies for Gmail Alias Generator Bot
"""

import subprocess
import sys

def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    print("-" * 40)
    
    requirements = [
        "python-telegram-bot[job-queue]==20.7",
        "python-dotenv==1.0.0"
    ]
    
    for package in requirements:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "--upgrade", package
            ])
            print(f"✅ {package} installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            return False
    
    print("\n" + "="*40)
    print("✅ All dependencies installed successfully!")
    print("\nNext steps:")
    print("1. Run: python setup_environment.py")
    print("2. Edit .env file with your bot token")
    print("3. Run: python run_bot.py")
    print("="*40)
    
    return True

if __name__ == '__main__':
    if install_dependencies():
        sys.exit(0)
    else:
        sys.exit(1)
