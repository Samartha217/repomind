"""
Code Scanner — scans source files for dangerous patterns using regex.
Catches: hardcoded secrets, SQL injection, dangerous functions, etc.
"""

import re
from pathlib import Path

# ── Pattern definitions ────────────────────────────────────────────────────────

PATTERNS = [
    {
        "id": "hardcoded_password",
        "name": "Hardcoded Password",
        "regex": re.compile(
            r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']',
            re.IGNORECASE,
        ),
        "severity": "HIGH",
        "description": "A password is hardcoded directly in the source code.",
        "fix": "Move secrets to environment variables and use os.getenv().",
    },
    {
        "id": "hardcoded_secret",
        "name": "Hardcoded Secret / API Key",
        "regex": re.compile(
            r'(?i)(secret|api_key|apikey|access_token|auth_token|private_key)\s*=\s*["\'][^"\']{8,}["\']',
            re.IGNORECASE,
        ),
        "severity": "HIGH",
        "description": "A secret key or API token is hardcoded in the source code.",
        "fix": "Store secrets in environment variables or a secrets manager.",
    },
    {
        "id": "sql_injection",
        "name": "SQL Injection Risk",
        "regex": re.compile(
            r'(?i)(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER).{0,60}(%s|\+\s*(str|request|input|params|data|query))',
            re.IGNORECASE,
        ),
        "severity": "HIGH",
        "description": "SQL query appears to be built by string concatenation — vulnerable to SQL injection.",
        "fix": "Use parameterized queries or an ORM instead of string formatting.",
    },
    {
        "id": "eval_usage",
        "name": "Dangerous eval()",
        "regex": re.compile(r'\beval\s*\('),
        "severity": "MEDIUM",
        "description": "eval() executes arbitrary code — dangerous if any input is user-controlled.",
        "fix": "Avoid eval(). Use json.loads() for JSON, ast.literal_eval() for Python literals.",
    },
    {
        "id": "exec_usage",
        "name": "Dangerous exec()",
        "regex": re.compile(r'\bexec\s*\('),
        "severity": "MEDIUM",
        "description": "exec() executes arbitrary code strings.",
        "fix": "Avoid exec() in production code. Refactor to explicit function calls.",
    },
    {
        "id": "shell_injection",
        "name": "Shell Injection Risk (shell=True)",
        "regex": re.compile(r'shell\s*=\s*True'),
        "severity": "HIGH",
        "description": "subprocess with shell=True can allow shell injection if any input is user-controlled.",
        "fix": "Use shell=False and pass arguments as a list: subprocess.run(['cmd', arg])",
    },
    {
        "id": "os_system",
        "name": "os.system() Usage",
        "regex": re.compile(r'\bos\.system\s*\('),
        "severity": "MEDIUM",
        "description": "os.system() passes commands to the shell — risky with user input.",
        "fix": "Use subprocess.run() with shell=False instead.",
    },
    {
        "id": "debug_true",
        "name": "Debug Mode Enabled",
        "regex": re.compile(r'(?i)\bdebug\s*=\s*True'),
        "severity": "MEDIUM",
        "description": "Debug mode exposes stack traces and internal info in production.",
        "fix": "Set DEBUG=False in production and read from environment variables.",
    },
    {
        "id": "hardcoded_ip",
        "name": "Hardcoded IP Address",
        "regex": re.compile(r'["\'](\d{1,3}\.){3}\d{1,3}["\']'),
        "severity": "LOW",
        "description": "A hardcoded IP address was found — may cause issues across environments.",
        "fix": "Move IP addresses to configuration files or environment variables.",
    },
]

# File types to scan
SCAN_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".php"}

# Directories to skip
SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build"}


# ── Scanner ────────────────────────────────────────────────────────────────────

def scan_code(repo_path: str) -> list[dict]:
    """
    Walk all code files in repo_path and scan for dangerous patterns.
    Returns list of findings.
    """
    findings = []
    repo = Path(repo_path)

    for file_path in repo.rglob("*"):
        if file_path.is_dir():
            continue
        if any(skip in file_path.parts for skip in SKIP_DIRS):
            continue
        if file_path.suffix not in SCAN_EXTENSIONS:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        relative_path = str(file_path.relative_to(repo))
        lines = content.splitlines()

        for pattern in PATTERNS:
            for line_num, line in enumerate(lines, start=1):
                if pattern["regex"].search(line):
                    findings.append({
                        "type": "code",
                        "rule_id": pattern["id"],
                        "name": pattern["name"],
                        "file": relative_path,
                        "line": line_num,
                        "snippet": line.strip()[:120],
                        "severity": pattern["severity"],
                        "description": pattern["description"],
                        "fix": pattern["fix"],
                    })

    return findings
