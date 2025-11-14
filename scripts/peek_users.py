import asyncio
from datetime import datetime
from typing import Any

import asyncpg
import sys
import os

# Ensure project root is on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.core.config import settings


async def main() -> None:
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    print(f"Connecting to: {dsn}")
    conn = await asyncpg.connect(dsn)
    try:
        rows = await conn.fetch(
            """
            SELECT id, phone_number, name, surname, is_admin, created_at
            FROM users
            ORDER BY id DESC
            LIMIT 10
            """
        )
        if not rows:
            print("No users found.")
            return
        print("Last users:")
        for r in rows:
            created = r["created_at"]
            if isinstance(created, datetime):
                created_s = created.strftime("%Y-%m-%d %H:%M:%S")
            else:
                created_s = str(created)
            print(
                f"- id={r['id']}, phone={r['phone_number']}, name={r['name']} {r['surname'] or ''}, admin={r['is_admin']}, created_at={created_s}"
            )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
