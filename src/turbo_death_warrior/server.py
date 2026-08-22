"""Serve Turbo Death Warrior in the browser.

Usage:
    python3 server.py            # http://localhost:8001 (or see .env)

Configuration is read from a .env file next to this script (TDW_HOST,
TDW_PORT). Variables already present in the real environment take
precedence. Standard library only - no third-party packages required.
"""

import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from turbo_death_warrior.game_engine import Game

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def _load_env(path=ENV_FILE):
    """Load KEY=VALUE pairs from .env; existing env vars are not overridden."""
    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and " " not in key and key not in os.environ:
            os.environ[key] = value


_load_env()

HOST = os.environ.get("TDW_HOST", "127.0.0.1")
PORT = int(os.environ.get("TDW_PORT", "8001"))
WEB_DIR = Path(__file__).resolve().parents[1] / "web"

GAMES = {}
LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # --- helpers ------------------------------------------------------

    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, message):
        self._json(code, {"error": message})

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return {}

    # --- routes -------------------------------------------------------

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                html = (WEB_DIR / "index.html").read_bytes()
            except FileNotFoundError:
                return self._error(500, "web/index.html is missing")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        self._error(404, "not found")

    def do_POST(self):
        if self.path == "/api/game":
            gid = secrets.token_hex(8)
            game = Game()
            with LOCK:
                GAMES[gid] = game
            payload = game.start()
            payload["game_id"] = gid
            return self._json(200, payload)

        parts = self.path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "game"]:
            _, _, gid, op = parts
            with LOCK:
                game = GAMES.get(gid)
                if game is None:
                    return self._error(404, "unknown game - refresh to start a new one")
                body = self._body()
                if op == "action":
                    payload = game.act(str(body.get("id", "")))
                elif op == "name":
                    payload = game.submit_name(str(body.get("name", "")))
                else:
                    return self._error(404, "unknown operation")
            return self._json(200, payload)

        self._error(404, "not found")


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print("=" * 46)
    print("   TURBO DEATH WARRIOR - web edition")
    print(f"   Serving on http://{HOST}:{PORT}  (Ctrl+C to stop)")
    print("=" * 46)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down. Farewell, warrior.")
        server.server_close()


if __name__ == "__main__":
    main()
