import frappe

# Prices in the database are stored in this currency
BASE_CURRENCY = "USD"

# Language-primary-tag → currency; anything else falls back to EUR
_LANG_TO_CURRENCY: dict[str, str] = {
    "EN": "USD",
    "EN-US": "USD",
    "EN-GB": "USD",
}

# Price fields present in list vs detail responses
PRICE_FIELDS_LIST = ["price_per_adult", "price_per_child", "transfer_fee"]
PRICE_FIELDS_DETAIL = [
    "price_per_adult",
    "price_per_child",
    "internal_transfer_fee",
    "external_transfer_fee",
    "transfer_fee",
]


def get_request_currency() -> str:
    """
    Resolve the target currency for the current request.

    Priority:
      1. ``X-Currency`` header — explicit client override (e.g. "EUR", "USD")
      2. ``Accept-Language`` header — EN variants → USD, everything else → EUR
      3. Falls back to USD when neither header is present.
    """
    explicit = frappe.request.headers.get("X-Currency", "").strip().upper()
    if explicit:
        return explicit

    lang_header = frappe.request.headers.get("Accept-Language", "").strip()
    if lang_header:
        primary = lang_header.split(",")[0].split(";")[0].strip().upper()
        return _LANG_TO_CURRENCY.get(primary, "EUR")

    return BASE_CURRENCY


def get_conversion_rate(from_currency: str, to_currency: str) -> float:
    """
    Return the conversion rate from *from_currency* to *to_currency* using
    Frappe's ``Currency Exchange`` doctype (rate entered manually by admins).

    Returns 1.0 when the currencies are the same or no rate record exists.
    """
    if from_currency == to_currency:
        return 1.0

    rate = frappe.db.get_value(
        "Currency Exchange",
        filters={"from_currency": from_currency, "to_currency": to_currency},
        fieldname="exchange_rate",
        order_by="date desc",
    )

    return float(rate) if isinstance(rate, (int, float, str)) else 1.0


def apply_currency(record: dict, price_fields: list[str], currency: str, rate: float) -> dict:
    """
    Convert all *price_fields* in *record* in-place using *rate*, then
    attach ``currency`` and ``exchange_rate`` to the record for the client.
    """
    for field in price_fields:
        if record.get(field) is not None:
            record[field] = round(float(record[field]) * rate, 2)
    record["currency"] = currency
    record["exchange_rate"] = rate
    return record
