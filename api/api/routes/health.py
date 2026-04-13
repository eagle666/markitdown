"""Health check and information endpoints."""

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from ...core.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    service: str


class FormatInfo(BaseModel):
    """Information about a supported format."""
    extension: str
    name: str
    category: str


class FormatsResponse(BaseModel):
    """Supported formats response."""
    formats: List[FormatInfo]
    total_count: int
    max_file_size_mb: int


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the API is running and healthy.",
)
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        service=settings.app_name,
    )


@router.get(
    "/formats",
    response_model=FormatsResponse,
    summary="Supported formats",
    description="Get list of all supported file formats for conversion.",
)
async def get_formats():
    """
    Get a list of all supported file formats.
    """
    # Map extensions to names and categories
    format_info = {
        # Documents
        ".pdf": ("PDF", "document"),
        ".docx": ("Word Document", "document"),
        ".pptx": ("PowerPoint", "document"),
        ".ppt": ("PowerPoint", "document"),
        ".xlsx": ("Excel Spreadsheet", "document"),
        ".xls": ("Excel Spreadsheet (Legacy)", "document"),
        # Web
        ".html": ("HTML", "web"),
        ".htm": ("HTML", "web"),
        # Data
        ".csv": ("CSV", "data"),
        ".json": ("JSON", "data"),
        ".xml": ("XML", "data"),
        # Archives & Books
        ".zip": ("ZIP Archive", "archive"),
        ".epub": ("EPUB E-Book", "ebook"),
        ".ipynb": ("Jupyter Notebook", "notebook"),
        ".md": ("Markdown", "document"),
        # Images
        ".jpg": ("JPEG Image", "image"),
        ".jpeg": ("JPEG Image", "image"),
        ".png": ("PNG Image", "image"),
        ".gif": ("GIF Image", "image"),
        ".webp": ("WebP Image", "image"),
        ".tiff": ("TIFF Image", "image"),
        ".tif": ("TIFF Image", "image"),
        ".bmp": ("Bitmap Image", "image"),
        ".svg": ("SVG Image", "image"),
        # Audio
        ".mp3": ("MP3 Audio", "audio"),
        ".wav": ("WAV Audio", "audio"),
        ".flac": ("FLAC Audio", "audio"),
        ".m4a": ("M4A Audio", "audio"),
        ".ogg": ("OGG Audio", "audio"),
        ".aac": ("AAC Audio", "audio"),
        # Video
        ".mp4": ("MP4 Video", "video"),
        ".avi": ("AVI Video", "video"),
        ".mkv": ("MKV Video", "video"),
        ".mov": ("MOV Video", "video"),
        ".wmv": ("WMV Video", "video"),
        ".flv": ("FLV Video", "video"),
        ".webm": ("WebM Video", "video"),
    }

    formats = []
    for ext in settings.allowed_extensions:
        ext_lower = ext.lower()
        if ext_lower in format_info:
            name, category = format_info[ext_lower]
        else:
            name = ext_lower.lstrip(".").upper() + " File"
            category = "other"
        formats.append(FormatInfo(extension=ext, name=name, category=category))

    return FormatsResponse(
        formats=formats,
        total_count=len(formats),
        max_file_size_mb=settings.max_file_size_mb,
    )
