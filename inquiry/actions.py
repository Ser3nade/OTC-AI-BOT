from datetime import datetime

from inquiry.model import InquiryStatus
from inquiry.repository import repository
from pricing.engine import get_sheet_rate


def _is_specific_quote(inquiry):

    asset = str(inquiry.trade.asset).strip().upper()
    fiat = str(inquiry.trade.fiat).strip().upper()
    action = str(inquiry.trade.action).strip().lower()

    return (
        asset in ["USDT", "USDC"]
        and fiat in ["PHP", "USD"]
        and action in ["buy", "sell"]
    )


def _attach_quote_preview(inquiry):

    if _is_specific_quote(inquiry):

        inquiry.trade.quoted_rate = get_sheet_rate(
            asset=inquiry.trade.asset,
            fiat=inquiry.trade.fiat,
            action=inquiry.trade.action,
        )

    else:

        inquiry.trade.quoted_rate = None

    return inquiry


def claim_inquiry(inquiry_id: str, trader_id: int, trader_name: str):

    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    if inquiry.status != InquiryStatus.NEW:
        return inquiry

    inquiry.status = InquiryStatus.CLAIMED

    inquiry.ownership.claimed_by_id = trader_id
    inquiry.ownership.claimed_by_name = trader_name
    inquiry.ownership.claimed_at = datetime.utcnow()

    inquiry = _attach_quote_preview(inquiry)

    inquiry.updated_at = datetime.utcnow()

    repository.save(inquiry)

    return inquiry


def ignore_inquiry(inquiry_id: str):

    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    inquiry.status = InquiryStatus.CANCELLED
    inquiry.updated_at = datetime.utcnow()

    repository.save(inquiry)

    return inquiry


def prepare_quote(inquiry_id: str):

    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    inquiry = _attach_quote_preview(inquiry)

    inquiry.updated_at = datetime.utcnow()

    repository.save(inquiry)

    return inquiry


def mark_quote_sent(inquiry_id: str):

    inquiry = repository.get(inquiry_id)

    if inquiry is None:
        return None

    inquiry.status = InquiryStatus.QUOTE_SENT
    inquiry.updated_at = datetime.utcnow()

    repository.save(inquiry)

    return inquiry