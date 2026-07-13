from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# =====================================================
# STATUS
# =====================================================

class InquiryStatus(Enum):
    NEW = "NEW"
    CLAIMED = "CLAIMED"
    QUOTE_READY = "QUOTE_READY"
    QUOTE_SENT = "QUOTE_SENT"
    LOCK_PREVIEW = "LOCK_PREVIEW"
    LOCKED = "LOCKED"
    LOGGED = "LOGGED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# =====================================================
# TELEGRAM
# =====================================================

@dataclass
class TelegramInfo:

    chat_id: int

    message_id: int

    group_name: str

    source_message_id: Optional[int] = None

    card_message_id: Optional[int] = None

    card_chat_id: Optional[int] = None

    chat_username: Optional[str] = None


# =====================================================
# CUSTOMER
# =====================================================

@dataclass
class CustomerInfo:

    telegram_name: str

    telegram_id: Optional[int] = None

    resolved_name: Optional[str] = None


# =====================================================
# TRADE
# =====================================================

@dataclass
class TradeInfo:

    action: str

    asset: str

    fiat: str

    currency_pair: str

    amount: Optional[float]

    quoted_rate: Optional[float] = None

    mentioned_rate: Optional[float] = None

    fiat_amount: Optional[float] = None


# =====================================================
# OWNERSHIP
# =====================================================

@dataclass
class OwnershipInfo:

    claimed_by_id: Optional[int] = None

    claimed_by_name: Optional[str] = None

    claimed_at: Optional[datetime] = None


# =====================================================
# INQUIRY
# =====================================================

@dataclass
class Inquiry:

    inquiry_id: str

    telegram: TelegramInfo

    customer: CustomerInfo

    trade: TradeInfo

    ownership: OwnershipInfo = field(default_factory=OwnershipInfo)

    status: InquiryStatus = InquiryStatus.NEW

    original_message: str = ""

    confidence: float = 0.0

    cancel_reason: Optional[str] = None

    quote_sent_at: Optional[datetime] = None

    locked_at: Optional[datetime] = None

    lock_sequence: Optional[int] = None

    trade_logged_at: Optional[datetime] = None

    trade_log_worksheet: Optional[str] = None

    trade_log_row: Optional[int] = None

    completed_at: Optional[datetime] = None

    created_at: datetime = field(default_factory=datetime.utcnow)

    updated_at: datetime = field(default_factory=datetime.utcnow)
