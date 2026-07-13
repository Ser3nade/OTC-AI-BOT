from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from inquiry.actions import build_message_link
from inquiry.model import Inquiry, InquiryStatus


def _open_group_button(inquiry: Inquiry):
    link = build_message_link(inquiry)

    if link:
        return InlineKeyboardButton("Open Group", url=link)

    return InlineKeyboardButton(
        "No Group Link",
        callback_data=f"open:{inquiry.inquiry_id}",
    )


def inquiry_keyboard(inquiry: Inquiry, edit_mode=False):
    inquiry_id = inquiry.inquiry_id

    if inquiry.status in {InquiryStatus.COMPLETED, InquiryStatus.CANCELLED}:
        return None

    if edit_mode:
        keyboard = [
            [
                InlineKeyboardButton("USDT/PHP", callback_data=f"pair_usdt_php:{inquiry_id}"),
                InlineKeyboardButton("USDC/PHP", callback_data=f"pair_usdc_php:{inquiry_id}"),
            ],
            [
                InlineKeyboardButton("USDT/USD", callback_data=f"pair_usdt_usd:{inquiry_id}"),
                InlineKeyboardButton("USDC/USD", callback_data=f"pair_usdc_usd:{inquiry_id}"),
            ],
            [
                InlineKeyboardButton("Buy", callback_data=f"direction_buy:{inquiry_id}"),
                InlineKeyboardButton("Sell", callback_data=f"direction_sell:{inquiry_id}"),
            ],
            [
                InlineKeyboardButton("Set Stable Amount", callback_data=f"set_stable:{inquiry_id}"),
                InlineKeyboardButton("Set Fiat Amount", callback_data=f"set_fiat:{inquiry_id}"),
            ],
            [
                InlineKeyboardButton("Set Rate", callback_data=f"set_rate:{inquiry_id}"),
            ],
            [
                InlineKeyboardButton("Lock Preview", callback_data=f"lock_preview:{inquiry_id}"),
                InlineKeyboardButton("Done Editing", callback_data=f"done_edit:{inquiry_id}"),
            ],
        ]

        return InlineKeyboardMarkup(keyboard)

    keyboard = [
        [
            _open_group_button(inquiry),
            InlineKeyboardButton("Edit", callback_data=f"edit:{inquiry_id}"),
        ],
        [
            InlineKeyboardButton("Send Quote", callback_data=f"quote:{inquiry_id}"),
            InlineKeyboardButton("Refresh Quote", callback_data=f"refresh_rate:{inquiry_id}"),
        ],
        [
            InlineKeyboardButton("Lock Preview", callback_data=f"lock_preview:{inquiry_id}"),
            InlineKeyboardButton("Lock Trade", callback_data=f"lock:{inquiry_id}"),
        ],
        [
            InlineKeyboardButton("Complete", callback_data=f"complete:{inquiry_id}"),
            InlineKeyboardButton("No Deal", callback_data=f"cancel:{inquiry_id}"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)
