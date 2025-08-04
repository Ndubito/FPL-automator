from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Player(Base):
    __tablename__ = 'players'

    id = Column(Integer, primary_key=True)
    web_name = Column(String)
    first_name = Column(String)
    second_name = Column(String)
    team_id = Column(Integer)
    position_id = Column(Integer)
    now_cost = Column(Float)
    selected_by_percent = Column(Float)
    form = Column(Float)
    total_points = Column(Integer)
    status = Column(String)
    chance_of_playing_next_round = Column(Integer)

class Gameweek(Base):
    __tablename__ = 'gameweeks'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    deadline_time = Column(DateTime)
    average_entry_score = Column(Integer)
    highest_score = Column(Integer)
    is_current = Column(Boolean)
    is_next = Column(Boolean)
    is_finished = Column(Boolean)

class ManagerPick(Base):
    __tablename__ = 'manager_picks'

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer)
    gameweek = Column(Integer)
    player_id = Column(Integer, ForeignKey('players.id'))
    position = Column(Integer)
    is_captain = Column(Boolean)
    is_vice_captain = Column(Boolean)
    multiplier = Column(Integer)
    points = Column(Integer)

class Transfer(Base):
    __tablename__ = 'transfers'

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer)
    gameweek = Column(Integer)
    transfer_time = Column(DateTime)
    player_in_id = Column(Integer)
    player_out_id = Column(Integer)
    player_in_name = Column(String)
    player_out_name = Column(String)
    is_wildcard = Column(Boolean)
    is_free_hit = Column(Boolean)
    is_costed = Column(Boolean)
    cost = Column(Integer)

class PlayerGameweekStats(Base):
    __tablename__ = 'player_gameweek_stats'

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'))
    gameweek = Column(Integer)
    opponent_team = Column(String)
    was_home = Column(Boolean)
    minutes = Column(Integer)
    goals_scored = Column(Integer)
    assists = Column(Integer)
    goals_conceded = Column(Integer)
    saves = Column(Integer)
    bonus = Column(Integer)
    bps = Column(Integer)
    yellow_cards = Column(Integer)
    red_cards = Column(Integer)
    penalties_saved = Column(Integer)
    penalties_missed = Column(Integer)
    own_goals = Column(Integer)
    expected_goals = Column(Float)
    expected_assists = Column(Float)
    expected_goal_involvements = Column(Float)
    expected_goals_conceded = Column(Float)

class Team(Base):
    __tablename__ = 'teams'

    id = Column(Integer, primary_key=True)  # Matches FPL API team id
    name = Column(String, nullable=False)  # Full team name (e.g., 'Arsenal')
    short_name = Column(String, nullable=False)  # Abbreviation (e.g., 'ARS')
    code = Column(Integer, unique=True, nullable=True)  # Unique team code
    strength = Column(Integer, nullable=True)  # General team strength
    strength_attack_home = Column(Integer, nullable=True)
    strength_attack_away = Column(Integer, nullable=True)
    strength_defence_home = Column(Integer, nullable=True)
    strength_defence_away = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}', short_name='{self.short_name}')>"

class Manager(Base):
    __tablename__ = "managers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    current_gw = Column(Integer)
    total_points = Column(Integer)
    overall_rank = Column(Integer)

    def __repr__(self):
        return f"<Manager {self.name} - GW {self.current_gw} - {self.total_points} pts>"

def get_db_session():
    """Get a database session"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)