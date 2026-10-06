from pydantic import BaseModel, Field


class Tile(BaseModel):
    id: str
    title: str
    url: str
    icon: str = "🌐"
    description: str = ""
    category: str = "Web Applications & Dashboards"
    badge: str | None = None
    badge_color: str = "purple"
    footer_text: str = "Open →"
    sort_order: int = 0
    allowed_users: list[str] = Field(default_factory=lambda: ["*"])
    enabled: bool = True


class TileCreate(BaseModel):
    title: str
    url: str
    icon: str = "🌐"
    description: str = ""
    category: str = "Web Applications & Dashboards"
    badge: str | None = None
    badge_color: str = "purple"
    footer_text: str = "Open →"
    sort_order: int = 0
    allowed_users: list[str] = Field(default_factory=lambda: ["*"])
    enabled: bool = True


class TileUpdate(BaseModel):
    title: str | None = None
    url: str | None = None
    icon: str | None = None
    description: str | None = None
    category: str | None = None
    badge: str | None = None
    badge_color: str | None = None
    footer_text: str | None = None
    sort_order: int | None = None
    allowed_users: list[str] | None = None
    enabled: bool | None = None


class UserInfo(BaseModel):
    email: str
    is_admin: bool
