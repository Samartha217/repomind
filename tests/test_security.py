"""
Tests for the security scanner modules.
These tests run offline — no OSV.dev calls are made.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from security.code_scanner import scan_code
from security.config_scanner import scan_configs
from security.dependency_scanner import (
    _parse_package_json,
    _parse_requirements_txt,
    scan_dependencies,
)
from security.report import run_full_scan

# ── Helpers ────────────────────────────────────────────────────────────────────

def make_repo(files: dict) -> str:
    """Create a temporary directory with given files. Returns the path."""
    tmp = tempfile.mkdtemp()
    for relative_path, content in files.items():
        full_path = Path(tmp) / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
    return tmp


# ── Dependency scanner ─────────────────────────────────────────────────────────

class TestParseRequirementsTxt:
    def test_parses_pinned_versions(self):
        content = "requests==2.28.0\nflask==2.3.0\n"
        result = _parse_requirements_txt(content)
        assert {"name": "requests", "version": "2.28.0", "ecosystem": "PyPI"} in result
        assert {"name": "flask", "version": "2.3.0", "ecosystem": "PyPI"} in result

    def test_skips_unpinned(self):
        content = "requests>=2.0\nnumpy\n"
        result = _parse_requirements_txt(content)
        assert result == []

    def test_skips_comments(self):
        content = "# this is a comment\nrequests==2.28.0\n"
        result = _parse_requirements_txt(content)
        assert len(result) == 1

    def test_strips_extras(self):
        content = "requests[security]==2.28.0\n"
        result = _parse_requirements_txt(content)
        assert result[0]["name"] == "requests"

    def test_empty_file(self):
        assert _parse_requirements_txt("") == []


class TestParsePackageJson:
    def test_parses_dependencies(self):
        data = json.dumps({"dependencies": {"express": "^4.18.0"}, "devDependencies": {"jest": "~29.0.0"}})
        result = _parse_package_json(data)
        names = [p["name"] for p in result]
        assert "express" in names
        assert "jest" in names

    def test_strips_semver_prefix(self):
        data = json.dumps({"dependencies": {"lodash": "^4.17.21"}})
        result = _parse_package_json(data)
        assert result[0]["version"] == "4.17.21"

    def test_skips_wildcard_versions(self):
        data = json.dumps({"dependencies": {"foo": "*"}})
        result = _parse_package_json(data)
        assert result == []

    def test_invalid_json(self):
        assert _parse_package_json("not json") == []


class TestScanDependencies:
    def test_no_dep_files_returns_empty(self):
        repo = make_repo({"src/main.py": "print('hello')"})
        result = scan_dependencies(repo)
        assert result == []

    def test_no_pinned_versions_returns_empty(self):
        repo = make_repo({"requirements.txt": "requests>=2.0\n"})
        result = scan_dependencies(repo)
        assert result == []

    @patch("security.dependency_scanner.requests.post")
    def test_osv_hit_returns_finding(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"vulns": [{"id": "GHSA-test-1234", "summary": "Test vuln", "severity": [], "affected": []}]}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        repo = make_repo({"requirements.txt": "requests==2.20.0\n"})
        result = scan_dependencies(repo)
        assert len(result) == 1
        assert result[0]["vuln_id"] == "GHSA-test-1234"
        assert result[0]["package"] == "requests"

    @patch("security.dependency_scanner.requests.post")
    def test_osv_no_vulns_returns_empty(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"vulns": []}]}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        repo = make_repo({"requirements.txt": "requests==2.28.2\n"})
        result = scan_dependencies(repo)
        assert result == []


# ── Code scanner ───────────────────────────────────────────────────────────────

class TestScanCode:
    def test_detects_hardcoded_password(self):
        repo = make_repo({"app.py": 'password = "supersecret"\n'})
        findings = scan_code(repo)
        rule_ids = [f["rule_id"] for f in findings]
        assert "hardcoded_password" in rule_ids

    def test_detects_hardcoded_api_key(self):
        repo = make_repo({"config.py": 'api_key = "sk-abcdefghijklmnop"\n'})
        findings = scan_code(repo)
        rule_ids = [f["rule_id"] for f in findings]
        assert "hardcoded_secret" in rule_ids

    def test_detects_eval(self):
        repo = make_repo({"utils.py": "result = eval(user_input)\n"})
        findings = scan_code(repo)
        rule_ids = [f["rule_id"] for f in findings]
        assert "eval_usage" in rule_ids

    def test_detects_shell_true(self):
        repo = make_repo({"run.py": "subprocess.run(cmd, shell=True)\n"})
        findings = scan_code(repo)
        rule_ids = [f["rule_id"] for f in findings]
        assert "shell_injection" in rule_ids

    def test_detects_os_system(self):
        repo = make_repo({"run.py": "os.system('rm -rf /')\n"})
        findings = scan_code(repo)
        rule_ids = [f["rule_id"] for f in findings]
        assert "os_system" in rule_ids

    def test_clean_file_returns_no_findings(self):
        repo = make_repo({"clean.py": "def add(a, b):\n    return a + b\n"})
        findings = scan_code(repo)
        assert findings == []

    def test_skips_node_modules(self):
        repo = make_repo({"node_modules/pkg/index.js": 'eval("bad")\n'})
        findings = scan_code(repo)
        assert findings == []

    def test_finding_has_correct_fields(self):
        repo = make_repo({"app.py": 'password = "hunter2"\n'})
        findings = scan_code(repo)
        assert len(findings) >= 1
        f = findings[0]
        assert "file" in f
        assert "line" in f
        assert "severity" in f
        assert "fix" in f
        assert "snippet" in f


# ── Config scanner ─────────────────────────────────────────────────────────────

class TestScanConfigs:
    def test_detects_db_url_in_env(self):
        repo = make_repo({".env": "DATABASE_URL=postgres://user:password@localhost/db\n"})
        findings = scan_configs(repo)
        rule_ids = [f["rule_id"] for f in findings]
        assert "db_url_credentials" in rule_ids

    def test_ignores_placeholder_in_env_example(self):
        repo = make_repo({".env.example": "SECRET_KEY=your_secret_key_here\n"})
        findings = scan_configs(repo)
        # Placeholder values should not trigger real_secret_in_env
        real_secret_findings = [f for f in findings if f["rule_id"] == "real_secret_in_env"]
        assert real_secret_findings == []

    def test_detects_exposed_db_port_in_docker_compose(self):
        content = "services:\n  db:\n    ports:\n      - 5432:5432\n"
        repo = make_repo({"docker-compose.yml": content})
        findings = scan_configs(repo)
        rule_ids = [f["rule_id"] for f in findings]
        assert "exposed_sensitive_port" in rule_ids

    def test_non_sensitive_port_not_flagged(self):
        content = "services:\n  web:\n    ports:\n      - 8080:8080\n"
        repo = make_repo({"docker-compose.yml": content})
        findings = scan_configs(repo)
        assert findings == []

    def test_no_config_files_returns_empty(self):
        repo = make_repo({"src/main.py": "print('hello')"})
        findings = scan_configs(repo)
        assert findings == []


# ── Report ─────────────────────────────────────────────────────────────────────

class TestRunFullScan:
    def test_returns_correct_structure(self):
        repo = make_repo({"clean.py": "x = 1\n"})
        with patch("security.report.scan_dependencies", return_value=[]):
            report = run_full_scan(repo)
        assert "findings" in report
        assert "summary" in report
        assert "scanned" in report
        assert "errors" in report

    def test_summary_counts_match_findings(self):
        repo = make_repo({"app.py": 'password = "secret"\napi_key = "sk-longvalue"\n'})
        with patch("security.report.scan_dependencies", return_value=[]):
            report = run_full_scan(repo)
        total = report["summary"]["total"]
        assert total == len(report["findings"])

    def test_findings_sorted_by_severity(self):
        mock_findings = [
            {"severity": "LOW", "type": "code"},
            {"severity": "CRITICAL", "type": "code"},
            {"severity": "HIGH", "type": "code"},
        ]
        with patch("security.report.scan_dependencies", return_value=[]):
            with patch("security.report.scan_code", return_value=mock_findings):
                with patch("security.report.scan_configs", return_value=[]):
                    repo = make_repo({})
                    report = run_full_scan(repo)
        severities = [f["severity"] for f in report["findings"]]
        assert severities == ["CRITICAL", "HIGH", "LOW"]

    def test_dep_scan_error_captured_not_raised(self):
        repo = make_repo({"requirements.txt": "requests==2.20.0\n"})
        with patch("security.report.scan_dependencies", side_effect=RuntimeError("OSV.dev offline")):
            report = run_full_scan(repo)
        assert any("Dependency scan failed" in e for e in report["errors"])
        assert report["scanned"]["dependencies"] is False
