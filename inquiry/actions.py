import re
from datetime import datetime
from typing import Optional

from inquiry.model import InquiryStatus
from inquiry.repository import get_trade_group_key, repository
from pricing.engine import get_sheet_rate


class InquiryActionError(RuntimeError):
    pass


PAIR_PATTERN = re.compile(r"\b(USDT|USDC)\s*[/\-]?\s*(PHP|USD)\b", re.IGNORECASE)
RATE_PATTERN = re.compile(r"\brate\s*[:=]?\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(
    r"\b(?:amount|amt|qty|quantity)\s*[:=]?\s*(\d[\d,]*(?:\.\d+)?)\b",
    re.IGNORECASE,
)
ACTION_PATTERN = re.compile(r"\b(buy|bought|buying|sell|sold|selling)\b", re.IGNORECASE)


def _is_specific_quote(inquiry):
    asset = str(inquiry.trade.asset).strip().upper()
    fiat = str(inquiry.trade.fiat).strip().upper()
    action = str(inquiry.trade.action).strip().lower()

    return (
        asset in ["USDT", "USDC"]
        and fiat in ["PHP", "USD"]
        and action in ["buy", "sell"]
    )


def _attach_quote_preview(inquiry, force_refresh=False):
    if _is_specific_quote(inquiry) and (force_refresh or inquiry.trade.quoted_rate is None):
        try:
            inquiry.trade.quoted_rate = get_sheet_rate(
                asset=inquiry.trade.asset,
                fiat=inquiry.trade.fiat,
                action=inquiry.trade.action,
                force_refresh=force_refresh,
            )
        except Exception:
            if force_refresh:
                inquiry.trade.quoted_rate = None

    _refresh_fiat_amount(inquiry)
    return inquiry


def _refresh_fiat_amount(inquiry):
    amount = inquiry.trade.amount
    rate = inquiry.trade.quoted_rate

    if amount is not None and rate is not None:
        inquiry.trade.fiat_amount = amount * rate


def _refresh_stable_amount(inquiry):
    fiat_amount = inquiry.trade.fiat_amount
    rate = inquiry.trade.quoted_rate

    if fiat_amount is not None and rate is not None and rate > 0:
        inquiry.trade.amount = fiat_amount / rate


def _parse_number(value: str) -> float:
    text = str(value).strip().replace(",", "")

    if not re.fullmatch(r"\d+(\.\d+)?", text):
        raise InquiryActionError("Please send numbers only, like 122000 or 55.55.")

    return float(text)


def _ensure_claimed(inquiry, trader_id: int, trader_name: str):
    if inquiry.ownership.claimed_by_id is None:
        inquiry.ownership.claimed_by_id = trader_id
        inquiry.ownership.claimed_by_name = trader_name
        inquiry.ownership.claimed_at = datetime.utcnow()


def claim_inquiry(inquiry_id: str, trader_id: int, trader_name: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status != InquiryStatus.NEW:
        return inquiry

    inquiry.status = InquiryStatus.CLAIMED
    _ensure_claimed(inquiry, trader_id, trader_name)
    inquiry = _attach_quote_preview(inquiry)
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def mark_quote_ready(inquiry_id: str, trader_id: int, trader_name: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.CANCELLED, InquiryStatus.COMPLETED}:
        return inquiry

    _ensure_claimed(inquiry, trader_id, trader_name)
    inquiry = _attach_quote_preview(inquiry)
    inquiry.status = InquiryStatus.QUOTE_READY
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def mark_quote_sent(inquiry_id: str, trader_id: Optional[int] = None, trader_name: Optional[str] = None):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.CANCELLED, InquiryStatus.COMPLETED}:
        return inquiry

    if trader_id is not None and trader_name is not None:
        _ensure_claimed(inquiry, trader_id, trader_name)

    inquiry = _attach_quote_preview(inquiry)
    inquiry.status = InquiryStatus.QUOTE_SENT
    inquiry.quote_sent_at = datetime.utcnow()
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def ignore_inquiry(inquiry_id: str, reason: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    inquiry.status = InquiryStatus.CANCELLED
    inquiry.cancel_reason = reason.strip() or "No reason provided"
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def prepare_quote(inquiry_id: str):
    return mark_quote_ready(inquiry_id, trader_id=0, trader_name="System")


def preview_quote(inquiry):
    inquiry = _attach_quote_preview(inquiry)
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)
    return inquiry


