from typing import Tuple

from src.favorites import InvalidFavoritesStoreError
from src.server.common import (
    ApiError,
    Context,
    Request,
    invalid_favorites_store_error,
    load_favorites,
)


def _sorted_favorites(data: dict) -> list:
    items = [
        dict(entry, favorite_prompt_id=favorite_prompt_id)
        for favorite_prompt_id, entry in data.items()
    ]
    items.sort(key=lambda entry: (entry["updated_at"], entry["created_at"], entry["favorite_prompt_id"]), reverse=True)
    return items


def list_favorites(ctx: Context, req: Request) -> Tuple[int, dict]:
    favorites, favorites_invalid = load_favorites(ctx)
    if favorites_invalid:
        raise invalid_favorites_store_error()
    return 200, {"prompts": _sorted_favorites(favorites)}


def create_favorite(ctx: Context, req: Request) -> Tuple[int, dict]:
    text = req.json().get("text")
    if not isinstance(text, str) or not text.strip():
        raise ApiError(400, "text is required.")
    try:
        record = ctx.favorites_store.create(text)
    except InvalidFavoritesStoreError:
        raise invalid_favorites_store_error()
    except OSError:
        raise ApiError(500, "The favorite prompt could not be saved.")
    return 201, record


def update_favorite(ctx: Context, req: Request) -> Tuple[int, dict]:
    text = req.json().get("text")
    if not isinstance(text, str) or not text.strip():
        raise ApiError(400, "text is required.")
    try:
        record = ctx.favorites_store.update(req.params["favorite_prompt_id"], text)
    except InvalidFavoritesStoreError:
        raise invalid_favorites_store_error()
    except KeyError:
        raise ApiError(404, "Favorite prompt not found.")
    except OSError:
        raise ApiError(500, "The favorite prompt could not be saved.")
    return 200, record


def reset_favorites(ctx: Context, req: Request) -> Tuple[int, dict]:
    try:
        ctx.favorites_store.reset()
    except OSError:
        raise ApiError(500, "The favorites file could not be deleted.")
    return 200, {"reset": True}
