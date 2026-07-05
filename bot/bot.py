from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN

from core.router import route_message
from ai.parser import parse_message

from inquiry.service import create_inquiry

from telegram_ui.cards import build_inquiry_card
from telegram_ui.keyboards import inquiry_keyboard


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Ignore non-text messages
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

    # Decide if this is an OTC inquiry
    decision = route_message(message)

    print(f"ROUTER : {decision}")

    if decision != "PRICE":
        print("Ignored.")
        return

    # ----------------------------
    # Gemini Parsing
    # ----------------------------

    try:
        parsed = parse_message(message)

    except Exception as e:
        print(f"Gemini Error: {e}")
        return

    print()
    print("========== GEMINI ==========")
    print(parsed)
    print("============================")

    # ----------------------------
    # Create Inquiry Ticket
    # ----------------------------

    ticket = create_inquiry(
        customer_name=user,
        customer_group=group,
        parsed_trade=parsed,
    )

    print()
    print("========== INQUIRY ==========")
    print(ticket)
    print("=============================")

    # ----------------------------
    # Send Telegram Inquiry Card
    # ----------------------------

    await update.message.reply_text(
        build_inquiry_card(ticket),
        parse_mode="HTML",
        reply_markup=inquiry_keyboard(ticket.id),
    )


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