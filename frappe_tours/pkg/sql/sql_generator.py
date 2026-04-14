import  frappe
from typing import Dict, List, Literal, TypedDict, cast
import frappe
from pathlib import Path
TYPE_MAP: Dict[str, str] = {
    "varchar": "str",
    "char": "str",
    "text": "str",
    "longtext": "str",
    "int": "int",
    "bigint": "int",
    "decimal": "float",
    "float": "float",
    "double": "float",
    "date": "date",
    "datetime": "datetime",
    "timestamp": "datetime",
    "tinyint": "int",
    "smallint": "int",
    "json": "dict",
}


class InformationSchemaColumn(TypedDict):
    COLUMN_NAME: str
    DATA_TYPE: str
    IS_NULLABLE: Literal["YES", "NO"]
    COLUMN_DEFAULT: str | None

FRAPPE_SYSTEM_FIELDS = {
    "creation",
    "modified",
    "modified_by",
    "owner",
    "docstatus",
    "idx",
    "_user_tags",
    "_comments",
    "_assign",
    "_liked_by",
}

def is_not_required(col: InformationSchemaColumn) -> bool:
    return (
        col["IS_NULLABLE"] == "YES"
        or col["COLUMN_DEFAULT"] == "NULL"
        or col["COLUMN_NAME"] == "name"
        or  col["COLUMN_NAME"] in FRAPPE_SYSTEM_FIELDS
    )
def generate_typed_dict_for_table(
    table_name: str,
    *,
    dto_name: str | None = None,
    output_file: str | Path,
) -> Path:
    """
    Generate a TypedDict DTO from a MariaDB table or view using frappe.db.sql.

    - Uses Frappe-managed DB connection
    - Creates the output file if it does not exist
    - Overwrites the file if it already exists
    - Returns the absolute path to the generated file
    """

    # --------------------------------------------------------
    # Resolve output path (IMPORTANT)
    # --------------------------------------------------------
    output_path = Path(output_file).expanduser()

    # --------------------------------------------------------
    # Fetch schema info
    # --------------------------------------------------------
    raw_rows = frappe.db.sql(
        """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """,
        (table_name,),
        as_dict=True,
    )

    # --------------------------------------------------------
    # Sanity checks on DB result
    # --------------------------------------------------------
    if raw_rows is None:
        raise RuntimeError("frappe.db.sql returned None")

    if not isinstance(raw_rows, list):
        raise TypeError(
            f"Expected list from frappe.db.sql, got {type(raw_rows)}"
        )


    rows = cast(list[InformationSchemaColumn], raw_rows)

    # --------------------------------------------------------
    # Resolve DTO class name
    # --------------------------------------------------------
    class_name = (
        dto_name
        or table_name.replace("tab", "").replace(" ", "") + "DTO"
    )

    # --------------------------------------------------------
    # Generate file content
    # --------------------------------------------------------
    lines: list[str] = [
        "# AUTO-GENERATED FILE",
        "# Source: MariaDB information_schema",
        "# Do not edit manually",
        "",
        "from typing import TypedDict, NotRequired",
        "from datetime import date, datetime",
        "",
        f"class {class_name}(TypedDict):",
    ]

    for col in rows:
        db_type = col["DATA_TYPE"]
        py_type = TYPE_MAP.get(db_type, "str")
        if  is_not_required(col):
            py_type = f"NotRequired[{py_type}]"

        lines.append(f"    {col['COLUMN_NAME']}: {py_type}")

    content = "\n".join(lines) + "\n"

    # --------------------------------------------------------
    # File system sanity checks
    # --------------------------------------------------------
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to create directories for {output_path}"
        ) from exc

    # --------------------------------------------------------
    # Write file (create or overwrite)
    # --------------------------------------------------------
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise PermissionError(
            f"No permission to create directory: {output_path.parent}"
        ) from exc

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    frappe.logger().info(f"Generated DTO → {output_path}")

    return output_path

def table_to_dto_name(prefix: str, table_name: str) -> str:
    """
    Convert prefixed table name to PascalCase DTO name.

    Example:
      prefix: "tal_"
      tal_job_applicants_view -> JobApplicantsView
      tal_job_view -> JobView
    """
    if not table_name.startswith(prefix):
        raise ValueError(f"Table does not start with '{prefix}': {table_name}")

    name = table_name.removeprefix(prefix).replace(' ' , '_')
    parts = name.split("_")

    return "".join(p.capitalize() for p in parts if p)
