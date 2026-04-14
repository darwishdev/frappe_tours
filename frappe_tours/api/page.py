from dataclasses import asdict
import json
from typing import List, cast
import frappe
import re
def to_snake_case(name):
    # Replace spaces and non-alphanumeric characters with underscore
    s0 = re.sub(r'[\s\W]+', '_', name)

    # Insert underscore between lowercase/digit and uppercase
    s1 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s0)

    # Normalize multiple underscores and strip edges
    s2 = re.sub(r'_+', '_', s1).strip('_')

    return s2.lower()

def apply_translation(blocks, lang):
    """
    Apply translations to each block's web_template_values based on the given language code.
    Translations are stored inside web_template_values["translations"] and are always removed
    from the response regardless of whether a translation was applied.

    - blocks: list of block dicts (already deep-parsed)
    - lang: language code string (e.g. "DE", "RU", "AR")
    """
    # Normalize lang: take primary tag only (e.g. "de-DE, en;q=0.9" → "DE")
    if lang:
        lang = lang.split(",")[0].split(";")[0].strip().upper()

    for block in blocks:
        template_values = block.get("web_template_values")
        if not template_values or not isinstance(template_values, dict):
            continue

        translations = template_values.pop("translations", None)

        if not lang or not translations or not isinstance(translations, dict):
            continue

        lang_translations = translations.get(lang)
        if not lang_translations or not isinstance(lang_translations, list):
            continue

        for translation in lang_translations:
            field = translation.get("field")
            translated_value = translation.get("translated_value")
            if field and translated_value is not None and field in template_values:
                template_values[field] = translated_value

    return blocks


def deep_json_load(obj):
    if isinstance(obj, str):
        try:
            parsed = json.loads(obj)
            return deep_json_load(parsed)
        except Exception:
            return obj

    elif isinstance(obj, list):
        return [deep_json_load(item) for item in obj]

    elif isinstance(obj, dict):
        return {k: deep_json_load(v) for k, v in obj.items()}

    return obj
@frappe.whitelist(allow_guest=True)
def page_find(route: str):
    if not route:
        frappe.throw("Route is required", frappe.MandatoryError)

    # --- Read language from request headers (e.g. Accept-Language: AR) ---
    lang = frappe.request.headers.get("Accept-Language", "").strip()

    route = route.strip("/")

    page_values =  frappe.db.sql("""
                                SELECT * FROM web_page_view where name = %s
                                """ , (route,), as_dict=True,)
    if not isinstance(page_values , list):
        return ""
    if len(page_values) == 0:
        return ""
    page_info = page_values[0]
    if "blocks" in page_info:
        blocks = getattr(page_info, "blocks")
        parsed_blocks = deep_json_load(blocks)
        if isinstance(parsed_blocks, list):
            translated_blocks = apply_translation(parsed_blocks, lang)
            setattr(page_info, "blocks", translated_blocks)
    return page_info
    if not page_name:
        frappe.throw(
            f"No published Web Page found for route: /{route}",
            frappe.DoesNotExistError,
        )

    page_data = frappe.db.get_value(
        "Web Page",
        page_name,
        fieldname=[
            "name",
            "title",
            "route",
            "content_type",
            "meta_title",
            "meta_description",
            "meta_image",
            "header",
            "breadcrumbs",
            "modified",
        ],
        as_dict=True,
    )

    # --- Custom meta tags (og:, twitter:, keywords, etc.) ---
    meta_tags = frappe.db.get_all(
        "Website Meta Tag",
        filters={"parent": page_name, "parenttype": "Web Page"},
        fields=["key", "value"],
        order_by="idx asc",
    )

    # --- Blocks ---
    blocks = frappe.db.get_all(
        "Web Page Block",
        filters={"parent": page_name, "parenttype": "Web Page"},
        fields=[
            "web_template",
            "web_template_values",
            "hide_block",
            "idx",
        ],
        order_by="idx asc",
    )

    for block in blocks:
        raw = block.get("web_template_values")
        if raw:
            try:
                parsed = frappe.parse_json(raw)
                if isinstance(parsed, dict):
                    parsed = _apply_translations(parsed, lang)
                block["web_template_values"] = parsed
            except Exception as e:
                print("failed to parse json" , e)
                pass

    blocks = [b for b in blocks if not b.get("hide_block")]

    return {
        "page": page_data,
        "meta_tags": meta_tags,
        "blocks": blocks,
    }
