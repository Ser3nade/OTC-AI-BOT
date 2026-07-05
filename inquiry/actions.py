from datetime import datetime

from inquiry.model import InquiryStatus
from inquiry.repository import repository


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