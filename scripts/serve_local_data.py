"""Lokale CORS-enabled static file server voor data/export/gepubliceerd/.

Bedoeld voor `make dev-local-data` (issue #112/#218): de frontend haalt
perspectieven/onderwerpen/tags-data normaal op van de jsDelivr-CDN-kopie van
bipolariteit-data (PUBLIC_DATA_BASE_URL, zie docs/release.md) -- die data is
pas ververst na `make publish-data`. Dit script serveert de lokale
data/export/gepubliceerd/ i.p.v. dat, zodat een nog niet gepubliceerde
exportwijziging al lokaal getest kan worden.

Gebruik:
    uv run python scripts/serve_local_data.py
    uv run python scripts/serve_local_data.py --port 8899
"""

import argparse
import functools
import http.server
from pathlib import Path

GEPUBLICEERD_DIR = Path(__file__).parent.parent / "data" / "export" / "gepubliceerd"


class CORSHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Zelfde open CORS-policy als jsDelivr hanteert voor deze data --
        # geen gevoelige data, puur al-publieke exportbestanden.
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args()

    handler = functools.partial(CORSHandler, directory=str(GEPUBLICEERD_DIR))
    print(f"Lokale data-server op http://localhost:{args.port} (serveert {GEPUBLICEERD_DIR})")
    http.server.ThreadingHTTPServer(("", args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
