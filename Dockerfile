FROM python:3.13-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive
ENV EXIFTOOL_PATH=/usr/bin/exiftool
ENV FFMPEG_PATH=/usr/bin/ffmpeg

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    exiftool \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install MarkItDown core with all features
COPY packages/markitdown/pyproject.toml /app/packages/markitdown/pyproject.toml
RUN pip --no-cache-dir install packages/markitdown[all]

# Install API dependencies
COPY requirements-api.txt /app/requirements-api.txt
RUN pip --no-cache-dir install -r /app/requirements-api.txt

# Copy API code
COPY api /app/api

# Default USERID and GROUPID
ARG USERID=nobody
ARG GROUPID=nogroup

USER $USERID:$GROUPID

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run API server
# Railway expects PORT env var
ENV PORT=8000
ENV MARKITDOWN_HOST=0.0.0.0
ENV MARKITDOWN_PORT=8000
ENV MARKITDOWN_WORKERS=4

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]