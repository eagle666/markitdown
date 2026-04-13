"""Test all supported file formats."""

import os
import io
import tempfile
from pathlib import Path

# Create test files for different formats
def create_test_file(format_type, content=None):
    """Create a test file in memory for upload testing."""
    files = {
        # Text-based formats
        "md": b"# Test Markdown\n\nThis is a test document.\n\n## Section\n\nSome content here.",
        "html": b"<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello</h1><p>Test paragraph.</p></body></html>",
        "htm": b"<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello</h1></body></html>",
        "csv": b"name,age,city\nJohn,30,NYC\nJane,25,LA",
        "json": b'{"name": "test", "value": 123, "items": ["a", "b", "c"]}',
        "xml": b'<?xml version="1.0"?><root><item id="1">Content</item></root>',

        # Document formats (will fail without proper libs, but testing)
        "pdf": b"%PDF-1.4\n1 0 obj\n<<\x02\x03>>\nendobj\n",
        "docx": b"PK\x03\x04",  # ZIP signature - won't be valid but testing detection
        "xlsx": b"PK\x03\x04",
        "pptx": b"PK\x03\x04",

        # Image formats (will test metadata extraction)
        "jpg": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb",
        "png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",

        # Audio formats (will test metadata)
        "mp3": b"\xff\xfb\x90\x00",
        "wav": b"RIFF$\x00\x00\x00WAVEfmt ",
        "ogg": b"OggS\x00\x02",
        "m4a": b"\x00\x00\x00\x18ftypM4A",

        # Video formats
        "mp4": b"\x00\x00\x00\x18ftypmp42",
    }
    return files.get(format_type, b"test content")


def test_markitdown_formats():
    """Test all formats with MarkItDown directly."""
    from markitdown import MarkItDown

    md = MarkItDown()

    formats = {
        # Text-based - should work
        "md": (".md", "Markdown"),
        "html": (".html", "HTML"),
        "csv": (".csv", "CSV"),
        "json": (".json", "JSON"),
        "xml": (".xml", "XML"),

        # Audio/Video - depends on dependencies
        "mp3": (".mp3", "Audio"),
        "wav": (".wav", "Audio"),
        "mp4": (".mp4", "Video"),
    }

    print("=" * 70)
    print("Testing MarkItDown Core Library - All Formats")
    print("=" * 70)

    for key, (ext, desc) in formats.items():
        print(f"\n--- Testing {ext} ({desc}) ---")
        try:
            content = create_test_file(key)
            if not content:
                print(f"  SKIP: No test content for {ext}")
                continue

            stream = io.BytesIO(content)
            result = md.convert_stream(stream, file_extension=ext)

            print(f"  SUCCESS: {len(result.markdown)} chars")
            if result.markdown:
                preview = result.markdown[:100].replace('\n', ' ')
                print(f"  Preview: {preview}...")
            else:
                print(f"  WARNING: Empty markdown returned")
            if result.title:
                print(f"  Title: {result.title}")
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {str(e)[:100]}")


def test_api_server():
    """Test the API server endpoints."""
    import requests

    base_url = "http://localhost:8000"

    print("\n" + "=" * 70)
    print("Testing API Server Endpoints")
    print("=" * 70)

    # Test health
    print("\n--- Health Check ---")
    try:
        r = requests.get(f"{base_url}/health")
        print(f"  Status: {r.status_code}")
        print(f"  Response: {r.json()}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test formats
    print("\n--- Formats List ---")
    try:
        r = requests.get(f"{base_url}/formats")
        data = r.json()
        print(f"  Status: {r.status_code}")
        print(f"  Total formats: {data.get('total_count', 0)}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test file upload for each format
    formats_to_test = ["md", "html", "csv", "json", "xml", "pdf", "docx", "xlsx", "pptx", "jpg", "png", "mp3", "wav", "mp4"]

    print("\n--- File Upload Tests ---")
    for fmt in formats_to_test:
        content = create_test_file(fmt)
        if not content:
            print(f"  {fmt.upper()}: SKIP (no test content)")
            continue

        filename = f"test.{fmt}"
        files = {"file": (filename, content)}

        try:
            r = requests.post(f"{base_url}/convert/file", files=files)
            data = r.json()

            if r.status_code == 200:
                markdown_len = len(data.get("markdown", ""))
                print(f"  {fmt.upper()}: SUCCESS ({markdown_len} chars)")
                if not data.get("markdown"):
                    print(f"    WARNING: Empty markdown!")
            else:
                print(f"  {fmt.upper()}: ERROR {r.status_code} - {data.get('detail', r.text)[:80]}")
        except Exception as e:
            print(f"  {fmt.upper()}: ERROR - {type(e).__name__}: {str(e)[:50]}")


def check_dependencies():
    """Check if all dependencies are installed."""
    print("=" * 70)
    print("Checking Dependencies")
    print("=" * 70)

    deps = {
        "ffmpeg": "Video/Audio processing",
        "exiftool": "Metadata extraction",
        "speech_recognition": "Speech to text",
        "pydub": "Audio processing",
        "moviepy": "Video processing",
    }

    missing = []
    for dep, purpose in deps.items():
        try:
            import subprocess
            result = subprocess.run(["where" if os.name == "nt" else "which", dep],
                                 capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  {dep}: OK ({result.stdout.strip()[:50]})")
            else:
                print(f"  {dep}: MISSING ({purpose})")
                missing.append(dep)
        except Exception:
            print(f"  {dep}: CHECK FAILED")

    if missing:
        print(f"\n  Missing dependencies may affect some format conversions.")
        print(f"  Run: pip install pydub SpeechRecognition moviepy")
        print(f"  And install ffmpeg/exiftool system packages.")


if __name__ == "__main__":
    check_dependencies()
    test_markitdown_formats()
    test_api_server()
    print("\n" + "=" * 70)
    print("Tests completed!")
    print("=" * 70)
