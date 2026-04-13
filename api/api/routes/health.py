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

    This endpoint does not require API key authentication.
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

    Returns formats grouped by category with extension and name.
    """
    formats = [
        # Documents
        FormatInfo(extension=".pdf", name="PDF", category="document"),
        FormatInfo(extension=".docx", name="Word Document", category="document"),
        FormatInfo(extension=".pptx", name="PowerPoint", category="document"),
        FormatInfo(extension=".xlsx", name="Excel Spreadsheet", category="document"),
        FormatInfo(extension=".xls", name="Excel Spreadsheet (Legacy)", category="document"),

        # Web & Data
        FormatInfo(extension=".html", name="HTML", category="web"),
        FormatInfo(extension=".htm", name="HTML", category="web"),
        FormatInfo(extension=".csv", name="CSV", category="data"),
        FormatInfo(extension=".json", name="JSON", category="data"),
        FormatInfo(extension=".xml", name="XML", category="data"),

        # Archives & Books
        FormatInfo(extension=".zip", name="ZIP Archive", category="archive"),
        FormatInfo(extension=".epub", name="EPUB E-Book", category="ebook"),
        FormatInfo(extension=".ipynb", name="Jupyter Notebook", category="notebook"),

        # Images
        FormatInfo(extension=".jpg", name="JPEG Image", category="image"),
        FormatInfo(extension=".jpeg", name="JPEG Image", category="image"),
        FormatInfo(extension=".png", name="PNG Image", category="image"),
        FormatInfo(extension=".gif", name="GIF Image", category="image"),
        FormatInfo(extension=".webp", name="WebP Image", category="image"),
        FormatInfo(extension=".tiff", name="TIFF Image", category="image"),
        FormatInfo(extension=".bmp", name="Bitmap Image", category="image"),

        # Audio
        FormatInfo(extension=".mp3", name="MP3 Audio", category="audio"),
        FormatInfo(extension=".wav", name="WAV Audio", category="audio"),
        FormatInfo(extension=".flac", name="FLAC Audio", category="audio"),
        FormatInfo(extension=".m4a", name="M4A Audio", category="audio"),
        FormatInfo(extension=".ogg", name="OGG Audio", category="audio"),

        # Special
        FormatInfo(extension="youtube", name="YouTube Video", category="special"),
        FormatInfo(extension="wikipedia", name="Wikipedia Article", category="special"),
        FormatInfo(extension="rss", name="RSS Feed", category="special"),
    ]

    return FormatsResponse(
        formats=formats,
        total_count=len(formats),
        max_file_size_mb=settings.max_file_size_mb,
    )