from typing import NotRequired, TypedDict
import frappe
from frappe_tours.pkg.translation.translation_utils import get_request_lang, apply_doc_translations, apply_bulk_translations
from frappe_tours.pkg.currency.currency_utils import (
    get_request_currency,
    get_conversion_rate,
    apply_currency,
    BASE_CURRENCY,
    PRICE_FIELDS_LIST,
    PRICE_FIELDS_DETAIL,
)


@frappe.whitelist(allow_guest=True)
def tour_list(location: str | None = None):
    lang = get_request_lang()
    filters = {}
    if location:
        filters["to_destination"] = location
    records = frappe.get_all(
        "Tours",
        filters=filters,
        fields=[
            "name",
            "from_destination",
            "to_destination",
            "price_per_adult",
            "price_per_child",
            "image",
            "description",
            "tour_guide_included",
            "launch_included",
            "transfer_type",
            "transfer_fee",
        ],
        order_by="creation desc",
    )
    records = apply_bulk_translations(records, "Tours", lang)

    currency = get_request_currency()
    rate = get_conversion_rate(BASE_CURRENCY, currency)
    for record in records:
        apply_currency(record, PRICE_FIELDS_LIST, currency, rate)

    return records


@frappe.whitelist(allow_guest=True)
def tour_find(name: str):
    if not name:
        frappe.throw("Tour name is required", frappe.MandatoryError)

    if not frappe.db.exists("Tours", name):
        frappe.throw(f"Tour '{name}' not found", frappe.DoesNotExistError)

    doc = frappe.get_doc("Tours", name)
    result = doc.as_dict()
    result["images"] = [row.file for row in doc.images]

    lang = get_request_lang()
    result = apply_doc_translations(result, "Tours", lang)

    currency = get_request_currency()
    rate = get_conversion_rate(BASE_CURRENCY, currency)
    apply_currency(result, PRICE_FIELDS_DETAIL, currency, rate)

    return result


@frappe.whitelist(allow_guest=True)
def destination_list():
    lang = get_request_lang()
    records = frappe.get_all(
        "Locations",
        filters={"is_group": 0},
        fields=["name", "image", "parent_locations", "code"],
        order_by="name asc",
    )
    return apply_bulk_translations(records, "Locations", lang)


class TourReservationInput(TypedDict):
    client_name: str
    tour: str
    reservation_date: str
    adults: int
    children: NotRequired[int]
    infants: NotRequired[int]
    include_internal_transfer: NotRequired[bool]
    include_external_transfer: NotRequired[bool]


@frappe.whitelist(allow_guest=True)
def tour_reservation_create(data: dict):
    required = ["client_name", "tour", "reservation_date", "adults"]
    for field in required:
        if not data.get(field):
            frappe.throw(f"{field} is required", frappe.MandatoryError)

    if not frappe.db.exists("Tours", data["tour"]):
        frappe.throw(f"Tour '{data['tour']}' not found", frappe.DoesNotExistError)

    tour = frappe.get_doc("Tours", data["tour"])

    adults = int(data.get("adults", 0))
    children = int(data.get("children", 0))
    include_internal_transfer = int(data.get("include_internal_transfer", 0))
    include_external_transfer = int(data.get("include_external_transfer", 0))

    # Calculate total in base currency (USD) for storage
    total_price_usd = (adults * tour.price_per_adult) + (children * tour.price_per_child)
    if include_internal_transfer:
        total_price_usd += tour.internal_transfer_fee
    if include_external_transfer:
        total_price_usd += tour.external_transfer_fee

    reservation = frappe.get_doc({
        "doctype": "Tour Reservation",
        "client_name": data["client_name"],
        "tour": data["tour"],
        "reservation_date": data["reservation_date"],
        "adults": adults,
        "children": children,
        "infants": int(data.get("infants", 0)),
        "include_internal_transfer": include_internal_transfer,
        "include_external_transfer": include_external_transfer,
        "price_per_adult": tour.price_per_adult,
        "price_per_child": tour.price_per_child,
        "total_price": total_price_usd,
    })
    reservation.insert(ignore_permissions=True)

    # Convert the displayed total to the client's currency
    currency = get_request_currency()
    rate = get_conversion_rate(BASE_CURRENCY, currency)
    total_price_converted = round(total_price_usd * rate, 2)

    return {
        "name": reservation.name,
        "total_price": total_price_converted,
        "currency": currency,
        "exchange_rate": rate,
    }
