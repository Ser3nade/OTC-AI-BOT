from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from inquiry.model import InquiryStatus


def inquiry_keyboard(inquiry_id: str, status: InquiryStatus):

    if status == InquiryStatus.NEW:
        keyboard = [
            [
                InlineKeyboardButton(
                    "🙋 Claim",
                    callback_data=f"claim:{inquiry_id}",
                ),
                InlineKeyboardButton(
                    "❌ No Deal",
                    callback_data=f"ignore:{inquiry_id}",
                ),
            ]
        ]

        return InlineKeyboardMarkup(keyboard)

    if status == InquiryStatus.CLAIMED:
        keyboard = [
            [
                InlineKeyboardButton(
                    "↗️ Open Group",
                    callback_data=f"noop:{inquiry_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📨 Send Quote",
                    callback_data=f"quote:{inquiry_id}",
                ),
                InlineKeyboardButton(
                    "✏️ Edit",
                    callback_data=f"noop:{inquiry_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔒 Lock",
                    callback_data=f"noop:{inquiry_id}",
                ),
                InlineKeyboardButton(
                    "❌ No Deal",
                    callback_data=f"ignore:{inquiry_id}",
                ),
            ],
        ]

        return InlineKeyboardMarkup(keyboard)

    if status == InquiryStatus.QUOTE_SENT:
        keyboard = [
            [
                InlineKeyboardButton(
                    "↗️ Open Group",
                    callback_data=f"noop:{inquiry_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "✏️ Edit",
                    callback_data=f"noop:{inquiry_id}",
                ),
                InlineKeyboardButton(
                    "🔒 Lock",
                    callback_data=f"noop:{inquiry_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ No Deal",
                    callback_data=f"ignore:{inquiry_id}",
                ),
            ],
        ]

        return InlineKeyboardMarkup(keyboard)

    return None