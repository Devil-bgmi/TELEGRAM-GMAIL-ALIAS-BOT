import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------- START / BANNER ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banner = (
        "🔥 *GMAIL ALIAS GENERATOR BOT* 🔥\n\n"
        "✨ Send your Gmail address and I will automatically generate\n"
        "*maximum possible aliases* for you.\n\n"
        "📩 Example:\n"
        "`example@gmail.com`\n\n"
        "⚡ No limits • No type selection • Fully automatic"
    )

    await update.message.reply_text(
        banner,
        parse_mode="Markdown"
    )

# ---------------- ALIAS GENERATOR ----------------
def generate_all_aliases(email: str):
    local, domain = email.split("@")
    aliases = set()

    # ---- DOT ALIASES (ALL POSSIBLE) ----
    def dot_variations(name):
        results = set()

        def helper(index, current):
            if index == len(name):
                results.add(current)
                return
            helper(index + 1, current + name[index])
            if index > 0:
                helper(index + 1, current + "." + name[index])

        helper(0, "")
        return results

    dot_aliases = dot_variations(local)
    for d in dot_aliases:
        aliases.add(f"{d}@{domain}")

    # ---- PLUS ALIASES (SAFE PRACTICAL LIMIT) ----
    PLUS_LIMIT = 30  # safe, editable
    for i in range(1, PLUS_LIMIT + 1):
        aliases.add(f"{local}+{i}@{domain}")

    return sorted(aliases)

# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # ---- EMAIL VALIDATION ----
    if "@" not in text or not text.endswith("@gmail.com"):
        await update.message.reply_text(
            "❌ Please send a valid *Gmail* address.\n\n"
            "Example:\n`example@gmail.com`",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("⏳ Generating maximum possible aliases...")

    aliases = generate_all_aliases(text)

    if not aliases:
        await update.message.reply_text("❌ No aliases could be generated.")
        return

    # ---- SPLIT MESSAGE IF TOO LONG ----
    chunk = ""
    count = 0

    for alias in aliases:
        if len(chunk) + len(alias) > 3500:
            await update.message.reply_text(chunk)
            chunk = ""
        chunk += alias + "\n"
        count += 1

    if chunk:
        await update.message.reply_text(chunk)

    await update.message.reply_text(
        f"✅ *Done!*\n\n"
        f"📊 Total aliases generated: *{count}*",
        parse_mode="Markdown"
    )

# ---------------- MAIN ----------------
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("Bot started successfully...")
    application.run_polling()

# ---------------- RUN ----------------
if __name__ == "__main__":
    main()
