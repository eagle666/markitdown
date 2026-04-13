# MarkItDown API Documentation

REST API for converting various file formats to Markdown, built on Microsoft's MarkItDown library.

## Base URL

```
Local:    http://localhost:8000
Production: https://your-api-host.railway.app
```

## Authentication

All endpoints except `/health` require API key authentication.

| Header | Value |
|--------|-------|
| `X-API-Key` | Your API key |

## Endpoints

### Health Check

**GET** `/health`

Check if the API is running and healthy.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "service": "MarkItDown API"
}
```

---

### Get Supported Formats

**GET** `/formats`

Get a list of all supported file formats for conversion.

**Headers:**
- `X-API-Key` (required)

**Response:**
```json
{
  "formats": [
    {
      "extension": ".pdf",
      "name": "PDF",
      "category": "document"
    },
    {
      "extension": ".docx",
      "name": "Word Document",
      "category": "document"
    }
  ],
  "total_count": 28,
  "max_file_size_mb": 1024
}
```

---

### Convert File to Markdown

**POST** `/convert/file`

Upload a file and get its contents converted to Markdown format.

**Headers:**
- `X-API-Key` (required)

**Body:** `multipart/form-data`
- `file`: The file to convert

**Supported Formats:**
- Documents: PDF, DOCX, PPTX, XLSX, XLS
- Web: HTML
- Data: CSV, JSON, XML
- Archives: ZIP, EPUB
- Images: JPG, PNG, GIF, WEBP, TIFF, BMP (metadata and OCR)
- Audio: MP3, WAV, FLAC, M4A, OGG (metadata and transcription)
- Notebook: IPYNB

**Response:**
```json
{
  "success": true,
  "markdown": "# Document Title\n\nConverted content...",
  "title": "Document Title",
  "format": "PDF"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/convert/file \
  -H "X-API-Key: your-api-key" \
  -F "file=@document.pdf"
```

---

### Convert URL to Markdown

**POST** `/convert/url`

Convert a web page, YouTube video, Wikipedia article, or data URL to Markdown.

**Headers:**
- `X-API-Key` (required)
- `Content-Type: application/json`

**Body:**
```json
{
  "url": "https://en.wikipedia.org/wiki/Python_(programming_language)"
}
```

**Supported URLs:**
- Web pages (http://, https://)
- YouTube videos (transcription)
- Wikipedia articles
- RSS feeds
- Data URIs

**Response:**
```json
{
  "success": true,
  "markdown": "# Python (Programming Language)\n\nPython is a high-level...",
  "title": "Python (programming language) - Wikipedia",
  "format": "WIKIPEDIA"
}
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {}
  }
}
```

### Error Codes

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | `MISSING_URL` | URL is required |
| 400 | `INVALID_URL_SCHEME` | URL scheme must be http, https, or data |
| 400 | `UNSUPPORTED_FILE_TYPE` | File extension is not supported |
| 400 | `EMPTY_FILE` | Uploaded file is empty |
| 401 | `MISSING_API_KEY` | API key is required |
| 401 | `INVALID_API_KEY` | The provided API key is invalid |
| 413 | `FILE_TOO_LARGE` | File size exceeds maximum allowed |
| 429 | `RATE_LIMIT_EXCEEDED` | Rate limit exceeded |
| 500 | `CONVERSION_ERROR` | Error during file conversion |
| 504 | `CONVERSION_TIMEOUT` | Conversion timed out |

---

## Rate Limits

Default rate limit is 100 requests per minute per API key.

Response headers include rate limit information:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when the window resets

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKITDOWN_API_KEYS` | (none) | Comma-separated list of valid API keys |
| `MARKITDOWN_API_KEYS_REQUIRED` | false | If true, API keys are enforced |
| `MARKITDOWN_WORKERS` | 4 | Number of uvicorn workers |
| `MARKITDOWN_RATE_LIMIT_REQUESTS` | 100 | Requests per window |
| `MARKITDOWN_RATE_LIMIT_WINDOW_SECONDS` | 60 | Rate limit window in seconds |
| `MARKITDOWN_MAX_FILE_SIZE_MB` | 1024 | Maximum file size in MB |

---

## Import to Apifox

1. Open Apifox
2. Go to Settings > Import
3. Select "OpenAPI/Swagger"
4. Upload the `openapi.json` file or paste the URL
5. Configure your environment variables

## Import to Postman

1. Open Postman
2. Click Import
3. Select the `postman/MarkItDown-API.postman_collection.json` file
4. Update the `baseUrl` and `apiKey` variables

---

## Development

### Local Setup

```bash
# Install dependencies
pip install -r requirements-api.txt

# Set API keys for testing
export MARKITDOWN_API_KEYS="dev-key-1,dev-key-2"

# Run server
python -m uvicorn api.main:app --reload
```

### Docker

```bash
# Build image
docker build -t markitdown-api .

# Run container
docker run -p 8000:8000 \
  -e MARKITDOWN_API_KEYS="your-api-keys" \
  markitdown-api
```
