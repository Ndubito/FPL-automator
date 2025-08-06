from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from data.database import Base

class Fixture(Base):
    __tablename__ = 'fixture'

    id = Column(Integer, primary_key=True)
    gameweek = Column(Integer)
    home_team_id = Column(Integer, ForeignKey('teams.id'))
    away_team_id = Column(Integer, ForeignKey('teams.id'))
    difficulty_home = Column(Integer)
    difficulty_away = Column(Integer)
    kickoff_time = Column(DateTime)
    finished = Column(Boolean, default=False)

