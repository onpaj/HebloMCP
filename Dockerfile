# Multi-stage build for HebloMCP

# ============================================================================
# Builder Stage: Build the wheel
# ============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir hatchling build

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Build wheel
RUN python -m build --wheel --outdir dist/

# ============================================================================
# Runtime Stage: Minimal production image
# ============================================================================
FROM python:3.12-slim AS runtime

# Create non-root user
RUN useradd --create-home --shell /bin/bash heblo

# Set working directory
WORKDIR /app

# Copy wheel from builder stage
COPY --from=builder /build/dist/*.whl /tmp/

# Install the application
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm /tmp/*.whl

# Switch to non-root user
USER heblo

# Create directory for token cache (mount as volume)
RUN mkdir -p /home/heblo/.config/heblo-mcp

# Set environment variables
ENV HEBLO_TOKEN_CACHE_PATH=/home/heblo/.config/heblo-mcp/token_cache.json

# Expose port for SSE transport
EXPOSE 8000

# Volume for persistent token cache
VOLUME ["/home/heblo/.config/heblo-mcp"]

# Entrypoint
ENTRYPOINT ["heblo-mcp"]

# Default command - run in SSE mode for cloud deployment
CMD ["serve-sse"]

# Health check for Azure Web App
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5.0)" || exit 1

# Labels
LABEL org.opencontainers.image.title="HebloMCP"
LABEL org.opencontainers.image.description="MCP server for Heblo application"
LABEL org.opencontainers.image.version="0.1.0"