def apply_trade_edit(inquiry_id: str, edit_text: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.LOCKED, InquiryStatus.COMPLETED, InquiryStatus.CANCELLED}:
        raise InquiryActionError("Locked, completed, or cancelled inquiries cannot be edited.")

    text = edit_text.strip()

    pair_match = PAIR_PATTERN.search(text)
    if pair_match:
        asset = pair_match.group(1).upper()
        fiat = pair_match.group(2).upper()
        inquiry.trade.asset = asset
        inquiry.trade.fiat = fiat
        inquiry.trade.currency_pair = f"{asset}/{fiat}"

    action_match = ACTION_PATTERN.search(text)
    if action_match:
        action = action_match.group(1).lower()
        inquiry.trade.action = "buy" if action in {"buy", "buying", "bought"} else "sell"

    amount_match = AMOUNT_PATTERN.search(text)
    if amount_match:
        inquiry.trade.amount = float(amount_match.group(1).replace(",", ""))

    rate_match = RATE_PATTERN.search(text)
    if rate_match:
        inquiry.trade.quoted_rate = float(rate_match.group(1))
    elif _is_specific_quote(inquiry):
        inquiry = _attach_quote_preview(inquiry)

    if inquiry.trade.asset and inquiry.trade.fiat:
        inquiry.trade.currency_pair = f"{inquiry.trade.asset}/{inquiry.trade.fiat}"

    _refresh_fiat_amount(inquiry)
    inquiry.status = InquiryStatus.QUOTE_READY
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def set_pair(inquiry_id: str, asset: str, fiat: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.LOCKED, InquiryStatus.COMPLETED, InquiryStatus.CANCELLED}:
        raise InquiryActionError("Locked, completed, or cancelled inquiries cannot be edited.")

    inquiry.trade.asset = asset.upper()
    inquiry.trade.fiat = fiat.upper()
    inquiry.trade.currency_pair = f"{inquiry.trade.asset}/{inquiry.trade.fiat}"
    inquiry.trade.quoted_rate = None
    inquiry = _attach_quote_preview(inquiry)
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def set_direction(inquiry_id: str, action: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.LOCKED, InquiryStatus.COMPLETED, InquiryStatus.CANCELLED}:
        raise InquiryActionError("Locked, completed, or cancelled inquiries cannot be edited.")

    inquiry.trade.action = action.lower()
    inquiry.trade.quoted_rate = None
    inquiry = _attach_quote_preview(inquiry)
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def set_stable_amount(inquiry_id: str, value: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.LOCKED, InquiryStatus.COMPLETED, InquiryStatus.CANCELLED}:
        raise InquiryActionError("Locked, completed, or cancelled inquiries cannot be edited.")

    inquiry.trade.amount = _parse_number(value)
    _refresh_fiat_amount(inquiry)
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def set_fiat_amount(inquiry_id: str, value: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.LOCKED, InquiryStatus.COMPLETED, InquiryStatus.CANCELLED}:
        raise InquiryActionError("Locked, completed, or cancelled inquiries cannot be edited.")

    inquiry.trade.fiat_amount = _parse_number(value)
    _refresh_stable_amount(inquiry)
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def set_rate(inquiry_id: str, value: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.LOCKED, InquiryStatus.COMPLETED, InquiryStatus.CANCELLED}:
        raise InquiryActionError("Locked, completed, or cancelled inquiries cannot be edited.")

    inquiry.trade.quoted_rate = _parse_number(value)

    if inquiry.trade.amount is not None:
        _refresh_fiat_amount(inquiry)
    elif inquiry.trade.fiat_amount is not None:
        _refresh_stable_amount(inquiry)

    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def prepare_lock_preview(inquiry_id: str, trader_id: int, trader_name: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.CANCELLED, InquiryStatus.COMPLETED}:
        return inquiry

    _ensure_claimed(inquiry, trader_id, trader_name)

    if inquiry.trade.quoted_rate is None:
        inquiry = _attach_quote_preview(inquiry)

    if inquiry.trade.amount is not None:
        _refresh_fiat_amount(inquiry)
    elif inquiry.trade.fiat_amount is not None:
        _refresh_stable_amount(inquiry)

    if inquiry.trade.amount is None:
        raise InquiryActionError("Stable amount or fiat amount is required before lock preview.")

    if inquiry.trade.fiat_amount is None:
        raise InquiryActionError("Fiat amount could not be calculated. Set the rate first.")

    if inquiry.trade.quoted_rate is None:
        raise InquiryActionError("Rate is required before lock preview.")

    now = datetime.utcnow()
    trade_group_key = get_trade_group_key(inquiry)

    inquiry.lock_sequence = (
        repository.count_locked_today_for_group(
            trade_group_key,
            now=now,
            exclude_inquiry_id=inquiry.inquiry_id,
        )
        + 1
    )
    inquiry.status = InquiryStatus.LOCK_PREVIEW
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def adjust_rate(inquiry_id: str, delta: float):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.LOCKED, InquiryStatus.COMPLETED, InquiryStatus.CANCELLED}:
        raise InquiryActionError("Locked, completed, or cancelled inquiries cannot be edited.")

    if inquiry.trade.quoted_rate is None:
        inquiry = _attach_quote_preview(inquiry)

    if inquiry.trade.quoted_rate is None:
        raise InquiryActionError("No rate is available yet. Set the pair/action or check the price sheet.")

    inquiry.trade.quoted_rate = max(0, inquiry.trade.quoted_rate + delta)
    _refresh_fiat_amount(inquiry)
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def adjust_amount(inquiry_id: str, delta: float):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.LOCKED, InquiryStatus.COMPLETED, InquiryStatus.CANCELLED}:
        raise InquiryActionError("Locked, completed, or cancelled inquiries cannot be edited.")

    current = inquiry.trade.amount or 0
    inquiry.trade.amount = max(0, current + delta)
    _refresh_fiat_amount(inquiry)
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def refresh_sheet_rate(inquiry_id: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status in {InquiryStatus.LOCKED, InquiryStatus.COMPLETED, InquiryStatus.CANCELLED}:
        raise InquiryActionError("Locked, completed, or cancelled inquiries cannot be edited.")

    inquiry = _attach_quote_preview(inquiry, force_refresh=True)
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def lock_trade(inquiry_id: str, trader_id: int, trader_name: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status == InquiryStatus.LOCKED:
        return inquiry

    if inquiry.status in {InquiryStatus.CANCELLED, InquiryStatus.COMPLETED}:
        return inquiry

    _ensure_claimed(inquiry, trader_id, trader_name)

    if inquiry.trade.quoted_rate is None:
        inquiry = _attach_quote_preview(inquiry)

    _refresh_fiat_amount(inquiry)

    if inquiry.trade.amount is None and inquiry.trade.fiat_amount is not None:
        _refresh_stable_amount(inquiry)

    if inquiry.trade.fiat_amount is None and inquiry.trade.amount is not None:
        _refresh_fiat_amount(inquiry)

    if inquiry.trade.amount is None:
        raise InquiryActionError("Stable amount or fiat amount is required before locking a trade.")

    if inquiry.trade.quoted_rate is None:
        raise InquiryActionError("Rate is required before locking a trade.")

    now = datetime.utcnow()
    trade_group_key = get_trade_group_key(inquiry)

    inquiry.lock_sequence = (
        repository.count_locked_today_for_group(
            trade_group_key,
            now=now,
            exclude_inquiry_id=inquiry.inquiry_id,
        )
        + 1
    )
    inquiry.status = InquiryStatus.LOCKED
    inquiry.locked_at = now
    inquiry.updated_at = now
    repository.save(inquiry)

    return inquiry


def complete_inquiry(inquiry_id: str):
    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status == InquiryStatus.CANCELLED:
        return inquiry

    if inquiry.status != InquiryStatus.LOCKED:
        raise InquiryActionError("Only locked trades can be completed.")

    inquiry.status = InquiryStatus.COMPLETED
    inquiry.completed_at = datetime.utcnow()
    inquiry.updated_at = datetime.utcnow()
    repository.save(inquiry)

    return inquiry


def build_message_link(inquiry):
    message_id = inquiry.telegram.source_message_id or inquiry.telegram.message_id

    if not message_id:
        return None

    username = inquiry.telegram.chat_username
    if username:
        return f"https://t.me/{username}/{message_id}"

    chat_id = str(inquiry.telegram.chat_id)
    if chat_id.startswith("-100"):
        internal_id = chat_id[4:]
        return f"https://t.me/c/{internal_id}/{message_id}"

    return None
