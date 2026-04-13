"""Convert endpoint for file upload."""

import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from pydantic import BaseModel, Field

from ...core.markitdown_client import get_markitdown_client
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Conversion"])


class ConvertResponse(BaseModel):
    """Response model for successful conversion."""
    success: bool = True
    markdown: str = Field(..., description="Converted markdown content")
    title: Optional[str] = Field(None, description="Document title if available")
    format: str = Field(..., description="Detected file format")


class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: ErrorDetail


def validate_file_size(content_length: Optional[int] = None) -> None:
    """Validate file size is within limits."""
    if content_length and content_length > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": f"File size exceeds maximum allowed size of {settings.max_file_size_mb}MB",
                    "details": {
                        "max_size_mb": settings.max_file_size_mb,
                        "received_mb": round(content_length / (1024 * 1024), 2),
                    },
                }
            },
        )


def validate_file_extension(filename: Optional[str]) -> None:
    """Validate file extension is allowed."""
    if not filename:
        return

    _, ext = os.path.splitext(filename.lower())
    if ext and ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "UNSUPPORTED_FILE_TYPE",
                    "message": f"File extension '{ext}' is not supported",
                    "details": {
                        "allowed_extensions": settings.allowed_extensions,
                    },
                }
            },
        )


@router.post(
    "/file",
    response_model=ConvertResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Unsupported file type"},
        413: {"model": ErrorResponse, "description": "File too large"},
        500: {"model": ErrorResponse, "description": "Conversion error"},
    },
    summary="Convert file to Markdown",
    description="Upload a file and get its contents converted to Markdown format.",
)
async def convert_file(
    request: Request,
    file: UploadFile = File(..., description="File to convert"),
):
    """
    Convert an uploaded file to Markdown.

    Supported formats:
    - Documents: PDF, DOCX, PPTX, XLSX, XLS
    - Web: HTML
    - Data: CSV, JSON, XML
    - Archives: ZIP, EPUB
    - Images: JPG, PNG, GIF, etc. (metadata and OCR)
    - Audio: MP3, WAV, etc. (metadata and transcription)
    - Notebook: IPYNB
    """
    # Validate file size from header
    content_length = request.headers.get("content-length")
    if content_length:
        validate_file_size(int(content_length))

    # Validate file extension
    validate_file_extension(file.filename)

    # Check file is not empty
    if not file.size:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "EMPTY_FILE",
                    "message": "The uploaded file is empty",
                }
            },
        )

    # Validate size again with actual file size
    validate_file_size(file.size)

    # Read file content
    content = await file.read()

    # Double-check size after reading
    validate_file_size(len(content))

    # Convert
    client = get_markitdown_client()
    try:
        markdown, title = client.convert_bytes(
            data=content,
            filename=file.filename,
        )

        # Detect format from extension
        _, ext = os.path.splitext(file.filename or "")
        file_format = ext.lstrip(".").upper() or "unknown"

        logger.info(
            f"Converted file '{file.filename}' to markdown "
            f"(size: {len(markdown)} chars)"
        )

        return ConvertResponse(
            success=True,
            markdown=markdown,
            title=title,
            format=file_format,
        )

    except TimeoutError as e:
        logger.error(f"Conversion timeout for file '{file.filename}': {e}")
        raise HTTPException(
            status_code=504,
            detail={
                "error": {
                    "code": "CONVERSION_TIMEOUT",
                    "message": "Conversion timed out. The file may be too large or complex.",
                }
            },
        )
    except Exception as e:
        logger.error(f"Conversion error for file '{file.filename}': {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "CONVERSION_ERROR",
                    "message": f"Failed to convert file: {str(e)}",
                }
            },
        )
