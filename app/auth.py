from fastapi import HTTPException, Request, status

from app.config import settings
from app.models import UserInfo


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def is_lan_or_local(request: Request) -> bool:
    host = request.headers.get("Host", "").lower().split(":")[0]
    if host.endswith(".lan") or host in ("localhost", "127.0.0.1"):
        return True
    ip = get_client_ip(request)
    return ip.startswith("127.") or ip.startswith("192.168.0.") or ip == "::1"


def normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if "@" in cleaned:
        user_part, domain_part = cleaned.split("@", 1)
        if domain_part in ("gmail.com", "googlemail.com"):
            user_part = user_part.replace(".", "")
            if "+" in user_part:
                user_part = user_part.split("+", 1)[0]
        return f"{user_part}@{domain_part}"
    return cleaned


def get_current_user(request: Request) -> UserInfo:
    email = (
        request.headers.get("X-Auth-Request-Email")
        or request.headers.get("X-Auth-Request-User")
        or request.headers.get("X-Forwarded-User")
        or request.headers.get("Remote-Email")
        or request.headers.get("Remote-User")
        or request.headers.get("X-Dev-User")
    )

    if not email and settings.allow_lan_admin and is_lan_or_local(request):
        # Default LAN fallback to primary admin email if no header present
        email = settings.admin_emails[0] if settings.admin_emails else "admin@vendeuvre.lan"

    email_clean = (email or "anonymous").strip().lower()
    is_admin = any(
        normalize_email(email_clean) == normalize_email(admin_email)
        or (admin_email.lower() == "admin@vendeuvre.lan" and email_clean == "admin@vendeuvre.lan")
        for admin_email in settings.admin_emails
    )

    return UserInfo(email=email_clean, is_admin=is_admin)


def require_admin(request: Request) -> UserInfo:
    user = get_current_user(request)
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access this resource",
        )
    return user
