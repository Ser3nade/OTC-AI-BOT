from html import escape

from inquiry.model import Inquiry, InquiryStatus
from pricing.engine import get_sheet_rate


UNSPECIFIED = "Unspecified"

STATUS_LABELS = {
    InquiryStatus.NEW: "🟢 NEW",
    InquiryStatus.QUOTE_SENT: "📨 QUOTE SENT",
    InquiryStatus.LOCK_PREVIEW: "👀 LOCK PREVIEW",
    InquiryStatus.LOCKED: "🔒 LOCKED",
    InquiryStatus.COMPLETED: "✅ COMPLETE",
    InquiryStatus.CANCELLED: "❌ NO DEAL",
}


def _clean(value):
    text = str(value or "").strip()

    if not text or text.upper() == "UNKNOWN":
        return UNSPECIFIED

    return text


def _format_amount(amount):
    if amount is None:
        return UNSPECIFIED

    return f"{amount:,.2f}"


def _format_rate(rate):
    if rate is None:
        return UNSPECIFIED

    return f"{rate:.4f}"


def _is_specified(value):
    return _clean(value) != UNSPECIFIED


def _safe_get_rate(asset: str, fiat: str, action: str):
    try:
        return get_sheet_rate(
            asset=asset,
            fiat=fiat,
            action=action,
        ), None
    except Exception as exc:
        return None, str(exc)


SUPPORTED_RATE_PAIRS = [
    ("USDT", "PHP"),
    ("USDC", "PHP"),
    ("USDT", "USD"),
    ("USDC", "USD"),
]


def _pair(inquiry: Inquiry):
    pair = str(inquiry.trade.currency_pair or "").strip().upper()

    if pair and pair != "UNKNOWN":
        return pair

    asset = str(inquiry.trade.asset or "").strip().upper()
    fiat = str(inquiry.trade.fiat or "").strip().upper()

    if asset and fiat and asset != "UNKNOWN" and fiat != "UNKNOWN":
        return f"{asset}/{fiat}"

    return UNSPECIFIED


def _asset(inquiry: Inquiry):
    return _clean(inquiry.trade.asset).upper()


def _fiat(inquiry: Inquiry):
    return _clean(inquiry.trade.fiat).upper()


def _sheet_preview_pairs(inquiry: Inquiry):
    asset = str(inquiry.trade.asset or "").strip().upper()
    fiat = str(inquiry.trade.fiat or "").strip().upper()

    if (asset, fiat) in SUPPORTED_RATE_PAIRS:
        return [(asset, fiat)]

    if asset in {"USDT", "USDC"}:
        return [
            (pair_asset, pair_fiat)
            for pair_asset, pair_fiat in SUPPORTED_RATE_PAIRS
            if pair_asset == asset
        ]

    if fiat in {"PHP", "USD"}:
        return [
            (pair_asset, pair_fiat)
            for pair_asset, pair_fiat in SUPPORTED_RATE_PAIRS
            if pair_fiat == fiat
        ]

    return SUPPORTED_RATE_PAIRS


def _build_sheet_rate_preview(inquiry: Inquiry):
    lines = []
    errors = []

    for asset, fiat in _sheet_preview_pairs(inquiry):
        buy, buy_error = _safe_get_rate(asset, fiat, "buy")
        sell, sell_error = _safe_get_rate(asset, fiat, "sell")

        lines.append(
            f"{asset}/{fiat}: B {_format_rate(buy)} / S {_format_rate(sell)}"
        )

        if buy_error:
            errors.append(buy_error)
        if sell_error:
            errors.append(sell_error)

    if not lines:
        return None

    preview = "Sheet:\n" + "\n".join(lines)

    if errors and all("Unspecified" in line for line in lines):
        preview += "\nSheet error: use /rates"

    return preview


def build_quote_message(inquiry: Inquiry):
    asset = str(inquiry.trade.asset).strip().upper()
    fiat = str(inquiry.trade.fiat).strip().upper()
    action = str(inquiry.trade.action).strip().lower()
    pair = _pair(inquiry)
    amount = inquiry.trade.amount
    rate = inquiry.trade.quoted_rate

    has_specific_quote = (
        asset in {"USDT", "USDC"}
        and fiat in {"PHP", "USD"}
        and action in {"buy", "sell"}
        and rate is not None
    )

    if not has_specific_quote:
        return build_all_rates_message()

    action_label = "Buying" if action == "buy" else "Selling"

    message = f"""{pair}
{action_label}: {_format_rate(rate)} {_clean(fiat)}/{_clean(asset)}"""

    if amount is not None and rate is not None:
        total = inquiry.trade.fiat_amount
        if total is None:
            total = amount * rate

        message += f"""
For {_format_amount(amount)} {_clean(asset)}, estimated total is {_format_amount(total)} {_clean(fiat)}."""

    message += "\nLet us know if interested."
    return message


