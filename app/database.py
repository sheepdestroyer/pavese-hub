import json
import sqlite3
import uuid
from pathlib import Path
from urllib.parse import urlparse

from app.auth import normalize_email
from app.config import settings
from app.models import Tile, TileCreate, TileUpdate, UserInfo

SEED_TILES = [
    {
        "id": "sheepvibes",
        "title": "SheepVibes",
        "url": "https://sheepvibes.pavese.fr/",
        "icon": "🐑",
        "description": "Revived NetVibes RSS reader, customizable widget dashboard, and news aggregator.",
        "category": "Web Applications & Dashboards",
        "badge": "🔒 SSO",
        "badge_color": "purple",
        "footer_text": "Launch Reader →",
        "sort_order": 1,
        "allowed_users": ["*"],
        "enabled": True,
    },
    {
        "id": "sheepflix",
        "title": "SheepFlix",
        "url": "https://sheepflix.pavese.fr/",
        "icon": "🎬",
        "description": "Personal media streaming platform with hardware transcoding (Jellyfin).",
        "category": "Web Applications & Dashboards",
        "badge": "🔒 SSO",
        "badge_color": "purple",
        "footer_text": "Watch Now →",
        "sort_order": 2,
        "allowed_users": ["*"],
        "enabled": True,
    },
    {
        "id": "minecraft",
        "title": "Minecraft Gateway",
        "url": "https://minecraft.pavese.fr/",
        "icon": "🎮",
        "description": "Personalized in-game credentials, dedicated server addresses, and live 3D BlueMap.",
        "category": "Web Applications & Dashboards",
        "badge": "🔒 SSO",
        "badge_color": "purple",
        "footer_text": "View Gateway →",
        "sort_order": 3,
        "allowed_users": ["*"],
        "enabled": True,
    },
    {
        "id": "divorce",
        "title": "Divorce-IA",
        "url": "https://divorce.pavese.fr/",
        "icon": "⚖️",
        "description": "Legal dossier intelligence, chronologies, evidence analysis & litigation strategy.",
        "category": "Web Applications & Dashboards",
        "badge": "🔒 SSO",
        "badge_color": "purple",
        "footer_text": "Access Dossier →",
        "sort_order": 4,
        "allowed_users": ["sheepdestroyer@gmail.com", "sheepyboy.x570@gmail.com"],
        "enabled": True,
    },
    {
        "id": "romm",
        "title": "RomM Library",
        "url": "https://romm.pavese.fr/",
        "icon": "🕹️",
        "description": "Retro gaming collection manager, artwork, saves & in-browser emulation.",
        "category": "Web Applications & Dashboards",
        "badge": "🔒 SSO",
        "badge_color": "purple",
        "footer_text": "Launch RomM →",
        "sort_order": 5,
        "allowed_users": ["sheepdestroyer@gmail.com", "sheepyboy.x570@gmail.com"],
        "enabled": True,
    },
    {
        "id": "coroot",
        "title": "Coroot Observability",
        "url": "https://coroot.pavese.fr/",
        "icon": "📈",
        "description": "eBPF-powered infrastructure telemetry, service maps, node health, and root-cause analysis.",
        "category": "Web Applications & Dashboards",
        "badge": "🔒 SSO",
        "badge_color": "purple",
        "footer_text": "Open Dashboards →",
        "sort_order": 6,
        "allowed_users": ["*"],
        "enabled": True,
    },
    {
        "id": "homeassistant",
        "title": "Home Assistant",
        "url": "https://hass.pavese.fr/",
        "icon": "🏠",
        "description": "Smart home automation platform, energy monitoring, device control, and status dashboards.",
        "category": "Web Applications & Dashboards",
        "badge": "🏠 Native Auth",
        "badge_color": "green",
        "footer_text": "Open Home →",
        "sort_order": 7,
        "allowed_users": ["*"],
        "enabled": True,
    },
    {
        "id": "cockpit",
        "title": "Cockpit Console",
        "url": "https://cockpit.pavese.fr/",
        "icon": "🖥️",
        "description": "Linux system administration, web terminal, service health, storage & podman management.",
        "category": "Web Applications & Dashboards",
        "badge": "🔒 SSO",
        "badge_color": "purple",
        "footer_text": "Manage Server →",
        "sort_order": 8,
        "allowed_users": ["*"],
        "enabled": True,
    },
    {
        "id": "gx10",
        "title": "Asus Ascend GX10",
        "url": "https://gx10.vendeuvre.lan/",
        "icon": "⚡",
        "description": "NVIDIA GB10 Blackwell & Grace ARM64 node, DGX system telemetry, GPU metrics & administration.",
        "category": "Web Applications & Dashboards",
        "badge": "GB10 Blackwell",
        "badge_color": "green",
        "footer_text": "Open Dashboard →",
        "sort_order": 9,
        "allowed_users": ["*"],
        "enabled": True,
    },
    {
        "id": "unsloth",
        "title": "Unsloth Studio",
        "url": "https://unsloth.gx10.vendeuvre.lan/",
        "icon": "🦥",
        "description": (
            "Local AI training & inference studio, Qwen3.8-27B NVFP4, Qwen-Image-2.1 diffusion & code execution."
        ),
        "category": "Web Applications & Dashboards",
        "badge": "GB10 NVFP4",
        "badge_color": "green",
        "footer_text": "Launch Studio →",
        "sort_order": 10,
        "allowed_users": ["*"],
        "enabled": True,
    },
    {
        "id": "jupyter",
        "title": "GX10 JupyterLab",
        "url": "https://jupyter.gx10.vendeuvre.lan/",
        "icon": "🪐",
        "description": "Interactive PyTorch, CUDA 13 & Blackwell notebook workspace on Asus Ascend GX10.",
        "category": "Web Applications & Dashboards",
        "badge": "ARM64 Python",
        "badge_color": "orange",
        "footer_text": "Open Notebooks →",
        "sort_order": 11,
        "allowed_users": ["*"],
        "enabled": True,
    },
    {
        "id": "hermes",
        "title": "Hermes Agent",
        "url": "https://hermes.pavese.fr/",
        "icon": "🤖",
        "description": "Autonomous AI agent orchestrator, live tool execution traces, sessions & system skills.",
        "category": "Web Applications & Dashboards",
        "badge": "🔒 SSO",
        "badge_color": "purple",
        "footer_text": "Launch Agent UI →",
        "sort_order": 12,
        "allowed_users": ["*"],
        "enabled": True,
    },
]


