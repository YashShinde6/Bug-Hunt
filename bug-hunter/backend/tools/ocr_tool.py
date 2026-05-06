"""OCR Tool — extract code from screenshots using Gemini Vision API (with Tesseract fallback)."""
import base64
import json
import re
import shutil
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image, ImageEnhance, ImageFilter

from config import settings


# ── Gemini Vision OCR (primary) ──────────────────────────────────────────────

OCR_SYSTEM_PROMPT = """You are an expert code extraction assistant.
Extract the EXACT source code visible in this screenshot image.

Rules:
1. Reproduce the code EXACTLY as shown — preserve indentation, spacing, comments, and line breaks.
2. Do NOT add, modify, or omit any code. Extract only what is visible.
3. If line numbers are visible in the screenshot, REMOVE them from your output (extract only the code itself).
4. If the image contains non-code text (e.g. UI elements, headers), ignore those and extract only the code portion.
5. Return ONLY the raw code — no markdown fences, no explanations, no commentary.
6. If no code is visible in the image, return the single word: NO_CODE_FOUND"""

LANG_DETECT_PROMPT = """Look at the code in this image and identify the programming language.
Return ONLY one of these exact strings: python, javascript, typescript, java, c, cpp, csharp, go, rust, ruby, php, html, css, sql, unknown
Return nothing else — just the language name."""


async def extract_code_from_image(image_path: str) -> dict:
    """Extract code text from a screenshot image using Gemini Vision API.

    Falls back to Tesseract if Gemini is unavailable.
    """
    # Validate the image file exists and is readable
    path = Path(image_path)
    if not path.exists():
        return {
            "success": False,
            "code": "",
            "language": "unknown",
            "error": f"Image file not found: {image_path}",
        }

    # Preprocess the image for better extraction
    preprocessed_path = _preprocess_image(image_path)
    target_path = preprocessed_path or image_path

    # Try Gemini Vision first
    gemini_error = None
    if settings.has_gemini:
        result = await _extract_with_gemini(target_path)
        if result["success"]:
            # Clean up preprocessed temp file
            if preprocessed_path and preprocessed_path != image_path:
                try:
                    Path(preprocessed_path).unlink(missing_ok=True)
                except Exception:
                    pass
            return result
        else:
            gemini_error = result["error"]
            print(f"Gemini Vision API failed: {gemini_error}")

    # Fallback to Tesseract
    if not shutil.which("tesseract"):
        error_msg = "OCR unavailable: Tesseract is not installed."
        if gemini_error:
            error_msg = f"Gemini Vision API failed: {gemini_error}\nAnd Tesseract fallback is not installed."
        
        # Clean up preprocessed temp file
        if preprocessed_path and preprocessed_path != image_path:
            try:
                Path(preprocessed_path).unlink(missing_ok=True)
            except Exception:
                pass

        return {
            "success": False,
            "code": "",
            "language": "unknown",
            "error": error_msg,
        }

    result = _extract_with_tesseract(target_path)

    # Clean up preprocessed temp file
    if preprocessed_path and preprocessed_path != image_path:
        try:
            Path(preprocessed_path).unlink(missing_ok=True)
        except Exception:
            pass

    return result


async def _extract_with_gemini(image_path: str) -> dict:
    """Use Gemini Vision API to extract code from an image."""
    try:
        # Read and encode the image
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Detect MIME type
        ext = Path(image_path).suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp"}
        mime_type = mime_map.get(ext, "image/png")

        # Call Gemini Vision for code extraction
        url = f"{settings.GEMINI_URL}?key={settings.GEMINI_API_KEY}"

        async with httpx.AsyncClient(timeout=60) as client:
            # Step 1: Extract the code
            response = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "parts": [
                            {"text": OCR_SYSTEM_PROMPT},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": base64_image,
                                }
                            },
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.0,
                        "maxOutputTokens": 8192,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            candidates = data.get("candidates", [])
            if not candidates:
                return {
                    "success": False,
                    "code": "",
                    "language": "unknown",
                    "error": "Gemini returned no candidates. The image may have been rejected.",
                }
            
            candidate = candidates[0]
            if "content" not in candidate or "parts" not in candidate["content"]:
                finish_reason = candidate.get("finishReason", "UNKNOWN")
                return {
                    "success": False,
                    "code": "",
                    "language": "unknown",
                    "error": f"Gemini failed to extract text. Reason: {finish_reason}. The image might be blocked by safety filters.",
                }

            extracted_text = candidate["content"]["parts"][0].get("text", "")

            # Check for no-code response
            if extracted_text.strip() == "NO_CODE_FOUND":
                return {
                    "success": False,
                    "code": "",
                    "language": "unknown",
                    "error": "No code was found in the image.",
                }

            # Clean the extracted code
            cleaned = _clean_ocr_output(extracted_text)

            # Step 2: Detect the language
            lang_response = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "parts": [
                            {"text": LANG_DETECT_PROMPT},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": base64_image,
                                }
                            },
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.0,
                        "maxOutputTokens": 20,
                    },
                },
            )
            lang_response.raise_for_status()
            lang_data = lang_response.json()
            
            lang_candidates = lang_data.get("candidates", [])
            if lang_candidates and "content" in lang_candidates[0] and "parts" in lang_candidates[0]["content"]:
                detected_lang = lang_candidates[0]["content"]["parts"][0].get("text", "").strip().lower()
            else:
                detected_lang = "unknown"

            # Validate detected language
            valid_langs = {
                "python", "javascript", "typescript", "java", "c", "cpp",
                "csharp", "go", "rust", "ruby", "php", "html", "css", "sql",
            }
            if detected_lang not in valid_langs:
                detected_lang = _detect_language_from_code(cleaned)

        return {
            "success": True,
            "code": cleaned,
            "language": detected_lang,
            "raw_text": extracted_text,
            "line_count": len(cleaned.splitlines()),
            "method": "gemini_vision",
        }

    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "code": "",
            "language": "unknown",
            "error": f"Gemini Vision API error: {e.response.status_code} — {e.response.text[:200]}",
        }
    except Exception as e:
        return {
            "success": False,
            "code": "",
            "language": "unknown",
            "error": f"Gemini Vision OCR failed: {str(e)}",
        }


