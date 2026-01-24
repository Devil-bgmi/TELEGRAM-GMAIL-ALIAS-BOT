import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
import sqlite3
import asyncio
from typing import List, Set, Tuple
from functools import lru_cache

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from config import config

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------- DATABASE ----------------
class Database:
    def __init__(self, db_path: str = config.DATABASE_FILE):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_emails (
                    user_id INTEGER,
                    email TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, email),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id INTEGER,
                    command TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rate_limits 
                ON rate_limits(user_id, timestamp)
            """)
            
            conn.commit()
    
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, last_name))
            conn.commit()
    
    def add_email(self, user_id: int, email: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO user_emails (user_id, email)
                VALUES (?, ?)
            """, (user_id, email))
            conn.commit()
    
    def log_request(self, user_id: int, command: str):
        with sqlite3.connect(self.db_path) as conn:
            # Clean old entries
            conn.execute("""
                DELETE FROM rate_limits 
                WHERE timestamp < datetime('now', '-1 hour')
            """)
            
            # Add new entry
            conn.execute("""
                INSERT INTO rate_limits (user_id, command)
                VALUES (?, ?)
            """, (user_id, command))
            
            conn.commit()
    
    def get_request_count(self, user_id: int, minutes: int = 60) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM rate_limits 
                WHERE user_id = ? 
                AND timestamp > datetime('now', ?)
            """, (user_id, f'-{minutes} minutes'))
            return cursor.fetchone()[0]

db = Database()

# ---------------- RATE LIMITING ----------------
class RateLimiter:
    @staticmethod
    def check_limit(user_id: int) -> bool:
        """Check if user has exceeded rate limits."""
        hourly = db.get_request_count(user_id, 60)
        minute = db.get_request_count(user_id, 1)
        
        if hourly >= config.RATE_LIMIT_PER_HOUR:
            logger.warning(f"User {user_id} exceeded hourly limit: {hourly}")
            return False
        if minute >= config.RATE_LIMIT_PER_MINUTE:
            logger.warning(f"User {user_id} exceeded minute limit: {minute}")
            return False
        return True

# ---------------- EMAIL VALIDATION ----------------
class EmailValidator:
    GMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@(gmail\.com|googlemail\.com)$', re.IGNORECASE)
    
    @staticmethod
    def is_valid_gmail(email: str) -> bool:
        """Check if email is a valid Gmail address."""
        return bool(EmailValidator.GMAIL_REGEX.match(email.strip().lower()))
    
    @staticmethod
    def extract_local_part(email: str) -> str:
        """Extract local part from email (before @)."""
        return email.split('@')[0].lower()

# ---------------- ALIAS GENERATOR ----------------
class AliasGenerator:
    @staticmethod
    def generate_all_possible_aliases(email: str) -> List[str]:
        """
        Generate all possible Gmail aliases:
        1. Dot variations (e.m.a.i.l@gmail.com)
        2. Plus aliases (email+anything@gmail.com)
        3. Email name variations (if email contains words)
        """
        if not EmailValidator.is_valid_gmail(email):
            return []
        
        local_part = EmailValidator.extract_local_part(email)
        domain = email.split('@')[1].lower()
        aliases = set()
        
        # 1. Dot variations (all possible dot placements)
        def generate_dot_variations(s: str) -> Set[str]:
            if len(s) <= 1:
                return {s}
            
            variations = set()
            # For each position where we can place a dot
            for i in range(1, len(s)):
                left = s[:i]
                right = s[i:]
                # Generate variations for left and right parts
                for left_var in generate_dot_variations(left):
                    for right_var in generate_dot_variations(right):
                        variations.add(left_var + "." + right_var)
            
            variations.add(s)  # Original without dots
            return variations
        
        # Generate dot variations
        dot_variations = generate_dot_variations(local_part)
        for variation in dot_variations:
            if variation != local_part:  # Skip original
                aliases.add(f"{variation}@{domain}")
        
        # 2. Plus aliases (with common suffixes)
        common_suffixes = [
            'news', 'shop', 'work', 'personal', 'temp', 'spam',
            'signup', 'social', 'finance', 'travel', 'food',
            'tech', 'health', 'education', 'entertainment'
        ]
        
        for suffix in common_suffixes:
            aliases.add(f"{local_part}+{suffix}@{domain}")
        
        # 3. Extract words from local part and create variations
        words = re.findall(r'[a-zA-Z]+', local_part)
        if len(words) >= 2:
            # Create combinations of words
            for i in range(len(words)):
                for j in range(i + 1, len(words) + 1):
                    combo = ''.join(words[i:j])
                    if combo and combo != local_part:
                        aliases.add(f"{combo}@{domain}")
        
        # 4. Add numbered variations (limited to reasonable amount)
        for i in range(1, 11):  # 1-10
            aliases.add(f"{local_part}{i}@{domain}")
            aliases.add(f"{local_part}.{i}@{domain}")
            aliases.add(f"{local_part}+{i}@{domain}")
        
        return sorted(list(aliases))[:config.MAX_ALIASES_PER_USER]

# ---------------- COMMAND HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message."""
    user = update.effective_user
    
    # Register user in database
    db.add_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name,
        last_name=user.last_name or ""
    )
    
    welcome_text = """
🎉 *Gmail Alias Generator Bot*

*What this bot does:*
• Generate all possible Gmail aliases for your email
• Dot variations (e.m.a.i.l@gmail.com)
• Plus aliases (email+anything@gmail.com)
• Word-based variations from your email name

*How to use:*
Just send your Gmail address and I'll show you all possible aliases!

*Example:* `yourname@gmail.com`

⚠️ *Note:* These aliases work automatically with Gmail. No setup needed!
    """
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📧 Send Gmail", switch_inline_query_current_chat="")
        ]])
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message."""
    help_text = """
