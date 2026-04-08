import os

from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print(
        "WARNING: GOOGLE_API_KEY is not set. "
        "Copy .env.example to .env and add your Google API key. "
        "Get one free at https://aistudio.google.com/apikey"
    )

# Model settings
EMBEDDING_MODEL = "nomic-embed-text"   # runs locally via Ollama — free, no API key
LLM_MODEL = "gemini-2.5-flash"         # runs via Google Gemini — free tier, 250 req/day

# Paths
REPOS_DIR = "repos"
STORAGE_DIR = "storage"

# Chunking settings
CHUNK_SIZE = 1500  # max characters per chunk
CHUNK_OVERLAP = 200

# Retrieval settings
TOP_K = 10  # number of chunks to retrieve per query

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
