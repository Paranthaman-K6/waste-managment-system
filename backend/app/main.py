"""FastAPI entry point.
Sets up the application, registers routers, and provides a simple health‑check.
Uses venv for runtime, postgres via podman for DB (no podman for backend).
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse as SlowJSONResponse

import os
from pathlib import Path

from .db.session import engine
from .core.config import get_settings

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Waste Management API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: SlowJSONResponse({"detail": "Rate limit exceeded"}, status_code=429))
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fix stale chunk 404: HTML must be no-cache, hashed assets immutable (Cloudflare respects)
@app.middleware("http")
async def cache_headers(request: Request, call_next):
    resp = await call_next(request)
    path = request.url.path
    ctype = resp.headers.get("content-type", "")
    if path.startswith("/assets/") and resp.status_code == 200:
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path == "/" or path == "/index.html" or ctype.startswith("text/html"):
        # SPA shell — never cache, otherwise old HTML requests old hashed chunks -> 404
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp

# Register routers from canonical api package (venv-based)
from .api import auth, user, collector, recycler, management, rewards, vouchers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(collector.router)
app.include_router(recycler.router)
app.include_router(management.router)
app.include_router(rewards.router)
app.include_router(vouchers.router)
@app.on_event("startup")
async def on_startup():
    print(f"[startup] cwd={Path.cwd()} file={__file__} DATABASE_URL={settings.DATABASE_URL} UPLOAD_DIR={settings.UPLOAD_DIR} PORT={os.getenv('PORT')}")
    try:
        dist_check = Path(__file__).resolve().parents[2] / "apps" / "web" / "dist"
        print(f"[startup] dist exists={dist_check.exists()} at {dist_check} cwd_dist={(Path.cwd() / 'apps' / 'web' / 'dist').exists()}")
    except Exception as e:
        print(f"[startup] dist check failed: {e}")
    # Create tables if they don't exist (simple sync for demo purposes) — resilient for Voroa single-instance sqlite
    try:
        from sqlmodel import SQLModel
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            # Backfill legacy rows where accepted_waste_types is NULL (project data)
            try:
                await conn.execute(text("UPDATE public_bins SET accepted_waste_types='[]' WHERE accepted_waste_types IS NULL"))
            except Exception as e:
                print(f"[startup] backfill public_bins skipped: {e}")
            try:
                await conn.execute(text("UPDATE recyclers SET accepted_waste_types='[]' WHERE accepted_waste_types IS NULL"))
            except Exception as e:
                print(f"[startup] backfill recyclers skipped: {e}")
        print("[startup] DB ready")
    except Exception as e:
        print(f"[startup] DB init failed (will still serve health): {e}")
    # Auto-seed demo data if DB is empty (ensures Mass Recycled KPI shows 25kg after sqlite wipe / Render redeploy)
    # Set AUTO_SEED=0 to disable for production with real data
    if os.getenv("AUTO_SEED", "1") != "0":
        try:
            from app.db.seed_demo import seed_all

            await seed_all()
            print("[startup] seed completed")
        except Exception as e:
            print(f"[startup] auto-seed skipped: {e}")

@app.get("/health", response_class=JSONResponse)
async def health_check():
    return {"status": "ok"}


# Serve uploads (proofs, reports) — always, required for frontend Download & proof_url
# Must be mounted BEFORE SPA fallback so /uploads/* is served, not fallback to index.html
try:
    from fastapi.staticfiles import StaticFiles

    upload_path = Path(settings.UPLOAD_DIR)
    if not upload_path.is_absolute():
        for base in [Path.cwd(), Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1]]:
            cand = base / upload_path
            if cand.exists() or upload_path.parts[0] not in base.parts:
                upload_path = cand
                if upload_path.exists():
                    break
        if not upload_path.exists():
            alt = Path("/app") / settings.UPLOAD_DIR.lstrip("./")
            if alt.parent.exists():
                upload_path = alt
    upload_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")
except Exception as e:
    print(f"[mount] uploads skipped: {e}")

# Serve built frontend (apps/web/dist) when present — enables single-port on Render
try:
    dist = Path(__file__).resolve().parents[2] / "apps" / "web" / "dist"
    # also try repo root when running with different cwd (e.g. /app on Render)
    if not dist.exists():
        alt = Path.cwd() / "apps" / "web" / "dist"
        if alt.exists():
            dist = alt
    if dist.exists() and (dist / "index.html").exists():
        from fastapi.staticfiles import StaticFiles

        # mount at /assets first (vite hashed assets) — immutable via middleware
        if (dist / "assets").exists():
            app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="assets")

        # SPA fallback for browser hard-refresh / direct URL (e.g. /analytics, /my-batches)
        # Use 404 handler instead of catch-all route so /uploads StaticFiles is not shadowed
        API_EXCLUDE = (
            "/auth", "/user", "/collector", "/recycler", "/management",
            "/rewards", "/vouchers", "/health", "/docs", "/redoc", "/openapi.json",
            "/assets", "/uploads",
        )

        @app.exception_handler(404)
        async def spa_404_handler(request: Request, exc):
            # API / asset 404s stay JSON
            if any(request.url.path.startswith(p) for p in API_EXCLUDE):
                # Let StaticFiles handle /uploads and /assets 404s natively (avoid HTML)
                if request.url.path.startswith("/uploads") or request.url.path.startswith("/assets"):
                    return JSONResponse({"detail": "Not found"}, status_code=404)
                return JSONResponse({"detail": "Not found"}, status_code=404)
            # SPA deep link → serve index.html
            idx = dist / "index.html"
            if idx.exists():
                return FileResponse(
                    str(idx),
                    media_type="text/html",
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0",
                    },
                )
            return JSONResponse({"detail": "Not found"}, status_code=404)

        # catch-all for SPA — must be last
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
except Exception:
    pass
