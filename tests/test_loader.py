"""
Tests for ingestion/loader.py

KEY CONCEPT: "tmp_path fixture"
pytest has a built-in fixture called `tmp_path` that gives you
a temporary directory. It's automatically created before each test
and cleaned up after. This lets us create fake file structures
without touching real files.

You use it by adding `tmp_path` as a parameter to your test function.
pytest magically injects it — you don't need to create it yourself.
This is called "dependency injection."

KEY CONCEPT: "Testing file I/O"
loader.py reads files from disk. We can't test it with real GitHub repos
(that would be slow and need internet). Instead, we create a fake
folder structure with tmp_path and test against that.
"""

from ingestion.loader import get_all_files, load_repo


def create_fake_repo(tmp_path):
    """
    Helper: create a fake repository structure for testing.

    tmp_path is a pathlib.Path object, so we can use / operator
    to create subdirectories (e.g., tmp_path / "src" / "main.py")
    """
    # Create a Python file
    py_file = tmp_path / "main.py"
    py_file.write_text("def hello():\n    print('hello')")

    # Create a JS file in a subdirectory
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    js_file = src_dir / "app.js"
    js_file.write_text("function greet() { return 'hi'; }")

    # Create a file we should IGNORE (not a supported extension)
    txt_file = tmp_path / "README.txt"
    txt_file.write_text("This is a readme")

    # Create a node_modules dir (should be ignored)
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    ignored_file = node_modules / "package.js"
    ignored_file.write_text("should be ignored")

    return tmp_path


# ===== get_all_files tests =====

def test_get_all_files_finds_python(tmp_path):
    """Should find .py files."""
    repo = create_fake_repo(tmp_path)
    files = get_all_files(str(repo))

    paths = [f["path"] for f in files]
    assert "main.py" in paths


def test_get_all_files_finds_javascript(tmp_path):
    """Should find .js files in subdirectories."""
    repo = create_fake_repo(tmp_path)
    files = get_all_files(str(repo))

    # The path should be relative, like "src/app.js"
    paths = [f["path"] for f in files]
    # Check that some path contains app.js
    assert any("app.js" in p for p in paths)


def test_get_all_files_ignores_unsupported_extensions(tmp_path):
    """Should NOT include .txt files."""
    repo = create_fake_repo(tmp_path)
    files = get_all_files(str(repo))

    paths = [f["path"] for f in files]
    assert not any(p.endswith(".txt") for p in paths)


def test_get_all_files_ignores_node_modules(tmp_path):
    """Should skip everything inside node_modules/."""
    repo = create_fake_repo(tmp_path)
    files = get_all_files(str(repo))

    paths = [f["path"] for f in files]
    assert not any("node_modules" in p for p in paths)


def test_get_all_files_returns_content(tmp_path):
    """Each file dict should include the actual file content."""
    repo = create_fake_repo(tmp_path)
    files = get_all_files(str(repo))

    # Find the Python file
    py_files = [f for f in files if f["path"] == "main.py"]
    assert len(py_files) == 1
    assert "def hello" in py_files[0]["content"]


def test_get_all_files_returns_required_fields(tmp_path):
    """Each file should have path, content, extension, and name."""
    repo = create_fake_repo(tmp_path)
    files = get_all_files(str(repo))

    for f in files:
        assert "path" in f
        assert "content" in f
        assert "extension" in f
        assert "name" in f


def test_get_all_files_correct_extension(tmp_path):
    """The extension field should match the actual file extension."""
    repo = create_fake_repo(tmp_path)
    files = get_all_files(str(repo))

    py_files = [f for f in files if f["name"] == "main.py"]
    assert py_files[0]["extension"] == ".py"


def test_get_all_files_skips_empty_files(tmp_path):
    """Empty files should be skipped — nothing to chunk or embed."""
    empty_file = tmp_path / "empty.py"
    empty_file.write_text("")

    # Also create a non-empty file so we get some results
    real_file = tmp_path / "real.py"
    real_file.write_text("x = 1")

    files = get_all_files(str(tmp_path))
    paths = [f["path"] for f in files]
    assert "empty.py" not in paths


def test_get_all_files_ignores_git_dir(tmp_path):
    """Should never index .git directory contents."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    git_file = git_dir / "HEAD"
    git_file.write_text("ref: refs/heads/main")

    real_file = tmp_path / "app.py"
    real_file.write_text("x = 1")

    files = get_all_files(str(tmp_path))
    paths = [f["path"] for f in files]
    assert not any(".git" in p for p in paths)


def test_get_all_files_empty_repo(tmp_path):
    """A repo with no supported files should return an empty list."""
    # Create only unsupported files
    txt = tmp_path / "readme.txt"
    txt.write_text("hello")

    files = get_all_files(str(tmp_path))
    assert files == []


# ===== load_repo tests =====

def test_load_repo_local_path(tmp_path):
    """
    load_repo should work with local paths (not just GitHub URLs).
    When given a local path, it should skip cloning and just read files.
    """
    py_file = tmp_path / "test.py"
    py_file.write_text("x = 1")

    files = load_repo(str(tmp_path))
    assert len(files) == 1
    assert files[0]["name"] == "test.py"
