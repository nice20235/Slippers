# Migration helper scripts

This folder contains tools to analyze a local SQLite database, generate a best-effort PostgreSQL schema, copy data, and verify integrity.

Prerequisites
- Python 3.8+
- Install migration script dependencies locally (recommended to use a virtualenv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install psycopg2-binary
```

Quick steps
1. Analyze your local SQLite DB (default path `./slippers.db`):

```bash
python3 scripts/analyze_sqlite.py --db ./slippers.db
```

This writes `scripts/analysis/<timestamp>_sqlite_analysis.json` and a best-effort `migrations/pg_schema.sql`.

2. Review `migrations/pg_schema.sql` and adjust types / FKs as needed. The generated SQL is a best-effort conversion and should be reviewed before applying.

3. Run migration (creates tables and copies data):

```bash
python3 scripts/migrate_data.py --sqlite ./slippers.db --pg "dbname=mydb user=me password=pass host=127.0.0.1 port=5432"
```

4. Verify integrity:

```bash
python3 scripts/verify_integrity.py --sqlite ./slippers.db --pg "dbname=mydb user=me password=pass host=127.0.0.1 port=5432"
```

Notes and recommended flow
- Put your app into maintenance/read-only mode while migrating to avoid drift.
- For an async FastAPI app the recommended DB driver for PostgreSQL is `asyncpg` with SQLAlchemy `async` support. To keep changes minimal, update the `DATABASE_URL` environment variable to something like `postgresql+asyncpg://user:pass@localhost/dbname` and install `asyncpg`.
- If you prefer to use `psycopg2` everywhere instead, be aware it's synchronous and will require code changes if your app uses async DB sessions.

Logs
- Logs are written to `scripts/logs/`.

If you want, I can now:
- Run analysis here if you upload your `slippers.db` file or provide a path on the machine.
- Or continue and update `app/db/database.py` to switch to PostgreSQL with `asyncpg` and provide a small diff (minimal changes).
