# API — 7 Routers + Health

> `FastAPI 0.141` `SQLModel` `pydantic[email]` `python-multipart` `Argon2` `python-jose` `SlowAPI 5/min`

**Live:** [`https://wms.getvoroa.com`](https://wms.getvoroa.com) `health /health` `docs /docs` `openapi /openapi.json`

**Base:** `VITE_API_URL=""` → same-port via Vite `proxy` (`5173→8000`) + Caddy `:8080` (`handle /auth* → backend:8000`) + Render `uvicorn` single-port `dist` + `StaticFiles(/uploads)` `Cache-Control: public immutable` for `/assets`, `no-cache` for `/`.

**Auth:** `POST /auth/login {username,password} → {access_token, refresh_token, role, token_type}` `OAuth2PasswordBearer(tokenUrl=/auth/login)` `Authorization: Bearer` `localStorage wm_*` `backend/app/api/auth.py:21` `POST /auth/register` resident-only `UserRole.USER` `POST /auth/refresh` `GET /auth/me` `POST /auth/logout` (revoke).

| Prefix | File | Routes (key) |
|--------|------|--------------|
| `POST /auth` | `auth.py:21` | `login` `49` `register:25` `refresh:86` `logout:127` `me:136` |
| `/user` | `user.py:13` | `GET /bins` `POST /pickups {waste_type, quantity_kg>0, location, lat/lng}` `GET /pickups` `GET /analytics/summary` `PUT /profile` |
| `/collector` | `collector.py:14` | `GET /pickups/available` `POST /pickups/{id}/accept` `PUT /pickups/{id}/status {en_route,collected}` (creates `WasteBatch AVAILABLE`) `GET /bins` `GET /schedule` |
| `/recycler` | `recycler.py:19` | `GET /batches` `GET /batches/my` `POST /batches/{id}/request` `POST /batches/{id}/accept` `POST /batches/{id}/proof` (multipart `image/jpeg|png|webp` → `COMPLETED` + `award_points`) `PUT /batches/{id} {status:COMPLETED}` `GET /analytics/summary {total_kg 25}` |
| `/management` | `management.py:26` | `GET /dashboard/summary` `GET- POST /bins` `PUT /bins/{id}` `DELETE` `GET- POST /users` `DELETE /users/{id}` (FK `collector.user_id` nullify) `POST /reports/{users|pickups|batches|bins|rewards|vouchers|redemptions}` `GET /reports` |
| `/rewards` | `rewards.py:9` | `GET /rates` `GET /balance` `GET /history` |
| `/vouchers` | `vouchers.py:18` | `GET /vouchers` (active) `GET /all` (admin) `POST /redeem/{id}` `POST /` `PATCH /{id}` `DELETE` `GET /redemptions` `PATCH /redemptions/{id} {issued,cancelled}` |
| `GET /health` | `main.py:88` | `{"status":"ok"}` |
| `GET /docs` `/redoc` `/openapi.json` | `FastAPI` | Swagger |

**Schemas:** `schemas/__init__.py:246` `ReportResponse` `267 RewardBalance` `287 VoucherCreate cost_points>0 valid_until future` `333 RedemptionResponse`.

**RBAC:** `deps.py` `require_user|collector|recycler|management` `role` exact `UserRole.MANAGEMENT="management"` `is_active` check.

**Rate-limit:** `auth.py:49` `@limiter.limit("5/minute")` on `login`.
