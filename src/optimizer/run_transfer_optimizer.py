from optimizer.transfer_optimizer import TransferOptimizer
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

def run_optimizer():
    with SessionLocal() as session:
        # Get latest gameweek with picks
        latest_pick = session.query(ManagerPick).order_by(ManagerPick.gameweek.desc()).first()
        if not latest_pick:
            print("No manager picks found.")
            return

        gw = latest_pick.gameweek
        available_players = get_available_players(session)
        current_team = get_current_team(session, gw)

        optimizer = TransferOptimizer()
        selected = optimizer.optimize_transfers(current_team, available_players, budget=100.0)

        print(f"\n📊 Suggested Transfers (GW {gw}):\n")
        for p in selected:
            print(f"{p['name']} - {p['position']} - £{p['price']} - {p['expected_points']} pts")

if __name__ == "__main__":
    run_optimizer()
