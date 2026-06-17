# Smart Bhopal — Grievance Redressal System (Backend)

Citizen-centric civic grievance backend with **verified resolution, escalation,
gamification and analytics**, built to the architecture & app-flow you provided.

- **Stack:** FastAPI · SQLAlchemy · SQLite (Postgres-ready) · JWT auth · bcrypt · pytest
- **Roles (RBAC):** Citizen · Worker · NGO · Nodal Officer · Higher Authority · Super Admin
- **Runs with zero external setup** (SQLite + auto-seed). Swap `DATABASE_URL` for Postgres in prod.

---

## Quick start

```bash
# 1. activate the virtualenv (already provisioned)
source venv/bin/activate

# 2. (optional) seed demo data — also runs automatically on startup
python -m app.seed

# 3. run the API
uvicorn app.main:app --reload

# Interactive docs:  http://localhost:8000/docs
```

### Run the tests

```bash
python -m pytest -q          # 49 tests, full lifecycle + RBAC + analytics
```

---

## Demo credentials (created by the seeder)

| Role            | Phone        | Password    |
|-----------------|--------------|-------------|
| Super Admin     | 9000000000   | `Admin@123` |
| Nodal Officer   | 9000000001   | `Passw0rd!` |
| Worker          | 9000000002   | `Passw0rd!` |
| Worker 2        | 9000000003   | `Passw0rd!` |
| NGO             | 9000000004   | `Passw0rd!` |
| Higher Authority| 9000000005   | `Passw0rd!` |
| Citizen         | 9000000006   | `Passw0rd!` |

Login: `POST /auth/login {"phone": "...", "password": "..."}` → returns a JWT.
Send it as `Authorization: Bearer <token>` on every protected request.

---

## Master complaint lifecycle (state machine)

```
submitted → verified → assigned → in_progress → resolved → closed
     │          │                                   │
     └─ rejected └─ escalated (→ NGO / Authority)    └─ reopened (if not satisfied)
```

Implemented in [`app/services/complaint_service.py`](app/services/complaint_service.py).
Every transition is guarded (wrong-state → `409`), writes a **status-history** row,
fires **notifications**, and records an **audit log**.

| Step | Actor | Endpoint |
|------|-------|----------|
| Register complaint (+AI validation, duplicate check, +points) | Citizen | `POST /complaints` |
| Verify / reject | Nodal Officer | `POST /nodal/complaints/{id}/verify` |
| Assign worker (+deadline) | Nodal Officer | `POST /nodal/complaints/{id}/assign` |
| Accept → Start (before image) → Complete (after image) | Worker | `POST /worker/tasks/{id}/{accept,start,complete}` |
| Verify work quality | Nodal Officer | `POST /nodal/complaints/{id}/verify-work` |
| Feedback (satisfied → closed, else → reopened) | Citizen | `POST /complaints/{id}/feedback` |
| Escalate to NGO / Authority | Nodal Officer / Authority | `POST /nodal/complaints/{id}/escalate` |
| Adopt + submit proof | NGO | `POST /ngo/complaints/{id}/{adopt,submit-proof}` |
| Reopen / request close | Citizen | `POST /complaints/{id}/{reopen,close-request}` |

---

## Endpoints by module

- **Auth** — `/auth/register`, `/auth/login`, `/auth/token` (OAuth2), `/auth/me`
- **Citizen** — `/complaints` (create), `/complaints/mine`, `/complaints/track/{tracking_id}`,
  `/complaints/{id}` (detail+history), feedback / reopen / close-request
- **Worker** — `/worker/tasks`, accept / start / complete
- **NGO** — `/ngo/available`, `/ngo/adopted`, adopt / submit-proof
- **Nodal Officer** — `/nodal/complaints` (queue + filters), `/nodal/workers`,
  verify / assign / verify-work / escalate / close
- **Higher Authority** — `/authority/dashboard`, `/authority/escalated`,
  `/authority/analytics/{areas,top-issues,ward-performance,worker-performance,ngo-performance,heatmap,engagement}`
- **Super Admin** — `/admin/users` (CRUD), `/admin/wards`, `/admin/categories`,
  `/admin/complaints`, `/admin/audit-logs`
- **Rewards** — `/rewards/me`, `/rewards/leaderboard`
- **Certificates** — `/certificates/me`, `/certificates/verify/{code}`
- **Notifications** — `/notifications`, mark read / read-all
- **Reference (frontend dropdowns)** — `/meta/categories`, `/meta/wards`, `/meta/enums`
- **Uploads** — `POST /uploads` (image/video → returns `/media/...` URL), served at `/media/*`

---

## Gamification (badges)

`POINTS`: submit `+10`, resolved-and-closed `+20`, worker completes `+15`.
Crossing a threshold auto-issues a **certificate** + notification.

| Points | Badge |
|--------|-------|
| 0–50    | Green Starter |
| 51–150  | Active Citizen |
| 151–300 | Cleanliness Champion |
| 301–500 | Swachh Hero |
| 500+    | Smart Bhopal Ambassador |

---

## Project layout

```
app/
  main.py            FastAPI app, middleware (CORS, gzip, security headers), routers
  config.py          env-driven settings
  database.py        engine / session / Base / init_db
  security.py        bcrypt hashing + JWT
  deps.py            DB session, current-user, require_roles() RBAC guard
  enums.py           roles, statuses, priorities, badge thresholds
  models/            SQLAlchemy: user, complaint(+history), feedback, notification,
                     certificate, ward, category, audit
  schemas/           Pydantic request/response models
  services/          business logic: auth, complaint state machine, rewards,
                     notifications, analytics, audit
  routers/           HTTP layer per role
  seed.py            idempotent demo data
tests/               pytest suite (auth, full flow, RBAC, rewards, analytics, admin, notifications)
```

## Security & performance notes

- Passwords hashed with **bcrypt** (direct lib — passlib is incompatible with bcrypt 5.x).
- **JWT** bearer tokens; per-route **role enforcement**; account-deactivation blocks login & tokens.
- Ownership checks on every single-complaint read (`assert_can_view`).
- Input validation via Pydantic (lengths, ranges, enums) → `422` on bad input.
- Middleware: **CORS**, **gzip**, security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).
- Upload guard: type allow-list + 10 MB size cap.
- Global exception handler returns clean JSON `500` (no stack-trace leakage).

## Switching to PostgreSQL

```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/smart_bhopal
python -m app.seed && uvicorn app.main:app
```
The existing `psycopg2-binary` dependency is already included.
