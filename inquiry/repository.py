from datetime import datetime, timedelta, timezone

from inquiry.model import Inquiry, InquiryStatus


ACTIVE_STATUSES = {
    InquiryStatus.NEW,
    InquiryStatus.CLAIMED,
    InquiryStatus.QUOTE_READY,
    InquiryStatus.QUOTE_SENT,
    InquiryStatus.LOCK_PREVIEW,
}


PH_TZ = timezone(timedelta(hours=8))


def get_trade_group_key(inquiry: Inquiry):
    if inquiry.telegram.chat_id is not None:
        return f"chat:{inquiry.telegram.chat_id}"

    group_name = (inquiry.telegram.group_name or "").strip().lower()
    return f"group:{group_name}"


def _ph_date(value: datetime):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(PH_TZ).date()


class InquiryRepository:
    """
    In-memory repository.

    Later this can be replaced with:
    - SQLite
    - Firestore
    - PostgreSQL

    without changing the rest of the application.
    """

    def __init__(self):

        self._counter = 1

        self._inquiries = {}

    # ------------------------

    def next_id(self):

        inquiry_id = f"INQ-{self._counter:06}"

        self._counter += 1

        return inquiry_id

    # ------------------------

    def save(self, inquiry: Inquiry):

        self._inquiries[inquiry.inquiry_id] = inquiry

    # ------------------------

    def get(self, inquiry_id: str):

        return self._inquiries.get(inquiry_id)

    # ------------------------

    def get_all(self):

        return list(self._inquiries.values())

    # ------------------------

    def count(self):

        return len(self._inquiries)

    # ------------------------

    def exists(self, inquiry_id: str):

        return inquiry_id in self._inquiries

    # ------------------------

    def find_active_for_customer(self, customer_id, chat_id):
        for inquiry in reversed(self.get_all()):
            if inquiry.status not in ACTIVE_STATUSES:
                continue

            if inquiry.telegram.chat_id != chat_id:
                continue

            if customer_id is not None:
                if inquiry.customer.telegram_id == customer_id:
                    return inquiry
                continue

        return None

    # ------------------------

    def count_locked_today_for_group(self, trade_group_key, now=None, exclude_inquiry_id=None):
        if now is None:
            now = datetime.utcnow()

        today_ph = _ph_date(now)

        count = 0

        for inquiry in self.get_all():
            if exclude_inquiry_id and inquiry.inquiry_id == exclude_inquiry_id:
                continue

            locked_at = inquiry.locked_at

            if inquiry.status not in {
                InquiryStatus.LOCKED,
                InquiryStatus.COMPLETED,
                InquiryStatus.LOGGED,
            }:
                continue

            if locked_at is None or _ph_date(locked_at) != today_ph:
                continue

            if get_trade_group_key(inquiry) == trade_group_key:
                count += 1

        return count


repository = InquiryRepository()
