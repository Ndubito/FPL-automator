# fpl_data_fetcher.py
import logging

import requests
from sqlalchemy.orm import Session
from datetime import datetime
from data.database import SessionLocal
from data.fpl_api import FPLApi
from models import Player, Team, Gameweek, ManagerPick, Transfer, PlayerGameweekStats, Manager, Fixture
from models.create_missing_tables import create_missing_tables
from models.manager_info import ManagerInfo


class FPLDataFetcher:
    def __init__(self):
        self.api = FPLApi()
        # Ensure all tables exist before attempting to fetch data
        create_missing_tables()
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
                        is_finished=gw_data.get('finished', False)
                    )
                    session.add(db_gw)
                else:
                    # Update existing
                    db_gw.name = f"Gameweek {gw_data['id']}"
                    db_gw.deadline_time = datetime.strptime(gw_data['deadline_time'], '%Y-%m-%dT%H:%M:%SZ')
                    db_gw.average_entry_score = gw_data['average_entry_score']
                    db_gw.highest_score = gw_data['highest_score']
                    db_gw.is_current = gw_data['is_current']
                    db_gw.is_next = gw_data['is_next']
                    db_gw.is_finished = gw_data.get('finished', False)

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
                #update the player details
                else:
                    db_player.now_cost = player_data['now_cost'] / 10
                    db_player.selected_by_percent = player_data['selected_by_percent']
                    db_player.form = player_data['form']
                    db_player.total_points = player_data['total_points']
                    db_player.status = player_data['status']
                    db_player.chance_of_playing_next_round = player_data['chance_of_playing_next_round']

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
                # Check if this pick already exists
                db_pick = (
                    session.query(ManagerPick)
                    .filter_by(
                        entry_id=self.api.team_id,
                        gameweek=gameweek,
                        player_id=pick_data['element']
                    )
                    .first()
                )

                if db_pick:
                    db_pick.position = pick_data['position']
                    db_pick.is_captain = pick_data['is_captain']
                    db_pick.is_vice_captain = pick_data['is_vice_captain']
                    db_pick.multiplier = pick_data['multiplier']

                else:
                    # Insert new row
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
                db_transfer = (
                    session.query(Transfer)
                    .filter_by(
                        entry_id=self.api.team_id,
                        gameweek=transfer_data['event'],
                        transfer_time=transfer_data['time'],
                    )
                    .first()
                )

                if not db_transfer:
                    db_transfer = Transfer(
                        entry_id=self.api.team_id,
                        gameweek=transfer_data['event'],
                        transfer_time=datetime.strptime(transfer_data['time'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                        player_in_id=transfer_data['element_in'],
                        player_out_id=transfer_data['element_out'],
                        player_in_name=transfer_data.get('element_in_name', ''),
                        player_out_name=transfer_data.get('element_out_name', ''),
                        cost=transfer_data['element_in_cost']
                    )
                    session.add(db_transfer)

                session.commit()
            self.logger.info("Transfers updated successfully")
        except Exception as e:
            self.logger.error(f"Error updating transfers: {e}")
            session.rollback()
            raise

    def fetch_player_gameweek_stats(self, session: Session, gameweek: int):
        """Fetch and store detailed player stats for a specific gameweek"""
        try:

            bootstrap = self.api.get_bootstrap_static()
            bootstrap_players = {p["id"]: p for p in bootstrap["elements"]}

            # Get all players from a database to iterate through
            players = session.query(Player).all()

            for player in players:
                try:
                    # Fetch player's detailed stats for the gameweek
                    player_data = self.api.get_player_summary(player.id)

                    # Find the gameweek data in the player's history
                    gameweek_data = None
                    if "history" in player_data:
                        for gw_data in player_data["history"]:
                            if gw_data['round'] == gameweek:
                                gameweek_data = gw_data
                                break

                    if gameweek_data:
                        # Check if stats already exist for this player and gameweek
                        existing_stats = session.query(PlayerGameweekStats).filter_by(
                            player_id=player.id,
                            gameweek=gameweek
                        ).first()

                        bootstrap_info = bootstrap_players.get(player.id, {})
                        expected_points = float(bootstrap_info.get("ep_this", 0.0))

                        if not existing_stats:

                            db_stats = PlayerGameweekStats(
                                player_id=player.id,
                                gameweek=gameweek,
                                expected_points = expected_points,
                                points=gameweek_data.get('total_points', 0),
                                opponent_team=gameweek_data.get('opponent_team', ''),
                                was_home=gameweek_data.get('was_home', False),
                                minutes=gameweek_data.get('minutes', 0),
                                goals_scored=gameweek_data.get('goals_scored', 0),
                                assists=gameweek_data.get('assists', 0),
                                goals_conceded=gameweek_data.get('goals_conceded', 0),
                                saves=gameweek_data.get('saves', 0),
                                bonus=gameweek_data.get('bonus', 0),
                                bps=gameweek_data.get('bps', 0),
                                yellow_cards=gameweek_data.get('yellow_cards', 0),
                                red_cards=gameweek_data.get('red_cards', 0),
                                penalties_saved=gameweek_data.get('penalties_saved', 0),
                                penalties_missed=gameweek_data.get('penalties_missed', 0),
                                own_goals=gameweek_data.get('own_goals', 0),
                                expected_goals=gameweek_data.get('expected_goals', 0.0),
                                expected_assists=gameweek_data.get('expected_assists', 0.0),
                                expected_goal_involvements=gameweek_data.get('expected_goal_involvements', 0.0),
                                expected_goals_conceded=gameweek_data.get('expected_goals_conceded', 0.0)
                            )
                            session.add(db_stats)
                        else:
                            # Update existing stats
                            existing_stats.points = gameweek_data.get('total_points', existing_stats.points)
                            existing_stats.opponent_team = gameweek_data.get('opponent_team',
                                                                             existing_stats.opponent_team)
                            existing_stats.was_home = gameweek_data.get('was_home', existing_stats.was_home)
                            existing_stats.minutes = gameweek_data.get('minutes', existing_stats.minutes)
                            existing_stats.goals_scored = gameweek_data.get('goals_scored', existing_stats.goals_scored)
                            existing_stats.assists = gameweek_data.get('assists', existing_stats.assists)
                            existing_stats.goals_conceded = gameweek_data.get('goals_conceded',
                                                                              existing_stats.goals_conceded)
                            existing_stats.saves = gameweek_data.get('saves', existing_stats.saves)
                            existing_stats.bonus = gameweek_data.get('bonus', existing_stats.bonus)
                            existing_stats.bps = gameweek_data.get('bps', existing_stats.bps)
                            existing_stats.yellow_cards = gameweek_data.get('yellow_cards', existing_stats.yellow_cards)
                            existing_stats.red_cards = gameweek_data.get('red_cards', existing_stats.red_cards)
                            existing_stats.penalties_saved = gameweek_data.get('penalties_saved',
                                                                               existing_stats.penalties_saved)
                            existing_stats.penalties_missed = gameweek_data.get('penalties_missed',
                                                                                existing_stats.penalties_missed)
                            existing_stats.own_goals = gameweek_data.get('own_goals', existing_stats.own_goals)
                            existing_stats.expected_goals = gameweek_data.get('expected_goals',
                                                                              existing_stats.expected_goals)
                            existing_stats.expected_points = float(bootstrap_info.get("ep_this",
                                                                                existing_stats.expected_points))
                            existing_stats.expected_assists = gameweek_data.get('expected_assists',
                                                                                existing_stats.expected_assists)
                            existing_stats.expected_goal_involvements = gameweek_data.get('expected_goal_involvements',
                                                                                          existing_stats.expected_goal_involvements)
                            existing_stats.expected_goals_conceded = gameweek_data.get('expected_goals_conceded',
                                                                                       existing_stats.expected_goals_conceded)

                except Exception as player_error:
                    self.logger.warning(f"Error fetching stats for player {player.id}: {player_error}")
                    continue

            session.commit()
            self.logger.info(f"Player gameweek stats for GW {gameweek} updated successfully")

        except Exception as e:
            self.logger.error(f"Error updating player gameweek stats for GW {gameweek}: {e}")
            session.rollback()
            raise

    def fetch_manager(self, session: Session):
        if not self.api.team_id:
            raise ValueError("TEAM_ID not set in environment variables.")

        try:
            url = f"{self.api.BASE_URL}/entry/{self.api.team_id}/"
            response = requests.get(url)
            response.raise_for_status()

            data = response.json()
            manager_id = data["id"]

            # Check if manager exists in DB
            manager = session.query(Manager).get(manager_id)

            if manager:
                # Update existing manager
                manager.name = f"{data['player_first_name']} {data['player_last_name']}"
                manager.current_gw = data.get("current_event")
                manager.total_points = data.get("summary_overall_points")
                manager.overall_rank = data.get("summary_overall_rank")
            else:
                # Add new manager
                manager = Manager(
                    id=manager_id,
                    name=f"{data['player_first_name']} {data['player_last_name']}",
                    current_gw=data.get("current_event"),
                    total_points=data.get("summary_overall_points"),
                    overall_rank=data.get("summary_overall_rank")
                )
                session.add(manager)

            session.commit()
            print(f"Manager data saved: {manager}")

        except requests.exceptions.HTTPError as e:
            print(f"HTTP error fetching manager: {e}")
        except Exception as e:
            print(f"Error fetching manager: {e}")

    def fetch_manager_info(self, session: Session):
        """Fetch and store manager's basic information and metadata"""
        try:
            # Get manager's entry information
            entry_data = self.api.get_entry()

            # Also get chip usage information (if available)
            history_data = self.api.get_history()

            # Check if manager info already exists
            db_manager_info = session.query(ManagerInfo).filter_by(id=self.api.team_id).first()

            # Determine current gameweek
            current_gw = session.query(Gameweek).filter_by(is_current=True).first()
            current_gameweek = current_gw.id if current_gw else entry_data.get('current_event', 1)

            # Check chip usage from history
            chips_used = {
                'wildcard_used': False,
                'bench_boost_used': False,
                'triple_captain_used': False,
                'free_hit_used': False
            }

            if 'chips' in history_data:
                for chip in history_data['chips']:
                    chip_name = chip.get('name', '').lower()
                    if 'wildcard' in chip_name:
                        chips_used['wildcard_used'] = True
                    elif 'bboost' in chip_name or 'bench boost' in chip_name:
                        chips_used['bench_boost_used'] = True
                    elif '3xc' in chip_name or 'triple captain' in chip_name:
                        chips_used['triple_captain_used'] = True
                    elif 'freehit' in chip_name or 'free hit' in chip_name:
                        chips_used['free_hit_used'] = True

            if not db_manager_info:
                db_manager_info = ManagerInfo(
                    id=self.api.team_id,
                    current_gameweek=current_gameweek,
                    wildcard_used=chips_used['wildcard_used'],
                    bench_boost_used=chips_used['bench_boost_used'],
                    triple_captain_used=chips_used['triple_captain_used'],
                    free_hit_used=chips_used['free_hit_used']
                )
                session.add(db_manager_info)
            else:
                # Update existing manager info
                db_manager_info.current_gameweek = current_gameweek
                db_manager_info.wildcard_used = chips_used['wildcard_used']
                db_manager_info.bench_boost_used = chips_used['bench_boost_used']
                db_manager_info.triple_captain_used = chips_used['triple_captain_used']
                db_manager_info.free_hit_used = chips_used['free_hit_used']

            session.commit()
            self.logger.info("Manager info updated successfully")

        except Exception as e:
            self.logger.error(f"Error updating manager info: {e}")
            session.rollback()
            raise

    def update_all_data(self):
        """Update all FPL data"""
        try:
            with SessionLocal() as session:
                # 1. FOUNDATION DATA (must come first)
                self.logger.info("Fetching bootstrap static data...")
                self.fetch_bootstrap_static(session)

                self.logger.info("Fetching fixtures...")
                self.fetch_fixtures(session)

                self.logger.info("Fetching manager...")
                self.fetch_manager(session)

                # 2. MANAGER DATA (depends on gameweeks existing)
                self.logger.info("Fetching manager info...")
                self.fetch_manager_info(session)

                self.logger.info("Fetching transfers...")
                self.fetch_transfers(session)

                # Get current gameweek
                current_gw = session.query(Gameweek).filter_by(is_current=True).first()
                if current_gw:
                    # Update data for all gameweeks up to current
                    for gw in range(1, current_gw.id + 1):
                        self.fetch_manager_picks(session, gw)

                    start_gw = max(1, current_gw.id - 4)  # Last 5 gameweeks
                    self.logger.info(f"Fetching player gameweek stats for GWs {start_gw}-{current_gw}...")
                    for gw in range(start_gw, current_gw.id + 1):
                        try:
                            self.fetch_player_gameweek_stats(session, gw)
                        except Exception as e:
                            self.logger.warning(f"Could not fetch player stats for GW {gw}: {e}")
                            continue

                self.fetch_transfers(session)
                self.logger.info("All FPL data updated successfully")
        except Exception as e:
            self.logger.error(f"Error in update_all_data: {e}")
            raise

    def fetch_fixtures(self, session):
        """Fetch all fixtures from the FPL API"""
        try:
            fixtures_data = self.api.get_fixtures()  # Use the API method

        # Update fixtures (NEW ADDITION)

            for fixture in fixtures_data:
                # Check if fixture already exists
                db_fixture = session.query(Fixture).filter_by(id=fixture['id']).first()
                if not db_fixture:
                    db_fixture = Fixture(
                        id=fixture['id'],
                        gameweek=fixture.get('event', 0),
                        home_team_id=fixture['team_h'],
                        away_team_id=fixture['team_a'],
                        difficulty_home=fixture.get('team_h_difficulty', 0),
                        difficulty_away=fixture.get('team_a_difficulty', 0),
                        kickoff_time=datetime.strptime(fixture['kickoff_time'],
                                                       '%Y-%m-%dT%H:%M:%SZ') if fixture.get(
                            'kickoff_time') else None,
                        finished=fixture.get('finished', False)
                    )
                    session.add(db_fixture)
                else:
                    # Update existing fixture
                    db_fixture.gameweek = fixture.get('event', db_fixture.gameweek)
                    db_fixture.home_team_id = fixture['team_h']
                    db_fixture.away_team_id = fixture['team_a']
                    db_fixture.difficulty_home = fixture.get('team_h_difficulty',
                                                                  db_fixture.difficulty_home)
                    db_fixture.difficulty_away = fixture.get('team_a_difficulty',
                                                                  db_fixture.difficulty_away)
                    if fixture.get('kickoff_time'):
                        db_fixture.kickoff_time = datetime.strptime(fixture['kickoff_time'],
                                                                    '%Y-%m-%dT%H:%M:%SZ')
                    db_fixture.finished = fixture.get('finished', db_fixture.finished)
        except Exception as e:
            self.logger.error(f"Error updating fixtures: {e}")
            session.rollback()
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = FPLDataFetcher()
    fetcher.update_all_data()
    session = SessionLocal()

    current_gw = session.query(Gameweek).filter_by(is_current=True).first()
    fetcher.fetch_player_gameweek_stats(session, current_gw)

