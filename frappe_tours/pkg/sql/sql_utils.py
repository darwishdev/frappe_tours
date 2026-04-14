import subprocess, shlex, frappe
import frappe
from pathlib import Path
from typing import Dict, Iterable
import frappe
from frappe.model.document import Document
import pymysql.cursors
def exec_sql_file(sql_path: Path) -> None:
    """Execute a SQL file using mysql CLI (supports DELIMITER)."""
    site_conf = frappe.get_site_config()
    db_name = site_conf.get("db_name")
    db_user = site_conf.get("db_name")
    db_password = site_conf.get("db_password")
    host = site_conf.get("db_host", "localhost")

    if not sql_path.exists():
        frappe.throw(f"SQL file not found: {sql_path}")

    cmd = f"mariadb -h {host} -u {db_user} -p{db_password} {db_name} < {shlex.quote(str(sql_path))}"
    subprocess.check_call(cmd, shell=True)

def run_sql_dir(base_dir: str | Path) -> None:
    """
    Run all .sql files inside base_dir sequentially.
    Sorted alphabetically to ensure deterministic order.
    """
    base_dir = Path(base_dir)
    if not base_dir.exists():
        frappe.throw(f"SQL directory not found: {base_dir}")

    sql_files = sorted(base_dir.glob("*.sql"))
    if not sql_files:
        frappe.logger().info(f"No SQL files found in {base_dir}")
        return

    for sql_file in sql_files:
        frappe.logger().info(f"Executing SQL file: {sql_file}")
        exec_sql_file(sql_file)
def run_sql(callback):
    conn = frappe.db.get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor) # type: ignore[arg-type]
    try:
        result = callback(cur , conn)
        return result
    finally:
        cur.close()

# ------------------------------------------------------------
# DB → Python type mapping
# ------------------------------------------------------------