# ── Tesseract fallback ──────────────────────────────────────────────────────

def _extract_with_tesseract(image_path: str) -> dict:
    """Fallback: extract code from image using Tesseract OCR."""
    if not shutil.which("tesseract"):
        return {
            "success": False,
            "code": "",
            "language": "unknown",
            "error": (
                "OCR unavailable: Gemini Vision API failed and Tesseract is not installed. "
                "Either configure GEMINI_API_KEY in .env or install Tesseract from "
                "https://github.com/tesseract-ocr/tesseract"
            ),
        }

    try:
        import pytesseract

        img = Image.open(image_path)
        img = img.convert("L")

        raw_text = pytesseract.image_to_string(img, config="--psm 6")
        cleaned = _clean_ocr_output(raw_text)
        language = _detect_language_from_code(cleaned)

        return {
            "success": True,
            "code": cleaned,
            "language": language,
            "raw_text": raw_text,
            "line_count": len(cleaned.splitlines()),
            "method": "tesseract",
        }

    except ImportError:
        return {
            "success": False,
            "code": "",
            "language": "unknown",
            "error": "pytesseract or Pillow not installed",
        }
    except Exception as e:
        return {
            "success": False,
            "code": "",
            "language": "unknown",
            "error": f"Tesseract OCR failed: {str(e)}",
        }


# ── Image preprocessing ─────────────────────────────────────────────────────

def _preprocess_image(image_path: str) -> Optional[str]:
    """Preprocess image for better OCR: enhance contrast, sharpen, resize if small."""
    try:
        img = Image.open(image_path)

        # Convert to RGB if necessary (handles RGBA, P-mode, etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Upscale small images (< 800px width) for better text recognition
        if img.width < 800:
            scale = 800 / img.width
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.LANCZOS)

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Sharpen
        img = img.filter(ImageFilter.SHARPEN)

        # Save preprocessed image
        preprocessed_path = str(Path(image_path).parent / f"_preprocessed_{Path(image_path).name}")
        # Ensure output format matches — save as PNG for lossless quality
        img.save(preprocessed_path, format="PNG")
        return preprocessed_path

    except Exception:
        return None


# ── Utilities ────────────────────────────────────────────────────────────────

def _clean_ocr_output(text: str) -> str:
    """Clean OCR output to improve code quality."""
    # Remove markdown code fences if present
    text = re.sub(r'^```\w*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n?```$', '', text, flags=re.MULTILINE)

    lines = text.splitlines()
    cleaned = []

    for line in lines:
        stripped = line.rstrip()

        # Fix common OCR mistakes in code
        stripped = stripped.replace("\u2014", "--")       # em dash
        stripped = stripped.replace("\u201c", '"')        # left double quote
        stripped = stripped.replace("\u201d", '"')        # right double quote
        stripped = stripped.replace("\u2018", "'")        # left single quote
        stripped = stripped.replace("\u2019", "'")        # right single quote
        stripped = stripped.replace("\u2026", "...")      # ellipsis
        stripped = stripped.replace("\u00a0", " ")        # non-breaking space

        cleaned.append(stripped)

    # Remove leading/trailing empty lines
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()

    return "\n".join(cleaned)


def _detect_language_from_code(code: str) -> str:
    """Heuristically detect language from extracted code content."""
    if not code.strip():
        return "unknown"

    code_lower = code.lower()

    # Python indicators
    py_score = sum([
        "def " in code, "import " in code, "from " in code,
        "class " in code and "self" in code, "print(" in code,
        "elif " in code, "    " in code,  # 4-space indent is common in Python
    ])

    # JavaScript/TypeScript indicators
    js_score = sum([
        "function " in code, "const " in code, "let " in code,
        "var " in code, "=>" in code, "console.log" in code,
        "require(" in code, "module.exports" in code,
    ])

    ts_score = js_score + sum([
        ": string" in code_lower, ": number" in code_lower,
        "interface " in code, ": boolean" in code_lower,
    ])

    if ts_score > py_score and ts_score > js_score:
        return "typescript"
    if js_score > py_score:
        return "javascript"
    if py_score > 0:
        return "python"

    return "python"  # Default fallback
