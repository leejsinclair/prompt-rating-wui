import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

DEFAULT_FAVORITES_PATH = Path.home() / ".claude" / "claude-rating-tool" / "favorites.json"


class InvalidFavoritesStoreError(Exception):
    """The favorites file exists but is not valid JSON or has the wrong shape."""


def _valid_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate(data) -> Dict[str, dict]:
    if not isinstance(data, dict):
        raise InvalidFavoritesStoreError("favorites file is not a JSON object")
    for favorite_prompt_id, entry in data.items():
        if not isinstance(entry, dict):
            raise InvalidFavoritesStoreError(f"entry {favorite_prompt_id!r} is not an object")
        if not _valid_text(entry.get("text")):
            raise InvalidFavoritesStoreError(f"entry {favorite_prompt_id!r} has invalid text")
        if not isinstance(entry.get("created_at"), str):
            raise InvalidFavoritesStoreError(f"entry {favorite_prompt_id!r} is missing created_at")
        if not isinstance(entry.get("updated_at"), str):
            raise InvalidFavoritesStoreError(f"entry {favorite_prompt_id!r} is missing updated_at")
    return data


class FavoritePromptsStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_FAVORITES_PATH
        self._lock = threading.Lock()

    def load(self) -> Dict[str, dict]:
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        except UnicodeDecodeError as exc:
            raise InvalidFavoritesStoreError(f"favorites file could not be read: {exc}") from exc
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise InvalidFavoritesStoreError("favorites file is not valid JSON") from exc
        return _validate(data)

    def create(self, text: str) -> dict:
        if not _valid_text(text):
            raise ValueError("text must be a non-empty string")
        with self._lock:
            data = self.load()
            now = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
            favorite_prompt_id = str(uuid.uuid4())
            record = {
                "text": text,
                "created_at": now,
                "updated_at": now,
            }
            data[favorite_prompt_id] = record
            self._write(data)
        return dict(record, favorite_prompt_id=favorite_prompt_id)

    def update(self, favorite_prompt_id: str, text: str) -> dict:
        if not _valid_text(text):
            raise ValueError("text must be a non-empty string")
        with self._lock:
            data = self.load()
            current = data.get(favorite_prompt_id)
            if current is None:
                raise KeyError(favorite_prompt_id)
            record = {
                "text": text,
                "created_at": current["created_at"],
                "updated_at": datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            }
            data[favorite_prompt_id] = record
            self._write(data)
        return dict(record, favorite_prompt_id=favorite_prompt_id)

    def reset(self) -> None:
        with self._lock:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass

    def _write(self, data: Dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(self.path.parent), prefix=".favorites-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            os.replace(tmp_name, self.path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
