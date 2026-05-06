"""Agent Orchestrator — coordinates the full multi-agent bug detection pipeline."""
import os
from pathlib import Path
from typing import Optional

from config import settings
from agents.parser_agent import parse_code
from agents.static_analysis_agent import run_static_analysis
from agents.bug_detector_agent import detect_bugs
from agents.ensemble_agent import validate_with_ensemble
from agents.rag_agent import retrieve_similar_bugs, store_bugs
from tools.ocr_tool import extract_code_from_image
from tools.csv_analyzer import analyze_csv


async def run_pipeline(
    file_path: str,
    file_content: Optional[str] = None,
    language: str = "python",
) -> dict:
    """Execute the full agent pipeline.

    Pipeline stages:
    1. Detect input type (code / CSV / image)
    2. If image → OCR → extract code
    3. If CSV → CSV Analyzer
    4. Parse code → structured representation
    5. Run static analysis
    6. Bug detection (combine results)
    7. LLM ensemble validation
    8. RAG retrieval for similar bugs
    9. Return final bug report
    """
    ext = Path(file_path).suffix.lower()
    pipeline_log = []

    # ── Stage 1: Input type detection ──
    if ext in settings.IMAGE_EXTENSIONS:
        return await _handle_image(file_path, pipeline_log)
    elif ext in settings.DATA_EXTENSIONS:
        return await _handle_csv(file_path, language, pipeline_log)
    else:
        return await _handle_code(file_path, file_content, language, pipeline_log)


async def _handle_image(file_path: str, log: list) -> dict:
    """Handle image input: OCR → parse → analyze."""
    log.append("Stage 1: OCR extraction from image")

    ocr_result = await extract_code_from_image(file_path)

    if not ocr_result["success"]:
        return {
            "bugs": [{
                "bug_type": "OCR Error",
                "line_number": 0,
                "explanation": ocr_result.get("error", "Failed to extract code from image"),
                "impact": "Cannot analyze code",
                "suggested_fix": "Ensure the image contains readable code and a valid GEMINI_API_KEY is set in .env",
                "historical_bugs": [],
            }],
            "summary": {
                "total_bugs": 0,
                "pipeline_stages": log,
                "ocr_error": True,
            },
        }

    code = ocr_result["code"]
    # Use the language detected by the OCR tool (Gemini Vision detects it)
    language = ocr_result.get("language", _detect_language_from_code(code))
    ocr_method = ocr_result.get("method", "unknown")
    log.append(f"OCR extracted {ocr_result['line_count']} lines via {ocr_method}, detected language: {language}")

    result = await _handle_code(file_path, code, language, log, from_ocr=True)

    # Attach the extracted code so the frontend can display it
    result["extracted_code"] = code
    result["detected_language"] = language
    result["summary"]["ocr_method"] = ocr_method
    result["summary"]["ocr_lines_extracted"] = ocr_result["line_count"]

    return result


async def _handle_csv(file_path: str, language: str, log: list) -> dict:
    """Handle CSV input: pandas analysis."""
    log.append("Stage 1: CSV analysis")

    bugs = analyze_csv(file_path)
    log.append(f"Found {len(bugs)} data quality issues")

    # RAG retrieval for CSV bugs too
    try:
        bugs = await retrieve_similar_bugs(bugs, "csv")
        log.append("Stage 2: RAG retrieval complete")
    except Exception:
        for bug in bugs:
            bug["historical_bugs"] = []

    return {
        "bugs": bugs,
        "summary": {
            "total_bugs": len([b for b in bugs if b.get("bug_type") != "No Issues"]),
            "file_type": "csv",
            "pipeline_stages": log,
        },
    }


async def _handle_code(
    file_path: str,
    file_content: Optional[str],
    language: str,
    log: list,
    from_ocr: bool = False,
) -> dict:
    """Handle code input: parse → static analysis → detect → validate → RAG."""

    # Read file content if not provided
    if file_content is None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                file_content = f.read()

    # ── Stage 2: Parse code ──
    log.append("Stage 2: Code parsing (AST extraction)")
    parsed = parse_code(file_content, language)
    log.append(
        f"Parsed: {len(parsed.get('functions', []))} functions, "
        f"{len(parsed.get('variables', []))} variables, "
        f"{len(parsed.get('risks', []))} risks detected"
    )

    # ── Stage 3: Static analysis ──
    log.append("Stage 3: Static analysis")
    if not from_ocr:
        static_findings = run_static_analysis(file_path, language)
    else:
        # For OCR-extracted code, save to temp file for analysis
        import tempfile
        ext = ".py" if language == "python" else ".js"
        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False, encoding="utf-8") as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        static_findings = run_static_analysis(tmp_path, language)
        os.unlink(tmp_path)

    log.append(f"Static analysis: {len(static_findings)} findings")

    # ── Stage 4: Bug detection ──
    log.append("Stage 4: Bug detection (combining results)")
    candidate_bugs = detect_bugs(file_content, parsed, static_findings, language)
    log.append(f"Detected {len(candidate_bugs)} candidate bugs")

    # ── Stage 5: LLM Ensemble validation ──
    log.append("Stage 5: LLM ensemble validation")
    try:
        validated_bugs = await validate_with_ensemble(file_content, candidate_bugs, language)
        log.append(f"Validated {len(validated_bugs)} bugs through LLM ensemble")
    except Exception as e:
        validated_bugs = candidate_bugs
        for bug in validated_bugs:
            bug["llm_validated"] = False
            bug["validation_note"] = f"LLM validation error: {str(e)}"
        log.append(f"LLM validation failed: {str(e)}")

    # ── Stage 6: RAG retrieval ──
    log.append("Stage 6: RAG retrieval for similar bugs")
    try:
        validated_bugs = await retrieve_similar_bugs(validated_bugs, language)
        log.append("RAG retrieval complete")
    except Exception as e:
        for bug in validated_bugs:
            bug["historical_bugs"] = []
        log.append(f"RAG retrieval failed: {str(e)}")

    # ── Stage 7: Store bugs for future RAG retrieval ──
    try:
        confirmed_bugs = [b for b in validated_bugs if b.get("severity") in ("high", "critical")]
        if confirmed_bugs:
            await store_bugs(confirmed_bugs, language)
            log.append(f"Stored {len(confirmed_bugs)} bugs in RAG memory")
    except Exception:
        pass

    # Build summary
    severity_counts = {}
    for bug in validated_bugs:
        sev = bug.get("severity", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "bugs": validated_bugs,
        "summary": {
            "total_bugs": len(validated_bugs),
            "severity_breakdown": severity_counts,
            "file_type": language,
            "line_count": parsed.get("line_count", 0),
            "functions_found": len(parsed.get("functions", [])),
            "pipeline_stages": log,
            "from_ocr": from_ocr,
        },
    }


def _detect_language_from_code(code: str) -> str:
    """Heuristically detect language from code content."""
    if "def " in code and "import " in code:
        return "python"
    if "function " in code or "const " in code or "=>" in code:
        return "javascript"
    if "class " in code and ":" in code and "self" in code:
        return "python"
    return "python"  # Default
