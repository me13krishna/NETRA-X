"""
Run the testbed without Docker.

The Docker path is the full article: real Tor, a real .onion address, nginx
serving the leaky config. But every misconfiguration this testbed plants is a
property of the HTTP *response*, not of the transport -- so they can be
reproduced faithfully by a small server, and the probe cannot tell the
difference.

That makes the testbed usable before Docker is installed, and makes `verify.py`
runnable in CI without pulling images.

    python testbed/darkweb-service/serve_local.py

Serves the hidden-service content on :8081 and the clearnet twin on :8082,
matching the ports docker-compose binds. Ctrl+C to stop.

What this does NOT give you: an actual onion address, or any exercise of Tor
itself. For the infra-misconfig demo that is fine, because the module inspects
what the service returns. For anything about Tor behaviour, use Docker.
"""

import os
import sys
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))

# Mirrors nginx/onion.conf. Kept here as the single leaky-header definition so
# the two paths cannot drift apart silently.
LEAKY_HEADERS = {
    "Server": "nginx/1.24.0 (Ubuntu)",              # LEAK 3
    "X-Powered-By": "PHP/8.1.2-1ubuntu2.14",        # LEAK 4
    "Via": "1.1 vendor-edge-01.internal",           # LEAK 5
}

CLEAN_HEADERS = {
    "Server": "nginx",   # the twin behaves itself; it is findable for other reasons
}


class Handler(SimpleHTTPRequestHandler):
    extra_headers: dict = {}

    def end_headers(self):
        for k, v in self.extra_headers.items():
            self.send_header(k, v)
        super().end_headers()

    def send_response(self, code, message=None):
        # SimpleHTTPRequestHandler emits its own Server header; suppress it so
        # ours is the only one and the probe sees exactly what nginx would send.
        self.log_request(code)
        self.send_response_only(code, message)
        self.send_header("Date", self.date_time_string())

    def translate_path(self, path):
        # LEAK 2: /server-status is an extensionless route in nginx, so map it
        # onto the file the same way the alias directive does.
        if path.split("?")[0].rstrip("/") == "/server-status":
            return os.path.join(self.directory, "server-status.html")
        return super().translate_path(path)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"  {self.server.server_port}  {fmt % args}\n")


def make_handler(directory: str, headers: dict):
    cls = type("BoundHandler", (Handler,), {"extra_headers": headers})
    return partial(cls, directory=directory)


def serve(directory: str, port: int, headers: dict, label: str):
    httpd = HTTPServer(("127.0.0.1", port), make_handler(directory, headers))
    print(f"  {label:<24} http://127.0.0.1:{port}")
    httpd.serve_forever()


def main():
    print("\nNETRA-X testbed (no-Docker mode)")
    print("=" * 54)
    threads = [
        threading.Thread(target=serve, args=(os.path.join(HERE, "site"), 8081,
                                             LEAKY_HEADERS, "hidden-service content"),
                         daemon=True),
        threading.Thread(target=serve, args=(os.path.join(HERE, "clearnet-twin"), 8082,
                                             CLEAN_HEADERS, "clearnet twin"),
                         daemon=True),
    ]
    for t in threads:
        t.start()
    print("\n  No Tor, no .onion address -- the leaks are in the responses.")
    print("  Verify with:  python testbed/darkweb-service/verify.py")
    print("  Ctrl+C to stop.\n")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n  stopped\n")


if __name__ == "__main__":
    main()
