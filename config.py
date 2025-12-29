import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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