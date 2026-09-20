import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

DEFAULT_STORE_PATH = Path.home() / ".claude" / "claude-rating-tool" / "ratings.json"


class InvalidStoreError(Exception):
    """The ratings file exists but is not valid JSON, has the wrong shape, or holds an out-of-range value."""


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def valid_rating_value(value) -> bool:
    return _is_int(value) and 1 <= value <= 10


def _validate(data) -> Dict[str, dict]:
    if not isinstance(data, dict):
        raise InvalidStoreError("ratings file is not a JSON object")
    for prompt_id, entry in data.items():
        if not isinstance(entry, dict):
            raise InvalidStoreError(f"entry {prompt_id!r} is not an object")
        if not valid_rating_value(entry.get("value")):
            raise InvalidStoreError(f"entry {prompt_id!r} has a value outside 1-10")
        if not isinstance(entry.get("session_id"), str):
            raise InvalidStoreError(f"entry {prompt_id!r} is missing session_id")
        if not _is_int(entry.get("position")) or entry["position"] < 0:
            raise InvalidStoreError(f"entry {prompt_id!r} has an invalid position")
        if not isinstance(entry.get("rated_at"), str):
            raise InvalidStoreError(f"entry {prompt_id!r} is missing rated_at")
    return data


class RatingsStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_STORE_PATH
        self._lock = threading.Lock()

    def load(self) -> Dict[str, dict]:
        """Return all ratings. A missing file is an empty store; an invalid one raises InvalidStoreError."""
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        except (OSError, UnicodeDecodeError) as exc:
            raise InvalidStoreError(f"ratings file could not be read: {exc}") from exc
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise InvalidStoreError("ratings file is not valid JSON") from exc
        return _validate(data)

    def get(self, prompt_id: str) -> Optional[dict]:
        return self.load().get(prompt_id)

    def set(self, prompt_id: str, session_id: str, position: int, value: int) -> dict:
        if not valid_rating_value(value):
            raise ValueError("value must be an integer from 1 to 10")
        with self._lock:
            data = self.load()
            record = {
                "session_id": session_id,
                "position": position,
                "value": value,
                "rated_at": datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            }
            data[prompt_id] = record
            self._write(data)
        return dict(record, prompt_id=prompt_id)

    def reset(self) -> None:
        """Delete the ratings file. Succeeds if the file is already absent."""
        with self._lock:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass

    def _write(self, data: Dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(self.path.parent), prefix=".ratings-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            os.replace(tmp_name, self.path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
