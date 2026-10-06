import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.port: int = int(os.environ.get("PORT", "5003"))
        self.host: str = os.environ.get("HOST", "127.0.0.1")
        self.database_path: str = os.environ.get("DATABASE_PATH", str(Path(__file__).parent.parent / "data" / "hub.db"))
        admin_emails_raw = os.environ.get("ADMIN_EMAILS", "sheepdestroyer@gmail.com,sheepyboy.x570@gmail.com")
        self.admin_emails: list[str] = [email.strip().lower() for email in admin_emails_raw.split(",") if email.strip()]
        self.allow_lan_admin: bool = os.environ.get("ALLOW_LAN_ADMIN", "true").lower() in (
            "1",
            "true",
            "yes",
        )


settings = Settings()
