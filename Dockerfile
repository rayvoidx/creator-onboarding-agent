# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Production stage
FROM python:3.11-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    # Default model names
    ANTHROPIC_MODEL_NAME=claude-sonnet-4-5-20250929 \
    OPENAI_MODEL_NAME=gpt-4o \
    GEMINI_MODEL_NAME=gemini-2.0-flash

WORKDIR /app

# System dependencies for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    libpq5 \
    # Tesseract OCR for image processing
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    # For healthcheck
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy wheels from builder stage and install
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY prompts.yaml ./
COPY pyproject.toml ./

# Create necessary directories for data and logs
RUN mkdir -p /app/data /app/logs /app/chroma_db && \
    chmod -R 755 /app/data /app/logs /app/chroma_db

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser && \
    chown -R appuser:appgroup /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