class TablesSearchResult(TypedDict):
    TABLE_NAME: str

def sql_generate_by_prefix(
    *,
    prefix:str,
    output_file: str | Path = "../apps/mawhub/mawhub/sqltypes/tal_models.py",
) -> Path:
    """
    Generate TypedDicts for all tables/views starting with `tal_`
    and write them into a single Python file.
    """

    output_path = Path(output_file).expanduser()

    # --------------------------------------------------------
    # Fetch all tal_* tables & views
    # --------------------------------------------------------
    raw_tables = frappe.db.sql(
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME LIKE concat(%(prefix)s)
        ORDER BY TABLE_NAME
        """,
        {"prefix" : f"{prefix}%"},
        as_dict=True,
    )

    if not raw_tables:
        raise ValueError(f"No tables found with prefix '{prefix}'")

    if not isinstance(raw_tables, list):
        raise TypeError(
            f"Expected list from frappe.db.sql, got {type(raw_tables)}"
        )


    tables = cast(list[TablesSearchResult], raw_tables)

    table_names = [row["TABLE_NAME"] for row in tables]
    # --------------------------------------------------------
    # File header
    # --------------------------------------------------------
    lines: list[str] = [
        "# AUTO-GENERATED FILE",
        "# Source: MariaDB information_schema",
        f"# Contains TypedDicts for ${prefix}* tables",
        "# Do not edit manually",
        "",
        "from typing import TypedDict, NotRequired",
        "from datetime import date, datetime",
        "",
    ]

    # --------------------------------------------------------
    # Generate DTOs
    # --------------------------------------------------------
    for table_name in table_names:
        raw_columns = frappe.db.sql(
            """
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            (table_name,),
            as_dict=True,
        )

        if not raw_columns:
            continue

        columns = cast(list[InformationSchemaColumn], raw_columns)
        class_name = table_to_dto_name(prefix,table_name)

        lines.append(f"class {class_name}(TypedDict):")

        for col in columns:
            py_type = TYPE_MAP.get(col["DATA_TYPE"], "str")
            if is_not_required(col):
                py_type = f"NotRequired[{py_type}]"

            lines.append(f"    {col['COLUMN_NAME']}: {py_type}")

        lines.append("")  # blank line between classes

    # --------------------------------------------------------
    # Write file
    # --------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    frappe.logger().info(
        f"Generated {prefix} DTOs for {len(table_names)} tables → {output_path}"
    )

    return output_path


def sql_generate_by_table_names(
    *,
    table_names:List[str],
    output_file: str | Path = "../apps/mawhub/mawhub/sqltypes/table_models.py",
) -> Path:
    """
    Generate TypedDicts for all tables/views starting with `tal_`
    and write them into a single Python file.
    """

    output_path = Path(output_file).expanduser()

    # --------------------------------------------------------
    # Fetch all tal_* tables & views
    # --------------------------------------------------------


    lines: list[str] = [
        "# AUTO-GENERATED FILE",
        "# Source: MariaDB information_schema",
        f"# Contains TypedDicts for ${table_names}* tables",
        "# Do not edit manually",
        "",
        "from typing import TypedDict, NotRequired",
        "from datetime import date, datetime",
        "",
    ]

    # --------------------------------------------------------
    # Generate DTOs
    # --------------------------------------------------------
    for table_name in table_names:
        raw_columns = frappe.db.sql(
            """
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            (table_name,),
            as_dict=True,
        )

        if not raw_columns:
            continue

        columns = cast(list[InformationSchemaColumn], raw_columns)
        class_name = table_to_dto_name("tab",table_name)

        lines.append(f"class {class_name}(TypedDict):")

        for col in columns:
            py_type = TYPE_MAP.get(col["DATA_TYPE"], "str")
            if is_not_required(col):
                py_type = f"NotRequired[{py_type}]"

            lines.append(f"    {col['COLUMN_NAME']}: {py_type}")

        lines.append("")  # blank line between classes

    # --------------------------------------------------------
    # Write file
    # --------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    frappe.logger().info(
        f"Generated DTOs for {len(table_names)} tables → {output_path}"
    )

    return output_path

