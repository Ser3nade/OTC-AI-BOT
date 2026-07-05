import os
import re
from typing import Optional

import gspread
from dotenv import load_dotenv


load_dotenv()


class PriceLookupError(Exception):
    pass


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

    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    sheet_id = os.getenv("PRICE_SHEET_ID")
    worksheet_name = os.getenv("PRICE_WORKSHEET_NAME", "Prices")

    if not service_account_file:
        raise PriceLookupError("GOOGLE_SERVICE_ACCOUNT_FILE is missing in .env")

    if not sheet_id:
        raise PriceLookupError("PRICE_SHEET_ID is missing in .env")

    gc = gspread.service_account(filename=service_account_file)

    spreadsheet = gc.open_by_key(sheet_id)

    return spreadsheet.worksheet(worksheet_name)


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
            "ask",
            "ask_rate",
            "sell",
            "sell_rate",
            "offer",
            "offer_rate",
        ]

    elif action == "sell":
        candidate_columns = [
            "client_sell_rate",
            "sell_rate",
            "bid",
            "bid_rate",
            "buy",
            "buy_rate",
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


def get_sheet_rate(asset: str, fiat: str, action: str) -> float:

    asset = asset.strip().upper()
    fiat = fiat.strip().upper()
    action = action.strip().lower()

    worksheet = _get_worksheet()

    records = _get_records_from_worksheet(worksheet)

    for raw_row in records:

        row = _normalize_row(raw_row)

        if not _row_matches(row, asset, fiat):
            continue

        return _get_rate_from_row(row, action)

    raise PriceLookupError(
        f"No matching price row found for {asset}/{fiat}"
    )