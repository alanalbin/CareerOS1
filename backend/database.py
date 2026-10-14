import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()
logger = logging.getLogger("careeros.db")

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

def get_engine():
    global DATABASE_URL
    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)

    if DATABASE_URL:
        target_url = DATABASE_URL
        if target_url.startswith("postgresql://"):
            target_url = target_url.replace("postgresql://", "postgresql+psycopg2://", 1)

        try:
            pg_engine = create_engine(target_url, pool_pre_ping=True, pool_size=5, max_overflow=10, connect_args={"connect_timeout": 5})
            # Test connection
            with pg_engine.connect() as conn:
                logger.info("Successfully connected to PostgreSQL database.")
            return pg_engine
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed ({e}). Falling back to local persistent SQLite database.")

    sqlite_url = "sqlite:///./data/careeros.db"
    return create_engine(sqlite_url, connect_args={"check_same_thread": False})

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
