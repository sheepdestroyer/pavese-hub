from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app import database
from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def test_db(tmp_path: pytest.TempPathFactory) -> Generator[str, None, None]:
    db_file = str(tmp_path / "test_hub.db")
    settings.database_path = db_file
    settings.admin_emails = ["sheepdestroyer@gmail.com", "sheepyboy.x570@gmail.com"]
    settings.allow_lan_admin = True
    database.init_db(db_file)
    yield db_file


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
