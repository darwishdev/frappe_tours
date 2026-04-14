import frappe
from frappe.utils.password import update_password
from typing import Dict
DEFAULT_DOMAIN = "gt.tours"
DEFAULT_PASSWORD = "Avec@2290100"   # static password for seeded users
DEFAULT_LANGUAGE = "en"
def seed_app_roles(roles_config: Dict[str, dict], domain: str = DEFAULT_DOMAIN) -> dict:
    """
    roles_config format:
    {
      "POS Cashier": {
          "desk_access": True,
          "perms": {
              "POS Invoice": {"create":1, "read":1, "write":1, "submit":1},
              "Customer": {"read":1, "create":1},
          }
      },
      "Accountant": {
          "desk_access": True,
          "perms": {
              "Payment Entry": {"read":1, "print_perm":1},
          }
      }
    }
    """
    frappe.only_for("System Manager")
    frappe.flags.in_install = True

    created = []

    for role_name, cfg in roles_config.items():
        desk = 1
        perms = cfg.get("perms", {})

        # 1) Ensure Role
        if frappe.db.exists("Role", role_name):
            frappe.db.set_value("Role", role_name, "desk_access", desk)
        else:
            frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": desk}).insert(ignore_permissions=True)

        # 2) Ensure Custom DocPerms
        for dt, flags in perms.items():
            _ensure_custom_docperm(dt, role_name, flags)
            frappe.clear_cache(doctype=dt)

        # 3) Ensure User with same name as role
        email_local = role_name.lower().replace(" ", ".")
        email = f"{email_local}@{domain}"
        if frappe.db.exists("User", email):
            user = frappe.get_doc("User", email)
            user.set('enabled' , 1)
            user.set('language' , DEFAULT_LANGUAGE)
            user.set('role_profile_name' , None)
            user.save(ignore_permissions=True)
        else:
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": role_name,
                "send_welcome_email": 0,
                "language": DEFAULT_LANGUAGE,
                "user_type": "System User",
                "enabled": 1,
            })
            user.insert(ignore_permissions=True)

        # Always reset password to DEFAULT_PASSWORD
        update_password(user.name, DEFAULT_PASSWORD)

        created.append({"role": role_name, "email": email})

    frappe.db.commit()
    return {"ok": True, "users": created}


# ---------------- helper ----------------
def _ensure_custom_docperm(dt: str, role: str, flags: Dict[str, int]) -> None:
    from frappe.permissions import add_permission

    # Ensure row exists
    add_permission(dt, role, permlevel=0)

    name = frappe.db.get_value("Custom DocPerm", {"parent": dt, "role": role, "permlevel": 0}, "name")
    if not name:
        rows = frappe.get_all("Custom DocPerm", filters={"parent": dt, "role": role, "permlevel": 0}, pluck="name")
        name = rows[0] if rows else None

    if not name:
        doc = frappe.get_doc({
            "doctype": "Custom DocPerm",
            "parent": dt,
            "role": role,
            "permlevel": 0,
        })
    else:
        doc = frappe.get_doc("Custom DocPerm", f"{name}")

    if "print_perm" in flags:
        flags = {**flags, "print": flags["print_perm"]}
        flags.pop("print_perm", None)

    changed = False
    for k, v in flags.items():
        v01 = 1 if v else 0
        if doc.get(k) != v01:
            doc.set(k, v01)
            changed = True

    if changed or doc.is_new():
        doc.save(ignore_permissions=True)
