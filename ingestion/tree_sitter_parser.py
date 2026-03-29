"""
Tree-sitter based parser for multiple programming languages.
Extracts functions, classes, and methods as semantic chunks.
"""

import tree_sitter_c as ts_c
import tree_sitter_cpp as ts_cpp
import tree_sitter_go as ts_go
import tree_sitter_java as ts_java
import tree_sitter_javascript as ts_javascript
import tree_sitter_rust as ts_rust
import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser

from config import LANGUAGE_NODE_TYPES, TREE_SITTER_LANGUAGES

# Initialize language objects
LANGUAGES = {
    "javascript": Language(ts_javascript.language()),
    "typescript": Language(ts_typescript.language_typescript()),
    "tsx": Language(ts_typescript.language_tsx()),
    "java": Language(ts_java.language()),
    "go": Language(ts_go.language()),
    "rust": Language(ts_rust.language()),
    "c": Language(ts_c.language()),
    "cpp": Language(ts_cpp.language()),
}


def get_parser(language: str) -> Parser:
    """Get a parser for the specified language."""
    parser = Parser()

    lang_obj = LANGUAGES.get(language)
    if lang_obj is None:
        raise ValueError(f"Unsupported language: {language}")

    parser.language = lang_obj
    return parser


def extract_node_text(content: bytes, node) -> str:
    """Extract the text content of a node."""
    return content[node.start_byte:node.end_byte].decode('utf-8')


def get_node_name(node, content: bytes) -> str:
    """Extract the name of a function/class/method node."""
    # Try to find the name child node
    for child in node.children:
        if child.type == "identifier" or child.type == "property_identifier":
            return extract_node_text(content, child)
        # For Java/TypeScript type identifiers
        if child.type == "type_identifier":
            return extract_node_text(content, child)

    # For arrow functions assigned to variables, look for the variable name
    if node.type == "arrow_function":
        parent = node.parent
        if parent and parent.type == "variable_declarator":
            for child in parent.children:
                if child.type == "identifier":
                    return extract_node_text(content, child)

    # For function expressions assigned to variables
    if node.type == "function_expression":
        parent = node.parent
        if parent and parent.type == "variable_declarator":
            for child in parent.children:
                if child.type == "identifier":
                    return extract_node_text(content, child)

    return "anonymous"


def get_docstring(node, content: bytes, lines: list[str]) -> str:
    """Try to extract a docstring/comment before the node."""
    start_line = node.start_point[0]

    # Look at the line(s) before the node for comments
    docstring_lines = []
    line_idx = start_line - 1

    while line_idx >= 0:
        line = lines[line_idx].strip()
        if line.startswith("//") or line.startswith("/*") or line.startswith("*") or line.startswith("/**"):
            docstring_lines.insert(0, line)
            line_idx -= 1
        elif line == "":
            line_idx -= 1
        else:
            break

    return "\n".join(docstring_lines) if docstring_lines else ""


def node_type_to_chunk_type(node_type: str) -> str:
    """Convert tree-sitter node type to our chunk type."""
    if "function" in node_type or "method" in node_type or "constructor" in node_type:
        return "function"
    elif "class" in node_type or "interface" in node_type:
        return "class"
    elif "struct" in node_type:
        return "struct"
    elif "enum" in node_type:
        return "enum"
    elif "impl" in node_type:
        return "impl"
    elif "type" in node_type:
        return "type"
    else:
        return "code_block"


def parse_with_tree_sitter(content: str, file_path: str, language: str) -> list[dict]:
    """
    Parse a file using tree-sitter and extract semantic chunks.

    Args:
        content: The file content as a string
        file_path: The path to the file (for metadata)
        language: The language identifier (javascript, typescript, java, etc.)

    Returns:
        List of chunk dictionaries
    """
    chunks = []

    # Get the appropriate parser
    try:
        parser = get_parser(language)
    except Exception as e:
        print(f"Failed to get parser for {language}: {e}")
        return []

    # Parse the content
    content_bytes = content.encode('utf-8')
    try:
        tree = parser.parse(content_bytes)
    except Exception as e:
        print(f"Failed to parse {file_path}: {e}")
        return []

    # Get lines for docstring extraction
    lines = content.split('\n')

    # Get the node types to extract for this language
    target_node_types = LANGUAGE_NODE_TYPES.get(language, [])

    # Walk the tree and extract target nodes
    def walk_tree(node):
        if node.type in target_node_types:
            # Extract the chunk
            chunk_content = extract_node_text(content_bytes, node)
            chunk_name = get_node_name(node, content_bytes)
            chunk_type = node_type_to_chunk_type(node.type)
            docstring = get_docstring(node, content_bytes, lines)

            # Line numbers (tree-sitter uses 0-indexed)
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1

            chunks.append({
                "content": chunk_content,
                "type": chunk_type,
                "name": chunk_name,
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "docstring": docstring
            })

        # Recurse into children
        for child in node.children:
            walk_tree(child)

    walk_tree(tree.root_node)

    return chunks


def is_tree_sitter_supported(extension: str) -> bool:
    """Check if the file extension is supported by tree-sitter."""
    return extension in TREE_SITTER_LANGUAGES


def get_language_for_extension(extension: str) -> str:
    """Get the tree-sitter language identifier for a file extension."""
    return TREE_SITTER_LANGUAGES.get(extension, None)
