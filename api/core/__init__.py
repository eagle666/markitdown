"""Core module for MarkItDown API."""

from .config import settings
from .markitdown_client import MarkItDownClient, get_markitdown_client

__all__ = ["settings", "MarkItDownClient", "get_markitdown_client"]