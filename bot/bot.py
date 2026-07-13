import logging

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ai.parser import ParsedTrade, parse_message
from config import (
    BOT_TOKEN,
    TRADER_GROUP_CHAT_ID,
    ConfigError,
    get_trader_user_ids,
    validate_required_settings,
)
from core.router import route_message
from inquiry.actions import (
    InquiryActionError,
    build_message_link,
    complete_inquiry,
    ignore_inquiry,
    lock_trade,
    mark_quote_sent,
    prepare_lock_preview,
    preview_quote,
    refresh_sheet_rate,
    set_direction,
    set_fiat_amount,
    set_pair,
    set_rate,
    set_stable_amount,
)
from inquiry.repository import repository
from inquiry.service import create_inquiry
from telegram_ui.cards import (
    build_all_rates_message,
    build_rates_debug_message,
    build_inquiry_card,
    build_lock_confirmation,
    build_quote_message,
)
from telegram_ui.keyboards import inquiry_keyboard
from trade_log.logger import TradeLogError, log_locked_trade


logger = logging.getLogger(__name__)
CONFIGURED_TRADER_USER_IDS = get_trader_user_ids()


def _pending_key(user_id: int):
    return f"pending:{user_id}"


def _known_trader_key():
    return "known_trader_user_ids"


def _known_trader_user_ids(context: ContextTypes.DEFAULT_TYPE):
    known_ids = context.application.bot_data.setdefault(_known_trader_key(), set())
    return CONFIGURED_TRADER_USER_IDS | known_ids


def _remember_trader(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    context.application.bot_data.setdefault(_known_trader_key(), set()).add(user_id)


async def _refresh_card(context: ContextTypes.DEFAULT_TYPE, inquiry, edit_mode=False):
    if not inquiry.telegram.card_message_id or not inquiry.telegram.card_chat_id:
        return

    await context.bot.edit_message_text(
        chat_id=inquiry.telegram.card_chat_id,
        message_id=inquiry.telegram.card_message_id,
        text=build_inquiry_card(inquiry),
        parse_mode="HTML",
        reply_markup=inquiry_keyboard(inquiry, edit_mode=edit_mode),
    )


async def _delete_message_safely(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id):
    if not message_id:
        return

    try:
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id,
        )
    except Exception:
        logger.info("Could not delete message_id=%s in chat_id=%s", message_id, chat_id)


