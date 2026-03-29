import os
import shutil
from pathlib import Path

from git import Repo

from config import IGNORE_DIRS, REPOS_DIR, SUPPORTED_EXTENSIONS


def clone_repo(github_url: str) -> str:
    """Clone a GitHub repo and return the local path."""

    # Extract repo name from URL
    repo_name = github_url.rstrip("/").split("/")[-1].replace(".git", "")
    local_path = os.path.join(REPOS_DIR, repo_name)

    # Remove if already exists
    if os.path.exists(local_path):
        shutil.rmtree(local_path)

    # Clone
    print(f"Cloning {github_url}...")
    Repo.clone_from(github_url, local_path)
    print(f"Cloned to {local_path}")

    return local_path


def get_all_files(repo_path: str) -> list[dict]:
    """Walk repo and return all supported code files."""

    files = []
    repo_path = Path(repo_path)

    for file_path in repo_path.rglob("*"):
        # Skip directories
        if file_path.is_dir():
            continue

        # Skip ignored directories
        if any(ignored in file_path.parts for ignored in IGNORE_DIRS):
            continue

        # Check extension
        if file_path.suffix not in SUPPORTED_EXTENSIONS:
            continue

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        # Skip empty files
        if not content.strip():
            continue

        files.append({
            "path": str(file_path.relative_to(repo_path)),
            "content": content,
            "extension": file_path.suffix,
            "name": file_path.name
        })

    print(f"Found {len(files)} code files")
    return files


def load_repo(source: str) -> list[dict]:
    """Main function: load from GitHub URL or local path."""

    if source.startswith("http"):
        repo_path = clone_repo(source)
    else:
        repo_path = source

    return get_all_files(repo_path)
