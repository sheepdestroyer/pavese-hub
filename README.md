# Pavese Cloud Hub (`hub.pavese.fr` / `hub.vendeuvre.lan`)

> **Master Generic Specification**: [manuals/pavese-hub.md](https://github.com/sheepdestroyer/x570-boy-infra/blob/main/manuals/pavese-hub.md)

Unified Services Directory Hub with Dynamic Admin RBAC Tile Visibility & Reverse-Proxy Authorization.

## Architecture

- **Backend**: FastAPI 0.115+ (Python 3.12+), SQLite with automated initial seed migration.
- **Frontend**: Clean glassmorphism dark mode with Jinja2 server-side filtered rendering and interactive Admin Management Dashboard.
- **Security & Single-Source-of-Truth RBAC**:
  - Ingress forward-auth via Google OAuth2-Proxy (`X-Auth-Request-Email` header).
  - Configurable admin privileges via `ADMIN_EMAILS` environment variable.
  - Per-tile visibility & subdomain ACLs: `allowed_users` allows `*` (all authenticated users) or specific email addresses (e.g. `sheepdestroyer@gmail.com`).
  - Dynamic reverse-proxy authorization endpoint (`GET/HEAD /api/authz`): evaluates per-subdomain access from `hub.db` for Freedora DMZ HAProxy (`lua.auth-intercept`).
  - Auto-synced OAuth2 whitelist (`ALLOWED_EMAILS_PATH`): automatically regenerates `allowed_emails.txt` (with dotted and dotless Gmail normalization) on startup and on every tile CRUD change.
  - Protected Admin UI (`/admin`) and CRUD API (`/api/admin/tiles`) with 403 Forbidden enforcement.

## Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `5003` | Listening port (Dev: `5004`) |
| `HOST` | `127.0.0.1` | Binding interface (Container: `0.0.0.0`) |
| `DATABASE_PATH` | `data/hub.db` | Path to persistent SQLite database |
| `ALLOWED_EMAILS_PATH` | `""` | Optional path to auto-synced `oauth2-proxy` `allowed_emails.txt` |
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

## Production Deployment (Quadlet)

The production Quadlet is tracked in [`deploy/pavese-hub.container`](deploy/pavese-hub.container) (unit `pavese-hub.service`, container `production-pavese-hub`, loopback `127.0.0.1:5003`). It sets `Sysctl="net.ipv4.ip_local_port_range=62000 65000"` so pasta's host-side UDP flow sockets stay off the host's ephemeral range (see the x570 wiki concept `pasta-ephemeral-port-range`).

After a release is merged (E10), install it on the host:

```bash
deploy/install.sh --dry-run          # show what would change
deploy/install.sh --restart          # back up the old unit, install, daemon-reload, restart pavese-hub.service
```

`install.sh` is idempotent, backs up a differing unit as `<unit>.bak-<timestamp>`, and wraps `systemctl --user` in `timeout`. Use `--no-reload` to skip `daemon-reload`, `--dest DIR` for another Quadlet directory. `tests/test_deploy.py` pins the invariants and exercises the script.
