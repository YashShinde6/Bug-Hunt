"""Static Analysis Agent — pylint/eslint integration."""
import json
import subprocess
import shutil
from pathlib import Path


def run_static_analysis(file_path: str, language: str) -> list[dict]:
    """Run appropriate static analyzer and return structured findings."""
    if language == "python":
        return _run_pylint(file_path)
    elif language in ("javascript", "typescript"):
        return _run_eslint(file_path)
    return []


def _run_pylint(file_path: str) -> list[dict]:
    """Run pylint on a Python file."""
    if not shutil.which("pylint"):
        return [{"line": 0, "issue": "pylint not installed — skipping static analysis", "severity": "info", "tool": "pylint"}]

    try:
        result = subprocess.run(
            ["pylint", "--output-format=json", "--disable=C,R", file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        findings = []
        if result.stdout.strip():
            try:
                pylint_output = json.loads(result.stdout)
                for item in pylint_output:
                    severity = _map_pylint_severity(item.get("type", ""))
                    findings.append({
                        "line": item.get("line", 0),
                        "column": item.get("column", 0),
                        "issue": item.get("message", ""),
                        "code": item.get("message-id", ""),
                        "severity": severity,
                        "tool": "pylint",
                        "symbol": item.get("symbol", ""),
                    })
            except json.JSONDecodeError:
                pass

        return findings

    except subprocess.TimeoutExpired:
        return [{"line": 0, "issue": "pylint timed out", "severity": "warning", "tool": "pylint"}]
    except Exception as e:
        return [{"line": 0, "issue": f"pylint error: {str(e)}", "severity": "error", "tool": "pylint"}]


def _run_eslint(file_path: str) -> list[dict]:
    """Run eslint on a JavaScript/TypeScript file."""
    eslint_cmd = shutil.which("eslint")
    if not eslint_cmd:
        return [{"line": 0, "issue": "eslint not installed — skipping static analysis", "severity": "info", "tool": "eslint"}]

    try:
        result = subprocess.run(
            [eslint_cmd, "--format=json", "--no-eslintrc", file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        findings = []
        if result.stdout.strip():
            try:
                eslint_output = json.loads(result.stdout)
                for file_result in eslint_output:
                    for msg in file_result.get("messages", []):
                        severity = "high" if msg.get("severity", 1) == 2 else "medium"
                        findings.append({
                            "line": msg.get("line", 0),
                            "column": msg.get("column", 0),
                            "issue": msg.get("message", ""),
                            "code": msg.get("ruleId", ""),
                            "severity": severity,
                            "tool": "eslint",
                        })
            except json.JSONDecodeError:
                pass

        return findings

    except subprocess.TimeoutExpired:
        return [{"line": 0, "issue": "eslint timed out", "severity": "warning", "tool": "eslint"}]
    except Exception as e:
        return [{"line": 0, "issue": f"eslint error: {str(e)}", "severity": "error", "tool": "eslint"}]


def _map_pylint_severity(pylint_type: str) -> str:
    mapping = {
        "error": "high",
        "fatal": "critical",
        "warning": "medium",
        "convention": "low",
        "refactor": "low",
        "information": "info",
    }
    return mapping.get(pylint_type, "medium")
