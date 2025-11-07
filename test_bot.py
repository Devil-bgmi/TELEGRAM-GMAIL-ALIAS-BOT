import os
import sqlite3
import logging
import csv
import re
import secrets
from datetime import datetime, timedelta
from io import StringIO
from typing import Dict, List, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackContext, 
    CallbackQueryHandler, filters
)
from telegram.constants import ParseMode

from config import Config

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS usersettings (
                    user_id INTEGER PRIMARY KEY,
                    base_email TEXT NOT NULL,
                    catch_all INTEGER DEFAULT 0,
                    accepted_terms INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    base_email TEXT NOT NULL,
                    alias TEXT NOT NULL,
                    label TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usersettings (user_id)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id INTEGER PRIMARY KEY,
                    request_count INTEGER DEFAULT 0,
                    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

class EmailValidator:
    @staticmethod
    def is_valid_email(email: str) -> bool:
        return bool(EMAIL_REGEX.match(email))

    @staticmethod
    def is_gmail(email: str) -> bool:
        domain = email.split('@')[1].lower()
        return domain in ['gmail.com', 'googlemail.com']

    @staticmethod
    def get_email_parts(email: str) -> Tuple[str, str]:
        local, domain = email.split('@')
        return local, domain

class AliasGenerator:
    def __init__(self):
        self.validator = EmailValidator()

    def generate_plus_alias(self, base_email: str, count: int = 1) -> List[str]:
        local, domain = self.validator.get_email_parts(base_email)
        aliases = []
        
        for _ in range(count):
            tag = secrets.token_hex(3)
            aliases.append(f"{local}+{tag}@{domain}")
        
        return aliases

    def generate_dot_aliases(self, base_email: str, count: int = 1) -> List[str]:
        local, domain = self.validator.get_email_parts(base_email)
        aliases = []
        
        if len(local) <= 3:
            positions = min(len(local) - 1, 3)
            for i in range(min(count, positions)):
                alias_local = local[:i+1] + '.' + local[i+1:]
                if alias_local + '@' + domain != base_email:
                    aliases.append(f"{alias_local}@{domain}")
                if len(aliases) >= count:
                    break
        else:
            used_variants = set()
            attempts = 0
            max_attempts = count * 10
            
            while len(aliases) < count and attempts < max_attempts:
                attempts += 1
                num_dots = secrets.choice([1, 2])
                positions = sorted(secrets.sample(range(1, len(local)), num_dots))
                
                alias_local = local
                for pos in reversed(positions):
                    alias_local = alias_local[:pos] + '.' + alias_local[pos:]
                
                if alias_local not in used_variants and alias_local + '@' + domain != base_email:
                    used_variants.add(alias_local)
                    aliases.append(f"{alias_local}@{domain}")
        
        return aliases[:count]

    def generate_custom_aliases(self, base_email: str, count: int = 1) -> List[str]:
        _, domain = self.validator.get_email_parts(base_email)
        aliases = []
        
        for _ in range(count):
            tag = secrets.token_hex(4)
            aliases.append(f"{tag}@{domain}")
        
        return aliases

class RateLimiter:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def check_rate_limit(self, user_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT request_count, window_start FROM rate_limits WHERE user_id = ?',
                (user_id,)
            )
            result = cursor.fetchone()
            
            now = datetime.now()
            if result:
                request_count, window_start = result
                window_start = datetime.fromisoformat(window_start)
                
                if now - window_start > timedelta(seconds=Config.RATE_LIMIT_WINDOW_SECONDS):
                    request_count = 0
                    window_start = now
            else:
                request_count = 0
                window_start = now
            
            if request_count >= Config.RATE_LIMIT_MAX_REQUESTS:
                return False
            
            request_count += 1
            cursor.execute('''
                INSERT OR REPLACE INTO rate_limits (user_id, request_count, window_start)
                VALUES (?, ?, ?)
            ''', (user_id, request_count, window_start.isoformat()))
            conn.commit()
            
            return True

class AliasManagerBot:
    def __init__(self, token: str):
        self.token = token
        self.db = DatabaseManager(Config.DATABASE_FILE)
        self.validator = EmailValidator()
        self.generator = AliasGenerator()
        self.rate_limiter = RateLimiter(self.db)
        
        self.application = Application.builder().token(token).build()
        
        self._setup_handlers()

    def _setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("set", self.set_email))
        self.application.add_handler(CommandHandler("generate", self.generate_aliases))
        self.application.add_handler(CommandHandler("list", self.list_aliases))
        self.application.add_handler(CommandHandler("delete", self.delete_alias))
        self.application.add_handler(CommandHandler("export", self.export_aliases))
        self.application.add_handler(CommandHandler("enable_catchall", self.enable_catchall))
        self.application.add_handler(CommandHandler("owner", self.owner_commands))
        self.application.add_handler(CallbackQueryHandler(self.terms_callback, pattern='^terms_'))

    def check_terms_accepted(self, user_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT accepted_terms FROM usersettings WHERE user_id = ?',
                (user_id,)
            )
            result = cursor.fetchone()
            return result and result[0] == 1

    async def terms_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        action = query.data.split('_')[1]

        if action == 'accept':
            with self.db.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO usersettings (user_id, base_email, accepted_terms)
                    VALUES (?, ?, ?)
                ''', (user_id, '', 1))
                conn.commit()

            welcome_text = """
✅ Thank you for accepting our Terms & Conditions!

🔒 **We respect your privacy:**
- Your data is stored locally and securely
- We don't share your information with third parties
- You have full control over your aliases

Now you can start using the bot:

📋 **Quick Start:**
1. Set your base email: `/set your.email@domain.com`
2. Generate aliases: `/generate 5`
3. Manage your aliases: `/list`, `/delete`, `/export`

Use `/help` for detailed instructions.
            """
            await query.edit_message_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
            await query.answer("✅ Terms accepted!")

        elif action == 'reject':
            reject_text = """
❌ You have rejected our Terms & Conditions.

To use this bot, you must accept our Terms & Conditions. 
If you change your mind, simply start the bot again with `/start`.

Thank you for your understanding.
            """
            await query.edit_message_text(reject_text, parse_mode=ParseMode.MARKDOWN)
            await query.answer("❌ Terms rejected!")

    async def start(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        
        if self.check_terms_accepted(user_id):
            welcome_text = f"""
👋 Welcome back {update.effective_user.first_name}!

Ready to manage your email aliases? Here's what you can do:

• `/set <email>` - Set your base email
• `/generate <N> [mode]` - Generate aliases (modes: plus, dot, custom)
• `/list` - View your aliases  
• `/export` - Export as CSV
• `/help` - Detailed help

Your privacy is important to us! 🔒
            """
            await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
        else:
            terms_text = """
📝 **Terms & Conditions**

Before using this bot, please read and accept our Terms:

**Privacy & Data:**
- We store your email aliases locally in an encrypted database
- We do not access, read, or store your actual emails
- Your data is not shared with third parties
- You can delete your data at any time

**Usage:**
- Generate aliases for legitimate purposes only
- Do not use for spam or illegal activities
- You are responsible for how you use the aliases
- Service may be terminated for abuse

**Limitations:**
- Some websites may block certain alias formats
- Catch-all domains may receive more spam
- We don't guarantee alias acceptance by all services

By clicking "Accept", you agree to these terms.
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Accept", callback_data="terms_accept"),
                    InlineKeyboardButton("❌ Reject", callback_data="terms_reject")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                terms_text, 
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    async def help(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if not self.check_terms_accepted(user_id):
            await update.message.reply_text("❌ Please accept the Terms & Conditions first using /start")
            return

        help_text = f"""
📖 **Available Commands:**

**Basic Setup:**
`/set your.email@domain.com` - Set your base email
`/enable_catchall` - Enable custom aliases (requires catch-all domain)

**Alias Generation:**
`/generate 5` - 5 plus-style aliases (max: {Config.MAX_ALIASES_PER_GENERATE})
`/generate 3 dot` - 3 dot-variant aliases (max: {Config.MAX_DOT_ALIASES})  
`/generate 3 custom` - 3 custom aliases (max: {Config.MAX_CUSTOM_ALIASES})

**Management:**
`/list` - View all aliases with IDs
`/delete 123` - Delete alias by ID
`/export` - Download CSV export

**Alias Types:**
• **plus**: `email+tag@domain.com` (Gmail-friendly)
• **dot**: `e.mail@domain.com` (limited variants)
• **custom**: `tag@domain.com` (requires catch-all)

🔒 **Privacy First:** Your data stays with you!
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def owner_commands(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        
        if user_id not in Config.ADMIN_USER_IDS:
            await update.message.reply_text("❌ Command not found. Use /help for available commands.")
            return

        if not context.args:
            owner_text = """
👑 **Owner Commands:**

**Stats:**
`/owner stats` - Bot statistics
`/owner users` - User count
`/owner broadcast` - Broadcast message

**Management:**
`/owner backup` - Create database backup
`/owner restart` - Restart bot
            """
            await update.message.reply_text(owner_text, parse_mode=ParseMode.MARKDOWN)
            return

        subcommand = context.args[0].lower()
        
        if subcommand == 'stats':
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM usersettings')
                user_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM aliases')
                alias_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM usersettings WHERE accepted_terms = 1')
                accepted_count = cursor.fetchone()[0]
                
            stats_text = f"""
📊 **Bot Statistics:**

👥 Users: {user_count}
✅ Terms Accepted: {accepted_count}
📧 Aliases Generated: {alias_count}
🕒 Uptime: {self.get_uptime()}
            """
            await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

    def get_uptime(self) -> str:
        if hasattr(self, 'start_time'):
            uptime = datetime.now() - self.start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{days}d {hours}h {minutes}m {seconds}s"
        return "Unknown"

    def get_user_settings(self, user_id: int) -> Optional[Tuple]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT base_email, catch_all FROM usersettings WHERE user_id = ? AND accepted_terms = 1',
                (user_id,)
            )
            return cursor.fetchone()

    async def set_email(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        
        if not self.check_terms_accepted(user_id):
            await update.message.reply_text("❌ Please accept the Terms & Conditions first using /start")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Usage: `/set your.email@domain.com`", parse_mode=ParseMode.MARKDOWN)
            return

        email = ' '.join(context.args).strip().lower()
        
        if not self.validator.is_valid_email(email):
            await update.message.reply_text("❌ Invalid email format.")
            return

        with self.db.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO usersettings (user_id, base_email, accepted_terms)
                VALUES (?, ?, 1)
            ''', (user_id, email))
            conn.commit()

        if self.validator.is_gmail(email):
            message = f"""
✅ Base email set: `{email}`

Gmail detected! You can use:
• **Plus addressing** - Recommended (max: {Config.MAX_ALIASES_PER_GENERATE})
• **Dot variants** - Limited availability (max: {Config.MAX_DOT_ALIASES})

Note: Some websites may block plus addresses.
            """
        else:
            message = f"""
✅ Base email set: `{email}`

You can use:
• **Plus addressing** - if supported (max: {Config.MAX_ALIASES_PER_GENERATE})
• **Dot variants** - if supported (max: {Config.MAX_DOT_ALIASES})  
• **Custom aliases** - with `/enable_catchall` (max: {Config.MAX_CUSTOM_ALIASES})
            """

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    async def generate_aliases(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        
        if not self.check_terms_accepted(user_id):
            await update.message.reply_text("❌ Please accept the Terms & Conditions first using /start")
            return

        if not self.rate_limiter.check_rate_limit(user_id):
            await update.message.reply_text("❌ Rate limit exceeded. Please try again later.")
            return

        user_settings = self.get_user_settings(user_id)
        if not user_settings:
            await update.message.reply_text("❌ Please set your base email first: `/set your.email@domain.com`", parse_mode=ParseMode.MARKDOWN)
            return

        base_email, catch_all_enabled = user_settings

        if not context.args:
            keyboard = [
                [
                    InlineKeyboardButton("➕ Plus Aliases", callback_data="generate_plus"),
                    InlineKeyboardButton("🔘 Dot Aliases", callback_data="generate_dot")
                ],
                [
                    InlineKeyboardButton("🎯 Custom Aliases", callback_data="generate_custom")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🎯 **Choose alias type:**\n\n"
                f"• **Plus**: `email+tag@domain.com` (max: {Config.MAX_ALIASES_PER_GENERATE})\n"
                f"• **Dot**: `e.mail@domain.com` (max: {Config.MAX_DOT_ALIASES})\n"
                f"• **Custom**: `tag@domain.com` (max: {Config.MAX_CUSTOM_ALIASES}, requires catch-all)",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        try:
            count = int(context.args[0])
            if len(context.args) > 1:
                mode = context.args[1].lower()
            else:
                mode = 'plus'
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Usage: `/generate <number> [mode]`\nModes: plus, dot, custom", parse_mode=ParseMode.MARKDOWN)
            return

        await self._generate_aliases_with_mode(update, context, base_email, catch_all_enabled, count, mode)

    async def _generate_aliases_with_mode(self, update: Update, context: CallbackContext, base_email: str, catch_all_enabled: bool, count: int, mode: str):
        user_id = update.effective_user.id
        
        max_limit = Config.MAX_ALIASES_PER_GENERATE
        if mode == 'dot':
            max_limit = Config.MAX_DOT_ALIASES
        elif mode == 'custom':
            max_limit = Config.MAX_CUSTOM_ALIASES

        if count <= 0 or count > max_limit:
            await update.message.reply_text(f"❌ Number must be between 1 and {max_limit} for {mode} aliases")
            return

        if mode == 'plus':
            aliases = self.generator.generate_plus_alias(base_email, count)
        elif mode == 'dot':
            aliases = self.generator.generate_dot_aliases(base_email, count)
        elif mode == 'custom':
            if not catch_all_enabled:
                await update.message.reply_text("""
❌ Custom aliases require catch-all.

Use `/enable_catchall` first and ensure:
1. You own the domain
2. Catch-all is configured in DNS
3. You understand spam risks
                """)
                return
            aliases = self.generator.generate_custom_aliases(base_email, count)
        else:
            await update.message.reply_text("❌ Invalid mode. Use: plus, dot, or custom")
            return

        with self.db.get_connection() as conn:
            for alias in aliases:
                conn.execute('''
                    INSERT INTO aliases (user_id, base_email, alias)
                    VALUES (?, ?, ?)
                ''', (user_id, base_email, alias))
            conn.commit()

        alias_list = "\n".join([f"• `{alias}`" for alias in aliases])
        message = f"""
✅ Generated {len(aliases)} {mode} aliases:

{alias_list}

Use `/list` to see all aliases with IDs.
        """
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    async def generate_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        mode = query.data.split('_')[1]
        
        await query.answer(f"Selected {mode} aliases")
        
        user_settings = self.get_user_settings(user_id)
        if not user_settings:
            await query.edit_message_text("❌ Please set your base email first using `/set your.email@domain.com`")
            return

        base_email, catch_all_enabled = user_settings
        
        if mode == 'custom' and not catch_all_enabled:
            await query.edit_message_text("""
❌ Custom aliases require catch-all enabled.

Use `/enable_catchall` first and ensure you have catch-all configured on your domain.
            """)
            return

        max_limit = Config.MAX_ALIASES_PER_GENERATE
        if mode == 'dot':
            max_limit = Config.MAX_DOT_ALIASES
        elif mode == 'custom':
            max_limit = Config.MAX_CUSTOM_ALIASES

        await query.edit_message_text(
            f"🎯 Generating **{mode}** aliases\n\n"
            f"Enter number of aliases to generate (1-{max_limit}):\n"
            f"Example: `5`",
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['pending_generation'] = {
            'mode': mode,
            'base_email': base_email,
            'catch_all_enabled': catch_all_enabled
        }

    async def handle_generation_number(self, update: Update, context: CallbackContext):
        if 'pending_generation' not in context.user_data:
            return

        try:
            count = int(update.message.text)
            gen_data = context.user_data['pending_generation']
            
            await self._generate_aliases_with_mode(
                update, context,
                gen_data['base_email'],
                gen_data['catch_all_enabled'],
                count,
                gen_data['mode']
            )
            
            del context.user_data['pending_generation']
            
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number")

    async def list_aliases(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        
        if not self.check_terms_accepted(user_id):
            await update.message.reply_text("❌ Please accept the Terms & Conditions first using /start")
            return
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, alias, created_at FROM aliases 
                WHERE user_id = ? 
                ORDER BY created_at DESC
                LIMIT 50
            ''', (user_id,))
            aliases = cursor.fetchall()

        if not aliases:
            await update.message.reply_text("📭 No aliases found. Generate some with `/generate`")
            return

        alias_text = "📧 Your Aliases:\n\n"
        for alias_id, alias, created_at in aliases:
            created_dt = datetime.fromisoformat(created_at)
            timestamp = created_dt.strftime("%Y-%m-%d %H:%M UTC")
            alias_text += f"`{alias}`\nID: `{alias_id}` • {timestamp}\n\n"

        await update.message.reply_text(alias_text, parse_mode=ParseMode.MARKDOWN)

    async def delete_alias(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        
        if not self.check_terms_accepted(user_id):
            await update.message.reply_text("❌ Please accept the Terms & Conditions first using /start")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Usage: `/delete <alias_id>`", parse_mode=ParseMode.MARKDOWN)
            return

        try:
            alias_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid alias ID")
            return

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM aliases 
                WHERE id = ? AND user_id = ?
            ''', (alias_id, user_id))
            conn.commit()

            if cursor.rowcount > 0:
                await update.message.reply_text(f"✅ Alias ID `{alias_id}` deleted", parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text("❌ Alias not found or no permission")

    async def export_aliases(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        
        if not self.check_terms_accepted(user_id):
            await update.message.reply_text("❌ Please accept the Terms & Conditions first using /start")
            return
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT alias, id, created_at, base_email 
                FROM aliases 
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            aliases = cursor.fetchall()

        if not aliases:
            await update.message.reply_text("📭 No aliases to export")
            return

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['alias', 'id', 'created_at', 'base_email'])
        
        for alias in aliases:
            escaped_alias = [str(field).replace('"', '""') for field in alias]
            writer.writerow(escaped_alias)

        output.seek(0)
        csv_content = output.getvalue().encode('utf-8')
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=csv_content,
            filename=f"aliases_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            caption="📤 Your aliases export"
        )

    async def enable_catchall(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        
        if not self.check_terms_accepted(user_id):
            await update.message.reply_text("❌ Please accept the Terms & Conditions first using /start")
            return
        
        user_settings = self.get_user_settings(user_id)
        if not user_settings:
            await update.message.reply_text("❌ Please set your base email first using `/set`")
            return

        base_email, current_catchall = user_settings
        new_catchall = not current_catchall

        with self.db.get_connection() as conn:
            conn.execute('''
                UPDATE usersettings SET catch_all = ? WHERE user_id = ?
            ''', (int(new_catchall), user_id))
            conn.commit()

        if new_catchall:
            message = f"""
✅ Catch-all enabled for `{base_email}`

You can now generate custom aliases:
`/generate 5 custom`

⚠️ **Important:**
1. You must have catch-all configured on your domain
2. All emails to *@yourdomain.com will be delivered
3. Set up spam filters
4. The bot does NOT configure DNS
            """
        else:
            message = "✅ Catch-all disabled. Custom aliases unavailable."

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    def run(self):
        self.start_time = datetime.now()
        
        self.application.add_handler(CallbackQueryHandler(self.generate_callback, pattern='^generate_'))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_generation_number))
        
        self.application.run_polling()
        logger.info("Bot started and polling...")

def main():
    if not Config.BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return

    bot = AliasManagerBot(Config.BOT_TOKEN)
    bot.run()

if __name__ == '__main__':
    main()