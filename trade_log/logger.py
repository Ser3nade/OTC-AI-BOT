from datetime import datetime, timedelta, timezone

from config import (
    GOOGLE_SERVICE_ACCOUNT_FILE,
    TRADE_LOG_SHEET_ID,
    TRADE_LOG_WORKSHEET_NAME,
    TRADE_LOG_WORKSHEET_TEMPLATE,
)
from inquiry.repository import repository
from trade_log.sheet_selector import select_trade_log_worksheet_name


PH_TZ = timezone(timedelta(hours=8))

HEADERS = [
    "Logged At PH",
    "Inquiry ID",
    "Deal #",
    "Status",
    "Trade Group",
    "Client",
    "Trader",
    "Direction",
    "Pair",
    "Stablecoin",
    "Stable Amount",
    "Fiat",
    "Fiat Amount",
    "Rate",
    "Source Chat ID",
    "Source Message ID",
    "Original Message",
]


class TradeLogError(RuntimeError):
    pass


def is_trade_log_enabled():
    return bool(str(TRADE_LOG_SHEET_ID or "").strip())


def _ph_timestamp(value=None):
    if value is None:
        value = datetime.utcnow()

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(PH_TZ).strftime("%Y-%m-%d %H:%M:%S")


def _open_spreadsheet():
    if not GOOGLE_SERVICE_ACCOUNT_FILE:
        raise TradeLogError("GOOGLE_SERVICE_ACCOUNT_FILE is missing in .env")

    if not TRADE_LOG_SHEET_ID:
        raise TradeLogError("TRADE_LOG_SHEET_ID is missing in .env")

    import gspread

    gc = gspread.service_account(filename=GOOGLE_SERVICE_ACCOUNT_FILE)
    return gc.open_by_key(str(TRADE_LOG_SHEET_ID).strip())


def _get_or_create_worksheet(spreadsheet, worksheet_name):
    from gspread.exceptions import WorksheetNotFound

    try:
        return spreadsheet.worksheet(worksheet_name)
    except WorksheetNotFound:
        return spreadsheet.add_worksheet(
            title=worksheet_name,
            rows=1000,
            cols=len(HEADERS),
        )


def _ensure_headers(worksheet):
    values = worksheet.get_all_values()

    if not values:
        worksheet.update("A1:Q1", [HEADERS])
        return []

    first_row = values[0]

    if first_row[:len(HEADERS)] != HEADERS:
        worksheet.update("A1:Q1", [HEADERS])
        values[0] = HEADERS

    return values


def _find_existing_log_row(values, inquiry_id):
    if not values:
        return None

    try:
        inquiry_id_column = values[0].index("Inquiry ID")
    except ValueError:
        return None

    for row_number, row in enumerate(values[1:], start=2):
        if inquiry_id_column >= len(row):
            continue

        if str(row[inquiry_id_column]).strip() == inquiry_id:
            return row_number

    return None


def _pair(inquiry):
    pair = str(inquiry.trade.currency_pair or "").strip().upper()

    if pair and pair != "UNKNOWN":
        return pair

    asset = str(inquiry.trade.asset or "").strip().upper()
    fiat = str(inquiry.trade.fiat or "").strip().upper()

    if asset and fiat and asset != "UNKNOWN" and fiat != "UNKNOWN":
        return f"{asset}/{fiat}"

    return ""


def _action_label(value):
    action = str(value or "").strip().lower()

    if action == "buy":
        return "BUY"

    if action == "sell":
        return "SELL"

    return action.upper()


def _row_for_inquiry(inquiry):
    return [
        _ph_timestamp(),
        inquiry.inquiry_id,
        inquiry.lock_sequence or "",
        inquiry.status.value,
        inquiry.telegram.group_name or "Private Chat",
        inquiry.customer.telegram_name,
        inquiry.ownership.claimed_by_name or "",
        _action_label(inquiry.trade.action),
        _pair(inquiry),
        str(inquiry.trade.asset or "").upper(),
        inquiry.trade.amount if inquiry.trade.amount is not None else "",
        str(inquiry.trade.fiat or "").upper(),
        inquiry.trade.fiat_amount if inquiry.trade.fiat_amount is not None else "",
        inquiry.trade.quoted_rate if inquiry.trade.quoted_rate is not None else "",
        inquiry.telegram.chat_id,
        inquiry.telegram.source_message_id or inquiry.telegram.message_id or "",
        inquiry.original_message or "",
    ]


def log_locked_trade(inquiry):
    if not is_trade_log_enabled():
        return None

    if inquiry.trade_logged_at is not None:
        return {
            "worksheet": inquiry.trade_log_worksheet,
            "row": inquiry.trade_log_row,
            "already_logged": True,
        }

    worksheet_name = select_trade_log_worksheet_name(
        inquiry.locked_at or datetime.utcnow(),
        fixed_name=TRADE_LOG_WORKSHEET_NAME,
        template=TRADE_LOG_WORKSHEET_TEMPLATE,
    )

    try:
        spreadsheet = _open_spreadsheet()
        worksheet = _get_or_create_worksheet(spreadsheet, worksheet_name)
        values = _ensure_headers(worksheet)
        existing_row = _find_existing_log_row(values, inquiry.inquiry_id)

        if existing_row:
            row_number = existing_row
            already_logged = True
        else:
            row_number = len(values) + 1 if values else 2
            worksheet.append_row(
                _row_for_inquiry(inquiry),
                value_input_option="USER_ENTERED",
            )
            already_logged = False
    except Exception as exc:
        raise TradeLogError(str(exc)) from exc

    inquiry.trade_logged_at = datetime.utcnow()
    inquiry.trade_log_worksheet = worksheet_name
    inquiry.trade_log_row = row_number
    repository.save(inquiry)

    return {
        "worksheet": worksheet_name,
        "row": row_number,
        "already_logged": already_logged,
    }
