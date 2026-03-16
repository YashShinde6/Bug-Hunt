"""Bug Detection Agent — combines parser + static analysis to detect bugs."""
import re


def detect_bugs(code: str, parsed: dict, static_findings: list[dict], language: str) -> list[dict]:
    """Detect bugs by combining parser output and static analysis results."""
    bugs = []

    # 1. Bugs from static analysis
    for finding in static_findings:
        if finding.get("severity") in ("high", "critical"):
            bugs.append({
                "bug_type": _classify_bug(finding.get("issue", ""), finding.get("symbol", "")),
                "line_number": finding.get("line", 0),
                "explanation": finding.get("issue", "Unknown issue"),
                "impact": _assess_impact(finding.get("severity", "medium")),
                "source": finding.get("tool", "static_analysis"),
                "severity": finding.get("severity", "medium"),
                "suggested_fix": "",
            })

    # 2. Bugs from parser risks
    for risk in parsed.get("risks", []):
        risk_type = risk.get("type", "")
        bugs.append({
            "bug_type": _risk_to_bug_type(risk_type),
            "line_number": risk.get("line", 0),
            "explanation": risk.get("message", ""),
            "impact": _risk_impact(risk_type),
            "source": "parser",
            "severity": _risk_severity(risk_type),
            "suggested_fix": _risk_fix(risk_type, risk),
        })

    # 3. Pattern-based detection on the code itself
    if language == "python":
        bugs.extend(_detect_python_patterns(code, parsed))
    elif language in ("javascript", "typescript"):
        bugs.extend(_detect_js_patterns(code, parsed))

    # Deduplicate by line number + bug type
    seen = set()
    unique_bugs = []
    for bug in bugs:
        key = (bug["line_number"], bug["bug_type"])
        if key not in seen:
            seen.add(key)
            unique_bugs.append(bug)

    return unique_bugs


def _detect_python_patterns(code: str, parsed: dict) -> list[dict]:
    """Detect common Python patterns that lead to bugs."""
    bugs = []
    lines = code.splitlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Mutable default arguments
        if re.search(r'def\s+\w+\(.*=\s*(\[\]|\{\}|\(\))', stripped):
            bugs.append({
                "bug_type": "Mutable Default Argument",
                "line_number": i,
                "explanation": "Using mutable default argument (list/dict/tuple). This is shared across all calls.",
                "impact": "Unexpected behavior — mutations persist between function calls",
                "source": "pattern_detector",
                "severity": "high",
                "suggested_fix": "Use None as default and initialize inside the function body",
            })

        # Unused variable (simple check: assigned but never used later)
        # Already covered by pylint, so skip

        # Index access without length check
        if re.search(r'\w+\[\d+\]', stripped) and not re.search(r'(if|while|for|len)', stripped):
            if re.search(r'\w+\[-?\d{2,}\]', stripped):  # Only flag large index access
                bugs.append({
                    "bug_type": "Index Out of Range",
                    "line_number": i,
                    "explanation": "Hard-coded index access may cause IndexError",
                    "impact": "Runtime crash if index exceeds collection size",
                    "source": "pattern_detector",
                    "severity": "medium",
                    "suggested_fix": "Add bounds checking or use try/except",
                })

        # String formatting with .format or % without matching args
        if re.search(r'except\s*:', stripped) and not re.search(r'except\s+\w', stripped):
            bugs.append({
                "bug_type": "Bare Except",
                "line_number": i,
                "explanation": "Bare except clause catches all exceptions including SystemExit and KeyboardInterrupt",
                "impact": "May hide critical errors and make debugging difficult",
                "source": "pattern_detector",
                "severity": "medium",
                "suggested_fix": "Catch specific exceptions: except (ValueError, TypeError) as e:",
            })

        # Hardcoded passwords/keys
        if re.search(r'(password|secret|api_key|token)\s*=\s*["\'][^"\']+["\']', stripped, re.IGNORECASE):
            bugs.append({
                "bug_type": "Hardcoded Secret",
                "line_number": i,
                "explanation": "Sensitive value appears to be hardcoded",
                "impact": "Security vulnerability — credentials may be exposed in source control",
                "source": "pattern_detector",
                "severity": "critical",
                "suggested_fix": "Use environment variables or a secrets manager",
            })

        # Global variable mutation
        if stripped.startswith("global "):
            bugs.append({
                "bug_type": "Global Variable Usage",
                "line_number": i,
                "explanation": "Global keyword used — modifies global state",
                "impact": "Makes code harder to test and reason about",
                "source": "pattern_detector",
                "severity": "low",
                "suggested_fix": "Consider passing values as function parameters instead",
            })

    return bugs


def _detect_js_patterns(code: str, parsed: dict) -> list[dict]:
    """Detect common JavaScript patterns that lead to bugs."""
    bugs = []
    lines = code.splitlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments
        if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
            continue

        # == instead of ===
        if re.search(r'[^=!]==[^=]', stripped) and '===' not in stripped:
            bugs.append({
                "bug_type": "Loose Equality",
                "line_number": i,
                "explanation": "Using == instead of === may cause unexpected type coercion",
                "impact": "Logical error due to type coercion",
                "source": "pattern_detector",
                "severity": "medium",
                "suggested_fix": "Use strict equality === instead of ==",
            })

        # eval usage
        if "eval(" in stripped:
            bugs.append({
                "bug_type": "Security Vulnerability",
                "line_number": i,
                "explanation": "eval() executes arbitrary code — major security risk",
                "impact": "Code injection vulnerability",
                "source": "pattern_detector",
                "severity": "critical",
                "suggested_fix": "Use JSON.parse() for data or a safe alternative",
            })

        # Hardcoded secrets
        if re.search(r'(password|secret|api_key|token)\s*[:=]\s*["\'][^"\']+["\']', stripped, re.IGNORECASE):
            bugs.append({
                "bug_type": "Hardcoded Secret",
                "line_number": i,
                "explanation": "Sensitive value appears to be hardcoded",
                "impact": "Security vulnerability — credentials exposed in source code",
                "source": "pattern_detector",
                "severity": "critical",
                "suggested_fix": "Use environment variables or a secrets manager",
            })

    return bugs


