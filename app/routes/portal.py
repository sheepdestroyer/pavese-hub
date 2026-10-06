from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import database
from app.auth import get_current_user, normalize_email
from app.models import Tile, UserInfo

router = APIRouter(tags=["portal"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def is_tile_permitted(tile: Tile, user: UserInfo) -> bool:
    if "*" in tile.allowed_users:
        return True
    user_email_norm = normalize_email(user.email)
    return any(user_email_norm == normalize_email(u) for u in tile.allowed_users)


@router.get("/", response_class=HTMLResponse)
def get_portal(request: Request, user: UserInfo = Depends(get_current_user)) -> HTMLResponse:
    all_tiles = database.get_tiles(include_disabled=False)
    permitted_tiles = [tile for tile in all_tiles if is_tile_permitted(tile, user)]

    categories: dict[str, list[Tile]] = defaultdict(list)
    for tile in permitted_tiles:
        categories[tile.category].append(tile)

    return templates.TemplateResponse(
        request=request,
        name="portal.html",
        context={"user": user, "categories": dict(categories)},
    )


@router.get("/api/tiles", response_model=list[Tile])
def get_user_tiles(user: UserInfo = Depends(get_current_user)) -> list[Tile]:
    all_tiles = database.get_tiles(include_disabled=False)
    return [tile for tile in all_tiles if is_tile_permitted(tile, user)]
