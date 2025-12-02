# Slippers API

FastAPI-based slippers ordering & payment system with user authentication, catalog, orders, and OCTO payment integration.

## Quick overview

- Stack: FastAPI, async SQLAlchemy (2.x), PostgreSQL (asyncpg), Pydantic v2
- Payments: OCTO gateway integration (create, webhook notify, refund)
- Auth: JWT (access + refresh) stored in HttpOnly cookies
- Features: catalog (slippers & categories), multi-image upload, orders, payments, basic admin endpoints


## Setup (development)

1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create a local `.env` (copy from `.env.example` if present) and fill values — do not commit it.

3. Initialize sample data (optional)

```bash
python init_system.py
```

4. Run dev server

```bash
python -m uvicorn app.main:app --reload
```

## Important endpoints (summary)

- Auth: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`
- Users: `/users/` (admin), `/users/{id}`
- Slippers: `/slippers/`, `/slippers/{id}`, image upload endpoints
- Orders: `/orders/` (create/update/list)
- Payments (OCTO): `/payments/octo/create`, `/payments/octo/notify`, `/payments/octo/refund`

See the code in `app/api/endpoints` for full request/response details and validation schemas.

## Contributing / Next steps

- If you'd like, I can add CI (ruff + black), pre-commit hooks, and a small smoke test harness to keep the repo clean and make it easier for the team to review changes.

---

Happy hacking 🥿