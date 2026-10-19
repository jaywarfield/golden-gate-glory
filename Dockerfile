# Dockerfile
# Mission Veteran AI
#
# Serves the static front-end with Python's built-in HTTP server.
# No dependencies to install — uses the stdlib only.
#
# Build:
#   docker build -t golden-gate-glory-web:latest .
#
# Run:
#   docker run --rm -p 8080:8080 golden-gate-glory-web:latest

FROM python:3.11-slim

WORKDIR /app

# Copy only the static web files
COPY web/index.html ./index.html

EXPOSE 8080

CMD ["python", "-m", "http.server", "8080"]
