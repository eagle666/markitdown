"""MarkItDown client with instance pooling for concurrent requests."""

import io
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from queue import Queue, Empty
from typing import Optional
import threading

from markitdown import MarkItDown
from markitdown._exceptions import (
    UnsupportedFormatException,
    FileConversionException,
)

from .config import settings

logger = logging.getLogger(__name__)


class MarkItDownClient:
    """
    A client wrapper around MarkItDown with instance pooling.

    This solves the concurrency problem by maintaining a pool of pre-initialized
    MarkItDown instances. Each instance is thread-safe for conversion operations,
    and the pool allows us to serve multiple concurrent requests without
    recreating the expensive magika model for each request.

    Thread safety: MarkItDown itself is stateless after initialization,
    but the magika model and requests session are shared. We use a lock
    per instance to ensure thread-safe access.
    """

    def __init__(
        self,
        pool_size: Optional[int] = None,
        enable_plugins: bool = False,
    ):
        """
        Initialize the MarkItDown client with a pool of instances.

        Args:
            pool_size: Number of MarkItDown instances to pool. Defaults to config value.
            enable_plugins: Whether to enable plugin converters.
        """
        self.pool_size = pool_size or settings.markitdown_pool_size
        self.enable_plugins = enable_plugins or settings.markitdown_enable_plugins
        self._pool: Queue[MarkItDown] = Queue()
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=self.pool_size * 2)

        # Pre-populate the pool
        for _ in range(self.pool_size):
            instance = self._create_instance()
            self._pool.put(instance)

        logger.info(f"MarkItDownClient initialized with {self.pool_size} instances")

    def _create_instance(self) -> MarkItDown:
        """Create a new MarkItDown instance."""
        return MarkItDown(enable_plugins=self.enable_plugins)

    def _get_instance(self, timeout: float = 30.0) -> MarkItDown:
        """
        Get an instance from the pool.

        Args:
            timeout: How long to wait for an instance to become available.

        Returns:
            A MarkItDown instance.

        Raises:
            TimeoutError: If no instance becomes available within the timeout.
        """
        try:
            return self._pool.get(timeout=timeout)
        except Empty:
            # Pool exhausted, create a temporary instance
            logger.warning("MarkItDown pool exhausted, creating temporary instance")
            return self._create_instance()

    def _return_instance(self, instance: MarkItDown) -> None:
        """Return an instance to the pool."""
        try:
            self._pool.put_nowait(instance)
        except Exception:
            # Pool full, discard this instance
            logger.debug("MarkItDown pool full, discarding instance")

    def convert_bytes(
        self,
        data: bytes,
        filename: Optional[str] = None,
        file_extension: Optional[str] = None,
        timeout: float = 120.0,
    ) -> tuple[str, Optional[str]]:
        """
        Convert bytes to markdown.

        Args:
            data: The file content as bytes.
            filename: Original filename (for format detection).
            file_extension: Override file extension.
            timeout: Conversion timeout in seconds.

        Returns:
            Tuple of (markdown_content, title)

        Raises:
            UnsupportedFormatException: If the file format is not supported.
            FileConversionException: If conversion fails.
            TimeoutError: If conversion takes too long.
        """
        def _do_convert():
            instance = self._get_instance()
            try:
                stream = io.BytesIO(data)

                # Determine extension from filename if not provided
                ext = file_extension
                if not ext and filename:
                    import os
                    _, ext = os.path.splitext(filename)

                result = instance.convert_stream(
                    stream,
                    file_extension=ext,
                )
                return result.markdown, result.title
            finally:
                self._return_instance(instance)

        future = self._executor.submit(_do_convert)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise TimeoutError(f"Conversion timed out after {timeout} seconds")

    def convert_url(
        self,
        url: str,
        timeout: float = 120.0,
    ) -> tuple[str, Optional[str]]:
        """
        Convert a URL to markdown.

        Args:
            url: The URL to convert (http, https, data URI).
            timeout: Conversion timeout in seconds.

        Returns:
            Tuple of (markdown_content, title)

        Raises:
            UnsupportedFormatException: If the URL format is not supported.
            FileConversionException: If conversion fails.
            TimeoutError: If conversion takes too long.
        """
        def _do_convert():
            instance = self._get_instance()
            try:
                result = instance.convert_uri(url)
                return result.markdown, result.title
            finally:
                self._return_instance(instance)

        future = self._executor.submit(_do_convert)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise TimeoutError(f"Conversion timed out after {timeout} seconds")

    def shutdown(self) -> None:
        """Shutdown the client, releasing all resources."""
        self._executor.shutdown(wait=True)
        # Drain the pool
        while not self._pool.empty():
            try:
                self._pool.get_nowait()
            except Empty:
                break
        logger.info("MarkItDownClient shutdown complete")


# Global client instance (per worker process)
_client: Optional[MarkItDownClient] = None
_client_lock = threading.Lock()


def get_markitdown_client() -> MarkItDownClient:
    """
    Get the global MarkItDownClient instance for this worker process.

    This ensures each worker process has its own pool of MarkItDown instances.
    """
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = MarkItDownClient()
    return _client