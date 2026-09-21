import json
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qs

from src.favorites import FavoritePromptsStore, InvalidFavoritesStoreError
from src.discovery import discover_session_files
from src.parsing import Session, parse_session_file
from src.ratings import InvalidStoreError, RatingsStore

PAGE_SIZE = 20
MAX_CHARS = 2000
MAX_WORDS = 500
INVALID_STORE_MESSAGE = "The local ratings file is invalid. Reset it to start over with empty ratings."
INVALID_FAVORITES_STORE_MESSAGE = "The local favorites file is invalid. Reset it to start over with empty favorites."
_TAG_RE = re.compile(r"<[^>]+>")
_COMMAND_BLOCK_RE = re.compile(
    r"(?:<command-name>|&lt;command-name&gt;)(?P<name>.*?)(?:</command-name>|&lt;/command-name&gt;)\s*"
    r"(?:<command-message>|&lt;command-message&gt;)(?P<message>.*?)(?:</command-message>|&lt;/command-message&gt;)\s*"
    r"(?:<command-args>|&lt;command-args&gt;)(?P<args>.*?)(?:</command-args>|&lt;/command-args&gt;)",
    re.DOTALL,
)


class ApiError(Exception):
    def __init__(self, status: int, message: str, **extra) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.extra = extra


def invalid_store_error() -> ApiError:
    return ApiError(409, INVALID_STORE_MESSAGE, ratings_invalid=True)


def invalid_favorites_store_error() -> ApiError:
    return ApiError(409, INVALID_FAVORITES_STORE_MESSAGE, favorites_invalid=True)


@dataclass(init=False)
class Context:
    store: RatingsStore
    projects_root: Optional[Path] = None
    static_dir: Optional[Path] = None
    now: Optional[datetime] = None
    favorites_store: FavoritePromptsStore = field(default_factory=FavoritePromptsStore)

    def __init__(
        self,
        store: RatingsStore,
        projects_root: Optional[Path] = None,
        static_dir: Optional[Path] = None,
        now: Optional[datetime] = None,
        *,
        favorites_store: Optional[FavoritePromptsStore] = None,
    ) -> None:
        self.store = store
        self.projects_root = projects_root
        self.static_dir = static_dir
        self.now = now
        self.favorites_store = favorites_store or FavoritePromptsStore()


@dataclass
class Request:
    params: Dict[str, str] = field(default_factory=dict)
    query: Dict[str, list] = field(default_factory=dict)
    body: bytes = b""

    def page(self) -> int:
        try:
            return max(1, int(self.query.get("page", ["1"])[0]))
        except ValueError:
            return 1

    def json(self) -> dict:
        try:
            data = json.loads(self.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "Request body must be valid JSON.")
        if not isinstance(data, dict):
            raise ApiError(400, "Request body must be a JSON object.")
        return data


def parse_query(raw: str) -> Dict[str, list]:
    return parse_qs(raw, keep_blank_values=True)


def truncate_text(text: str) -> Tuple[str, bool]:
    """Apply the FR-013 rule: over ~500 words or ~2000 characters is cut short."""
    if len(text) <= MAX_CHARS and len(text.split()) <= MAX_WORDS:
        return text, False
    cut = text[:MAX_CHARS]
    if len(text) > MAX_CHARS and not text[MAX_CHARS].isspace():
        boundary = max(cut.rfind(" "), cut.rfind("\n"), cut.rfind("\t"))
        if boundary > 0:
            cut = cut[:boundary]
    words = list(re.finditer(r"\S+", cut))
    if len(words) > MAX_WORDS:
        cut = cut[: words[MAX_WORDS - 1].end()]
    return cut.rstrip(), True


def strip_markup(text: str) -> str:
    return _TAG_RE.sub("", unescape(text))


def humanize_command_markup(text: str) -> str:
    def replace(match) -> str:
        name = strip_markup(match.group("name")).strip()
        message = strip_markup(match.group("message")).strip()
        args = strip_markup(match.group("args")).strip()
        command = " ".join(part for part in (name, args) if part).strip()
        if message and message not in {command, command.lstrip("/")}:
            return f"{command} — {message}" if command else message
        return command or message

    return _COMMAND_BLOCK_RE.sub(replace, text)


def now_utc(ctx: Context) -> datetime:
    return ctx.now or datetime.now(timezone.utc)


def session_files(ctx: Context) -> Dict[str, Path]:
    files: Dict[str, Path] = {}
    for path in discover_session_files(ctx.projects_root):
        files.setdefault(path.stem, path)
    return files


def load_session(ctx: Context, session_id: str) -> Session:
    path = session_files(ctx).get(session_id)
    if path is None:
        raise ApiError(404, "Session not found.")
    return parse_session_file(path)


def load_ratings(ctx: Context) -> Tuple[Dict[str, dict], bool]:
    """Return (ratings, invalid). An invalid store yields no ratings plus invalid=True."""
    try:
        return ctx.store.load(), False
    except InvalidStoreError:
        return {}, True


def load_favorites(ctx: Context) -> Tuple[Dict[str, dict], bool]:
    """Return (favorites, invalid). An invalid store yields no favorites plus invalid=True."""
    try:
        return ctx.favorites_store.load(), False
    except InvalidFavoritesStoreError:
        return {}, True