async def _handle_pending_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(TRADER_GROUP_CHAT_ID):
        return False

    user_id = update.effective_user.id
    pending = context.application.bot_data.pop(_pending_key(user_id), None)

    if not pending:
        return False

    inquiry_id = pending["inquiry_id"]
    pending_type = pending["type"]
    prompt_message_id = pending.get("prompt_message_id")
    text = update.message.text

    try:
        if pending_type == "edit":
            await update.message.reply_text("This edit mode was updated. Press Edit and choose a field button.")
            return True

        if pending_type == "set_stable":
            inquiry = set_stable_amount(inquiry_id, text)
            if inquiry is None:
                await update.message.reply_text("Inquiry not found.")
                return True

            await _refresh_card(context, inquiry, edit_mode=True)
            await _delete_message_safely(context, update.effective_chat.id, prompt_message_id)
            await _delete_message_safely(context, update.effective_chat.id, update.message.message_id)
            return True

        if pending_type == "set_fiat":
            inquiry = set_fiat_amount(inquiry_id, text)
            if inquiry is None:
                await update.message.reply_text("Inquiry not found.")
                return True

            await _refresh_card(context, inquiry, edit_mode=True)
            await _delete_message_safely(context, update.effective_chat.id, prompt_message_id)
            await _delete_message_safely(context, update.effective_chat.id, update.message.message_id)
            return True

        if pending_type == "set_rate":
            inquiry = set_rate(inquiry_id, text)
            if inquiry is None:
                await update.message.reply_text("Inquiry not found.")
                return True

            await _refresh_card(context, inquiry, edit_mode=True)
            await _delete_message_safely(context, update.effective_chat.id, prompt_message_id)
            await _delete_message_safely(context, update.effective_chat.id, update.message.message_id)
            return True

        if pending_type == "cancel":
            inquiry = ignore_inquiry(inquiry_id, reason=text)
            if inquiry is None:
                await update.message.reply_text("Inquiry not found.")
                return True

            await _refresh_card(context, inquiry)
            await update.message.reply_text(f"{inquiry.inquiry_id} marked no deal.")
            return True

    except InquiryActionError as exc:
        await update.message.reply_text(str(exc))
        return True

    return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if await _handle_pending_text(update, context):
        return

    if str(update.effective_chat.id) == str(TRADER_GROUP_CHAT_ID):
        return

    user = update.effective_user.full_name
    user_id = update.effective_user.id

    if user_id in _known_trader_user_ids(context):
        logger.info(
            "Ignoring trader reply from user_id=%s in client chat_id=%s",
            user_id,
            update.effective_chat.id,
        )
        return

    group = (
        update.effective_chat.title
        if update.effective_chat.title
        else "Private Chat"
    )
    chat_username = update.effective_chat.username
    message = update.message.text

    logger.info(
        "Received message from %s in %s; chat_id=%s message_id=%s",
        user,
        group,
        update.effective_chat.id,
        update.message.message_id,
    )

    decision = route_message(message)
    logger.info("Router decision: %s", decision)

    if decision != "PRICE":
        return

    active = repository.find_active_for_customer(
        customer_id=user_id,
        chat_id=update.effective_chat.id,
    )
    if active:
        logger.info(
            "Suppressing duplicate inquiry from user_id=%s; active=%s",
            user_id,
            active.inquiry_id,
        )
        return

    try:
        parsed = parse_message(message)
    except Exception:
        logger.exception("Gemini parsing failed; creating vague inquiry fallback")
        parsed = ParsedTrade(confidence=0.0)

    logger.info("Parsed inquiry: %s", parsed)

    ticket = create_inquiry(
        customer_name=user,
        customer_id=user_id,
        customer_group=group,
        chat_id=update.effective_chat.id,
        message_id=update.message.message_id,
        chat_username=chat_username,
        original_message=message,
        parsed=parsed,
    )
    ticket = preview_quote(ticket)

    logger.info("Created inquiry %s", ticket.inquiry_id)

    try:
        sent_message = await context.bot.send_message(
            chat_id=TRADER_GROUP_CHAT_ID,
            text=build_inquiry_card(ticket),
            parse_mode="HTML",
            reply_markup=inquiry_keyboard(ticket),
        )
    except Exception:
        logger.exception("Failed to send inquiry card for %s", ticket.inquiry_id)
        return

    ticket.telegram.card_message_id = sent_message.message_id
    ticket.telegram.card_chat_id = int(TRADER_GROUP_CHAT_ID)
    ticket.telegram.message_id = sent_message.message_id
    repository.save(ticket)


async def handle_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Chat ID: {update.effective_chat.id}")


async def handle_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_rates_debug_message())


