# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv "$VIRTUAL_ENV"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/*

RUN python - <<'PY'
import os
import shutil
import tarfile
import tempfile
import urllib.request

url = 'https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-x86_64-100.13.0.tgz'
target_dir = '/opt/mongodb-database-tools'

with tempfile.TemporaryDirectory() as temp_dir:
    archive_path = os.path.join(temp_dir, 'mongodb-database-tools.tgz')
    urllib.request.urlretrieve(url, archive_path)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    with tarfile.open(archive_path, 'r:gz') as archive:
        archive.extractall(target_dir)
    nested_dirs = [
        os.path.join(target_dir, name)
        for name in os.listdir(target_dir)
        if os.path.isdir(os.path.join(target_dir, name))
    ]
    source_root = nested_dirs[0] if nested_dirs else target_dir
    for binary in ('mongodump', 'mongorestore'):
        source = os.path.join(source_root, 'bin', binary)
        destination = os.path.join('/usr/local/bin', binary)
        shutil.copy2(source, destination)
        os.chmod(destination, 0o755)
PY

# Copy Python dependencies from builder
COPY --from=builder /opt/venv /opt/venv

# Copy backend application code
COPY backend ./backend

# Set environment variables
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8808/health', timeout=5)" || exit 1

# Run application
CMD ["python", "backend/run.py"]
