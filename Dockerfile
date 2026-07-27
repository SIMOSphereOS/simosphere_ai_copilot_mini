# SIMOSphere AI Copilot Mini — self-contained ExApp image.
# Bakes the embedding model (e5-large, CPU) AND the prebuilt Nextcloud-docs index into the image,
# so the app runs fully offline: the only outbound call at runtime is to the user's chosen LLM.
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/models \
    COPILOT_MINI_DATA=/app/data \
    APP_HOST=0.0.0.0 \
    APP_PORT=9034

WORKDIR /app

# CPU-only torch first, so the heavy CUDA wheels are never pulled in by sentence-transformers.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Python deps from the project metadata.
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install "nc_py_api>=0.30" . && python -c "import copilot_mini; print(copilot_mini.__version__)"

# Bake the embedding model into the image (network only during build).
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('intfloat/multilingual-e5-large')"

# Prebuilt, self-contained knowledge index (CC BY 3.0 Nextcloud docs).
COPY data/ ./data/

# Run offline from here on — model + index are baked in.
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1

EXPOSE 9034
ENTRYPOINT ["python", "-m", "copilot_mini.app"]
