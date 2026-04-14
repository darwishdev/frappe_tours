import ast
import json
from pathlib import Path

TYPE_MAP = {
    "str": "string",
    "int": "number",
    "float": "number",
    "bool": "boolean",
    "Any": "any",
    "dict": "Record<string, any>",
    "list": "any[]",
    "datetime": "string",
    "date": "string",
    "List": "any[]"
}
def generate_api_resources(input_file: Path, app_name: str) -> str:
    """Parses a Frappe API file and generates TS resource functions."""
    tree = ast.parse(input_file.read_text(encoding="utf-8"))
    module_path = input_file.stem  # e.g., 'job_opening'

    # Imports for the generated TS file
    ts_code = [
        "import { createResource } from '@/utils/resource';",
        "// Import your DTOs here - you might want to automate this path",
        "import { JobOpeningDTO } from './tal_models';",
        ""
    ]

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            # Check if function is whitelisted
            decorators = [
                d.func.id if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)
                else (d.id if isinstance(d, ast.Name) else "")
                for d in node.decorator_list
            ]

            # raise Exception(f"edec {tree} {json.dumps(decorators)}")
            # if "whitelist" not in decorators:
            #     continue
            #
            func_name = node.name
            # Frappe path: app_name.folder.file.func_name
            frappe_path = f"{app_name}.{module_path}.{func_name}"

            # 1. Parse Arguments
            args = []
            arg_interface = []
            for arg in node.args.args:
                arg_name = arg.arg
                py_type = ast.unparse(arg.annotation) if arg.annotation else "Any"
                ts_type = TYPE_MAP.get(py_type, py_type)
                args.append(f"{arg_name}: {ts_type}")
                arg_interface.append(f"  {arg_name}: {ts_type};")

            # 2. Parse Return Type
            ret_py = ast.unparse(node.returns) if node.returns else "Any"
            # Handle List[DTO] -> DTO[]
            if "List[" in ret_py:
                inner = ret_py.replace("List[", "").replace("]", "")
                ret_ts = f"{TYPE_MAP.get(inner, inner)}[]"
            else:
                ret_ts = TYPE_MAP.get(ret_py, ret_py)

            # 3. Generate the TS function
            ts_code.append(f"export function use_{func_name}(initialParams?: {{ {', '.join(args)} }}) {{")
            ts_code.append(f"  return createResource<{ret_ts}>({{")
            ts_code.append(f"    url: '{frappe_path}',")
            # Logic to detect method (defaults to POST for whitelist usually)
            ts_code.append(f"    params: initialParams,")
            ts_code.append(f"  }});")
            ts_code.append(f"}}\n")

    return "\n".join(ts_code)
def convert_py_file_to_ts(input_file: Path) -> str:
    """Parses a Python file and extracts TypedDicts as TS Interfaces."""
    try:
        tree = ast.parse(input_file.read_text(encoding="utf-8"))
    except Exception:
        return ""

    ts_chunks = []

    # Mapping for standard types

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            # Verify it inherits from TypedDict
            is_dto = any(isinstance(b, ast.Name) and b.id == "TypedDict" for b in node.bases)
            if not is_dto:
                continue

            ts_chunks.append(f"export interface {node.name} {{")

            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field = item.target.id

                    # 1. Check for Wrappers (Required, NotRequired, Optional)
                    # We unparse the annotation to check the string representation
                    raw_type_str = ast.unparse(item.annotation)

                    is_optional = "NotRequired" in raw_type_str or "Optional" in raw_type_str
                    # Required[str] is NOT optional in TS, so we just strip the wrapper

                    # 2. Extract the core type inside the brackets [...]
                    # This cleans "Required[str]" -> "str" or "List[JobDTO]" -> "List[JobDTO]"
                    clean_type = raw_type_str
                    for wrapper in ["Required", "NotRequired", "Optional"]:
                        if raw_type_str.startswith(wrapper):
                            # Extract content between first '[' and last ']'
                            start = raw_type_str.find("[") + 1
                            end = raw_type_str.rfind("]")
                            clean_type = raw_type_str[start:end]
                            break

                    # 3. Handle Lists (List[Type] -> Type[])
                    if clean_type.startswith("List["):
                        inner = clean_type[5:-1] # Strip "List[" and "]"
                        final_type = f"{TYPE_MAP.get(inner, inner)}[]"
                    else:
                        final_type = TYPE_MAP.get(clean_type, clean_type)

                    optional_suffix = "?" if is_optional else ""
                    ts_chunks.append(f"  {field}{optional_suffix}: {final_type};")

            ts_chunks.append("}\n")

    return "\n".join(ts_chunks)

# Usage
# print(generate_ts_from_py("your_models_file.py"))
def process_ts_conversion(input_path: str, output_path: str):
    in_p = Path(input_path).expanduser()
    out_p = Path(output_path).expanduser()

    # Case 1: Single File
    if in_p.is_file():
        content = convert_py_file_to_ts(in_p)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        # If output_path is a directory, name the file based on input
        final_out = out_p / in_p.with_suffix(".ts").name if out_p.is_dir() else out_p
        final_out.write_text(content)
        return [final_out]

    # Case 2: Directory
    generated_files = []
    for py_file in in_p.glob("**/*.py"):
        content = convert_py_file_to_ts(py_file)
        if not content.strip(): continue # Skip files with no TypedDicts

        # Maintain folder structure in output
        relative_path = py_file.relative_to(in_p).with_suffix(".ts")
        target = out_p / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        generated_files.append(target)

    return generated_files
