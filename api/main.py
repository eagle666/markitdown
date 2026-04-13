"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .api.routes import convert_router, health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"MarkItDown pool size: {settings.markitdown_pool_size}")
    logger.info(f"Max file size: {settings.max_file_size_mb}MB")

    yield

    # Shutdown
    logger.info("Shutting down...")
    from .core.markitdown_client import get_markitdown_client
    client = get_markitdown_client()
    client.shutdown()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="""
    MarkItDown API - Convert various file formats to Markdown.

    This API allows you to convert documents, images, audio, and web content
    to Markdown format, optimized for use with LLMs.

    ## Features

    - **File Conversion**: Upload PDF, DOCX, PPTX, XLSX, and more
    - **URL Conversion**: Convert web pages, YouTube videos, Wikipedia articles
    - **Image OCR**: Extract text from images
    - **Audio Transcription**: Convert speech in audio files to text

    Note: Authentication and rate limiting are handled by the API gateway (RapidAPI).
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(convert_router)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirects to docs."""
    return JSONResponse({
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "formats": "/formats",
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.debug,
    )