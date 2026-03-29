"""
Tests for ingestion/parser.py

KEY CONCEPT: "Testing behavior, not implementation"
We don't test HOW the parser works internally.
We test WHAT it produces. Give it input, check the output.
This way, if you refactor the code later, the tests still pass
as long as the behavior stays the same.

KEY CONCEPT: "Test data as strings"
We pass Python code as strings to the parser.
No need for actual files — the parser just needs text content.
"""

from ingestion.parser import parse_file, parse_python_file, simple_chunk

# ======================================================
# SIMPLE_CHUNK TESTS
# simple_chunk breaks text into pieces by character limit
# ======================================================

def test_simple_chunk_returns_list():
    """Should always return a list, even for small input."""
    result = simple_chunk("x = 1", "test.py")
    assert isinstance(result, list)


def test_simple_chunk_small_content():
    """Content smaller than CHUNK_SIZE should produce exactly 1 chunk."""
    result = simple_chunk("x = 1", "test.py")
    assert len(result) == 1


def test_simple_chunk_has_required_fields():
    """
    Every chunk must have these fields — the rest of the pipeline
    (embedder, retriever, context_builder) depends on them.
    """
    result = simple_chunk("x = 1", "test.py")
    chunk = result[0]

    required_fields = ["content", "type", "name", "file_path", "start_line", "end_line", "docstring"]
    for field in required_fields:
        assert field in chunk, f"Chunk is missing required field: '{field}'"


def test_simple_chunk_preserves_file_path():
    """The chunk should remember which file it came from."""
    result = simple_chunk("x = 1", "src/utils.py")
    assert result[0]["file_path"] == "src/utils.py"


def test_simple_chunk_type_is_code_block():
    """Simple chunks are generic code blocks (not functions or classes)."""
    result = simple_chunk("x = 1", "test.py")
    assert result[0]["type"] == "code_block"


def test_simple_chunk_content_preserved():
    """The actual code content should be in the chunk."""
    code = "x = 1\ny = 2\nz = x + y"
    result = simple_chunk(code, "test.py")
    assert result[0]["content"] == code


def test_simple_chunk_line_numbers():
    """First chunk should start at line 1."""
    result = simple_chunk("x = 1", "test.py")
    assert result[0]["start_line"] == 1


def test_simple_chunk_splits_large_content():
    """
    Content larger than CHUNK_SIZE should be split into multiple chunks.
    We create a string that's definitely larger than 1500 chars.
    """
    # Create content with 200 lines of 20 chars each = 4000+ chars
    lines = [f"variable_{i} = {i}" for i in range(200)]
    large_content = "\n".join(lines)

    result = simple_chunk(large_content, "big_file.py")
    assert len(result) > 1, "Large content should be split into multiple chunks"


def test_simple_chunk_no_content_lost():
    """
    When splitting, all original content should be preserved.
    Nothing should be silently dropped.
    """
    lines = [f"line_{i} = {i}" for i in range(200)]
    original = "\n".join(lines)

    chunks = simple_chunk(original, "test.py")

    # Reassemble all chunk contents
    reassembled = "\n".join(chunk["content"] for chunk in chunks)
    assert reassembled == original


def test_simple_chunk_sequential_line_numbers():
    """
    Chunk line numbers should be sequential — no gaps, no overlaps.
    Chunk 1 ends at line 50, chunk 2 starts at line 51.
    """
    lines = [f"line_{i} = {i}" for i in range(200)]
    large_content = "\n".join(lines)

    chunks = simple_chunk(large_content, "test.py")

    if len(chunks) > 1:
        for i in range(len(chunks) - 1):
            current_end = chunks[i]["end_line"]
            next_start = chunks[i + 1]["start_line"]
            assert next_start == current_end + 1, (
                f"Gap between chunk {i} (ends {current_end}) and "
                f"chunk {i+1} (starts {next_start})"
            )


# ======================================================
# PARSE_PYTHON_FILE TESTS
# parse_python_file uses Python's AST to extract functions and classes
# ======================================================

def test_parse_python_extracts_function():
    """Should find a simple function definition."""
    code = '''
def greet(name):
    """Say hello."""
    return f"Hello, {name}"
'''
    result = parse_python_file(code.strip(), "greet.py")

    assert len(result) >= 1
    func_chunk = result[0]
    assert func_chunk["type"] == "function"
    assert func_chunk["name"] == "greet"


def test_parse_python_extracts_class():
    """Should find a class definition."""
    code = '''
class Dog:
    """A good boy."""
    def bark(self):
        return "Woof!"
'''
    result = parse_python_file(code.strip(), "dog.py")

    # Should find both the class AND the method inside it
    types = [chunk["type"] for chunk in result]
    names = [chunk["name"] for chunk in result]

    assert "class" in types
    assert "Dog" in names


def test_parse_python_extracts_method():
    """Methods inside classes should also be extracted."""
    code = '''
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
'''
    result = parse_python_file(code.strip(), "calc.py")
    names = [chunk["name"] for chunk in result]

    assert "add" in names
    assert "subtract" in names


def test_parse_python_extracts_async_function():
    """Async functions should be extracted too."""
    code = '''
async def fetch_data(url):
    """Fetch data from URL."""
    return await get(url)
'''
    result = parse_python_file(code.strip(), "async.py")

    assert len(result) >= 1
    assert result[0]["name"] == "fetch_data"
    assert result[0]["type"] == "function"


def test_parse_python_captures_docstring():
    """If a function has a docstring, it should be captured."""
    code = '''
def important_func():
    """This function is very important."""
    pass
'''
    result = parse_python_file(code.strip(), "test.py")

    func = result[0]
    assert "very important" in func["docstring"]


def test_parse_python_preserves_line_numbers():
    """Line numbers should match where the function actually is."""
    code = '''# Some comment
# Another comment

def my_func():
    pass
'''
    result = parse_python_file(code.strip(), "test.py")

    func = [c for c in result if c["name"] == "my_func"][0]
    assert func["start_line"] == 4  # function starts at line 4


def test_parse_python_syntax_error_falls_back():
    """
    If the Python code has a syntax error, AST parsing fails.
    The parser should gracefully fall back to simple_chunk
    instead of crashing.
    """
    bad_code = "def broken(\n    this is not valid python"
    result = parse_python_file(bad_code, "broken.py")

    # Should still return chunks (from simple_chunk fallback)
    assert len(result) > 0
    assert result[0]["type"] == "code_block"  # simple_chunk type


def test_parse_python_no_functions_falls_back():
    """
    A Python file with only top-level code (no functions/classes)
    should fall back to simple chunking.
    """
    code = '''
import os
import sys

x = 1
y = 2
print(x + y)
'''
    result = parse_python_file(code.strip(), "script.py")

    assert len(result) > 0
    # Should be code_blocks since there are no functions/classes
    assert result[0]["type"] == "code_block"


# ======================================================
# PARSE_FILE TESTS (the router function)
# parse_file decides which parser to use based on file extension
# ======================================================

def test_parse_file_routes_python():
    """'.py' files should go through the Python AST parser."""
    code = "def hello():\n    pass"
    result = parse_file(code, "hello.py", ".py")

    assert len(result) >= 1
    assert result[0]["name"] == "hello"


def test_parse_file_unknown_extension_uses_simple_chunk():
    """Unknown extensions should fall back to simple chunking."""
    result = parse_file("some code here", "file.xyz", ".xyz")

    assert len(result) > 0
    assert result[0]["type"] == "code_block"
