from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

load_dotenv()

# If DATABASE_URL is not set in .env, default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# For SQLite, you usually need check_same_thread=False
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db_session():
    """Get a database session"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)