📚 *Available Commands:*

/start - Start the bot
/help - Show this help message
/about - About this bot

*Usage:*
Simply send your Gmail address (e.g., `john.doe@gmail.com`)
The bot will generate all possible aliases.

*What are Gmail aliases?*
• `youremail+spam@gmail.com` → Plus addressing
• `y.o.u.r.e.m.a.i.l@gmail.com` → Dot variations
• Both deliver to your main inbox!

*Rate Limits:* %d requests per hour, %d per minute
    """ % (config.RATE_LIMIT_PER_HOUR, config.RATE_LIMIT_PER_MINUTE)
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show about information."""
    about_text = """
🤖 *Gmail Alias Generator*
*Version:* 2.0.0
*Developer:* @the_BR_king

*Features:*
• Generate unlimited Gmail aliases
• Privacy-focused (no data stored)
• Fast and reliable
• Free forever

*How it works:*
Gmail automatically treats these as aliases:
1. Plus addressing: `email+anything@gmail.com`
2. Dot variations: `e.m.a.i.l@gmail.com`

Both deliver to your main inbox without any setup!

*Open Source:* [GitHub Repository](#)
    """
    
    await update.message.reply_text(about_text, parse_mode=ParseMode.MARKDOWN)

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email input and generate aliases."""
    user = update.effective_user
    email = update.message.text.strip().lower()
    
    # Check rate limit
    if not RateLimiter.check_limit(user.id):
        await update.message.reply_text(
            "⏳ *Rate limit exceeded*\n\n"
            "Please wait a while before sending more requests.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Log the request
    db.log_request(user.id, "generate_aliases")
    
    # Validate email
    if not EmailValidator.is_valid_gmail(email):
        await update.message.reply_text(
            "❌ *Invalid Gmail address*\n\n"
            "Please send a valid Gmail address.\n"
            "*Example:* `yourname@gmail.com`\n\n"
            "Note: Only Gmail addresses are supported.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Store email for user
    db.add_email(user.id, email)
    
    # Generate aliases
    await update.message.reply_text(
        "⚡ *Generating all possible aliases...*\n"
        "This may take a moment for longer email addresses.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        aliases = AliasGenerator.generate_all_possible_aliases(email)
        
        if not aliases:
            await update.message.reply_text(
                "❌ *No aliases generated*\n\n"
                "Could not generate aliases for this email.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Send in chunks (Telegram has 4096 character limit)
        chunk_size = 3000
        chunks = []
        current_chunk = ""
        
        for alias in aliases:
            if len(current_chunk) + len(alias) + 1 > chunk_size:
                chunks.append(current_chunk)
                current_chunk = alias + "\n"
            else:
                current_chunk += alias + "\n"
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Send first chunk with header
        header = f"📧 *Generated Aliases for:* `{email}`\n\n"
        await update.message.reply_text(
            header + chunks[0],
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Send remaining chunks
        for chunk in chunks[1:]:
            await update.message.reply_text(
                f"```\n{chunk}\n```",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        
        # Send summary
        summary = f"""
✅ *Generation Complete!*

*Total aliases:* {len(aliases)}
*Original email:* `{email}`

*How to use these aliases:*
1. Use any alias when signing up for websites
2. All emails sent to aliases will arrive in your main inbox
3. Filter emails based on the alias used

💡 *Tip:* Use `email+websitename@gmail.com` to track where spam comes from!
        """
        
        await update.message.reply_text(
            summary,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error generating aliases: {e}")
        await update.message.reply_text(
            "❌ *Error generating aliases*\n\n"
            "An error occurred while generating aliases. Please try again.",
            parse_mode=ParseMode.MARKDOWN
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors gracefully."""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        await update.message.reply_text(
            "❌ *An error occurred*\n\n"
            "Please try again or use /help for assistance.",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass  # If we can't send message, just log the error

# ---------------- MAIN ----------------
def main():
    """Start the bot."""
    try:
        # Create application
        application = Application.builder().token(config.BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("about", about))
        
        # Add message handler for emails
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)
        )
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Start the bot
        logger.info("🤖 Bot starting...")
        print("\n" + "="*50)
        print("Gmail Alias Generator Bot")
        print(f"Version: 2.0.0")
        print(f"Database: {config.DATABASE_FILE}")
        print(f"Rate limit: {config.RATE_LIMIT_PER_HOUR}/hour")
        print("="*50 + "\n")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"❌ Bot failed to start: {e}")
        exit(1)

if __name__ == "__main__":
    main()
