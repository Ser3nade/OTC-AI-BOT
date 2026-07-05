from inquiry.model import Inquiry


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


repository = InquiryRepository()