# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy project files (excluding secrets via .dockerignore)
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Create virtual environment and install dependencies
RUN /root/.cargo/bin/uv venv /app/.venv && \
    /root/.cargo/bin/uv pip install -e . --python /app/.venv/bin/python

# Runtime stage - ARM64 optimized for Raspberry Pi 3
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Health check for HTTP mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Default to HTTP mode for Pi deployment; override TRANSPORT env var to use MCP mode
ENV TRANSPORT=http

EXPOSE 8000

# Run the MCP/HTTP server
CMD ["python", "-m", "solax_cloud_mcp"]
