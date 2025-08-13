from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from data.database import Base


class Fixture(Base):
    __tablename__ = 'fixtures'
    __table_args__ = {'extend_existing': True}  # Add this line


    id = Column(Integer, primary_key=True, autoincrement=True)
    gameweek = Column(Integer, nullable=False)

    home_team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    away_team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)

    difficulty_home = Column(Integer, nullable=False)
    difficulty_away = Column(Integer, nullable=False)

    kickoff_time = Column(DateTime, nullable=False)
    finished = Column(Boolean, default=False)

    # Relationships to Team model (if you have a Team model)
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])

    def __repr__(self):
        return f"<Gameweek {self.id}: GW{self.gameweek} - Home {self.home_team_id} vs Away {self.away_team_id}>"

