from typing import Tuple

from src.ratings import InvalidStoreError, valid_rating_value
from src.server.common import ApiError, Context, Request, invalid_store_error


def put_rating(ctx: Context, req: Request) -> Tuple[int, dict]:
    body = req.json()
    value = body.get("value")
    session_id = body.get("session_id")
    position = body.get("position")
    if not valid_rating_value(value):
        raise ApiError(400, "Rating value must be an integer from 1 to 10.")
    if not isinstance(session_id, str) or not session_id:
        raise ApiError(400, "session_id is required.")
    if not isinstance(position, int) or isinstance(position, bool) or position < 0:
        raise ApiError(400, "position must be a non-negative integer.")
    try:
        record = ctx.store.set(req.params["prompt_id"], session_id, position, value)
    except InvalidStoreError:
        raise invalid_store_error()
    except OSError:
        raise ApiError(500, "The rating could not be saved.")
    return 200, record


def reset_ratings(ctx: Context, req: Request) -> Tuple[int, dict]:
    try:
        ctx.store.reset()
    except OSError:
        raise ApiError(500, "The ratings file could not be deleted.")
    return 200, {"reset": True}
