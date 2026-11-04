# PatchPilot Production Backend Dockerfile
# Optimized for Railway and Containerized Deployments
# Multi-arch compatible (x86_64 & arm64)

FROM python:3.12-slim-bookworm

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install system dependencies: OpenJDK 17, Apache Maven, Git, and networking tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless \
    maven \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up JAVA_HOME dynamically for both x86_64 and aarch64
RUN JAVA_BIN=$(readlink -f $(which javac)) && \
    JAVA_DIR=$(dirname $(dirname "$JAVA_BIN")) && \
    mkdir -p /usr/lib/jvm && \
    ln -s "$JAVA_DIR" /usr/lib/jvm/java-17-current

ENV JAVA_HOME=/usr/lib/jvm/java-17-current
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Install Python runtime dependencies
COPY requirements-api.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-api.txt

# Copy repository source code
COPY . .

# Compile JavaAstParser tool into bytecode during image construction
RUN javac -d /app/migration_engine/analyzers /app/migration_engine/analyzers/tools/JavaAstParser.java

# Healthcheck to verify FastAPI responds on /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8000}/health || exit 1

# Expose default port
EXPOSE 8000

# Start Uvicorn listening on 0.0.0.0 and Railway's injected $PORT
CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
