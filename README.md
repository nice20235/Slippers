# Slippers API

FastAPI-based slippers ordering & payment system with user authentication, catalog, orders, and OCTO payment integration.

## Features

- **Authentication**: JWT (access + refresh) in HttpOnly cookies
- **Role-Based Access**: Admin vs user protected endpoints
- **Slipper Catalog**: CRUD + pagination, search, sorting, category filter, multi-image upload
- **Categories**: CRUD & caching
- **Orders**: Creation with multiple items, status transitions, finance filter (only paid/refunded)
- **Payments (OCTO)**: One‑stage auto-capture prepare_payment, webhook (notify) handling, refunds
## Maintenance/cleanup notes

- Deprecated/unused modules removed: `app/api/endpoints/food.py`, `app/api/endpoints/system.py`, `app/crud/food.py`, `app/schemas/simple_order.py`.
- Slipper replaces legacy "food" naming everywhere; no public routes were removed.
- Health diagnostics kept at `/health`; extended diagnostics endpoint was removed.
- Requirements pruned slightly; if you need DNS or Alembic templates on deploy, keep `dnspython`, `Mako`, and `PyYAML`.

- **Caching Layer**: In‑memory TTL cache with pattern invalidation
- **Security & Performance**: Rate limiting, security headers, gzip, performance timing headers
- **Async Stack**: FastAPI + SQLAlchemy 2.0 async + PostgreSQL with asyncpg driver

## Setup

1. **Install dependencies**
  ```bash
  pip install -r requirements.txt
  ```

2. **Environment Configuration** – create a `.env` file in project root:
  ```env
  # --- Core ---
  DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/slippers
  SECRET_KEY=change_me_strong_secret
  ALGORITHM=HS256
  ACCESS_TOKEN_EXPIRE_MINUTES=15
  REFRESH_TOKEN_EXPIRE_DAYS=7
  ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.domain

  # --- OCTO Payments ---
  OCTO_API_BASE=https://secure.octo.uz
  OCTO_SHOP_ID=your_shop_id
  OCTO_SECRET=your_secret
  OCTO_RETURN_URL=https://your-frontend.domain/
  OCTO_NOTIFY_URL=https://your-backend.domain/payments/octo/notify
  OCTO_LANGUAGE=ru
  OCTO_AUTO_CAPTURE=true
  OCTO_CURRENCY=UZS
  OCTO_TEST=true
  # Slippers API

  FastAPI-based backend for slippers ordering, catalog, user management and OCTO payments.

  This README was trimmed and corrected to reflect the current repository state. Removed references to transient scripts and helper files that are not part of the repository.

  ## Quick overview

  - Stack: FastAPI, async SQLAlchemy (2.x), PostgreSQL (asyncpg), Pydantic v2
  - Payments: OCTO gateway integration (create, webhook notify, refund)
  - Auth: JWT (access + refresh) stored in HttpOnly cookies
  - Features: catalog (slippers & categories), multi-image upload, orders, payments, basic admin endpoints

  ## Requirements

  - Python 3.10+ (recommended)
  - PostgreSQL database
  - See `requirements.txt` for Python dependencies

  ## Setup (development)

  1. Install dependencies

  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

  2. Copy `.env.example` (if you have one) or create `.env` in the project root. Minimal variables:

  ```env
  DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/slippers
  SECRET_KEY=change_me
  OCTO_API_BASE=https://secure.octo.uz
  OCTO_SHOP_ID=
  OCTO_SECRET=
  OCTO_NOTIFY_URL=http://your-host/payments/octo/notify
  DEBUG=True
  ```

  3. Initialize sample data (optional)

  ```bash
  python init_system.py
  ```

  4. Run dev server

  ```bash
  python -m uvicorn app.main:app --reload
  ```

  For production, run uvicorn/gunicorn with multiple workers behind a reverse proxy (nginx). This repo doesn't include production helper scripts by default; adapt the service file you use in deployment.

  ## Database

  - The app uses async SQLAlchemy models in `app/models`.
  - Create the PostgreSQL database manually and provide `DATABASE_URL`.
  - Migrations are not included in this repo; the codebase uses a minimal set of migration helpers when needed.

  ## Important endpoints (summary)

  - Auth: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`
  - Users: `/users/` (admin), `/users/{id}`
  - Slippers: `/slippers/`, `/slippers/{id}`, image upload endpoints
  - Orders: `/orders/` (create/update/list)
  - Payments (OCTO): `/payments/octo/create`, `/payments/octo/notify`, `/payments/octo/refund`

  See the code in `app/api/endpoints` for full request/response details and validation schemas.

  ## OCTO integration notes

  - By default, the app does not send `user_data` to OCTO unless configured and validated. See `app/services/octo.py` and `app/core/config.py` for `OCTO_EXTRA_PARAMS` and `OCTO_SEND_USER_DATA` flags.
  - Ensure `OCTO_NOTIFY_URL` is reachable by OCTO and responds quickly. The webhook updates payment and order status on notify.

  ## Maintenance & cleanup performed

  - Removed references to transient `scripts/` helpers from the README (the directory is not present).
  - Ensured README only references files and services that exist in this repository.

  ## Contributing / Next steps

  If you want me to continue with deeper architecture cleanup (safe refactors, remove dead code, add typing & ruff/black, CI, tests), tell me which of the following you want prioritized:

  1. Add automated linting (ruff/black) and fix style issues
  2. Add/enable tests (pytest) and a few unit/integration tests for core flows
  3. Remove deprecated modules and run a code-usage analysis to safely delete dead code
  4. Produce a short architecture diagram and a one-page technical summary for leadership

  Pick one or more items and I will proceed.

  ---

  Happy hacking 🥿