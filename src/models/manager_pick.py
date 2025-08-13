from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from data.database import Base

class ManagerPick(Base):
    __tablename__ = 'manager_picks'
    __table_args__ = {'extend_existing': True}  # Add this line


    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey('managers.id'), nullable=False)
    gameweek = Column(Integer, ForeignKey('gameweeks.id'), nullable=False)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    position = Column(Integer, nullable=False)
    is_captain = Column(Boolean, default=False)
    is_vice_captain = Column(Boolean, default=False)
    multiplier = Column(Integer, default=1)
    points = Column(Integer, default=0)

    # Relationships
    manager = relationship("Manager", back_populates="picks")
    player = relationship("Player", back_populates="manager_picks")
    gameweek_obj = relationship("Gameweek", back_populates="manager_picks")

    def __repr__(self):
        return f"<ManagerPick(manager={self.entry_id}, gw={self.gameweek}, player={self.player_id})>"