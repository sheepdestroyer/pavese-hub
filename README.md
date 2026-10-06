# Pavese Cloud Hub (`hub.pavese.fr` / `hub.vendeuvre.lan`)

Unified Services Directory Hub with Dynamic Admin RBAC Tile Visibility.

## Architecture

- **Backend**: FastAPI 0.115+ (Python 3.12+), SQLite with automated initial seed migration.
- **Frontend**: Clean glassmorphism dark mode with Jinja2 server-side filtered rendering and interactive Admin Management Dashboard.
- **Security & RBAC**:
  - Ingress forward-auth via Google OAuth2-Proxy (`X-Auth-Request-Email` header).
  - Configurable admin privileges via `ADMIN_EMAILS` environment variable.
  - Per-tile visibility ACLs: `allowed_users` allows `*` (all authenticated users) or specific email addresses (e.g. `sheepdestroyer@gmail.com`).
  - Strict server-side filtering: unauthorized tiles are completely excluded from the HTTP and JSON responses.
  - Protected Admin UI (`/admin`) and CRUD API (`/api/admin/tiles`) with 403 Forbidden enforcement.

## Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `5003` | Listening port (Dev: `5004`) |
| `HOST` | `127.0.0.1` | Binding interface (Container: `0.0.0.0`) |
| `DATABASE_PATH` | `data/hub.db` | Path to persistent SQLite database |
| `ADMIN_EMAILS` | `sheepdestroyer@gmail.com,sheepyboy.x570@gmail.com` | Comma-separated admin emails |
| `ALLOW_LAN_ADMIN` | `true` | Allow default admin fallback for LAN/localhost queries without forward-auth |

## Development & Testing

```bash
# Run tests with 100% coverage
pytest

# Run linter
ruff check .

# Check formatting
ruff format --check .
```
