import argparse
import os
import sys

import psycopg2


def apply_sql(pg_dsn: str, sql_path: str) -> None:
    if not os.path.exists(sql_path):
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    print(f"Applying SQL from {sql_path} to {pg_dsn}")
    conn = psycopg2.connect(pg_dsn)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
        print("Done.")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a SQL file to a PostgreSQL database.")
    parser.add_argument("--pg", dest="pg_dsn", required=True, help="PostgreSQL DSN")
    parser.add_argument("--file", dest="sql_path", required=True, help="Path to SQL file")
    args = parser.parse_args()

    try:
        apply_sql(args.pg_dsn, args.sql_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
