from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from data.database import Base

class Player(Base):
    __tablename__ = 'players'
    __table_args__ = {'extend_existing': True}  # Add this line


    id = Column(Integer, primary_key=True)
    web_name = Column(String, nullable=False)
    first_name = Column(String)
    second_name = Column(String)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    position_id = Column(Integer, nullable=False)
    now_cost = Column(Float, nullable=False)
    selected_by_percent = Column(Float)
    form = Column(Float)
    total_points = Column(Integer, default=0)
    status = Column(String)
    chance_of_playing_next_round = Column(Integer)

    # Relationships - using string references
    team = relationship("Team", back_populates="players")
    manager_picks = relationship("ManagerPick", back_populates="player")
    gameweek_stats = relationship("PlayerGameweekStats", back_populates="player")

    def __repr__(self):
        return f"<Player(id={self.id}, web_name='{self.web_name}', team_id={self.team_id})>"