def build_all_rates_message():
    pairs = [
        ("USDT", "PHP"),
        ("USDC", "PHP"),
        ("USDT", "USD"),
        ("USDC", "USD"),
    ]

    sections = []
    errors = []

    for asset, fiat in pairs:
        buy, buy_error = _safe_get_rate(asset, fiat, "buy")
        sell, sell_error = _safe_get_rate(asset, fiat, "sell")

        sections.append(
            f"""{asset}/{fiat}
Buying {_format_rate(buy)} / Selling {_format_rate(sell)}"""
        )

        if buy_error:
            errors.append(buy_error)
        if sell_error:
            errors.append(sell_error)

    message = "\n\n".join(sections)

    return message


def build_rates_debug_message():
    message = build_all_rates_message()
    errors = []

    for asset, fiat in [
        ("USDT", "PHP"),
        ("USDC", "PHP"),
        ("USDT", "USD"),
        ("USDC", "USD"),
    ]:
        _, buy_error = _safe_get_rate(asset, fiat, "buy")
        _, sell_error = _safe_get_rate(asset, fiat, "sell")

        if buy_error:
            errors.append(f"{asset}/{fiat} buy: {buy_error}")
        if sell_error:
            errors.append(f"{asset}/{fiat} sell: {sell_error}")

    if errors:
        message += "\n\nErrors:\n" + "\n".join(errors[:4])

    return message


def build_lock_confirmation(inquiry: Inquiry):
    sequence = inquiry.lock_sequence or 1
    rate = _format_rate(inquiry.trade.quoted_rate)
    pair = _pair(inquiry)
    action = str(inquiry.trade.action).strip().lower()
    direction = "bought" if action == "buy" else "sold"
    asset = _asset(inquiry)
    fiat = _fiat(inquiry)
    amount = _format_amount(inquiry.trade.amount)
    fiat_amount = _format_amount(inquiry.trade.fiat_amount)

    return (
        f"{sequence}.\n\n"
        f"Rate is {rate} {pair}. You {direction} a total of "
        f"{amount} {asset} for {fiat_amount} {fiat}"
    )


def _direction(inquiry: Inquiry):
    action = _clean(inquiry.trade.action)

    if action != UNSPECIFIED:
        return action.upper()

    return UNSPECIFIED


def _build_trade_form(inquiry: Inquiry):
    lines = []

    if _pair(inquiry) != UNSPECIFIED:
        lines.append(f"Pair: {_pair(inquiry)}")

    if inquiry.trade.amount is not None:
        lines.append(f"Amount: {_format_amount(inquiry.trade.amount)}")

    if _is_specified(inquiry.trade.asset):
        lines.append(f"Stablecoin: {_asset(inquiry)}")

    if inquiry.trade.fiat_amount is not None:
        lines.append(f"Fiat amount: {_format_amount(inquiry.trade.fiat_amount)}")

    if _is_specified(inquiry.trade.fiat):
        lines.append(f"Fiat: {_fiat(inquiry)}")

    if inquiry.trade.quoted_rate is not None:
        lines.append(f"Rate: {_format_rate(inquiry.trade.quoted_rate)}")

    if _direction(inquiry) != UNSPECIFIED:
        lines.append(f"Direction: {_direction(inquiry)}")

    if not lines:
        lines.append("Details: rate inquiry")

    return "\n".join(lines)


def build_inquiry_card(inquiry: Inquiry) -> str:
    source_group = inquiry.telegram.group_name or "Private Chat"
    status_label = STATUS_LABELS.get(inquiry.status, inquiry.status.value)

    if inquiry.status == InquiryStatus.COMPLETED:
        return (
            f"<b>{escape(inquiry.inquiry_id)}</b> {escape(status_label)} | "
            f"From: {escape(source_group)} | "
            f"{escape(_direction(inquiry))} {escape(_format_amount(inquiry.trade.amount))} "
            f"{escape(_pair(inquiry))} @ {escape(_format_rate(inquiry.trade.quoted_rate))}"
        )

    if inquiry.status == InquiryStatus.CANCELLED:
        reason = inquiry.cancel_reason or "No reason provided"
        return (
            f"<b>{escape(inquiry.inquiry_id)}</b> {escape(status_label)} | "
            f"From: {escape(source_group)} | "
            f"{escape(_pair(inquiry))} | {escape(reason)}"
        )

    lines = [
        f"<b>{escape(inquiry.inquiry_id)}</b> | {escape(status_label)}",
        f"From: {escape(source_group)}",
        f"Client: {escape(inquiry.customer.telegram_name)}",
        escape(_build_trade_form(inquiry)),
    ]

    sheet_preview = _build_sheet_rate_preview(inquiry)
    if sheet_preview:
        lines.append(escape(sheet_preview))

    if inquiry.status == InquiryStatus.LOCK_PREVIEW:
        lines.append(f"Lock Preview: <code>{escape(build_lock_confirmation(inquiry))}</code>")

    if inquiry.status == InquiryStatus.LOCKED:
        lines.append(f"Locked: <code>{escape(build_lock_confirmation(inquiry))}</code>")

    return "\n".join(lines)
