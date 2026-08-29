# AppSail custom runtime (fallback when the managed Python runtime can't fit the
# scientific stack). Build for linux/amd64. The DuckDB mirror is bundled (built by
# `python -m data_engine.build` beforehand) so the service starts with data and
# needs no torch/sentence-transformers at runtime (embeddings are precomputed).
#
#   python -m data_engine.build                     # produces build/anveshak.duckdb
#   docker build --platform linux/amd64 -t anveshak-api -f backend/Dockerfile .
#
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Compilers are needed only while pip builds wheels. Install and REMOVE them in the
# SAME layer — a later purge cannot shrink an earlier layer, and 322MB of toolchain
# would otherwise ship. Deploy uploads the whole archive, so image size is deploy
# time: the 755MB tar stopped landing on Catalyst at all.
COPY requirements.txt ./requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip install -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/* /root/.cache /tmp/*

COPY backend ./backend
COPY data_engine ./data_engine
COPY schema ./schema
# Ship the VERIFIED SNAPSHOT, never the live build/anveshak.duckdb: that file is
# the one local tests and dev servers write to, and a build started while anything
# held it open once baked a torn database into the image (deployed app came up with
# db: error, cases: 0). `python scripts/stage_db.py` verifies before staging.
COPY build/deploy/anveshak.duckdb ./build/anveshak.duckdb
# Built SPA bundle, served by FastAPI at /ui (Web Client Hosting is blocked by the
# API Gateway's .html interception; the AppSail domain serves it cleanly).
COPY frontend/dist ./frontend/dist
# ONNX MiniLM for runtime embedding of NEW text (FIR intake, free-text similarity).
# Produced by `python scripts/fetch_onnx_model.py` before the build.
COPY models/minilm-onnx ./models/minilm-onnx

ENV DUCKDB_PATH=build/anveshak.duckdb \
    LLM_BACKEND=quickml \
    AGENTS_RUNNER=local \
    ENVIRONMENT=prod

# Catalyst injects X_ZOHO_CATALYST_LISTEN_PORT; bind 0.0.0.0 on it (fallback 9000).
# Run the SAME entrypoint app-config.json declares. These used to disagree — the
# image ran uvicorn directly while Catalyst was told `python -m backend.serve` — so
# whether the startup work (writable DB copy, cache prewarm, audit-table repair,
# database validation) happened at all depended on which one won.
CMD ["python", "-m", "backend.serve"]
