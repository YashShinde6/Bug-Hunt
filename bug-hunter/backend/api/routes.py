"""API routes for file upload, analysis, and history."""
import os
import uuid
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from config import settings
from orchestrator.pipeline import run_pipeline

router = APIRouter()

# In-memory analysis history
analysis_history: list[dict] = []


class AnalyzeRequest(BaseModel):
    file_path: str
    file_content: Optional[str] = None
    language: Optional[str] = None


class AnalyzeResponse(BaseModel):
    file_name: str
    language: str
    bugs: list[dict]
    summary: dict
    timestamp: float
    extracted_code: Optional[str] = None
    detected_language: Optional[str] = None


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a code file, CSV, or screenshot for analysis."""
    ext = Path(file.filename).suffix.lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    # Save file
    file_id = str(uuid.uuid4())[:8]
    safe_name = f"{file_id}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    # Detect language
    language = _detect_language(ext)

    # Read text content for code files
    text_content = None
    if ext in settings.CODE_EXTENSIONS or ext in settings.DATA_EXTENSIONS:
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            text_content = content.decode("latin-1")

    return {
        "file_id": file_id,
        "file_name": file.filename,
        "file_path": file_path,
        "language": language,
        "content": text_content,
        "size": len(content),
    }


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_file(request: AnalyzeRequest):
    """Run the multi-agent bug detection pipeline on a file."""
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    ext = Path(request.file_path).suffix.lower()
    language = request.language or _detect_language(ext)

    # Run the full agent pipeline
    result = await run_pipeline(
        file_path=request.file_path,
        file_content=request.file_content,
        language=language,
    )

    response = AnalyzeResponse(
        file_name=os.path.basename(request.file_path),
        language=result.get("detected_language", language),
        bugs=result.get("bugs", []),
        summary=result.get("summary", {}),
        timestamp=time.time(),
        extracted_code=result.get("extracted_code"),
        detected_language=result.get("detected_language"),
    )

    # Store in history
    analysis_history.append(response.model_dump())
    if len(analysis_history) > 100:
        analysis_history.pop(0)

    return response


@router.get("/history")
async def get_history():
    """Return recent analysis results."""
    return {"history": list(reversed(analysis_history)), "total": len(analysis_history)}


def _detect_language(ext: str) -> str:
    lang_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".csv": "csv",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
    }
    return lang_map.get(ext, "unknown")
