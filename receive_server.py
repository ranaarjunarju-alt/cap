#!/usr/bin/env python3
"""Tiny file-receiver for the APK relay.
POST /upload/<name>  -> save body to /tmp/upload/<name>
GET  /health         -> 200 ok
GET  /<name>         -> serve file from /tmp/upload/<name>
"""
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UP = "/tmp/upload"
os.makedirs(UP, exist_ok=True)
MAX = 200 * 1024 * 1024  # 200MB per file cap


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        with open("/tmp/upload/server.log", "a") as f:
            f.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code, body=b"", ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/health", "/"):
            return self._send(200, b"ok")
        name = os.path.basename(self.path)
        p = os.path.join(UP, name)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                data = f.read()
            return self._send(200, data)
        return self._send(404, b"not found")

    def do_POST(self):
        name = os.path.basename(self.path.split("?", 1)[0])
        if not name.startswith("part.") and name not in ("log.txt", "report.txt", "probe.txt"):
            return self._send(400, b"bad name")
        p = os.path.join(UP, name)
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX:
            return self._send(413, b"too big")
        total = 0
        with open(p, "wb") as out:
            while total < length:
                chunk = self.rfile.read(min(1 << 20, length - total))
                if not chunk:
                    break
                out.write(chunk)
                total += len(chunk)
        with open("/tmp/upload/server.log", "a") as f:
            f.write("SAVED %s %d bytes\n" % (name, total))
        self._send(200, ("saved %d" % total).encode())


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", 8000), H)
    print("relay receiver on :8000", flush=True)
    srv.serve_forever()
