import ast
from pathlib import Path

from config import IGNORE_DIRS


def parse_imports(content: str, file_path: str) -> list[dict]:
    """Extract all imports from a Python file."""

    imports = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        # import x, y, z
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "type": "import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "from_module": None
                })

        # from x import y, z
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append({
                    "type": "from_import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "from_module": module
                })

    return imports


def parse_classes_and_functions(content: str) -> dict:
    """Extract classes and functions from a Python file."""

    structure = {
        "classes": [],
        "functions": []
    }

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return structure

    for node in ast.iter_child_nodes(tree):
        # Top-level functions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            structure["functions"].append({
                "name": node.name,
                "args": [arg.arg for arg in node.args.args],
                "docstring": ast.get_docstring(node) or "",
                "lines": f"{node.lineno}-{node.end_lineno}"
            })

        # Classes
        elif isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        "name": item.name,
                        "args": [arg.arg for arg in item.args.args],
                        "docstring": ast.get_docstring(item) or ""
                    })

            structure["classes"].append({
                "name": node.name,
                "methods": methods,
                "docstring": ast.get_docstring(node) or "",
                "lines": f"{node.lineno}-{node.end_lineno}"
            })

    return structure


def analyze_repo(repo_path: str) -> dict:
    """Analyze entire repo structure and dependencies."""

    repo_path = Path(repo_path)

    analysis = {
        "files": {},
        "dependencies": [],
        "entry_points": [],
        "modules": set()
    }

    # Find all Python files
    for file_path in repo_path.rglob("*.py"):
        # Skip ignored directories
        if any(ignored in file_path.parts for ignored in IGNORE_DIRS):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        relative_path = str(file_path.relative_to(repo_path))

        # Parse file
        imports = parse_imports(content, relative_path)
        structure = parse_classes_and_functions(content)

        analysis["files"][relative_path] = {
            "imports": imports,
            "classes": structure["classes"],
            "functions": structure["functions"],
            "is_entry_point": _is_entry_point(content, file_path.name)
        }

        # Track module name
        module_name = file_path.stem
        analysis["modules"].add(module_name)

        # Check if entry point
        if analysis["files"][relative_path]["is_entry_point"]:
            analysis["entry_points"].append(relative_path)

    # Build dependency graph
    analysis["dependencies"] = _build_dependency_graph(analysis["files"], analysis["modules"])
    analysis["modules"] = list(analysis["modules"])

    return analysis


def _is_entry_point(content: str, filename: str) -> bool:
    """Check if file is an entry point."""

    entry_indicators = [
        'if __name__ == "__main__"',
        "if __name__ == '__main__'",
        "uvicorn.run",
        "app.run",
        "streamlit",
        "st.set_page_config"
    ]

    if filename in ["main.py", "app.py", "run.py", "cli.py"]:
        return True

    return any(indicator in content for indicator in entry_indicators)


def _build_dependency_graph(files: dict, local_modules: set) -> list[dict]:
    """Build dependency relationships between files."""

    dependencies = []

    for file_path, file_info in files.items():
        for imp in file_info["imports"]:
            # Check if it's a local import
            module = imp["from_module"] or imp["module"]
            module_base = module.split(".")[0]

            if module_base in local_modules:
                dependencies.append({
                    "from": file_path,
                    "to": module,
                    "type": imp["type"]
                })

    return dependencies
