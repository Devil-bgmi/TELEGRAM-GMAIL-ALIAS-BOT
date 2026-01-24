#!/usr/bin/env python3
"""
Main entry point for Gmail Alias Generator Bot
"""

import sys
import traceback
from alias_bot import main

if __name__ == '__main__':
    try:
        print("🚀 Starting Gmail Alias Generator Bot...")
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
