import frappe
from frappe_tours.container.app_container import AppContainer

_app_container = None


def get_app_container() -> AppContainer:
    global _app_container

    if _app_container is None:
        site_conf = frappe.get_site_config()
        gemini_key = site_conf.get("gemini_api_key")

        if not gemini_key:
            raise ValueError("gemini_api_key is missing in common_site_config.json")

        _app_container = AppContainer(gemini_api_key=str(gemini_key))

    return _app_container
