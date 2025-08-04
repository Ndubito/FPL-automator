import os
import requests
from dotenv import load_dotenv

class FPLApi:
    BASE_URL = "https://fantasy.premierleague.com/api"

    def __init__(self):
        load_dotenv()  # Load environment variables from .env
        self.session = requests.Session()
        self.team_id = os.getenv("TEAM_ID")

    def get_bootstrap_static(self):
        """Get all players, teams, and gameweek data"""
        url = f"{self.BASE_URL}/bootstrap-static/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_manager_team(self):
        """Get manager's general team info"""
        url = f"{self.BASE_URL}/entry/{self.team_id}/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_picks(self, gameweek):
        """Get your team picks for a specific gameweek"""
        url = f"{self.BASE_URL}/entry/{self.team_id}/event/{gameweek}/picks/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_transfers(self):
        """Get all transfers made"""
        url = f"{self.BASE_URL}/entry/{self.team_id}/transfers/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
