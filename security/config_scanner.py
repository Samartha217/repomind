"""
Config Scanner — checks config and environment files for exposed secrets,
dangerous settings, and misconfigurations.
"""

import re
from pathlib import Path

# Config files to look for
CONFIG_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.staging",
    ".env.example", ".env.sample", "config.yml", "config.yaml",
    "docker-compose.yml", "docker-compose.yaml", "settings.py",
    "application.properties", "application.yml",
}

SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__"}

# ── Patterns for config files ─────────────────────────────────────────────────

# Looks like a real secret (not a placeholder like "your_key_here" or "xxxx")
REAL_SECRET_PATTERN = re.compile(
    r'^(SECRET|API_KEY|PASSWORD|TOKEN|PRIVATE_KEY|DATABASE_URL|DB_PASSWORD)\s*=\s*(?!.*\b(your|example|placeholder|xxx+|change|replace|here|todo|dummy|test|sample|default)\b).{8,}',
    re.IGNORECASE | re.MULTILINE,
)

# Exposed database URLs with credentials embedded
DB_URL_PATTERN = re.compile(
    r'(postgres|mysql|mongodb|redis):\/\/\w+:\w+@',
    re.IGNORECASE,
)

# docker-compose port bindings that expose services publicly
EXPOSED_PORT_PATTERN = re.compile(
    r'^\s*-\s*["\']?(\d+):(\d+)["\']?',
    re.MULTILINE,
)

# Dangerous well-known ports if exposed
SENSITIVE_PORTS = {
    "5432": "PostgreSQL database",
    "3306": "MySQL database",
    "27017": "MongoDB database",
    "6379": "Redis",
    "9200": "Elasticsearch",
    "2181": "Zookeeper",
}


def _scan_env_file(content: str, file_path: str) -> list[dict]:
    """Check .env files for real (non-placeholder) secrets."""
    findings = []

    # Real .env files (not .example) with actual values
    is_example = "example" in file_path.lower() or "sample" in file_path.lower()

    for line_num, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Check for embedded DB URL credentials
        if DB_URL_PATTERN.search(line):
            findings.append({
                "type": "config",
                "rule_id": "db_url_credentials",
                "name": "Database URL with Embedded Credentials",
                "file": file_path,
                "line": line_num,
                "snippet": _mask_secret(line),
                "severity": "CRITICAL",
                "description": "Database connection string with username and password found in config file.",
                "fix": "Use separate DB_USER and DB_PASSWORD env vars, or a secrets manager.",
            })

        # Only flag real values in actual .env files (not .env.example)
        if not is_example and REAL_SECRET_PATTERN.match(line):
            findings.append({
                "type": "config",
                "rule_id": "real_secret_in_env",
                "name": "Real Secret in Environment File",
                "file": file_path,
                "line": line_num,
                "snippet": _mask_secret(line),
                "severity": "HIGH",
                "description": "A real secret value is present in an environment file committed to the repo.",
                "fix": "Add .env to .gitignore. Never commit real secrets — only commit .env.example.",
            })

    return findings


def _scan_docker_compose(content: str, file_path: str) -> list[dict]:
    """Check docker-compose for ports that expose sensitive services publicly."""
    findings = []

    for match in EXPOSED_PORT_PATTERN.finditer(content):
        host_port = match.group(1)
        container_port = match.group(2)

        if container_port in SENSITIVE_PORTS:
            service = SENSITIVE_PORTS[container_port]
            line_num = content[: match.start()].count("\n") + 1
            findings.append({
                "type": "config",
                "rule_id": "exposed_sensitive_port",
                "name": f"Sensitive Port Exposed ({service})",
                "file": file_path,
                "line": line_num,
                "snippet": match.group(0).strip(),
                "severity": "MEDIUM",
                "description": f"{service} port {container_port} is bound to host port {host_port} — accessible from outside the container.",
                "fix": f"Bind to localhost only: '127.0.0.1:{host_port}:{container_port}' or remove the port mapping.",
            })

    return findings


def _mask_secret(line: str) -> str:
    """Replace secret values with asterisks for safe display."""
    if "=" in line:
        key, _, value = line.partition("=")
        if len(value) > 4:
            return f"{key}=****{value[-2:]}"
    return line[:20] + "..."


# ── Public API ─────────────────────────────────────────────────────────────────

def scan_configs(repo_path: str) -> list[dict]:
    """
    Scan config and environment files in repo_path for misconfigurations.
    Returns list of findings.
    """
    findings = []
    repo = Path(repo_path)

    for file_path in repo.rglob("*"):
        if file_path.is_dir():
            continue
        if any(skip in file_path.parts for skip in SKIP_DIRS):
            continue
        if file_path.name not in CONFIG_FILENAMES:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        relative_path = str(file_path.relative_to(repo))

        if file_path.name.startswith(".env"):
            findings.extend(_scan_env_file(content, relative_path))
        elif "docker-compose" in file_path.name:
            findings.extend(_scan_docker_compose(content, relative_path))

    return findings
