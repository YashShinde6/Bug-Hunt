"""OCR Tool — extract code from screenshots using Tesseract."""
import shutil
from typing import Optional


def extract_code_from_image(image_path: str) -> dict:
    """Extract code text from a screenshot image."""
    if not shutil.which("tesseract"):
        return {
            "success": False,
            "code": "",
            "error": "Tesseract not installed. Install from https://github.com/tesseract-ocr/tesseract",
        }

    try:
        from PIL import Image
        import pytesseract

        img = Image.open(image_path)

        # Preprocess: convert to grayscale for better OCR
        img = img.convert("L")

        # Extract text
        raw_text = pytesseract.image_to_string(img, config="--psm 6")

        # Clean extracted code
        cleaned = _clean_ocr_output(raw_text)

        return {
            "success": True,
            "code": cleaned,
            "raw_text": raw_text,
            "line_count": len(cleaned.splitlines()),
        }

    except ImportError:
        return {
            "success": False,
            "code": "",
            "error": "pytesseract or Pillow not installed",
        }
    except Exception as e:
        return {
            "success": False,
            "code": "",
            "error": f"OCR failed: {str(e)}",
        }


def _clean_ocr_output(text: str) -> str:
    """Clean OCR output to improve code quality."""
    lines = text.splitlines()
    cleaned = []

    for line in lines:
        # Remove empty lines at start/end
        stripped = line.rstrip()

        # Fix common OCR mistakes in code
        stripped = stripped.replace("—", "--")
        stripped = stripped.replace(""", '"').replace(""", '"')
        stripped = stripped.replace("'", "'").replace("'", "'")
        stripped = stripped.replace("…", "...")

        cleaned.append(stripped)

    # Remove leading/trailing empty lines
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()

    return "\n".join(cleaned)
