import json
import os
import frappe


def _cleanup_corrupted_custom_fields():
    # Remove rows that can cause NoneType crashes
    frappe.db.sql("""
        DELETE FROM `tabCustom Field`
        WHERE
            dt IS NULL OR dt = ''
            OR fieldname IS NULL OR fieldname = ''
    """)
    frappe.db.commit()


def _validate_df(doctype: str, df: dict) -> bool:
    if not isinstance(df, dict):
        return False

    if not df.get("fieldname") or not df.get("fieldtype"):
        frappe.log_error(
            f"Invalid Custom Field for {doctype}: {df}",
            "Custom Fields Installer"
        )
        return False

    if df["fieldtype"] in ("Link", "Table") and not df.get("options"):
        frappe.log_error(
            f"Missing options for {df['fieldtype']} in {doctype}: {df}",
            "Custom Fields Installer"
        )
        return False

    return True

def _upsert_custom_field(doctype: str, df: dict) -> bool:
    """
    Returns True if DB changed (insert/update), False otherwise.
    """
    fieldname = df["fieldname"]
    doc = None  # ✅ ensure always defined

    existing_name = frappe.db.get_value(
        "Custom Field",
        {"dt": doctype, "fieldname": fieldname},
        "name",
    )

    if existing_name:
        try:
            doc = frappe.get_doc("Custom Field", f"{existing_name}")
        except Exception:
            # corrupted row → delete & recreate
            frappe.db.sql(
                "DELETE FROM `tabCustom Field` WHERE name=%s",
                (existing_name,),
            )
            frappe.db.commit()
            doc = None
            existing_name = None

    if not existing_name:
        # create
        payload = df.copy()
        payload.update({
            "doctype": "Custom Field",
            "dt": doctype,
            "owner": "Administrator",
        })
        doc = frappe.get_doc(payload)
        doc.flags.ignore_validate = True
        doc.insert(ignore_permissions=True)
        return True

    # update (doc is guaranteed to exist here)
    assert doc is not None, "Custom Field doc must exist here"
    before = doc.as_dict()
    doc.flags.ignore_validate = True
    doc.update(df)
    after = doc.as_dict()

    if before != after:
        doc.save(ignore_permissions=True)
        return True

    return False


def install_custom_fields(custom_dir: str):
    _cleanup_corrupted_custom_fields()

    doctypes_to_update = set()

    for fname in os.listdir(custom_dir):
        if not fname.endswith(".json"):
            continue

        path = os.path.join(custom_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            fields = json.load(f)

        if not fields:
            continue

        doctype = os.path.splitext(fname)[0].replace("_", " ")

        if not frappe.db.exists("DocType", doctype):
            frappe.throw(
                f"Invalid Doctype from customfields filename: {doctype}"
            )

        changed = False
        for df in fields:
            if not _validate_df(doctype, df):
                continue
            if _upsert_custom_field(doctype, df):
                changed = True

        if changed:
            doctypes_to_update.add(doctype)

    for doctype in doctypes_to_update:
        frappe.clear_cache(doctype=doctype)
        frappe.db.updatedb(doctype)

