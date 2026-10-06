import pytest
from fastapi.testclient import TestClient

from app import database
from app.auth import get_client_ip, get_current_user, is_lan_or_local
from app.config import settings
from app.models import Tile, TileUpdate, UserInfo
from app.routes.portal import is_tile_permitted


def test_health_check(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "pavese-hub"}


def test_auth_headers_and_roles(client: TestClient) -> None:
    # 1. Google OAuth2-Proxy Email header
    res = client.get("/api/tiles", headers={"X-Auth-Request-Email": "sheepdestroyer@gmail.com"})
    assert res.status_code == 200
    titles = [t["title"] for t in res.json()]
    assert "RomM Library" in titles
    assert "Divorce-IA" in titles

    # 2. Non-admin user email
    res2 = client.get(
        "/api/tiles",
        headers={
            "X-Auth-Request-Email": "ulysse.pavese@gmail.com",
            "Host": "hub.pavese.fr",
            "X-Forwarded-For": "203.0.113.195",
        },
    )
    assert res2.status_code == 200
    titles2 = [t["title"] for t in res2.json()]
    assert "RomM Library" not in titles2
    assert "Divorce-IA" not in titles2
    assert "SheepVibes" in titles2

    # 3. Fallback header X-Auth-Request-User
    res3 = client.get(
        "/api/tiles",
        headers={
            "X-Auth-Request-User": "sheepyboy.x570@gmail.com",
            "Host": "hub.pavese.fr",
            "X-Forwarded-For": "203.0.113.195",
        },
    )
    assert res3.status_code == 200
    assert "Divorce-IA" in [t["title"] for t in res3.json()]

    # 4. Fallback header X-Forwarded-User
    res4 = client.get(
        "/api/tiles",
        headers={
            "X-Forwarded-User": "other@pavese.fr",
            "Host": "hub.pavese.fr",
            "X-Forwarded-For": "203.0.113.195",
        },
    )
    assert res4.status_code == 200
    assert "Divorce-IA" not in [t["title"] for t in res4.json()]

    # 5. Fallback header X-Dev-User
    res5 = client.get(
        "/api/tiles",
        headers={
            "X-Dev-User": "dev@pavese.fr",
            "Host": "hub.pavese.fr",
            "X-Forwarded-For": "203.0.113.195",
        },
    )
    assert res5.status_code == 200
    assert "Divorce-IA" not in [t["title"] for t in res5.json()]


def test_portal_html_rendering(client: TestClient) -> None:
    # Admin gets Admin Panel button in HTML
    res_admin = client.get("/", headers={"X-Auth-Request-Email": "sheepdestroyer@gmail.com"})
    assert res_admin.status_code == 200
    assert "Admin Panel" in res_admin.text
    assert "RomM Library" in res_admin.text

    # Restricted user doesn't get Admin Panel button or restricted tiles
    res_user = client.get(
        "/",
        headers={
            "X-Auth-Request-Email": "ulysse.pavese@gmail.com",
            "Host": "hub.pavese.fr",
            "X-Forwarded-For": "203.0.113.50",
        },
    )
    assert res_user.status_code == 200
    assert "Admin Panel" not in res_user.text
    assert "RomM Library" not in res_user.text
    assert "SheepVibes" in res_user.text


def test_admin_access_control(client: TestClient) -> None:
    # Forbidden for non-admin
    res_forbidden = client.get(
        "/admin",
        headers={
            "X-Auth-Request-Email": "unknown@domain.com",
            "Host": "hub.pavese.fr",
            "X-Forwarded-For": "203.0.113.50",
        },
    )
    assert res_forbidden.status_code == 403
    assert res_forbidden.json()["detail"] == "Admin privileges required to access this resource"

    # Permitted for admin
    res_admin = client.get("/admin", headers={"X-Auth-Request-Email": "sheepdestroyer@gmail.com"})
    assert res_admin.status_code == 200
    assert "Hub Tile & Access Management" in res_admin.text


