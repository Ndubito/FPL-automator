from data.database import SessionLocal
from models import Player, ManagerPick
from sqlalchemy.orm import Session


def get_available_players(session: Session):
    """Fetch all players from the DB and map them for optimization"""
    players = session.query(Player).all()

    position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}

    available = []
    for p in players:
        if p.status != 'a':  # Skip unavailable (injured/suspended)
            continue
        available.append({
            'id': p.id,
            'name': p.web_name,
            'position': position_map[p.position_id],
            'price': p.now_cost,
            'expected_points': float(p.form),  # Use form as proxy for expected points
            'team_id': p.team_id
        })
    return available

def get_current_team(session: Session, gameweek: int):
    """Get the user's current squad for the given gameweek"""
    picks = session.query(ManagerPick).filter_by(gameweek=gameweek).all()
    players = session.query(Player).filter(Player.id.in_([p.player_id for p in picks])).all()

    position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}

    team = []
    for p in players:
        team.append({
            'id': p.id,
            'name': p.web_name,
            'position': position_map[p.position_id],
            'price': p.now_cost,
            'expected_points': float(p.form),
            'team_id': p.team_id
        })
    return team