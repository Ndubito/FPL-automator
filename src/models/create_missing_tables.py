import logging
from data.database import Base, engine

def create_missing_tables():
    try:
        Base.metadata.create_all(bind=engine)
        logging.info("All missing tables created successfully.")
    except Exception as e:
        logging.error(f"Error creating tables: {e}")
