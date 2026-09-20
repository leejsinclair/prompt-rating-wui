from typing import Dict, Tuple

from src.parsing import parse_session_file
from src.ratings import InvalidStoreError
from src.server.common import (
    PAGE_SIZE,
    Context,
    Request,
    humanize_command_markup,
    invalid_store_error,
    session_files,
    truncate_text,
)


def get_top_rated(ctx: Context, req: Request) -> Tuple[int, dict]:
    try:
        ratings = ctx.store.load()
    except InvalidStoreError:
        raise invalid_store_error()

    page = req.page()
    ranked = sorted(ratings.items(), key=lambda kv: (kv[1]["value"], kv[1]["rated_at"]), reverse=True)
    start = (page - 1) * PAGE_SIZE
    window = ranked[start : start + PAGE_SIZE]

    files = session_files(ctx) if window else {}
    parsed: Dict[str, object] = {}
    prompts = []
    for prompt_id, rating in window:
        session_id = rating["session_id"]
        if session_id not in parsed:
            path = files.get(session_id)
            parsed[session_id] = parse_session_file(path) if path else None
        session = parsed[session_id]
        prompt = None
        if session is not None and session.is_parseable:
            prompt = next((p for p in session.prompts if p.prompt_id == prompt_id), None)

        entry = {
            "prompt_id": prompt_id,
            "session_id": session_id,
            "position": rating["position"],
            "value": rating["value"],
            "rated_at": rating["rated_at"],
            "is_orphaned": prompt is None,
        }
        if prompt is not None:
            entry["text"], entry["is_truncated"] = truncate_text(humanize_command_markup(prompt.text))
        prompts.append(entry)

    return 200, {"page": page, "has_more": start + PAGE_SIZE < len(ranked), "prompts": prompts}
