# fpl_data_fetcher.py
import logging
from sqlalchemy.orm import Session
from datetime import datetime
from data.database import SessionLocal
from data.fpl_api import FPLApi
from models import Player, Team, Gameweek, ManagerPick, Transfer, PlayerGameweekStats, Manager

class FPLDataFetcher:
    def __init__(self):
        self.api = FPLApi()
        self.logger = logging.getLogger(__name__)

    def fetch_bootstrap_static(self, session: Session):
        """Fetch and update basic FPL data including teams, players, and gameweeks"""
        try:
            data = self.api.get_bootstrap_static()

            # Update teams
            for team_data in data['teams']:
                db_team = session.query(Team).filter_by(id=team_data['id']).first()
                if not db_team:
                    db_team = Team(
                        id=team_data['id'],
                        name=team_data['name'],
                        short_name=team_data['short_name'],
                        code=team_data['code'],
                        strength=team_data['strength'],
                        strength_attack_home=team_data['strength_attack_home'],
                        strength_attack_away=team_data['strength_attack_away'],
                        strength_defence_home=team_data['strength_defence_home'],
                        strength_defence_away=team_data['strength_defence_away']
                    )
                    session.add(db_team)
                else:
                    for key, value in team_data.items():
                        if hasattr(db_team, key):
                            setattr(db_team, key, value)

            # Update gameweeks
            for gw_data in data['events']:
                db_gw = session.query(Gameweek).filter_by(id=gw_data['id']).first()
                if not db_gw:
                    db_gw = Gameweek(
                        id=gw_data['id'],
                        name=f"Gameweek {gw_data['id']}",
                        deadline_time=datetime.strptime(gw_data['deadline_time'], '%Y-%m-%dT%H:%M:%SZ'),
                        average_entry_score=gw_data['average_entry_score'],
                        highest_score=gw_data['highest_score'],
                        is_current=gw_data['is_current'],
                        is_next=gw_data['is_next'],
                        is_finished=gw_data['is_finished']
                    )
                    session.add(db_gw)

            # Update players
            for player_data in data['elements']:
                db_player = session.query(Player).filter_by(id=player_data['id']).first()
                if not db_player:
                    db_player = Player(
                        id=player_data['id'],
                        web_name=player_data['web_name'],
                        first_name=player_data['first_name'],
                        second_name=player_data['second_name'],
                        team_id=player_data['team'],
                        position_id=player_data['element_type'],
                        now_cost=player_data['now_cost'] / 10.0,
                        selected_by_percent=player_data['selected_by_percent'],
                        form=player_data['form'],
                        total_points=player_data['total_points'],
                        status=player_data['status'],
                        chance_of_playing_next_round=player_data['chance_of_playing_next_round']
                    )
                    session.add(db_player)

            session.commit()
            self.logger.info("Bootstrap static data updated successfully")
        except Exception as e:
            self.logger.error(f"Error updating bootstrap static data: {e}")
            session.rollback()
            raise

    def fetch_manager_picks(self, session: Session, gameweek: int):
        """Fetch and store manager's team picks for a specific gameweek"""
        try:
            data = self.api.get_picks(gameweek)

            for pick_data in data['picks']:
                db_pick = ManagerPick(
                    entry_id=self.api.team_id,
                    gameweek=gameweek,
                    player_id=pick_data['element'],
                    position=pick_data['position'],
                    is_captain=pick_data['is_captain'],
                    is_vice_captain=pick_data['is_vice_captain'],
                    multiplier=pick_data['multiplier']
                )
                session.add(db_pick)

            session.commit()
            self.logger.info(f"Manager picks for gameweek {gameweek} updated successfully")
        except Exception as e:
            self.logger.error(f"Error updating manager picks for gameweek {gameweek}: {e}")
            session.rollback()
            raise

    def fetch_transfers(self, session: Session):
        """Fetch and store all transfers made by the manager"""
        try:
            transfers_data = self.api.get_transfers()

            for transfer_data in transfers_data:
                db_transfer = Transfer(
                    entry_id=self.api.team_id,
                    gameweek=transfer_data['event'],
                    transfer_time=datetime.strptime(transfer_data['time'], '%Y-%m-%dT%H:%M:%SZ'),
                    player_in_id=transfer_data['element_in'],
                    player_out_id=transfer_data['element_out'],
                    player_in_name=transfer_data.get('element_in_name', ''),
                    player_out_name=transfer_data.get('element_out_name', ''),
                    cost=transfer_data['cost']
                )
                session.add(db_transfer)

            session.commit()
            self.logger.info("Transfers updated successfully")
        except Exception as e:
            self.logger.error(f"Error updating transfers: {e}")
            session.rollback()
            raise

    def update_all_data(self):
        """Update all FPL data"""
        try:
            with SessionLocal() as session:
                self.fetch_bootstrap_static(session)

                # Get current gameweek
                current_gw = session.query(Gameweek).filter_by(is_current=True).first()
                if current_gw:
                    # Update data for all gameweeks up to current
                    for gw in range(1, current_gw.id + 1):
                        self.fetch_manager_picks(session, gw)

                self.fetch_transfers(session)
                self.logger.info("All FPL data updated successfully")
        except Exception as e:
            self.logger.error(f"Error in update_all_data: {e}")
            raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = FPLDataFetcher()
    fetcher.update_all_data()
