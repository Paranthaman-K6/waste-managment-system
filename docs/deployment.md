# Deployment — Podman Single-File + Render + Voroa

> `podman-compose.yml` **canonical** (no `docker-compose.yml`) `Caddy :8080` `Uploads /app/uploads` `AUTO_SEED=1`

## Live Deployments

| Env | URL | Branch | Service | Health | Deploy Via |
|-----|-----|--------|---------|--------|------------|
| **Prod (Voroa)** | [`https://wms.getvoroa.com`](https://wms.getvoroa.com) | `main` | `1v1j43kcitq8z06ci9ior1ub` | [`/health`](https://wms.getvoroa.com/health) [`/docs`](https://wms.getvoroa.com/docs) | `Dockerfile` at `/` `Root /` `MCP voroa_get_service_status` |
| **Prod (Render)** | [`https://waste-managment-system-873w.onrender.com`](https://waste-managment-system-873w.onrender.com) | `main` | `srv-dabh7gm1egvs73c3l10g` `python free oregon` | [`/health`](https://waste-managment-system-873w.onrender.com/health) [`/docs`](https://waste-managment-system-873w.onrender.com/docs) [`/analytics`](https://waste-managment-system-873w.onrender.com/analytics) | `MCP https://mcp.render.com/mcp` `POST /v1/services/.../deploys` |
| **Local Podman** | [`http://localhost:8080`](http://localhost:8080) | `main` | `podman-compose.yml` `backend:8000` `frontend:80` `caddy:8080` | `http://localhost:8000/health` | `podman-compose up -d --build` |
| **Local Vite** | [`http://localhost:5173`](http://localhost:5173) | `main` | `vite proxy` | `http://127.0.0.1:8000/health` | `./start.sh` |

> **Quick Live Check:** `curl https://wms.getvoroa.com/health # {"status":"ok"}`

## Voroa (MCP `https://api.getvoroa.com/mcp`)

- **Service:** `wms` `1v1j43kcitq8z06ci9ior1ub` `https://wms.getvoroa.com`
- **Root Directory:** `/` (repo root)
- **Branch:** `main`
- **Build Command:** `pip install -r backend/requirements.txt && pip install "pydantic[email]" python-multipart && npm install && npm run build`
- **Start Command:** `PYTHONPATH=backend python -m app.db.seed_demo; uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check:** `/health`
- **Database:** SQLite (default `sqlite+aiosqlite:///./test.db`, zero-config) or PostgreSQL (via `DATABASE_URL`)
- **Required Env:**
  - `DATABASE_URL`: `sqlite+aiosqlite:///./test.db` (or omit to use default SQLite)
  - `JWT_SECRET_KEY`: `supersecretkey` (or `<32-char-random-key>`)
  - `UPLOAD_DIR`: `/app/uploads` (or `./uploads`)
  - `VITE_API_URL`: `""` (single-port SPA mount via `backend/app/main.py:115-161`)
  - `PYTHONPATH`: `backend`

## Podman (prod-like)

```bash
podman-compose -f podman-compose.yml up -d --build
# backend: python:3.12-slim + curl + alembic + seed_demo → :8000 healthy
# frontend: node:20-alpine --npm ci --build → nginx:alpine :80 try_files
# caddy: caddy:2-alpine :8080 handle /auth* → backend:8000 handle { frontend:80 }
podman ps # waste-backend healthy :8000, waste-frontend :80, waste-caddy :8080
curl :8000/health # {"status":"ok"}
curl :8080/ # <!doctype html> no-cache
curl :8080/assets/index-*.js # 200 immutable
curl :8080/uploads/reports/*.csv # 200 text/csv utf-8-sig
podman-compose down      # volumes sqlite_data + upload_data persist
podman-compose down -v   # wipe → next up auto-seeds 6 bins + 25kg + 5 vouchers
```

**Env:** `DATABASE_URL sqlite+aiosqlite:////app/data/waste.db` (`sqlite_data:/app/data`) `JWT_SECRET_KEY supersecretkey` `UPLOAD_DIR /app/uploads` `VITE_API_URL=""` `PYTHONPATH /app` `Containerfile:21 mkdir -p /app/uploads`.

## Render (MCP `https://mcp.render.com/mcp`)

`service srv-dabh7gm1egvs73c3l10g` `https://waste-managment-system-873w.onrender.com` `branch main` `env python` `build: pip install -r backend/requirements.txt && pip install pydantic[email] python-multipart && npm install && npm run build` `start: alembic upgrade head; PYTHONPATH=backend python -m app.db.seed_demo; uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT` `health /health` `plan free` `region oregon`.

`backend/app/main.py:93` serves `dist` + `/uploads` single-port `FileResponse no-cache` for `index.html` + `StaticFiles` for `/assets` `immutable` + `ErrorBoundary` `chunk-reload` auto-reload on `Failed to fetch dynamically imported module`.

**Caddy:** `Caddyfile:3 handle /vouchers*` (not `/vouchers/*`) + `handle /auth|/user|/collector|/recycler|/management|/rewards|/health|/docs|/openapi.json|/uploads → backend:8000`.

**MCP:** `~/.config/opencode/opencode.jsonc: render: { url: https://mcp.render.com/mcp, headers: {Authorization: rnd_kxyrKFGt...}}` `curl -H "Authorization: Bearer $TOKEN" https://api.render.com/v1/services/.../deploys` `POST /deploys clearCache`.

## Nginx

`apps/web/nginx.conf:7 try_files $uri $uri/ /index.html` `location /assets/ expires 1y immutable`.

## ENV

`.env.example` `DATABASE_URL` `JWT_SECRET_KEY` `JWT_ALGORITHM HS256` `ACCESS_TOKEN_EXPIRE_MINUTES 30` `REFRESH_TOKEN_EXPIRE_DAYS 7` `UPLOAD_DIR` `VITE_API_URL=""` `POSTGRES_*` for `start.sh --postgres`.