def test_admin_tile_crud(client: TestClient) -> None:
    admin_hdr = {"X-Auth-Request-Email": "sheepdestroyer@gmail.com"}

    # List all tiles
    res_list = client.get("/api/admin/tiles", headers=admin_hdr)
    assert res_list.status_code == 200
    initial_count = len(res_list.json())

    # Create new tile
    new_tile = {
        "title": "Custom Service",
        "url": "https://custom.pavese.fr/",
        "icon": "🚀",
        "description": "Custom automated tool",
        "category": "Tools",
        "badge": "NEW",
        "badge_color": "blue",
        "footer_text": "Explore →",
        "sort_order": 99,
        "allowed_users": ["sheepdestroyer@gmail.com"],
        "enabled": True,
    }
    res_create = client.post("/api/admin/tiles", json=new_tile, headers=admin_hdr)
    assert res_create.status_code == 201
    created = res_create.json()
    tile_id = created["id"]
    assert created["title"] == "Custom Service"
    assert created["allowed_users"] == ["sheepdestroyer@gmail.com"]

    # Get single tile
    res_get = client.get(f"/api/admin/tiles/{tile_id}", headers=admin_hdr)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == tile_id

    # Get non-existent tile
    res_get_404 = client.get("/api/admin/tiles/nonexistent", headers=admin_hdr)
    assert res_get_404.status_code == 404

    # Update tile
    update_payload = {
        "title": "Updated Custom Service",
        "url": "https://updated.pavese.fr/",
        "description": "Updated description",
        "icon": "⚡",
        "category": "Compute",
        "badge": "UPDATED",
        "badge_color": "green",
        "footer_text": "Go →",
        "sort_order": 1,
        "allowed_users": ["*"],
        "enabled": False,
    }
    res_update = client.put(f"/api/admin/tiles/{tile_id}", json=update_payload, headers=admin_hdr)
    assert res_update.status_code == 200
    assert res_update.json()["title"] == "Updated Custom Service"
    assert res_update.json()["url"] == "https://updated.pavese.fr/"
    assert res_update.json()["enabled"] is False

    # Partial update (only title)
    res_partial = client.put(
        f"/api/admin/tiles/{tile_id}",
        json={"title": "Partial Updated Title"},
        headers=admin_hdr,
    )
    assert res_partial.status_code == 200
    assert res_partial.json()["title"] == "Partial Updated Title"

    # Update non-existent tile

    res_update_404 = client.put("/api/admin/tiles/nonexistent", json=update_payload, headers=admin_hdr)
    assert res_update_404.status_code == 404

    # Reorder tiles
    res_reorder = client.post(
        "/api/admin/reorder",
        json={"ordered_ids": [tile_id, "sheepvibes"]},
        headers=admin_hdr,
    )
    assert res_reorder.status_code == 200
    assert res_reorder.json() == {"status": "reordered"}

    # Delete tile
    res_delete = client.delete(f"/api/admin/tiles/{tile_id}", headers=admin_hdr)
    assert res_delete.status_code == 204

    # Delete non-existent tile
    res_delete_404 = client.delete(f"/api/admin/tiles/{tile_id}", headers=admin_hdr)
    assert res_delete_404.status_code == 404

    # Verify count restored
    res_list_after = client.get("/api/admin/tiles", headers=admin_hdr)
    assert len(res_list_after.json()) == initial_count


def test_auth_edge_cases_and_helpers() -> None:
    # Mock requests for get_client_ip and is_lan_or_local
    class MockClient:
        host = "192.168.0.50"

    class MockRequest:
        def __init__(self, headers: dict[str, str], host_attr: str = "192.168.0.50") -> None:
            self.headers = headers
            self.client = MockClient()
            self.client.host = host_attr

    # 1. Forwarded IP takes precedence
    req1 = MockRequest({"X-Forwarded-For": "203.0.113.1, 10.0.0.1"})
    assert get_client_ip(req1) == "203.0.113.1"

    # 2. No client object fallback
    req2 = MockRequest({})
    req2.client = None
    assert get_client_ip(req2) == "127.0.0.1"

    # 3. is_lan_or_local checks
    req_lan_host = MockRequest({"Host": "hub.vendeuvre.lan:443"})
    assert is_lan_or_local(req_lan_host) is True

    req_local_ip = MockRequest({"Host": "hub.pavese.fr"}, host_attr="127.0.0.1")
    assert is_lan_or_local(req_local_ip) is True

    req_ipv6_loopback = MockRequest({"Host": "hub.pavese.fr"}, host_attr="::1")
    assert is_lan_or_local(req_ipv6_loopback) is True

    req_external = MockRequest({"Host": "hub.pavese.fr"}, host_attr="203.0.113.88")
    assert is_lan_or_local(req_external) is False

    # 4. LAN admin fallback disabled
    settings.allow_lan_admin = False
    user_no_lan = get_current_user(req_external)
    assert user_no_lan.email == "anonymous"
    assert user_no_lan.is_admin is False

    # 5. LAN admin fallback with empty admin list
    settings.allow_lan_admin = True
    settings.admin_emails = []
    user_lan_fallback = get_current_user(req_lan_host)
    assert user_lan_fallback.email == "admin@vendeuvre.lan"
    assert user_lan_fallback.is_admin is False

    # Reset
    settings.admin_emails = ["sheepdestroyer@gmail.com", "admin@vendeuvre.lan"]
    user_admin_lan = get_current_user(req_lan_host)
    assert user_admin_lan.is_admin is True

    # 6. normalize_email tests
    from app.auth import normalize_email

    assert normalize_email("notanemail") == "notanemail"
    assert normalize_email("Ulysse.Pavese@gmail.com") == "ulyssepavese@gmail.com"
    assert normalize_email("test.user+tag123@googlemail.com") == "testuser@googlemail.com"
    assert normalize_email("user.name@custom.domain.com") == "user.name@custom.domain.com"


