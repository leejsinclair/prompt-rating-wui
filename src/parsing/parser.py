import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class Prompt:
    prompt_id: str
    session_id: str
    position: int
    text: str
    timestamp: Optional[str]
    response_text: str = ""
    activity_summary: Optional[str] = None
    duration_seconds: Optional[int] = None


@dataclass
class Session:
    session_id: str
    file_path: str
    project_path: Optional[str] = None
    started_at: Optional[str] = None
    last_activity_at: Optional[str] = None
    prompts: List[Prompt] = field(default_factory=list)
    is_parseable: bool = True
    error: Optional[str] = None
    parse_warnings: List[str] = field(default_factory=list)

    @property
    def prompt_count(self) -> int:
        return len(self.prompts)


class _Turn:
    """Accumulates the assistant activity that follows one prompt."""

    def __init__(self) -> None:
        self.texts: List[str] = []
        self.tool_uses = 0
        self.has_thinking = False
        self.last_timestamp: Optional[str] = None

    def add(self, content) -> None:
        if not isinstance(content, list):
            return
        for block in content:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "text":
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    self.texts.append(text)
            elif kind == "tool_use":
                self.tool_uses += 1
            elif kind == "thinking":
                self.has_thinking = True

    def summary(self) -> Optional[str]:
        if self.tool_uses:
            noun = "tool" if self.tool_uses == 1 else "tools"
            suffix = ", with reasoning" if self.has_thinking else ""
            return f"used {self.tool_uses} {noun}{suffix}"
        if self.has_thinking:
            return "internal reasoning"
        return None


def _seconds_between(start: Optional[str], end: Optional[str]) -> Optional[int]:
    if not start or not end:
        return None
    try:
        a = datetime.fromisoformat(start.replace("Z", "+00:00"))
        b = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0, round((b - a).total_seconds()))


def _is_real_prompt(obj: dict) -> bool:
    if obj.get("type") != "user":
        return False
    if obj.get("isMeta") or obj.get("isSidechain"):
        return False
    message = obj.get("message")
    return isinstance(message, dict) and isinstance(message.get("content"), str)


def _finish(prompt: Optional[Prompt], turn: Optional[_Turn]) -> None:
    if prompt is None or turn is None:
        return
    prompt.response_text = "\n\n".join(turn.texts)
    prompt.activity_summary = turn.summary()
    prompt.duration_seconds = _seconds_between(prompt.timestamp, turn.last_timestamp)


def parse_session_file(path) -> Session:
    """Parse one session .jsonl into a Session. Malformed lines are skipped per-line, never per-file."""
    path = Path(path)
    session = Session(session_id=path.stem, file_path=str(path))
    try:
        handle = path.open("r", encoding="utf-8", errors="replace")
    except OSError as exc:
        session.is_parseable = False
        session.error = f"Could not open session file ({exc.strerror or 'read error'})."
        return session

    seen_ids = set()
    current: Optional[Prompt] = None
    turn: Optional[_Turn] = None
    skipped = 0

    with handle:
        try:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except ValueError:
                    skipped += 1
                    continue
                if not isinstance(obj, dict):
                    skipped += 1
                    continue

                timestamp = obj.get("timestamp")
                if isinstance(timestamp, str):
                    session.last_activity_at = timestamp
                cwd = obj.get("cwd")
                if session.project_path is None and isinstance(cwd, str):
                    session.project_path = cwd

                if _is_real_prompt(obj):
                    _finish(current, turn)
                    position = len(session.prompts)
                    prompt_id = obj.get("promptId")
                    if not isinstance(prompt_id, str) or not prompt_id or prompt_id in seen_ids:
                        prompt_id = f"{session.session_id}:{position}"
                    seen_ids.add(prompt_id)
                    current = Prompt(
                        prompt_id=prompt_id,
                        session_id=session.session_id,
                        position=position,
                        text=obj["message"]["content"],
                        timestamp=timestamp if isinstance(timestamp, str) else None,
                    )
                    turn = _Turn()
                    session.prompts.append(current)
                    if session.started_at is None:
                        session.started_at = current.timestamp
                elif obj.get("type") == "assistant" and turn is not None and not obj.get("isSidechain"):
                    message = obj.get("message")
                    if isinstance(message, dict):
                        turn.add(message.get("content"))
                        if isinstance(timestamp, str):
                            turn.last_timestamp = timestamp
        except OSError as exc:
            session.is_parseable = False
            session.error = f"Could not read session file ({exc.strerror or 'read error'})."
            session.prompts = []
            return session

    _finish(current, turn)
    if skipped:
        session.parse_warnings.append(f"{skipped} malformed line(s) skipped")
    if session.last_activity_at is None:
        try:
            mtime = path.stat().st_mtime
            session.last_activity_at = (
                datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            )
        except OSError:
            pass
    return session
