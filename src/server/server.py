import json
import re
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit

from src.favorites import FavoritePromptsStore
from src.ratings import RatingsStore
from src.server.common import ApiError, Context, Request, parse_query
from src.server.handlers import favorites as favorites_handlers
from src.server.handlers import ratings as ratings_handlers
from src.server.handlers import sessions as session_handlers
from src.server.handlers import top_rated as top_rated_handlers

HOST = "127.0.0.1"
PORT = 5148
DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"
MAX_BODY_BYTES = 64 * 1024
LOCAL_HOSTNAMES = {"127.0.0.1", "localhost", "[::1]"}

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

# Route dispatch: (method, path pattern, handler). US1, US2 and US3 each append their routes here.
ROUTES = [
    ("GET", re.compile(r"^/api/sessions$"), session_handlers.list_sessions),
    ("GET", re.compile(r"^/api/favorites$"), favorites_handlers.list_favorites),
    ("POST", re.compile(r"^/api/favorites$"), favorites_handlers.create_favorite),
    (
        "PUT",
        re.compile(r"^/api/favorites/(?P<favorite_prompt_id>[^/]+)$"),
        favorites_handlers.update_favorite,
    ),
    ("POST", re.compile(r"^/api/favorites/reset$"), favorites_handlers.reset_favorites),
    ("GET", re.compile(r"^/api/prompts/search$"), session_handlers.search_prompts),
    ("GET", re.compile(r"^/api/sessions/(?P<session_id>[^/]+)$"), session_handlers.get_session),
    (
        "GET",
        re.compile(r"^/api/sessions/(?P<session_id>[^/]+)/prompts/(?P<prompt_id>[^/]+)$"),
        session_handlers.get_prompt,
    ),
    ("PUT", re.compile(r"^/api/ratings/(?P<prompt_id>[^/]+)$"), ratings_handlers.put_rating),
    ("GET", re.compile(r"^/api/top-rated$"), top_rated_handlers.get_top_rated),
    ("POST", re.compile(r"^/api/ratings/reset$"), ratings_handlers.reset_ratings),
]


def _hostname(value: str) -> str:
    """Hostname part of a Host header or Origin URL value, lowercased, without port."""
    value = value.strip().lower()
    if "://" in value:
        value = urlsplit(value).netloc
    if value.startswith("["):
        return value.split("]")[0] + "]"
    return value.split(":")[0]


def make_handler(ctx: Context):
    static_dir = (ctx.static_dir or DEFAULT_STATIC_DIR).resolve()

    class Handler(BaseHTTPRequestHandler):
        server_version = "ConversationReview"
        sys_version = ""

        def log_message(self, fmt, *args):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _send_json(self, status: int, payload: dict) -> None:
            self._send(status, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

        def _send_error(self, status: int, message: str, **extra) -> None:
            self._send_json(status, dict({"error": message}, **extra))

        def _guard(self) -> bool:
            """Reject requests that did not come from a page served from this machine (DNS rebinding / CSRF)."""
            host = self.headers.get("Host", "")
            if _hostname(host) not in LOCAL_HOSTNAMES:
                self._send_error(403, "Requests must be made to localhost.")
                return False
            origin = self.headers.get("Origin")
            if origin and _hostname(origin) not in LOCAL_HOSTNAMES:
                self._send_error(403, "Cross-origin requests are not allowed.")
                return False
            return True

        def _serve_static(self, path: str) -> None:
            name = "index.html" if path in ("", "/") else unquote(path).lstrip("/")
            target = (static_dir / name).resolve()
            if static_dir not in target.parents or not target.is_file():
                self._send_error(404, "Not found.")
                return
            content_type = CONTENT_TYPES.get(target.suffix.lower(), "application/octet-stream")
            try:
                body = target.read_bytes()
            except OSError:
                self._send_error(404, "Not found.")
                return
            self._send(200, body, content_type)

        def _dispatch(self) -> None:
            if not self._guard():
                return
            parts = urlsplit(self.path)
            path = parts.path
            try:
                if path.startswith("/api/"):
                    allowed = False
                    for method, pattern, handler in ROUTES:
                        match = pattern.match(path)
                        if not match:
                            continue
                        allowed = True
                        if method != self.command:
                            continue
                        body = b""
                        if method in ("PUT", "POST"):
                            length = int(self.headers.get("Content-Length") or 0)
                            if length > MAX_BODY_BYTES:
                                raise ApiError(413, "Request body is too large.")
                            body = self.rfile.read(length) if length else b""
                        request = Request(
                            params={k: unquote(v) for k, v in match.groupdict().items()},
                            query=parse_query(parts.query),
                            body=body,
                        )
                        status, payload = handler(ctx, request)
                        self._send_json(status, payload)
                        return
                    raise ApiError(405 if allowed else 404, "Method not allowed." if allowed else "Not found.")
                if self.command not in ("GET", "HEAD"):
                    raise ApiError(405, "Method not allowed.")
                self._serve_static(path)
            except ApiError as exc:
                self._send_error(exc.status, exc.message, **exc.extra)
            except (ValueError, TypeError):
                self._send_error(400, "Bad request.")
            except Exception:
                traceback.print_exc()
                self._send_error(500, "Something went wrong on the server.")

        do_GET = do_HEAD = do_PUT = do_POST = do_DELETE = _dispatch

    return Handler


def create_server(ctx: Optional[Context] = None, host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    ctx = ctx or Context(store=RatingsStore(), favorites_store=FavoritePromptsStore())
    server = ThreadingHTTPServer((host, port), make_handler(ctx))
    server.daemon_threads = True
    return server


def main() -> int:
    try:
        server = create_server()
    except OSError as exc:
        print(f"Could not start on http://{HOST}:{PORT} ({exc.strerror}). Is another copy already running?", file=sys.stderr)
        return 1
    print(f"Serving on http://{HOST}:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
