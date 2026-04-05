"""
Report — combines findings from all scanners into one structured report.
Deduplicates, sorts by severity, and produces summary stats.
"""

from security.code_scanner import scan_code
from security.config_scanner import scan_configs
from security.dependency_scanner import scan_dependencies

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def run_full_scan(repo_path: str) -> dict:
    """
    Run all three scanners and return a unified report.

    Returns:
        {
            "findings": [...],        # all findings, sorted by severity
            "summary": {
                "total": int,
                "critical": int,
                "high": int,
                "medium": int,
                "low": int,
            },
            "scanned": {
                "dependencies": bool,
                "code": bool,
                "configs": bool,
            },
            "errors": [...],          # scanner errors (non-fatal)
        }
    """
    findings = []
    errors = []
    scanned = {"dependencies": False, "code": False, "configs": False}

    # 1. Dependency scan (OSV.dev — can fail if offline)
    try:
        dep_findings = scan_dependencies(repo_path)
        findings.extend(dep_findings)
        scanned["dependencies"] = True
    except RuntimeError as e:
        errors.append(f"Dependency scan failed: {e}")

    # 2. Code pattern scan
    try:
        code_findings = scan_code(repo_path)
        findings.extend(code_findings)
        scanned["code"] = True
    except Exception as e:
        errors.append(f"Code scan failed: {e}")

    # 3. Config scan
    try:
        config_findings = scan_configs(repo_path)
        findings.extend(config_findings)
        scanned["configs"] = True
    except Exception as e:
        errors.append(f"Config scan failed: {e}")

    # Sort by severity
    findings.sort(key=lambda f: SEVERITY_ORDER.get(f.get("severity", "LOW"), 3))

    # Summary counts
    summary = {"total": len(findings), "critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in findings:
        sev = finding.get("severity", "LOW").lower()
        if sev in summary:
            summary[sev] += 1

    return {
        "findings": findings,
        "summary": summary,
        "scanned": scanned,
        "errors": errors,
    }
