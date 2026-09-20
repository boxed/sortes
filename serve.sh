#!/bin/bash
# Serve the app locally. Any static file server works in production; this one
# exists to say no-store, because the data files are rebuilt under a running
# browser and a cached manifest.json pointing at a text that no longer exists
# fails as a 404 on a chunk, several steps from the cause.
cd "$(dirname "$0")"
exec python3 - "${1:-8099}" <<'PY'
import functools, http.server, sys


class Fresh(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        super().end_headers()

    def log_message(self, form, *args):      # one line per request is plenty
        sys.stderr.write('%s %s\n' % (self.address_string(), form % args))


port = int(sys.argv[1])
print(f'http://localhost:{port}')
http.server.ThreadingHTTPServer(('', port), Fresh).serve_forever()
PY