def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    target_path = db_path or settings.database_path
    if target_path != ":memory:":
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tiles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                icon TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                badge TEXT,
                badge_color TEXT,
                footer_text TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                allowed_users TEXT NOT NULL DEFAULT '["*"]',
                enabled INTEGER NOT NULL DEFAULT 1
            )
        """)
        # Seed if empty
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM tiles")
        if cursor.fetchone()["cnt"] == 0:
            for tile in SEED_TILES:
                conn.execute(
                    """
                    INSERT INTO tiles (
                        id, title, url, icon, description, category,
                        badge, badge_color, footer_text, sort_order, allowed_users, enabled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tile["id"],
                        tile["title"],
                        tile["url"],
                        tile["icon"],
                        tile["description"],
                        tile["category"],
                        tile["badge"],
                        tile["badge_color"],
                        tile["footer_text"],
                        tile["sort_order"],
                        json.dumps(tile["allowed_users"]),
                        1 if tile["enabled"] else 0,
                    ),
                )
    conn.close()
    sync_allowed_emails_file(db_path=db_path)


def row_to_tile(row: sqlite3.Row) -> Tile:
    try:
        allowed = json.loads(row["allowed_users"])
        if not isinstance(allowed, list):
            allowed = ["*"]
    except Exception:
        allowed = ["*"]

    return Tile(
        id=row["id"],
        title=row["title"],
        url=row["url"],
        icon=row["icon"],
        description=row["description"],
        category=row["category"],
        badge=row["badge"],
        badge_color=row["badge_color"] or "purple",
        footer_text=row["footer_text"] or "Open →",
        sort_order=row["sort_order"],
        allowed_users=[str(u).strip() for u in allowed if str(u).strip()],
        enabled=bool(row["enabled"]),
    )


