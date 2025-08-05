# init_db.py
import logging
from sqlalchemy import text
from data.database import engine, SessionLocal
from database import Base

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_connection():
    """Test the database connection"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            logger.info("Database connection successful!")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def init_database():
    """Initialize the database by creating all tables"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("All tables created successfully!")

        # Test if we can create a session
        with SessionLocal() as session:
            # Try a simple query
            session.execute(text("SELECT 1"))
            logger.info("Session creation successful!")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    if test_connection():
        init_database()
    logger.info("Database initialization completed!")