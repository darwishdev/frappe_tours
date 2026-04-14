import frappe


def get_request_lang() -> str:
    """
    Parse the Accept-Language request header and return a normalized uppercase code.
    e.g. "ar-AE, ar;q=0.9, en;q=0.8" → "AR"
    Returns empty string if header is absent or equals EN (fallback is already English).
    """
    header = frappe.request.headers.get("Accept-Language", "").strip()
    if not header:
        return ""
    lang = header.split(",")[0].split(";")[0].strip().upper()
    # EN is the source language — no translation lookup needed
    if lang in ("EN", "EN-US", "EN-GB"):
        return ""
    return lang


def apply_doc_translations(record: dict, parent_type: str, lang: str) -> dict:
    """
    Fetch Web Translations for a single record and overlay translated values.
    Falls back to the original value when no translation exists.
    """
    if not lang:
        return record

    translations = frappe.db.get_all(
        "Web Translations",
        filters={
            "parent_type": parent_type,
            "parent_id": record.get("name"),
            "locale": lang,
        },
        fields=["translated_field", "translated_value"],
    )

    for t in translations:
        if t.translated_field in record and t.translated_value:
            record[t.translated_field] = t.translated_value

    return record


def apply_bulk_translations(records: list, parent_type: str, lang: str) -> list:
    """
    Fetch Web Translations for a list of records in a single query and overlay
    translated values. Falls back to the original value when no translation exists.
    """
    if not lang or not records:
        return records

    names = [r.get("name") for r in records if r.get("name")]
    if not names:
        return records

    translations = frappe.db.get_all(
        "Web Translations",
        filters={
            "parent_type": parent_type,
            "parent_id": ["in", names],
            "locale": lang,
        },
        fields=["parent_id", "translated_field", "translated_value"],
    )

    by_id: dict[str, dict] = {}
    for t in translations:
        by_id.setdefault(t.parent_id, {})[t.translated_field] = t.translated_value

    for record in records:
        rec_translations = by_id.get(record.get("name"), {})
        for field, value in rec_translations.items():
            if field in record and value:
                record[field] = value

    return records
