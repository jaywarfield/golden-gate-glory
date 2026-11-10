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

FROM python:3.11-slim

WORKDIR /app

# System deps (none beyond python-slim defaults needed for this stack)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./requirements.txt
COPY src/requirements.txt ./src/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r src/requirements.txt

# Copy project source
COPY src/       ./src/
COPY toolkits/  ./toolkits/
COPY knowledge-bases/ ./knowledge-bases/
COPY web/       ./web/

EXPOSE 8080

# Run the FastAPI bridge server
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8080"]
