import os
from typing import List, cast
from click import Path
import frappe
from pathlib import Path

from frappe.core.doctype.user.user import User
from frappe.model.document import Document
from frappe_tours.pkg.customfields.custom_fields_utils import install_custom_fields
from frappe_tours.pkg.seeder.role_utils import seed_app_roles
from frappe_tours.pkg.sql.sql_utils import run_sql_dir
SQL_DIR = Path(frappe.get_app_path("frappe_tours", "pkg", "sql" , "schema"))
CUSTOMFIELDS_PATH = os.path.join(frappe.get_app_path("frappe_tours"),  "pkg", "customfields" ,
                                 "fields")

INITIAL_USERS = [
    {"name": "Amr Emad", "email": "amr@gt.tours"},
    {"name": "Ahmed Darwish", "email": "ahmed@gt.tours"},
]

INITIAL_USERS_PASSWORD = "GT@2026"
ROLES_CONFIG = {
    "Marketer": {
        "desk_access": True,
        "perms": {
            "Comment": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
            "Web Page": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
            "Web Page Block": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1},
        },
    },
}

def update_client_secrets():
    client_secret = frappe.conf.get("OAUTH_CLIENT_SECRET")
    if not client_secret:
        frappe.log_error("OAUTH_CLIENT_SECRET not set in common_site_config.json")
        return

    def update_docs(docs_to_update: List[Document]):
        """Update client_secret on given docs"""
        for doc in docs_to_update:
            print("updating", doc, "with", client_secret)
            if hasattr(doc, "client_secret"):
                doc.set("client_secret", client_secret)
                doc.save(ignore_permissions=True)

    docs_to_update: List[Document] = []

    # Social Login Key (regular DocType)
    try:
        docs_to_update.append(frappe.get_doc("Social Login Key", "google"))
    except frappe.db.TableMissingError:
        frappe.logger().warning("Social Login Key table missing, skipping.")

    # Google Settings (Single DocType)
    try:
        docs_to_update.append(frappe.get_single("Google Settings"))
    except frappe.db.TableMissingError:
        frappe.logger().warning("Google Settings table missing, skipping.")

    # Call the small updater function
    update_docs(docs_to_update)

    frappe.db.commit()
    frappe.logger().info("OAuth client secrets updated from common_site_config.json")
def seed_initial_users(users: list[dict], password: str, role: str = "Marketer"):
    for u in users:
        email = u["email"].strip().lower()
        full_name = u["name"].strip()

        if frappe.db.exists("User", email):
            continue

        parts = full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        doc = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "enabled": 1,
            "send_welcome_email": 0,
        })

        doc.insert(ignore_permissions=True)
        doc = cast(User , doc)
        # set static password
        doc.new_password = password
        doc.save(ignore_permissions=True)

        # assign role
        doc.add_roles(role)

    frappe.db.commit()
def after_install():
    return {"ok" : True}
# Optional: run this on every migrate so changes apply during development
def after_migrate():
    install_custom_fields(CUSTOMFIELDS_PATH)
    run_sql_dir(SQL_DIR)
    seed_app_roles(ROLES_CONFIG, domain="gt.tours")
    seed_initial_users(
        INITIAL_USERS,
        password=INITIAL_USERS_PASSWORD,
        role="Marketer"
    )
    update_client_secrets()
    return {"ok" : True}


