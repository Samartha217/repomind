"""
Tests for retrieval/context_builder.py

KEY CONCEPT: "Test fixtures"
A fixture is test data you create to test with.
Below, we create fake "chunks" that look like what ChromaDB returns.
We don't need a real database — we just need data in the right shape.

KEY CONCEPT: "Edge cases"
An edge case is an unusual input that might break things.
- What if chunks is empty?
- What if two chunks are from the same file?
- What if a chunk has no content?
Good tests cover both normal cases AND edge cases.
"""

from retrieval.context_builder import build_context, build_sources_list

# ===== HELPER: Create fake chunks =====
# This is a common pattern — a helper function that builds test data.
# Much cleaner than copy-pasting the same dict everywhere.

def make_chunk(
    content="def hello():\n    return 'world'",
    file_path="src/main.py",
    chunk_type="function",
    name="hello",
    start_line=1,
    end_line=2,
):
    """Create a fake chunk for testing."""
    return {
        "content": content,
        "file_path": file_path,
        "type": chunk_type,
        "name": name,
        "start_line": start_line,
        "end_line": end_line,
    }


# ===== build_context tests =====

def test_build_context_empty_chunks():
    """When no chunks are found, should return a helpful message."""
    result = build_context([])
    assert result == "No relevant code found."


def test_build_context_returns_string():
    """Context should always be a string."""
    chunks = [make_chunk()]
    result = build_context(chunks)
    assert isinstance(result, str)


def test_build_context_includes_file_path():
    """The context should mention where the code is from."""
    chunks = [make_chunk(file_path="utils/helper.py")]
    result = build_context(chunks)
    assert "utils/helper.py" in result


def test_build_context_includes_line_numbers():
    """Context should show line numbers so devs can find the code."""
    chunks = [make_chunk(start_line=10, end_line=20)]
    result = build_context(chunks)
    assert "10" in result
    assert "20" in result


def test_build_context_includes_code_content():
    """The actual code should appear in the context."""
    chunks = [make_chunk(content="x = 42")]
    result = build_context(chunks)
    assert "x = 42" in result


def test_build_context_includes_chunk_type():
    """Context should mention if it's a function, class, etc."""
    chunks = [make_chunk(chunk_type="class")]
    result = build_context(chunks)
    assert "class" in result


def test_build_context_multiple_chunks():
    """Multiple chunks should all appear in the context."""
    chunks = [
        make_chunk(file_path="a.py", name="func_a"),
        make_chunk(file_path="b.py", name="func_b"),
    ]
    result = build_context(chunks)
    assert "a.py" in result
    assert "b.py" in result


def test_build_context_strips_embedding_prefix():
    """
    During embedding, we add metadata as a prefix to content.
    The context builder should strip that prefix and show only code.

    The prefix format is: "metadata\n\nactual code"
    So it splits on the first double newline.
    """
    chunks = [make_chunk(content="File: main.py | Type: function\n\ndef real_code():\n    pass")]
    result = build_context(chunks)
    assert "def real_code():" in result


# ===== build_sources_list tests =====

def test_build_sources_returns_list():
    """Sources should always be a list."""
    result = build_sources_list([])
    assert isinstance(result, list)


def test_build_sources_empty_input():
    """No chunks = no sources."""
    result = build_sources_list([])
    assert result == []


def test_build_sources_extracts_file_info():
    """Each source should have file, name, type, and lines."""
    chunks = [make_chunk(file_path="app.py", name="main", chunk_type="function", start_line=1, end_line=10)]
    result = build_sources_list(chunks)

    assert len(result) == 1
    source = result[0]
    assert source["file"] == "app.py"
    assert source["name"] == "main"
    assert source["type"] == "function"
    assert source["lines"] == "1-10"


def test_build_sources_deduplicates():
    """
    If two chunks are from the same file AND same start line,
    they should appear only once in sources.
    This prevents showing "app.py:1" twice in the UI.
    """
    chunk = make_chunk(file_path="app.py", start_line=1)
    result = build_sources_list([chunk, chunk])  # same chunk twice

    assert len(result) == 1  # should be deduplicated


def test_build_sources_keeps_different_locations():
    """
    Two chunks from the SAME file but DIFFERENT lines
    should both appear (they're different code).
    """
    chunk1 = make_chunk(file_path="app.py", start_line=1, end_line=10)
    chunk2 = make_chunk(file_path="app.py", start_line=20, end_line=30)
    result = build_sources_list([chunk1, chunk2])

    assert len(result) == 2
