import re
from datetime import datetime, timedelta
from typing import Tuple

from src.discovery import discover_session_files
from src.parsing import parse_session_file
from src.server.common import (
    PAGE_SIZE,
    ApiError,
    Context,
    Request,
    humanize_command_markup,
    load_ratings,
    load_session,
    now_utc,
    strip_markup,
    truncate_text,
)


def _preview(text: str, limit: int = 120) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


def list_sessions(ctx: Context, req: Request) -> Tuple[int, dict]:
    page = req.page()
    sessions = [parse_session_file(path) for path in discover_session_files(ctx.projects_root)]
    sessions = [s for s in sessions if not s.is_parseable or s.prompt_count > 0]
    sessions.sort(key=lambda s: s.last_activity_at or "", reverse=True)
    start = (page - 1) * PAGE_SIZE
    window = sessions[start : start + PAGE_SIZE]
    return 200, {
        "page": page,
        "has_more": start + PAGE_SIZE < len(sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "last_activity_at": s.last_activity_at,
                "prompt_count": s.prompt_count,
                "is_parseable": s.is_parseable,
                "project_path": s.project_path,
                "title": _preview(strip_markup(humanize_command_markup(s.prompts[0].text))) if s.prompts else None,
            }
            for s in window
        ],
    }


def get_session(ctx: Context, req: Request) -> Tuple[int, dict]:
    session = load_session(ctx, req.params["session_id"])
    ratings, ratings_invalid = load_ratings(ctx)
    payload = {
        "session_id": session.session_id,
        "project_path": session.project_path,
        "last_activity_at": session.last_activity_at,
        "is_parseable": session.is_parseable,
        "prompts": [],
    }
    if ratings_invalid:
        payload["ratings_invalid"] = True
    if not session.is_parseable:
        payload["error"] = session.error or "This session could not be read."
        return 200, payload
    for prompt in session.prompts:
        text, is_truncated = truncate_text(humanize_command_markup(prompt.text))
        rating = ratings.get(prompt.prompt_id)
        payload["prompts"].append(
            {
                "prompt_id": prompt.prompt_id,
                "position": prompt.position,
                "timestamp": prompt.timestamp,
                "text": text,
                "is_truncated": is_truncated,
                "has_response": bool(prompt.response_text.strip()),
                "activity_summary": prompt.activity_summary,
                "duration_seconds": prompt.duration_seconds,
                "rating": rating["value"] if rating else None,
            }
        )
    return 200, payload


def get_prompt(ctx: Context, req: Request) -> Tuple[int, dict]:
    session = load_session(ctx, req.params["session_id"])
    prompt_id = req.params["prompt_id"]
    prompt = next((p for p in session.prompts if p.prompt_id == prompt_id), None)
    if prompt is None:
        raise ApiError(404, "Prompt not found.")
    ratings, ratings_invalid = load_ratings(ctx)
    rating = ratings.get(prompt_id)
    payload = {
        "prompt_id": prompt.prompt_id,
        "text": humanize_command_markup(prompt.text),
        "response_text": prompt.response_text,
        "activity_summary": prompt.activity_summary,
        "duration_seconds": prompt.duration_seconds,
        "rating": rating["value"] if rating else None,
    }
    if ratings_invalid:
        payload["ratings_invalid"] = True
    return 200, payload


def _is_recent(timestamp: str, cutoff: datetime) -> bool:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed >= cutoff


def search_prompts(ctx: Context, req: Request) -> Tuple[int, dict]:
    query = req.query.get("q", [""])[0].strip()
    if not query:
        raise ApiError(400, "q is required.")

    page = req.page()
    cutoff = now_utc(ctx) - timedelta(days=7)
    needle = query.casefold()
    matches = []
    for path in discover_session_files(ctx.projects_root):
        session = parse_session_file(path)
        if not session.is_parseable:
            continue
        for prompt in session.prompts:
            if not prompt.timestamp or not _is_recent(prompt.timestamp, cutoff):
                continue
            text = humanize_command_markup(prompt.text)
            if needle not in text.casefold():
                continue
            snippet, is_truncated = truncate_text(text)
            matches.append(
                {
                    "prompt_id": prompt.prompt_id,
                    "session_id": session.session_id,
                    "position": prompt.position,
                    "timestamp": prompt.timestamp,
                    "project_path": session.project_path,
                    "text": snippet,
                    "is_truncated": is_truncated,
                }
            )

    matches.sort(key=lambda prompt: prompt["timestamp"], reverse=True)
    start = (page - 1) * PAGE_SIZE
    return 200, {
        "page": page,
        "has_more": start + PAGE_SIZE < len(matches),
        "query": query,
        "prompts": matches[start : start + PAGE_SIZE],
    }
