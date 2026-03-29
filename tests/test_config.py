"""
Tests for config.py

WHY TEST CONFIG?
Config values are used everywhere. If someone accidentally changes
CHUNK_SIZE to 0, or deletes a supported extension, everything breaks.
These tests catch that.

HOW PYTEST WORKS:
1. pytest finds all files named test_*.py
2. Inside those files, it finds all functions named test_*
3. It runs each one. If an 'assert' fails, the test fails.
4. It reports: 5 passed, 0 failed (or tells you what broke)
"""

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    IGNORE_DIRS,
    LANGUAGE_NODE_TYPES,
    LLM_MODEL,
    REPOS_DIR,
    STORAGE_DIR,
    SUPPORTED_EXTENSIONS,
    TOP_K,
    TREE_SITTER_LANGUAGES,
)

# ===== BASIC VALUE TESTS =====
# These check that config values are sensible.
# "assert X" means "I expect X to be True. If it's not, FAIL."

def test_chunk_size_is_positive():
    """Chunk size must be > 0, otherwise we'd create empty chunks."""
    assert CHUNK_SIZE > 0


def test_chunk_size_is_reasonable():
    """
    Chunk size shouldn't be too small (useless snippets)
    or too big (loses semantic meaning).
    A reasonable range is 500-5000 characters.
    """
    assert 500 <= CHUNK_SIZE <= 5000


def test_chunk_overlap_is_less_than_chunk_size():
    """
    Overlap must be smaller than chunk size.
    If overlap >= chunk size, chunks would never advance forward.
    """
    assert CHUNK_OVERLAP < CHUNK_SIZE


def test_chunk_overlap_is_non_negative():
    """Overlap can be 0 (no overlap) but never negative."""
    assert CHUNK_OVERLAP >= 0


def test_top_k_is_positive():
    """We must retrieve at least 1 result."""
    assert TOP_K > 0


def test_top_k_is_reasonable():
    """Retrieving too many chunks would flood the LLM context."""
    assert TOP_K <= 20


# ===== MODEL SETTINGS =====

def test_embedding_model_is_set():
    """We need an embedding model name, can't be empty."""
    assert EMBEDDING_MODEL
    assert isinstance(EMBEDDING_MODEL, str)


def test_llm_model_is_set():
    """We need an LLM model name, can't be empty."""
    assert LLM_MODEL
    assert isinstance(LLM_MODEL, str)


# ===== PATH SETTINGS =====

def test_repos_dir_is_set():
    assert REPOS_DIR
    assert isinstance(REPOS_DIR, str)


def test_storage_dir_is_set():
    assert STORAGE_DIR
    assert isinstance(STORAGE_DIR, str)


# ===== SUPPORTED EXTENSIONS =====

def test_supported_extensions_not_empty():
    """We must support at least one file type."""
    assert len(SUPPORTED_EXTENSIONS) > 0


def test_python_is_supported():
    """Python support is core to this project — must be there."""
    assert ".py" in SUPPORTED_EXTENSIONS


def test_extensions_start_with_dot():
    """
    Every extension should start with a dot.
    Catches mistakes like adding "py" instead of ".py"
    """
    for ext in SUPPORTED_EXTENSIONS:
        assert ext.startswith("."), f"Extension '{ext}' doesn't start with a dot"


# ===== IGNORE DIRS =====

def test_ignore_dirs_not_empty():
    assert len(IGNORE_DIRS) > 0


def test_git_is_ignored():
    """We should never index .git folders — they contain git internals, not code."""
    assert ".git" in IGNORE_DIRS


def test_node_modules_is_ignored():
    """node_modules can have 100K+ files — must be ignored."""
    assert "node_modules" in IGNORE_DIRS


def test_pycache_is_ignored():
    """__pycache__ is compiled Python bytecode, not source code."""
    assert "__pycache__" in IGNORE_DIRS


# ===== TREE-SITTER MAPPINGS =====

def test_tree_sitter_languages_not_empty():
    assert len(TREE_SITTER_LANGUAGES) > 0


def test_js_has_tree_sitter_support():
    """JavaScript is one of the most common languages — must be mapped."""
    assert ".js" in TREE_SITTER_LANGUAGES


def test_tree_sitter_extensions_start_with_dot():
    for ext in TREE_SITTER_LANGUAGES:
        assert ext.startswith("."), f"Tree-sitter extension '{ext}' doesn't start with a dot"


def test_every_tree_sitter_language_has_node_types():
    """
    Every language in TREE_SITTER_LANGUAGES should have
    corresponding node types in LANGUAGE_NODE_TYPES.
    Otherwise tree-sitter won't know what to extract.
    """
    for ext, language in TREE_SITTER_LANGUAGES.items():
        assert language in LANGUAGE_NODE_TYPES, (
            f"Language '{language}' (for {ext}) has no node types defined"
        )


def test_node_types_are_non_empty_lists():
    """Each language must have at least one node type to extract."""
    for language, node_types in LANGUAGE_NODE_TYPES.items():
        assert isinstance(node_types, list), f"{language} node_types is not a list"
        assert len(node_types) > 0, f"{language} has empty node_types"
