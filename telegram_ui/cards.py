from html import escape

from inquiry.model import Inquiry, InquiryStatus
from pricing.engine import get_sheet_rate


def _format_amount(amount):

    if amount is None:
        return "Not specified"

    return f"{amount:g}"


def _format_rate(rate):

    if rate is None:
        return "N/A"

    return f"{rate:g}"


def _safe_get_rate(asset: str, fiat: str, action: str):

    try:
        return get_sheet_rate(
            asset=asset,
            fiat=fiat,
            action=action,
        )

    except Exception:
        return None


def _build_all_rates_message():

    usdt_buy = _safe_get_rate("USDT", "PHP", "buy")
    usdt_sell = _safe_get_rate("USDT", "PHP", "sell")

    usdc_buy = _safe_get_rate("USDC", "PHP", "buy")
    usdc_sell = _safe_get_rate("USDC", "PHP", "sell")

    return f"""USDT/PHP
Buying: {_format_rate(usdt_buy)} PHP/USDT
Selling: {_format_rate(usdt_sell)} PHP/USDT

USDC/PHP
Buying: {_format_rate(usdc_buy)} PHP/USDC
Selling: {_format_rate(usdc_sell)} PHP/USDC

Let us know if interested."""


def _build_specific_quote_message(inquiry: Inquiry):

    asset = str(inquiry.trade.asset).strip().upper()
    fiat = str(inquiry.trade.fiat).strip().upper()
    action = str(inquiry.trade.action).strip().lower()
    pair = str(inquiry.trade.currency_pair).strip().upper()
    amount = inquiry.trade.amount
    rate = inquiry.trade.quoted_rate

    if not pair or pair == "UNKNOWN":
        pair = f"{asset}/{fiat}"

    if action == "buy":
        action_label = "Buying"

    elif action == "sell":
        action_label = "Selling"

    else:
        return _build_all_rates_message()

    message = f"""{pair}
{action_label}: {_format_rate(rate)} {fiat}/{asset}"""

    if amount is not None and rate is not None:

        total = amount * rate

        message += f"""

For {_format_amount(amount)} {asset}, estimated total is {total:,.2f} {fiat}."""

    message += """

Let us know if interested."""

    return message


def _build_quote_message(inquiry: Inquiry):

    asset = str(inquiry.trade.asset).strip().upper()
    fiat = str(inquiry.trade.fiat).strip().upper()
    action = str(inquiry.trade.action).strip().lower()

    is_specific = (
        asset in ["USDT", "USDC"]
        and fiat in ["PHP", "USD"]
        and action in ["buy", "sell"]
        and inquiry.trade.quoted_rate is not None
    )

    if is_specific:
        return _build_specific_quote_message(inquiry)

    return _build_all_rates_message()


def _build_cancelled_card(inquiry: Inquiry):

    claimed_by = (
        inquiry.ownership.claimed_by_name
        if inquiry.ownership.claimed_by_name
        else "Nobody"
    )

    return f"""
❌ <b>NO DEAL</b>

🆔 <code>{escape(inquiry.inquiry_id)}</code>
👤 <b>Client</b>: {escape(inquiry.customer.telegram_name)}
💵 <b>Pair</b>: {escape(inquiry.trade.currency_pair)}
🙋 <b>Claimed By</b>: {escape(claimed_by)}
"""


def build_inquiry_card(inquiry: Inquiry) -> str:

    if inquiry.status == InquiryStatus.CANCELLED:
        return _build_cancelled_card(inquiry)

    amount = _format_amount(inquiry.trade.amount)

    status_icon = {
        InquiryStatus.NEW: "🟢",
        InquiryStatus.CLAIMED: "🟡",
        InquiryStatus.QUOTE_READY: "🟣",
        InquiryStatus.QUOTE_SENT: "🔵",
        InquiryStatus.LOCKED: "🔒",
        InquiryStatus.LOGGED: "📝",
        InquiryStatus.COMPLETED: "✅",
        InquiryStatus.CANCELLED: "❌",
    }.get(inquiry.status, "⚪")

    claimed_by = (
        inquiry.ownership.claimed_by_name
        if inquiry.ownership.claimed_by_name
        else "Nobody"
    )

    quote_preview = ""

    if inquiry.status in [
        InquiryStatus.CLAIMED,
        InquiryStatus.QUOTE_READY,
        InquiryStatus.QUOTE_SENT,
    ]:

        quote_message = _build_quote_message(inquiry)

        quote_preview = f"""

📨 <b>Message Preview</b>
<pre>{escape(quote_message)}</pre>
"""

    return f"""
{status_icon} <b>OTC INQUIRY</b>

👤 <b>Client</b>
{escape(inquiry.customer.telegram_name)}

💱 <b>Trade</b>
{escape(inquiry.trade.action.upper())} {escape(amount)} {escape(inquiry.trade.asset)}

💵 <b>Pair</b>
{escape(inquiry.trade.currency_pair)}

📌 <b>Status</b>
{escape(inquiry.status.value)}

🙋 <b>Claimed By</b>
{escape(claimed_by)}

🎯 <b>Confidence</b>
{inquiry.confidence:.0%}
{quote_preview}
🆔 <code>{escape(inquiry.inquiry_id)}</code>
"""