# Build from the repo root:  docker build -f apps/api/Dockerfile -t redactd-api .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PRELOAD_MODES=thorough
WORKDIR /srv
# CPU-only torch first (gliner depends on it) so pip doesn't pull CUDA wheels
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY redactd/ redactd/
COPY apps/api/app/ apps/api/app/
# Models are baked into the image (or mount a volume / fetch from object storage at start)
COPY browser/models/openmed-small/ /models/openmed-small/
COPY browser/models/gliner/ /models/gliner/
ENV OPENMED_DIR=/models/openmed-small GLINER_DIR=/models/gliner
RUN useradd -r app && chown -R app /srv
USER app
WORKDIR /srv/apps/api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
