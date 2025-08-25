from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from data.database import Base

class PlayerGameweekStats(Base):
    __tablename__ = 'player_gameweek_stats'
    __table_args__ = {'extend_existing': True}  # Add this line


    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    gameweek = Column(Integer, ForeignKey('gameweeks.id'), nullable=False)
    expected_points = Column(Float, nullable=False)
    points = Column(Integer, default=0)
    opponent_team = Column(String)
    was_home = Column(Boolean)
    minutes = Column(Integer, default=0)
    goals_scored = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    goals_conceded = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    bonus = Column(Integer, default=0)
    bps = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    penalties_saved = Column(Integer, default=0)
    penalties_missed = Column(Integer, default=0)
    own_goals = Column(Integer, default=0)
    expected_goals = Column(Float, default=0.0)
    expected_assists = Column(Float, default=0.0)
    expected_goal_involvements = Column(Float, default=0.0)
    expected_goals_conceded = Column(Float, default=0.0)

    # Relationships
    player = relationship("Player", back_populates="gameweek_stats")
    gameweek_obj = relationship("Gameweek", back_populates="player_stats")

    def __repr__(self):
        return f"<PlayerGameweekStats(player={self.player_id}, gw={self.gameweek}, mins={self.minutes})>"

