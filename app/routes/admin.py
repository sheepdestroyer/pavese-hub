from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app import database
from app.auth import require_admin
from app.models import Tile, TileCreate, TileUpdate, UserInfo

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


class ReorderRequest(BaseModel):
    ordered_ids: list[str]


@router.get("/admin", response_class=HTMLResponse)
def get_admin_page(request: Request, user: UserInfo = Depends(require_admin)) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"user": user},
    )


@router.get("/api/admin/tiles", response_model=list[Tile])
def list_all_tiles(user: UserInfo = Depends(require_admin)) -> list[Tile]:
    return database.get_tiles(include_disabled=True)


@router.get("/api/admin/tiles/{tile_id}", response_model=Tile)
def get_tile(tile_id: str, user: UserInfo = Depends(require_admin)) -> Tile:
    tile = database.get_tile(tile_id)
    if not tile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tile not found")
    return tile


@router.post("/api/admin/tiles", response_model=Tile, status_code=status.HTTP_201_CREATED)
def create_new_tile(tile_data: TileCreate, user: UserInfo = Depends(require_admin)) -> Tile:
    return database.create_tile(tile_data)


@router.put("/api/admin/tiles/{tile_id}", response_model=Tile)
def update_existing_tile(tile_id: str, tile_data: TileUpdate, user: UserInfo = Depends(require_admin)) -> Tile:
    updated = database.update_tile(tile_id, tile_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tile not found")
    return updated


@router.delete("/api/admin/tiles/{tile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_tile(tile_id: str, user: UserInfo = Depends(require_admin)) -> None:
    deleted = database.delete_tile(tile_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tile not found")


@router.post("/api/admin/reorder")
def reorder_tiles(reorder_data: ReorderRequest, user: UserInfo = Depends(require_admin)) -> dict[str, str]:
    database.reorder_tiles(reorder_data.ordered_ids)
    return {"status": "reordered"}
