# Dockerfile
# Mission Veteran AI
#
# Runs the FastAPI bridge server which serves both the static front-end
# (GET /) and the AI API (POST /api/translate).
#
# Build:
#   docker build -t golden-gate-glory:latest .
#
# Run (pass watsonx credentials as env vars):
#   docker run --rm -p 8080:8080 \
#     -e WATSONX_API_KEY=<key> \
#     -e WATSONX_PROJECT_ID=<id> \
#     -e WATSONX_URL=https://us-south.ml.cloud.ibm.com \
#     golden-gate-glory:latest
#
# On Railway, RAILWAY_PUBLIC_DOMAIN is injected automatically by the platform.
# start.sh uses it to flip USE_MOCK=false in web/index.html before the server
# starts, so the Railway-served frontend calls the correct bridge URL.

FROM python:3.11-slim

WORKDIR /app

# System deps (none beyond python-slim defaults needed for this stack)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
# requirements.txt contains governance + RAG deps that aren't needed at
# runtime in the bridge container — install only the bridge's own deps
# plus the watsonx.ai SDK used directly by the toolkit functions.
COPY src/requirements.txt ./src/requirements.txt
RUN pip install --no-cache-dir -r src/requirements.txt

# Install toolkit runtime deps (watsonx SDK already covered above)
# Note: ibm-watsonx-orchestrate is NOT installed here — the bridge server calls
# toolkit functions directly and never needs the @tool decorator.  All 4 toolkit
# files have a try/except fallback so the import fails silently if absent.
RUN pip install --no-cache-dir \
    ibm-watsonx-ai>=1.1.0 \
    openpyxl>=3.1.0 \
    pandas>=2.0.0

# Copy project source
COPY src/       ./src/
COPY toolkits/  ./toolkits/
COPY knowledge-bases/ ./knowledge-bases/
COPY web/       ./web/
COPY start.sh   ./start.sh
RUN chmod +x start.sh

EXPOSE 8080

# start.sh injects API_BASE / flips USE_MOCK, then launches uvicorn.
# Railway sets RAILWAY_PUBLIC_DOMAIN automatically; API_BASE can also be
# set explicitly to override (e.g. for other platforms or local testing).
ENTRYPOINT ["sh", "start.sh"]
