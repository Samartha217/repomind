import ast
from pathlib import Path

from config import IGNORE_DIRS, SUPPORTED_EXTENSIONS, TREE_SITTER_LANGUAGES
from ingestion.tree_sitter_parser import get_parser, is_tree_sitter_supported

# Tree-sitter import node types per language
IMPORT_NODE_TYPES = {
    "javascript": ["import_statement"],
    "typescript": ["import_statement"],
    "tsx":        ["import_statement"],
    "java":       ["import_declaration"],
    "go":         ["import_declaration", "import_spec"],
    "rust":       ["use_declaration"],
    "c":          ["preproc_include"],
    "cpp":        ["preproc_include"],
}


def parse_imports(content: str, file_path: str) -> list[dict]:
    """Extract all imports from a Python file using AST."""

    imports = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "type": "import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "from_module": None
                })

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


def parse_imports_tree_sitter(content: str, file_path: str, language: str) -> list[dict]:
    """Extract import statements from non-Python files using Tree-sitter."""

    imports = []
    target_types = IMPORT_NODE_TYPES.get(language, [])
    if not target_types:
        return imports

    try:
        parser = get_parser(language)
        content_bytes = content.encode("utf-8")
        tree = parser.parse(content_bytes)
    except Exception:
        return imports

    def extract_import_text(node) -> str:
        """Get the raw text of an import node."""
        return content_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()

    def walk(node):
        if node.type in target_types:
            raw = extract_import_text(node)
            # Normalise to a module name for the dependency graph
            module = _normalise_import(raw, language)
            if module:
                imports.append({
                    "type": "import",
                    "module": module,
                    "alias": None,
                    "from_module": None,
                    "raw": raw,
                })
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return imports


def _normalise_import(raw: str, language: str) -> str:
    """
    Extract just the module name from a raw import statement.
    e.g. 'import React from "react"' → 'react'
         'import "fmt"'              → 'fmt'
         '#include <stdio.h>'        → 'stdio'
         'use std::collections'      → 'std'
    """
    import re

    raw = raw.strip()

    if language in ("javascript", "typescript", "tsx"):
        # from 'x' / from "x"  or  import 'x'
        match = re.search(r'from\s+["\']([^"\']+)["\']', raw)
        if match:
            return match.group(1)
        match = re.search(r'import\s+["\']([^"\']+)["\']', raw)
        if match:
            return match.group(1)

    elif language == "java":
        # import com.example.Foo;
        match = re.match(r'import\s+([\w.]+)', raw)
        if match:
            parts = match.group(1).split(".")
            return parts[0]  # top-level package

    elif language == "go":
        # import "fmt"  or  "github.com/user/pkg"
        match = re.search(r'"([^"]+)"', raw)
        if match:
            parts = match.group(1).split("/")
            return parts[-1]  # last path segment

    elif language == "rust":
        # use std::collections::HashMap
        match = re.match(r'use\s+([\w:]+)', raw)
        if match:
            return match.group(1).split("::")[0]

    elif language in ("c", "cpp"):
        # #include <stdio.h>  or  #include "myfile.h"
        match = re.search(r'#include\s+[<"]([^>"]+)[>"]', raw)
        if match:
            stem = Path(match.group(1)).stem
            return stem

    return ""


def parse_classes_and_functions(content: str) -> dict:
    """Extract classes and functions from a Python file."""

    structure = {"classes": [], "functions": []}

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return structure

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            structure["functions"].append({
                "name": node.name,
                "args": [arg.arg for arg in node.args.args],
                "docstring": ast.get_docstring(node) or "",
                "lines": f"{node.lineno}-{node.end_lineno}"
            })

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
    """Analyze entire repo structure and dependencies — Python + all Tree-sitter languages."""

    repo_path = Path(repo_path)

    analysis = {
        "files": {},
        "dependencies": [],
        "entry_points": [],
        "modules": set()
    }

    # Collect all supported files
    all_extensions = set(SUPPORTED_EXTENSIONS)

    for file_path in repo_path.rglob("*"):
        if file_path.is_dir():
            continue
        if any(ignored in file_path.parts for ignored in IGNORE_DIRS):
            continue
        if file_path.suffix not in all_extensions:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        relative_path = str(file_path.relative_to(repo_path))
        ext = file_path.suffix

        if ext == ".py":
            imports = parse_imports(content, relative_path)
            structure = parse_classes_and_functions(content)
            is_entry = _is_entry_point(content, file_path.name)
        elif is_tree_sitter_supported(ext):
            language = TREE_SITTER_LANGUAGES.get(ext)
            imports = parse_imports_tree_sitter(content, relative_path, language)
            # Reuse tree-sitter chunk extraction for classes/functions
            from ingestion.tree_sitter_parser import parse_with_tree_sitter
            chunks = parse_with_tree_sitter(content, relative_path, language)
            classes = [c for c in chunks if c["type"] == "class"]
            functions = [c for c in chunks if c["type"] == "function"]
            structure = {
                "classes": [{"name": c["name"], "methods": [], "docstring": c.get("docstring", ""), "lines": f"{c['start_line']}-{c['end_line']}"} for c in classes],
                "functions": [{"name": f["name"], "args": [], "docstring": f.get("docstring", ""), "lines": f"{f['start_line']}-{f['end_line']}"} for f in functions],
            }
            is_entry = _is_entry_point_generic(content, file_path.name)
        else:
            continue

        analysis["files"][relative_path] = {
            "imports": imports,
            "classes": structure["classes"],
            "functions": structure["functions"],
            "is_entry_point": is_entry,
            "language": ext,
        }

        module_name = file_path.stem
        analysis["modules"].add(module_name)

        if is_entry:
            analysis["entry_points"].append(relative_path)

    analysis["dependencies"] = _build_dependency_graph(analysis["files"], analysis["modules"])
    analysis["modules"] = list(analysis["modules"])

    return analysis


def _is_entry_point(content: str, filename: str) -> bool:
    """Check if a Python file is an entry point."""
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


def _is_entry_point_generic(content: str, filename: str) -> bool:
    """Check if a non-Python file is an entry point."""
    entry_names = {"main.js", "index.js", "main.ts", "index.ts", "main.go", "main.rs", "main.java"}
    return filename in entry_names


def _build_dependency_graph(files: dict, local_modules: set) -> list[dict]:
    """Build dependency relationships between files."""

    dependencies = []

    for file_path, file_info in files.items():
        for imp in file_info["imports"]:
            module = imp["from_module"] or imp["module"]
            module_base = module.split(".")[0] if module else ""

            if module_base in local_modules:
                dependencies.append({
                    "from": file_path,
                    "to": module,
                    "type": imp["type"]
                })

    return dependencies
