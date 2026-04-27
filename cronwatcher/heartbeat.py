"""Heartbeat receiver for cron job check-ins via HTTP."""

from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class HeartbeatHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that accepts GET /ping/<job_name>."""

    on_ping: Callable[[str], None]  # injected by HeartbeatServer

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "ping":
            job_name = parts[1]
            self.on_ping(job_name)
            self._respond(200, f"OK: {job_name}\n")
        else:
            self._respond(404, "Not found\n")

    def _respond(self, code: int, body: str) -> None:
        encoded = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt: str, *args: object) -> None:  # silence default stderr
        logger.debug(fmt, *args)


class HeartbeatServer:
    """Runs a lightweight HTTP server in a background thread."""

    def __init__(self, host: str, port: int, on_ping: Callable[[str], None]) -> None:
        self._on_ping = on_ping
        handler = type(
            "_Handler",
            (HeartbeatHandler,),
            {"on_ping": staticmethod(on_ping)},
        )
        self._server = HTTPServer((host, port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> None:
        logger.info("Heartbeat server starting on %s", self._server.server_address)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._thread.join(timeout=5)
        logger.info("Heartbeat server stopped")
