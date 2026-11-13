#!/bin/sh
# start.sh
# Container entrypoint — injects API_BASE into web/index.html at startup,
# then launches the FastAPI bridge server.
#
# When deployed on Railway, RAILWAY_PUBLIC_DOMAIN is set automatically to the
# app's public hostname (e.g. golden-gate-glory-production.up.railway.app).
# API_BASE can also be set explicitly to override.
#
# If neither is set the HTML is left as-is (USE_MOCK = true stays in place).

set -e

INDEX="web/index.html"

# Debug: print relevant env vars so Railway deployment logs show what was found
echo "start.sh: RAILWAY_PUBLIC_DOMAIN=${RAILWAY_PUBLIC_DOMAIN:-<not set>}"
echo "start.sh: API_BASE=${API_BASE:-<not set>}"
echo "start.sh: PORT=${PORT:-<not set>}"

# Determine the public URL of this container.
# Priority: explicit API_BASE > RAILWAY_PUBLIC_DOMAIN (set automatically by Railway)
if [ -z "$API_BASE" ] && [ -n "$RAILWAY_PUBLIC_DOMAIN" ]; then
  API_BASE="https://${RAILWAY_PUBLIC_DOMAIN}"
  echo "start.sh: derived API_BASE from RAILWAY_PUBLIC_DOMAIN → ${API_BASE}"
fi

if [ -n "$API_BASE" ]; then
  echo "start.sh: injecting API_BASE=${API_BASE} and enabling live mode"
  # Inject window.API_BASE just before </head>
  sed -i "s|</head>|<script>window.API_BASE='${API_BASE}';</script></head>|" "$INDEX"
  # Flip USE_MOCK to false
  sed -i "s|const USE_MOCK = true;.*|const USE_MOCK = false; // live mode via bridge server|" "$INDEX"
  echo "start.sh: injection complete"
else
  echo "start.sh: no API_BASE set — leaving USE_MOCK = true (mock mode)"
fi

# Start the FastAPI bridge server
# Railway sets PORT dynamically; default to 8080 for local/Docker use
echo "start.sh: starting uvicorn on port ${PORT:-8080}"
exec uvicorn src.server:app --host 0.0.0.0 --port "${PORT:-8080}"
