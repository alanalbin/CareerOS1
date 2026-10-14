import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from database import engine, Base
import models
from sqlalchemy import text

def reset_and_migrate():
    print("Connecting to database...")
    with engine.connect() as conn:
        # Check dialect
        dialect = engine.dialect.name
        print(f"Database dialect: {dialect}")

        if dialect == "postgresql":
            # Drop all public tables with cascade to clean out stale schemas
            print("Dropping obsolete tables in public schema with CASCADE...")
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
            conn.commit()
            print("Public schema reset cleanly.")
        else:
            # SQLite
            Base.metadata.drop_all(bind=engine)

        print("Recreating all Career OS production tables with exact schema...")
        Base.metadata.create_all(bind=engine)
        print("All tables recreated successfully!")

if __name__ == "__main__":
    reset_and_migrate()
