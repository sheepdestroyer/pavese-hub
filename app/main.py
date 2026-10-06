from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app import database
from app.config import settings
from app.routes import admin, health, portal


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    database.init_db()
    yield


app = FastAPI(
    title="Pavese Cloud Hub",
    description="Unified Service Directory Hub with Admin RBAC Tile Visibility",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(portal.router)
app.include_router(admin.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
