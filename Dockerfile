# Multi-stage Dockerfile for crypto trading bot
# Stage 1: Build stage
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-prod.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements-prod.txt

# Stage 2: Runtime stage
FROM python:3.12-slim as runtime

# Install runtime dependencies and security updates
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    tini \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r trading && useradd -r -g trading -u 1000 trading

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=trading:trading src/ ./src/
COPY --chown=trading:trading config/ ./config/
COPY --chown=trading:trading scripts/ ./scripts/
COPY --chown=trading:trading main.py ./

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/temp && \
    chown -R trading:trading /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO \
    TZ=UTC

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Switch to non-root user
USER trading

# Use tini as entrypoint to handle signals properly
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command
CMD ["python", "main.py"]

# Labels for metadata
LABEL maintainer="DevOps Team <devops@company.com>" \
      version="1.0.0" \
      description="Enterprise Crypto Trading Bot" \
      org.opencontainers.image.source="https://github.com/company/crypto-trading-bot" \
      org.opencontainers.image.vendor="Company Inc." \
      org.opencontainers.image.licenses="Proprietary"