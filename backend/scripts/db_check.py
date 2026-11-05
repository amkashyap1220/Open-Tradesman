"""Check a Postgres database before pointing the API at it.

Usage (from backend/, venv active). Pass the URL as an env var so it never lands in .env:
    DATABASE_URL='postgresql://user:pass@host/db?sslmode=require' python -m scripts.db_check

Creates the tables, seeds the demo tradesperson + price book if empty, and prints counts.
Safe to run more than once.
"""

from sqlalchemy import text
from sqlmodel import Session, func, select

from app.db import engine, init_db
from app.models import PriceBookItem, Tradesperson
from app.seed import seed


def main() -> None:
    url = engine.url
    print(f"Database: {url.get_backend_name()}+{url.get_driver_name()} at {url.host}/{url.database}")
    if url.get_backend_name() == "sqlite":
        print("That's the local SQLite file. Set DATABASE_URL to your Postgres URL to check that instead.")
    with engine.connect() as conn:
        print("Server:", conn.execute(text("select version()" if url.get_backend_name() != "sqlite" else "select sqlite_version()")).scalar())
    init_db()
    seed()
    with Session(engine) as s:
        tps = s.exec(select(func.count()).select_from(Tradesperson)).one()
        items = s.exec(select(func.count()).select_from(PriceBookItem)).one()
    print(f"Tables OK. Tradespeople: {tps}, price book items: {items}")


if __name__ == "__main__":
    main()
