from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN

from core.router import route_message
from ai.parser import parse_message

from inquiry.service import create_inquiry
from inquiry.actions import (
    claim_inquiry,
    ignore_inquiry,
    mark_quote_sent,
)
from inquiry.repository import repository

from telegram_ui.cards import build_inquiry_card
from telegram_ui.keyboards import inquiry_keyboard


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

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

    decision = route_message(message)

    print(f"ROUTER : {decision}")

    if decision != "PRICE":
        print("Ignored.")
        return

    try:
        parsed = parse_message(message)

    except Exception as e:
        print(f"Gemini Error: {e}")
        return

    print()
    print("========== GEMINI ==========")
    print(parsed)
    print("============================")

    ticket = create_inquiry(
        customer_name=user,
        customer_group=group,
        chat_id=update.effective_chat.id,
        message_id=update.message.message_id,
        original_message=message,
        parsed=parsed,
    )

    print()
    print("========== INQUIRY ==========")
    print(ticket)
    print("=============================")

    sent_message = await update.message.reply_text(
        build_inquiry_card(ticket),
        parse_mode="HTML",
        reply_markup=inquiry_keyboard(
            ticket.inquiry_id,
            ticket.status,
        ),
    )

    ticket.telegram.message_id = sent_message.message_id

    repository.save(ticket)


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query is None:
        return

    data = query.data

    action, inquiry_id = data.split(":", 1)

    trader = query.from_user
    trader_id = trader.id
    trader_name = trader.full_name

    if action == "claim":

        inquiry = claim_inquiry(
            inquiry_id=inquiry_id,
            trader_id=trader_id,
            trader_name=trader_name,
        )

        if inquiry is None:
            await query.answer(
                "Inquiry not found.",
                show_alert=True,
            )
            return

        await query.answer("Claimed.")

        await query.edit_message_text(
            text=build_inquiry_card(inquiry),
            parse_mode="HTML",
            reply_markup=inquiry_keyboard(
                inquiry.inquiry_id,
                inquiry.status,
            ),
        )

        return

    if action == "quote":

        inquiry = mark_quote_sent(
            inquiry_id=inquiry_id,
        )

        if inquiry is None:
            await query.answer(
                "Inquiry not found.",
                show_alert=True,
            )
            return

        await query.answer("Quote marked as sent.")

        await query.edit_message_text(
            text=build_inquiry_card(inquiry),
            parse_mode="HTML",
            reply_markup=inquiry_keyboard(
                inquiry.inquiry_id,
                inquiry.status,
            ),
        )

        return

    if action == "ignore":

        inquiry = ignore_inquiry(
            inquiry_id=inquiry_id,
        )

        if inquiry is None:
            await query.answer(
                "Inquiry not found.",
                show_alert=True,
            )
            return

        await query.answer("No deal.")

        await query.edit_message_text(
            text=build_inquiry_card(inquiry),
            parse_mode="HTML",
            reply_markup=inquiry_keyboard(
                inquiry.inquiry_id,
                inquiry.status,
            ),
        )

        return

    if action == "noop":

        await query.answer(
            "This button is not wired yet.",
            show_alert=False,
        )

        return


def run_bot():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    app.add_handler(
        CallbackQueryHandler(handle_button)
    )

    print("🚀 OTC AI Dealer is running...")

    app.run_polling(drop_pending_updates=True)