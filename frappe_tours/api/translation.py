import json
import frappe
from frappe_tours.bootstrap import get_app_container


@frappe.whitelist()
def generate_translations(fields: dict | str, target_languages: str) -> list:
    fields_dict: dict[str, str] = json.loads(fields) if isinstance(fields, str) else fields
    langs_list: list[str] = json.loads(target_languages) if isinstance(target_languages, str) else target_languages

    if not fields_dict:
        frappe.throw("fields is required", frappe.MandatoryError)
    if not langs_list:
        frappe.throw("target_languages is required", frappe.MandatoryError)

    container = get_app_container()
    return container.translation_agent.run(fields=fields_dict, target_languages=langs_list)
