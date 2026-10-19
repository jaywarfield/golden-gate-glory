"""
web/app.py
Mission Veteran AI

Serves the static web/index.html on port 8080 using the stdlib HTTP server.
No Flask, no proxy, no external dependencies — mock mode only.

Run:
    python web/app.py
    python web/app.py 9000   # optional port override
"""

import http.server
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8080))

# Serve files from the same directory as this script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

handler = http.server.SimpleHTTPRequestHandler

print(f"Serving on http://0.0.0.0:{PORT}")
with http.server.HTTPServer(("0.0.0.0", PORT), handler) as httpd:
    httpd.serve_forever()