def get_tiles(include_disabled: bool = False, db_path: str | None = None) -> list[Tile]:
    conn = get_db_connection(db_path)
    try:
        if include_disabled:
            cursor = conn.execute("SELECT * FROM tiles ORDER BY sort_order ASC, title ASC")
        else:
            cursor = conn.execute("SELECT * FROM tiles WHERE enabled = 1 ORDER BY sort_order ASC, title ASC")
        return [row_to_tile(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def get_tile(tile_id: str, db_path: str | None = None) -> Tile | None:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM tiles WHERE id = ?", (tile_id,))
        row = cursor.fetchone()
        return row_to_tile(row) if row else None
    finally:
        conn.close()


def create_tile(data: TileCreate, db_path: str | None = None) -> Tile:
    tile_id = str(uuid.uuid4())[:8]
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO tiles (
                    id, title, url, icon, description, category,
                    badge, badge_color, footer_text, sort_order, allowed_users, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tile_id,
                    data.title,
                    data.url,
                    data.icon,
                    data.description,
                    data.category,
                    data.badge,
                    data.badge_color,
                    data.footer_text,
                    data.sort_order,
                    json.dumps(data.allowed_users),
                    1 if data.enabled else 0,
                ),
            )
        tile = get_tile(tile_id, db_path=db_path)
    finally:
        conn.close()
    sync_allowed_emails_file(db_path=db_path)
    return tile  # type: ignore[return-value]


def update_tile(tile_id: str, data: TileUpdate, db_path: str | None = None) -> Tile | None:
    existing = get_tile(tile_id, db_path=db_path)
    if not existing:
        return None

    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return existing

    if "allowed_users" in fields and fields["allowed_users"] is not None:
        fields["allowed_users"] = json.dumps(fields["allowed_users"])
    if "enabled" in fields and fields["enabled"] is not None:
        fields["enabled"] = 1 if fields["enabled"] else 0

    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [tile_id]

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(f"UPDATE tiles SET {set_clause} WHERE id = ?", values)
        tile = get_tile(tile_id, db_path=db_path)
    finally:
        conn.close()
    sync_allowed_emails_file(db_path=db_path)
    return tile


def delete_tile(tile_id: str, db_path: str | None = None) -> bool:
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("DELETE FROM tiles WHERE id = ?", (tile_id,))
            deleted = cursor.rowcount > 0
    finally:
        conn.close()
    if deleted:
        sync_allowed_emails_file(db_path=db_path)
    return deleted


def reorder_tiles(ordered_ids: list[str], db_path: str | None = None) -> bool:
    conn = get_db_connection(db_path)
    try:
        with conn:
            for idx, tid in enumerate(ordered_ids):
                conn.execute("UPDATE tiles SET sort_order = ? WHERE id = ?", (idx + 1, tid))
        return True
    finally:
        conn.close()


def sync_allowed_emails_file(db_path: str | None = None, output_path: str | None = None) -> list[str]:
    target_file = output_path if output_path is not None else settings.allowed_emails_path
    emails: set[str] = set()

    for admin_email in settings.admin_emails:
        cleaned = admin_email.strip().lower()
        if cleaned and "@" in cleaned:
            emails.add(cleaned)
            emails.add(normalize_email(cleaned))

    for tile in get_tiles(include_disabled=False, db_path=db_path):
        for u in tile.allowed_users:
            cleaned = u.strip().lower()
            if cleaned and cleaned != "*" and "@" in cleaned:
                emails.add(cleaned)
                emails.add(normalize_email(cleaned))

    sorted_emails = sorted(emails)
    if target_file:
        path_obj = Path(target_file)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        content = "# Pavese Cloud Allowed Users Whitelist (Auto-generated by pavese-hub)\n"
        content += "\n".join(sorted_emails) + "\n"
        path_obj.write_text(content, encoding="utf-8")
    return sorted_emails


def extract_hostname(url_or_host: str) -> str:
    raw = url_or_host.strip().lower()
    if "://" in raw:
        parsed = urlparse(raw)
        return (parsed.hostname or "").lower()
    return raw.split("/")[0].split(":")[0]


def authorize_host_access(target_host: str, user: UserInfo, db_path: str | None = None) -> bool:
    if not user.email or user.email == "anonymous":
        return False
    if user.is_admin:
        return True

    host_clean = extract_hostname(target_host)
    if not host_clean:
        return False

    # Alias mappings to canonical tile hostnames
    alias_map = {
        "bluemap.minecraft.pavese.fr": "minecraft.pavese.fr",
        "paper.minecraft.pavese.fr": "minecraft.pavese.fr",
        "hermes-dashboard.pavese.fr": "hermes.pavese.fr",
        "homeassistant.pavese.fr": "hass.pavese.fr",
    }
    canonical_host = alias_map.get(host_clean, host_clean)
    enabled_tiles = get_tiles(include_disabled=False, db_path=db_path)
    user_norm = normalize_email(user.email)

    if canonical_host in ("hub.pavese.fr", "hub.vendeuvre.lan"):
        return any(
            "*" in tile.allowed_users or any(user_norm == normalize_email(u) for u in tile.allowed_users)
            for tile in enabled_tiles
        )

    matched_tiles = [tile for tile in enabled_tiles if extract_hostname(tile.url) == canonical_host]
    if not matched_tiles:
        return False

    return any(
        "*" in tile.allowed_users or any(user_norm == normalize_email(u) for u in tile.allowed_users)
        for tile in matched_tiles
    )
