"""
Dependency Scanner — checks requirements.txt / package.json against OSV.dev
OSV.dev is Google's free, open vulnerability database.
API docs: https://google.github.io/osv.dev/api/
"""

import json
import re
from pathlib import Path

import requests

OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"


# ── Parsers ────────────────────────────────────────────────────────────────────

def _parse_requirements_txt(content: str) -> list[dict]:
    """Parse requirements.txt into list of {name, version} dicts."""
    packages = []
    for line in content.splitlines():
        line = line.strip()
        # Skip comments and blank lines
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Strip extras like requests[security]==2.28.0
        line = re.sub(r"\[.*?\]", "", line)
        # Match name==version (exact pin only — OSV needs exact version)
        match = re.match(r"^([\w.-]+)==([\w.*+!-]+)", line)
        if match:
            packages.append({"name": match.group(1), "version": match.group(2), "ecosystem": "PyPI"})
    return packages


def _parse_package_json(content: str) -> list[dict]:
    """Parse package.json dependencies into list of {name, version} dicts."""
    packages = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return packages

    for section in ("dependencies", "devDependencies"):
        for name, version in data.get(section, {}).items():
            # Strip semver prefixes: ^1.0.0, ~1.0.0, >=1.0.0 → 1.0.0
            clean_version = re.sub(r"^[\^~>=<]+", "", version).strip()
            if clean_version and not clean_version.startswith("*"):
                packages.append({"name": name, "version": clean_version, "ecosystem": "npm"})
    return packages


def _find_dependency_files(repo_path: str) -> list[dict]:
    """Walk the repo and collect all parseable dependency files."""
    found = []
    repo = Path(repo_path)
    ignore = {"node_modules", ".git", "venv", ".venv", "__pycache__"}

    for path in repo.rglob("*"):
        if any(p in path.parts for p in ignore):
            continue
        if path.name == "requirements.txt":
            try:
                found.append({"file": str(path.relative_to(repo)), "type": "pip", "content": path.read_text(encoding="utf-8")})
            except (UnicodeDecodeError, PermissionError):
                pass
        elif path.name == "package.json":
            try:
                found.append({"file": str(path.relative_to(repo)), "type": "npm", "content": path.read_text(encoding="utf-8")})
            except (UnicodeDecodeError, PermissionError):
                pass
    return found


# ── OSV.dev API ────────────────────────────────────────────────────────────────

def _query_osv(packages: list[dict]) -> list[dict]:
    """
    Send a batch query to OSV.dev.
    Returns list of vulnerabilities, one entry per vulnerable package.
    """
    if not packages:
        return []

    queries = [
        {"version": pkg["version"], "package": {"name": pkg["name"], "ecosystem": pkg["ecosystem"]}}
        for pkg in packages
    ]

    try:
        response = requests.post(OSV_BATCH_URL, json={"queries": queries}, timeout=15)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError("OSV.dev API timed out. Try again in a moment.")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Could not reach OSV.dev. Check your internet connection.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"OSV.dev API error: {e}")

    results = response.json().get("results", [])
    findings = []

    for pkg, result in zip(packages, results):
        vulns = result.get("vulns", [])
        for vuln in vulns:
            # Extract CVSS score if available
            severity = _extract_severity(vuln)
            findings.append({
                "type": "dependency",
                "package": pkg["name"],
                "version": pkg["version"],
                "ecosystem": pkg["ecosystem"],
                "vuln_id": vuln.get("id", "UNKNOWN"),
                "summary": vuln.get("summary", "No description available."),
                "severity": severity,
                "fix": _extract_fix(vuln, pkg["name"]),
            })

    return findings


def _extract_severity(vuln: dict) -> str:
    """Pull CVSS score from OSV vuln object and convert to severity label."""
    for severity_entry in vuln.get("severity", []):
        score_str = severity_entry.get("score", "")
        # CVSS v3 vector string — extract base score
        match = re.search(r"(\d+\.\d+)$", score_str)
        if match:
            score = float(match.group(1))
            if score >= 9.0:
                return "CRITICAL"
            elif score >= 7.0:
                return "HIGH"
            elif score >= 4.0:
                return "MEDIUM"
            else:
                return "LOW"
    # No CVSS score available — default to MEDIUM
    return "MEDIUM"


def _extract_fix(vuln: dict, package_name: str) -> str:
    """Extract the fixed version from OSV affected ranges."""
    for affected in vuln.get("affected", []):
        if affected.get("package", {}).get("name", "").lower() != package_name.lower():
            continue
        for version_range in affected.get("ranges", []):
            for event in version_range.get("events", []):
                if "fixed" in event:
                    return f"Upgrade to {event['fixed']} or later"
    return "Check the advisory for fix details"


# ── Public API ─────────────────────────────────────────────────────────────────

def scan_dependencies(repo_path: str) -> list[dict]:
    """
    Main entry point. Scans all dependency files in repo_path.
    Returns list of vulnerability findings.
    """
    dep_files = _find_dependency_files(repo_path)
    if not dep_files:
        return []

    all_packages = []
    for dep_file in dep_files:
        if dep_file["type"] == "pip":
            all_packages.extend(_parse_requirements_txt(dep_file["content"]))
        elif dep_file["type"] == "npm":
            all_packages.extend(_parse_package_json(dep_file["content"]))

    if not all_packages:
        return []

    findings = _query_osv(all_packages)
    return findings
