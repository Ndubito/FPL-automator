# src/update_data.py
from data.fpl_data_fetcher import FPLDataFetcher
import logging

def main():
    logging.basicConfig(level=logging.INFO)
    fetcher = FPLDataFetcher()
    fetcher.update_all_data()

if __name__ == "__main__":
    main()