import logging
from optimizer.advisors import run_complete_advisor
from data.fpl_data_fetcher import FPLDataFetcher

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # First update data
        # logger.info("Updating FPL data...")
        # fetcher = FPLDataFetcher()
        # fetcher.update_all_data()
        
        # Run advisor
        logger.info("Running advisor system...")
        run_complete_advisor()
        
    except Exception as e:
        logger.error(f"Error running advisor system: {e}")
        raise

if __name__ == "__main__":
    main()