# Build from the repo root:  docker build -f apps/api/Dockerfile -t redactd-api .
# Model files must be present first:  bash scripts/fetch_models.sh   (see docs/DEPLOY.md)
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv
# CPU-only torch first: the gliner package imports it (GLiNER itself runs on ONNX Runtime), so pip must not pull CUDA wheels
# The optional `ca_bundle` secret is only for builds behind a TLS-inspecting proxy (see docs/DEPLOY.md). It is
# mounted for the pip steps and never stored in an image layer; normal builds (Fly, CI) simply don't pass it.
RUN --mount=type=secret,id=ca_bundle,required=false \
    sh -c '[ -f /run/secrets/ca_bundle ] && export PIP_CERT=/run/secrets/ca_bundle; pip install torch --index-url https://download.pytorch.org/whl/cpu'
COPY apps/api/requirements.txt .
RUN --mount=type=secret,id=ca_bundle,required=false \
    sh -c '[ -f /run/secrets/ca_bundle ] && export PIP_CERT=/run/secrets/ca_bundle; pip install -r requirements.txt'
COPY redactd/ redactd/
COPY apps/api/app/ apps/api/app/
COPY apps/api/alembic/ apps/api/alembic/
COPY apps/api/alembic.ini apps/api/alembic.ini
# Models are baked into the image; only the int8 files are copied (.dockerignore keeps everything else out).
# Production modes: Standard = distilled, Thorough = distilled + GLiNER. OpenMed is not shipped.
COPY browser/models/redactd-small/ /models/redactd-small/
COPY browser/models/gliner/ /models/gliner/
ENV DISTILLED_DIR=/models/redactd-small GLINER_DIR=/models/gliner OPENMED_DIR="" \
    REDACTD_STANDARD=distilled REDACTD_THOROUGH=distilled,gliner \
    PRELOAD_MODES=thorough HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN useradd -r -u 10001 app && chown -R app /srv
USER app
WORKDIR /srv/apps/api
EXPOSE 8000
# No core dumps (a dump would contain document text held in memory)
CMD ["sh", "-c", "ulimit -c 0 && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log --proxy-headers --forwarded-allow-ips='*'"]
