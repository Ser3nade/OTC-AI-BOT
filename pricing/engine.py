import re
import time
from typing import Optional

from config import (
    GOOGLE_SERVICE_ACCOUNT_FILE,
    PRICE_SHEET_ID,
    PRICE_WORKSHEET_NAME,
)


class PriceLookupError(Exception):
    pass


PRICE_CACHE_TTL_SECONDS = 30
_price_records_cache = {
    "expires_at": 0.0,
    "records": None,
    "error": None,
}


def clear_price_cache():
    _price_records_cache["expires_at"] = 0.0
    _price_records_cache["records"] = None
    _price_records_cache["error"] = None


def _normalize_key(value: str) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _normalize_pair(value: str) -> str:
    return (
        str(value)
        .strip()
        .upper()
        .replace(" ", "")
        .replace("-", "/")
    )


def _parse_rate(value) -> Optional[float]:

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    text = text.replace(",", "")

    match = re.search(r"\d+(\.\d+)?", text)

    if not match:
        return None

    return float(match.group(0))


def _get_worksheet():
    import gspread
    from gspread.exceptions import WorksheetNotFound

    service_account_file = GOOGLE_SERVICE_ACCOUNT_FILE
    sheet_id = str(PRICE_SHEET_ID or "").strip()
    worksheet_name = str(PRICE_WORKSHEET_NAME or "Prices").strip()

    if not service_account_file:
        raise PriceLookupError("GOOGLE_SERVICE_ACCOUNT_FILE is missing in .env")

    if not sheet_id:
        raise PriceLookupError("PRICE_SHEET_ID is missing in .env")

    gc = gspread.service_account(filename=service_account_file)

    spreadsheet = gc.open_by_key(sheet_id)

    try:
        return spreadsheet.worksheet(worksheet_name)
    except WorksheetNotFound:
        worksheets = spreadsheet.worksheets()
        available_titles = [worksheet.title for worksheet in worksheets]

        for worksheet in worksheets:
            if worksheet.title.strip().lower() == worksheet_name.lower():
                return worksheet

        if worksheets:
            return worksheets[0]

        raise PriceLookupError(
            f"Worksheet '{worksheet_name}' not found. Available tabs: {available_titles}"
        )
    except Exception as exc:
        raise PriceLookupError(
            f"Could not open worksheet '{worksheet_name}': {type(exc).__name__}: {exc}"
        ) from exc


def _get_records_from_worksheet(worksheet):

    values = worksheet.get_all_values()

    if not values:
        raise PriceLookupError("Price worksheet is empty")

    header_row_index = None
    header_row = None

    for index, row in enumerate(values):

        non_empty_headers = [
            _normalize_key(cell)
            for cell in row
            if _normalize_key(cell)
        ]

        if len(non_empty_headers) >= 2:
            header_row_index = index
            header_row = row
            break

    if header_row_index is None or header_row is None:
        raise PriceLookupError("Could not find a valid header row in the price worksheet")

    headers = []
    valid_indexes = []
    seen_headers = set()

    for index, header in enumerate(header_row):

        normalized_header = _normalize_key(header)

        if not normalized_header:
            continue

        if normalized_header in seen_headers:
            raise PriceLookupError(
                f"Duplicate non-empty header found: {header}"
            )

        seen_headers.add(normalized_header)
        headers.append(normalized_header)
        valid_indexes.append(index)

    records = []

    for row in values[header_row_index + 1:]:

        if not any(str(cell).strip() for cell in row):
            continue

        record = {}

        for header, index in zip(headers, valid_indexes):
            record[header] = row[index] if index < len(row) else ""

        records.append(record)

    return records


def _get_price_records(force_refresh=False):
    now = time.monotonic()

    if not force_refresh and _price_records_cache["expires_at"] > now:
        cached_error = _price_records_cache["error"]

        if cached_error is not None:
            raise cached_error

        return _price_records_cache["records"]

    try:
        worksheet = _get_worksheet()
        records = _get_records_from_worksheet(worksheet)
    except PriceLookupError as exc:
        _price_records_cache["expires_at"] = now + PRICE_CACHE_TTL_SECONDS
        _price_records_cache["records"] = None
        _price_records_cache["error"] = exc
        raise
    except Exception as exc:
        error = PriceLookupError(str(exc))
        _price_records_cache["expires_at"] = now + PRICE_CACHE_TTL_SECONDS
        _price_records_cache["records"] = None
        _price_records_cache["error"] = error
        raise error from exc

    _price_records_cache["expires_at"] = now + PRICE_CACHE_TTL_SECONDS
    _price_records_cache["records"] = records
    _price_records_cache["error"] = None

    return records


def _normalize_row(row: dict) -> dict:

    normalized = {}

    for key, value in row.items():
        normalized[_normalize_key(key)] = value

    return normalized


def _row_matches(row: dict, asset: str, fiat: str) -> bool:

    expected_pair_slash = f"{asset}/{fiat}"
    expected_pair_plain = f"{asset}{fiat}"

    pair_value = (
        row.get("currency_pair")
        or row.get("pair")
        or row.get("symbol")
        or row.get("market")
    )

    if pair_value:
        normalized_pair = _normalize_pair(pair_value)

        return normalized_pair in {
            expected_pair_slash,
            expected_pair_plain,
        }

    row_asset = (
        row.get("asset")
        or row.get("token")
        or row.get("coin")
        or row.get("stablecoin")
    )

    if row_asset:
        normalized_asset = _normalize_pair(row_asset)

        if normalized_asset in {
            expected_pair_slash,
            expected_pair_plain,
        }:
            return True

    row_fiat = (
        row.get("fiat")
        or row.get("currency")
        or row.get("quote")
    )

    if not row_asset or not row_fiat:
        return False

    return (
        str(row_asset).strip().upper() == asset
        and str(row_fiat).strip().upper() == fiat
    )


def _get_rate_from_row(row: dict, action: str) -> float:

    action = action.strip().lower()

    if action == "buy":
        candidate_columns = [
            "client_buy_rate",
            "buy_rate",
            "buying",
            "buying_rate",
            "ask",
            "ask_rate",
            "sell",
            "sell_rate",
            "selling",
            "selling_rate",
            "offer",
            "offer_rate",
        ]

    elif action == "sell":
        candidate_columns = [
            "client_sell_rate",
            "sell_rate",
            "selling",
            "selling_rate",
            "bid",
            "bid_rate",
            "buy",
            "buy_rate",
            "buying",
            "buying_rate",
        ]

    else:
        raise PriceLookupError(f"Unsupported action: {action}")

    for column in candidate_columns:

        if column not in row:
            continue

        rate = _parse_rate(row.get(column))

        if rate is not None:
            return rate

    raise PriceLookupError(
        f"No usable rate column found for action: {action}"
    )


def get_sheet_rate(asset: str, fiat: str, action: str, force_refresh=False) -> float:

    if not asset or not fiat or not action:
        raise PriceLookupError("Asset, fiat, and action are required")

    asset = asset.strip().upper()
    fiat = fiat.strip().upper()
    action = action.strip().lower()

    records = _get_price_records(force_refresh=force_refresh)

    for raw_row in records:

        row = _normalize_row(raw_row)

        if not _row_matches(row, asset, fiat):
            continue

        return _get_rate_from_row(row, action)

    raise PriceLookupError(
        f"No matching price row found for {asset}/{fiat}"
    )
