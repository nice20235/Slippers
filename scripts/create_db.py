#!/usr/bin/env python3
"""
Create a PostgreSQL database if it doesn't exist.

Usage:
  python3 scripts/create_db.py --pg "postgresql://user:pass@host:5432/postgres" --dbname slippers
"""
import argparse
import psycopg2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pg", required=True, help="Connection string to a maintenance DB (e.g. postgresql://user:pass@host:5432/postgres)")
    parser.add_argument("--dbname", required=True, help="Database name to create")
    args = parser.parse_args()

    conn = psycopg2.connect(args.pg)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (args.dbname,))
            exists = cur.fetchone() is not None
            if exists:
                print(f"Database '{args.dbname}' already exists")
                return
            cur.execute(f"CREATE DATABASE \"{args.dbname}\";")
            print(f"Database '{args.dbname}' created")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