def _classify_bug(issue: str, symbol: str) -> str:
    """Classify bug type from static analysis finding."""
    issue_lower = issue.lower()
    if "undefined" in issue_lower or "not defined" in issue_lower:
        return "Undefined Variable"
    if "import" in issue_lower:
        return "Import Error"
    if "syntax" in issue_lower:
        return "Syntax Error"
    if "type" in issue_lower:
        return "Type Error"
    if "unused" in issue_lower:
        return "Unused Code"
    if "not callable" in issue_lower:
        return "Not Callable"
    return "Code Issue"


def _assess_impact(severity: str) -> str:
    impacts = {
        "critical": "Application crash or security vulnerability",
        "high": "Runtime error likely",
        "medium": "Potential unexpected behavior",
        "low": "Code quality issue",
        "info": "Informational",
    }
    return impacts.get(severity, "Unknown impact")


def _risk_to_bug_type(risk_type: str) -> str:
    mapping = {
        "division": "Division by Zero",
        "bare_except": "Bare Except",
        "syntax_error": "Syntax Error",
        "security": "Security Vulnerability",
        "off_by_one": "Off-by-One Error",
        "undefined_variable": "Undefined Variable",
        "null_reference": "Null Reference",
        "out_of_bounds": "Index Out of Bounds",
        "null_argument": "Null Argument Passed",
        "negative_sqrt": "Negative Square Root",
        "zero_argument": "Zero Division Argument",
    }
    return mapping.get(risk_type, "Runtime Risk")


def _risk_severity(risk_type: str) -> str:
    mapping = {
        "division": "high",
        "bare_except": "medium",
        "syntax_error": "critical",
        "security": "critical",
        "off_by_one": "high",
        "undefined_variable": "high",
        "null_reference": "high",
        "out_of_bounds": "high",
        "null_argument": "high",
        "negative_sqrt": "high",
        "zero_argument": "high",
    }
    return mapping.get(risk_type, "medium")


def _risk_impact(risk_type: str) -> str:
    mapping = {
        "division": "Application crash if denominator is zero",
        "bare_except": "May hide critical errors",
        "syntax_error": "Code will not execute",
        "security": "Potential code injection",
        "off_by_one": "Accessing undefined array element causes NaN or errors that propagate silently",
        "undefined_variable": "ReferenceError at runtime — application crash",
        "null_reference": "TypeError at runtime — cannot read properties of null/undefined",
        "out_of_bounds": "IndexError at runtime — accessing element beyond list/array bounds",
        "null_argument": "TypeError when function tries to access properties of null parameter",
        "negative_sqrt": "ValueError at runtime — math.sqrt() cannot handle negative numbers",
        "zero_argument": "ZeroDivisionError — passing 0 as a divisor argument causes crash",
    }
    return mapping.get(risk_type, "Potential runtime issue")


def _risk_fix(risk_type: str, risk: dict = None) -> str:
    if risk_type == "off_by_one":
        arr = risk.get("array", "array") if risk else "array"
        var = risk.get("variable", "i") if risk else "i"
        return f"Change '{var} <= {arr}.length' to '{var} < {arr}.length' — arrays are zero-indexed so valid indices are 0 to length-1"
    if risk_type == "undefined_variable":
        var = risk.get("variable", "variable") if risk else "variable"
        return f"Declare '{var}' with let/const before using it, or check for a typo in the variable name"
    if risk_type == "null_reference":
        var = risk.get("variable", "obj") if risk else "obj"
        return f"Add a null check: if ({var} != null) before accessing properties, or use optional chaining: {var}?.property"
    if risk_type == "out_of_bounds":
        var = risk.get("variable", "list") if risk else "list"
        return f"Add a bounds check: if i + 1 < len({var}) before accessing {var}[i + 1]"
    if risk_type == "null_argument":
        fn = risk.get("function", "function") if risk else "function"
        return f"Add null/undefined check inside '{fn}()' before accessing parameter properties"
    if risk_type == "negative_sqrt":
        return "Add a guard: if x >= 0 before calling math.sqrt(x), or use cmath.sqrt() for complex number support"
    if risk_type == "zero_argument":
        fn = risk.get("function", "function") if risk else "function"
        param = risk.get("param", "param") if risk else "param"
        return f"Don't pass 0 to '{fn}()' — add validation: if {param} != 0 before calling, or handle ZeroDivisionError inside the function"

    mapping = {
        "division": "Add validation: if denominator != 0 before division",
        "bare_except": "Catch specific exceptions instead of using bare except",
        "syntax_error": "Fix the syntax error at the indicated line",
        "security": "Avoid using eval() or similar unsafe functions",
    }
    return mapping.get(risk_type, "Review and fix the detected issue")
