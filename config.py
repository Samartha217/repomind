import os

from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print(
        "WARNING: OPENAI_API_KEY is not set. "
        "Copy .env.example to .env and add your key."
    )

# Model settings
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"

# Paths
REPOS_DIR = "repos"
STORAGE_DIR = "storage"

# Chunking settings
CHUNK_SIZE = 1500  # max characters per chunk
CHUNK_OVERLAP = 200

# Retrieval settings
TOP_K = 6  # number of chunks to retrieve

# Supported file extensions
SUPPORTED_EXTENSIONS = [
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".go", ".rs", ".cpp", ".c",
    ".rb", ".php", ".swift", ".kt"
]

# Directories to ignore
IGNORE_DIRS = [
    "node_modules", ".git", "__pycache__",
    "venv", ".venv", "dist", "build",
    ".next", ".nuxt", "vendor"
]

# Tree-sitter language mappings (extension -> language identifier)
TREE_SITTER_LANGUAGES = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c",
    ".hpp": "cpp",
}

# Node types to extract for each language
LANGUAGE_NODE_TYPES = {
    "javascript": ["function_declaration", "function_expression", "arrow_function", "class_declaration", "method_definition"],
    "typescript": ["function_declaration", "function_expression", "arrow_function", "class_declaration", "method_definition"],
    "tsx": ["function_declaration", "function_expression", "arrow_function", "class_declaration", "method_definition"],
    "java": ["method_declaration", "class_declaration", "interface_declaration", "constructor_declaration"],
    "go": ["function_declaration", "method_declaration", "type_declaration"],
    "rust": ["function_item", "impl_item", "struct_item", "enum_item"],
    "c": ["function_definition", "struct_specifier"],
    "cpp": ["function_definition", "class_specifier", "struct_specifier"],
}
