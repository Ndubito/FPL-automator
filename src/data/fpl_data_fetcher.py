# fpl_data_fetcher.py
import os
import requests
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Player, Team, Gameweek, ManagerPick, Transfer, PlayerGameweekStats, Manager
from models import create_missing_tables

# Ensure tables are created
Base.metadata.create_all(bind=engine)
create_missing_tables()

TEAM_ID = os.getenv("TEAM_ID")
BASE_URL = "https://fantasy.premierleague.com/api"


def fetch_bootstrap_static(session: Session):
    url = f"{BASE_URL}/bootstrap-static/"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    # Update teams
    for team in data['teams']:
        db_team = session.query(Team).filter_by(id=team['id']).first()
        if not db_team:
            db_team = Team(
                id=team['id'],
                name=team['name'],
                short_name=team['short_name'],
                strength=team['strength']
            )
            session.add(db_team)

    # Update gameweeks
    for gw in data['events']:
        db_gw = session.query(Gameweek).filter_by(id=gw['id']).first()
        if not db_gw:
            db_gw = Gameweek(
                id=gw['id'],
                name=gw['name'],
                deadline_time=gw['deadline_time'],
                finished=gw['finished']
            )
            session.add(db_gw)

    # Update players
    for player in data['elements']:
        db_player = session.query(Player).filter_by(id=player['id']).first()
        if not db_player:
            db_player = Player(
                id=player['id'],
                name=f"{player['first_name']} {player['second_name']}",
                team=player['team'],
                position=player['element_type'],
                price=player['now_cost'] / 10.0,
                total_points=player['total_points']
            )
            session.add(db_player)

    session.commit()


def fetch_manager_picks(session: Session, gameweek: int):
    url = f"{BASE_URL}/entry/{TEAM_ID}/event/{gameweek}/picks/"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    for pick in data['picks']:
        mp = ManagerPick(
            gameweek=gameweek,
            player_id=pick['element'],
            is_captain=pick['is_captain'],
            is_vice_captain=pick['is_vice_captain'],
            multiplier=pick['multiplier']
        )
        session.add(mp)
    session.commit()


def fetch_transfers(session: Session):
    url = f"{BASE_URL}/entry/{TEAM_ID}/transfers/"
    response = requests.get(url)
    response.raise_for_status()
    transfers = response.json()

    for t in transfers:
        transfer = Transfer(
            gameweek=t['event'],
            player_in=t['element_in'],
            player_out=t['element_out'],
            cost=t['cost']
        )
        session.add(transfer)
    session.commit()


def fetch_player_gameweek_stats(session: Session, gameweek: int):
    url = f"{BASE_URL}/event/{gameweek}/live/"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    for p in data['elements']:
        stat = PlayerGameweekStats(
            player_id=p['id'],
            gameweek=gameweek,
            minutes=p['stats']['minutes'],
            goals_scored=p['stats']['goals_scored'],
            assists=p['stats']['assists'],
            clean_sheets=p['stats']['clean_sheets'],
            points=p['stats']['total_points']
        )
        session.add(stat)
    session.commit()


def run_all_fetches():
    with SessionLocal() as session:
        fetch_bootstrap_static(session)
        for gw in range(1, 39):
            fetch_manager_picks(session, gw)
            fetch_player_gameweek_stats(session, gw)
        fetch_transfers(session)

def fetch_manager_summary(session: Session):
    url = f"{BASE_URL}/entry/{TEAM_ID}/"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    db_manager = session.query(Manager).filter_by(id=data['id']).first()
    if not db_manager:
        db_manager = Manager(id=data['id'])

    db_manager.name = data['player_first_name'] + " " + data['player_last_name']
    db_manager.current_gw = data['current_event']
    db_manager.total_points = data['summary_overall_points']
    db_manager.overall_rank = data['summary_overall_rank']

    session.add(db_manager)
    session.commit()


if __name__ == "__main__":
    run_all_fetches()