async def handle_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Your Telegram user ID: {update.effective_user.id}"
    )


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query is None:
        return

    data = query.data or ""

    if ":" not in data:
        logger.warning("Received malformed callback data: %s", data)
        await query.answer("Invalid action.", show_alert=True)
        return

    action, inquiry_id = data.split(":", 1)
    stay_in_edit_mode = False

    trader = query.from_user
    trader_id = trader.id
    trader_name = trader.full_name
    _remember_trader(context, trader_id)

    try:
        if action == "lock":
            inquiry = lock_trade(
                inquiry_id=inquiry_id,
                trader_id=trader_id,
                trader_name=trader_name,
            )
            log_result = None
            log_failed = False
            if inquiry is not None:
                await context.bot.send_message(
                    chat_id=inquiry.telegram.chat_id,
                    text=build_lock_confirmation(inquiry),
                )
                try:
                    log_result = log_locked_trade(inquiry)
                except TradeLogError:
                    log_failed = True
                    logger.exception("Failed to log locked trade %s", inquiry.inquiry_id)

            if log_failed:
                answer = "Trade locked. Log failed."
            elif log_result:
                answer = "Trade locked and logged."
            else:
                answer = "Trade locked. Log not configured."

        elif action == "quote":
            inquiry = mark_quote_sent(
                inquiry_id=inquiry_id,
                trader_id=trader_id,
                trader_name=trader_name,
            )
            if inquiry is not None:
                await context.bot.send_message(
                    chat_id=inquiry.telegram.chat_id,
                    text=build_quote_message(inquiry),
                )
            answer = "Quote sent."

        elif action == "complete":
            inquiry = complete_inquiry(inquiry_id=inquiry_id)
            answer = "Completed."

        elif action == "edit":
            inquiry = repository.get(inquiry_id)
            if inquiry is None:
                await query.answer("Inquiry not found.", show_alert=True)
                return

            await query.answer("Edit mode.")
            await query.edit_message_text(
                text=build_inquiry_card(inquiry),
                parse_mode="HTML",
                reply_markup=inquiry_keyboard(inquiry, edit_mode=True),
            )
            return

        elif action == "done_edit":
            inquiry = repository.get(inquiry_id)
            answer = "Done editing."

        elif action.startswith("pair_"):
            _, asset, fiat = action.split("_", 2)
            inquiry = set_pair(inquiry_id, asset, fiat)
            answer = f"Pair set to {asset.upper()}/{fiat.upper()}."
            stay_in_edit_mode = True

        elif action == "direction_buy":
            inquiry = set_direction(inquiry_id, "buy")
            answer = "Direction set to buy."
            stay_in_edit_mode = True

        elif action == "direction_sell":
            inquiry = set_direction(inquiry_id, "sell")
            answer = "Direction set to sell."
            stay_in_edit_mode = True

        elif action == "set_stable":
            prompt_message = await query.message.reply_text("Send stable amount only, example: 122000")
            context.application.bot_data[_pending_key(trader_id)] = {
                "type": "set_stable",
                "inquiry_id": inquiry_id,
                "prompt_message_id": prompt_message.message_id,
            }
            await query.answer("Send stable amount only.", show_alert=False)
            return

        elif action == "set_fiat":
            prompt_message = await query.message.reply_text("Send fiat amount only, example: 7493240")
            context.application.bot_data[_pending_key(trader_id)] = {
                "type": "set_fiat",
                "inquiry_id": inquiry_id,
                "prompt_message_id": prompt_message.message_id,
            }
            await query.answer("Send fiat amount only.", show_alert=False)
            return

        elif action == "set_rate":
            prompt_message = await query.message.reply_text("Send rate only, example: 61.42")
            context.application.bot_data[_pending_key(trader_id)] = {
                "type": "set_rate",
                "inquiry_id": inquiry_id,
                "prompt_message_id": prompt_message.message_id,
            }
            await query.answer("Send rate only.", show_alert=False)
            return

        elif action == "refresh_rate":
            inquiry = refresh_sheet_rate(inquiry_id)
            answer = "Quote refreshed."

        elif action == "lock_preview":
            inquiry = prepare_lock_preview(
                inquiry_id=inquiry_id,
                trader_id=trader_id,
                trader_name=trader_name,
            )
            answer = "Lock preview ready."

        elif action == "cancel":
            context.application.bot_data[_pending_key(trader_id)] = {
                "type": "cancel",
                "inquiry_id": inquiry_id,
            }
            await query.answer("Send the no-deal reason.", show_alert=False)
            await query.message.reply_text("Send the No Deal reason.")
            return

        elif action == "open":
            inquiry = repository.get(inquiry_id)
            if inquiry is None:
                await query.answer("Inquiry not found.", show_alert=True)
                return

            link = build_message_link(inquiry)
            if link:
                await query.message.reply_text(link)
            else:
                await query.message.reply_text(
                    "No direct Telegram jump link is available for this chat. "
                    "Make the client group a supergroup or give it a public username, "
                    "then Open Group will redirect directly."
                )
            await query.answer("Open group link posted.")
            return

        else:
            logger.warning("Received unknown callback action: %s", action)
            await query.answer("Unknown action.", show_alert=True)
            return

    except InquiryActionError as exc:
        await query.answer(str(exc), show_alert=True)
        return
    except Exception:
        logger.exception("Failed to handle callback action=%s inquiry=%s", action, inquiry_id)
        await query.answer("Action failed. Check bot logs.", show_alert=True)
        return

    if inquiry is None:
        await query.answer("Inquiry not found.", show_alert=True)
        return

    await query.answer(answer)
    await query.edit_message_text(
        text=build_inquiry_card(inquiry),
        parse_mode="HTML",
        reply_markup=inquiry_keyboard(inquiry, edit_mode=stay_in_edit_mode),
    )


def run_bot():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        validate_required_settings()
    except ConfigError:
        logger.exception("Bot configuration is incomplete")
        raise

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )
    app.add_handler(CommandHandler("chatid", handle_chat_id))
    app.add_handler(CommandHandler("rates", handle_rates))
    app.add_handler(CommandHandler("whoami", handle_whoami))
    app.add_handler(CallbackQueryHandler(handle_button))

    logger.info("OTC AI Dealer is running")
    app.run_polling(drop_pending_updates=True)
