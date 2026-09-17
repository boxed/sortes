#!/bin/bash
# Serve the app locally. Any static file server works; the data is plain JSON.
cd "$(dirname "$0")"
exec python3 -m http.server "${1:-8099}"
