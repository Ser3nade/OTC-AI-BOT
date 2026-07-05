from telegram import Update
from ai.parser import parse_message
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN
from core.router import route_message


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Ignore messages with no text
    if not update.message or not update.message.text:
        return

    user = update.effective_user.full_name

    group = (
        update.effective_chat.title
        if update.effective_chat.title
        else "Private Chat"
    )

    message = update.message.text

    print("=" * 60)
    print(f"GROUP   : {group}")
    print(f"USER    : {user}")
    print(f"MESSAGE : {message}")
    print("=" * 60)

    # Router
    decision = route_message(message)

    print(f"ROUTER : {decision}")

    if decision == "PRICE":

        parsed = parse_message(message)

        print()
        print("========== GEMINI ==========")
        print(parsed)
        print("============================")

        await update.message.reply_text("📈 Price inquiry detected.")

    else:
        print("Ignored.")


def run_bot():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    print("🚀 OTC AI Dealer is running...")

    app.run_polling(drop_pending_updates=True)