def test_database_edge_cases(tmp_path: pytest.TempPathFactory) -> None:
    # Memory connection test
    mem_conn = database.get_db_connection(":memory:")
    mem_conn.close()

    db_file = str(tmp_path / "edge.db")
    database.init_db(db_file)

    # Calling init_db again does not duplicate seed data
    database.init_db(db_file)
    tiles = database.get_tiles(include_disabled=True, db_path=db_file)
    assert len(tiles) == len(database.SEED_TILES)

    # Empty update fields returns existing
    existing = tiles[0]
    unchanged = database.update_tile(existing.id, TileUpdate(), db_path=db_file)
    assert unchanged is not None
    assert unchanged.id == existing.id

    # Update non-existent
    assert database.update_tile("nonexistent", TileUpdate(title="X"), db_path=db_file) is None

    # Corrupted allowed_users in sqlite falls back gracefully to ["*"]
    conn = database.get_db_connection(db_file)
    with conn:
        conn.execute("UPDATE tiles SET allowed_users = 'invalid-json' WHERE id = ?", (existing.id,))
    conn.close()

    corrupted_tile = database.get_tile(existing.id, db_path=db_file)
    assert corrupted_tile is not None
    assert corrupted_tile.allowed_users == ["*"]

    # Allowed users with non-list json falls back to ["*"]
    conn = database.get_db_connection(db_file)
    with conn:
        conn.execute("UPDATE tiles SET allowed_users = '123' WHERE id = ?", (existing.id,))
    conn.close()

    number_tile = database.get_tile(existing.id, db_path=db_file)
    assert number_tile is not None
    assert number_tile.allowed_users == ["*"]


def test_is_tile_permitted(tmp_path: pytest.TempPathFactory) -> None:
    db_file = str(tmp_path / "perm.db")
    database.init_db(db_file)
    conn = database.get_db_connection(db_file)
    with conn:
        conn.execute(
            """
            INSERT INTO tiles (
                id, title, url, icon, description, category,
                badge, badge_color, footer_text, sort_order, allowed_users, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "wildcard_test",
                "Wildcard",
                "http://wildcard",
                "🌐",
                "",
                "Cat",
                None,
                None,
                None,
                0,
                '["*"]',
                1,
            ),
        )
        conn.execute(
            """
            INSERT INTO tiles (
                id, title, url, icon, description, category,
                badge, badge_color, footer_text, sort_order, allowed_users, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "restricted_test",
                "Restricted",
                "http://restricted",
                "🔒",
                "",
                "Cat",
                None,
                None,
                None,
                0,
                '["allowed@example.com", " "] ',
                1,
            ),
        )
    conn.close()

    tile_wildcard = database.get_tile("wildcard_test", db_path=db_file)
    assert tile_wildcard is not None
    assert is_tile_permitted(tile_wildcard, UserInfo(email="anyone@example.com", is_admin=False)) is True

    tile_restricted = database.get_tile("restricted_test", db_path=db_file)
    assert tile_restricted is not None
    assert is_tile_permitted(tile_restricted, UserInfo(email="allowed@example.com", is_admin=False)) is True
    assert is_tile_permitted(tile_restricted, UserInfo(email="denied@example.com", is_admin=False)) is False

    # Test Gmail dot normalization in is_tile_permitted
    tile_gmail = Tile(
        id="gmail_test",
        title="Gmail Test",
        url="http://test",
        icon="📧",
        description="",
        category="Cat",
        allowed_users=["ulysse.pavese@gmail.com"],
        enabled=True,
    )
    assert is_tile_permitted(tile_gmail, UserInfo(email="ulyssepavese@gmail.com", is_admin=False)) is True
    assert is_tile_permitted(tile_gmail, UserInfo(email="Ulysse.Pavese@gmail.com", is_admin=False)) is True
