from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from data.database import Base

class Transfer(Base):
    __tablename__ = 'transfers'

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey('managers.id'), nullable=False)
    gameweek = Column(Integer, ForeignKey('gameweeks.id'), nullable=False)
    transfer_time = Column(DateTime, default=datetime.utcnow)
    player_in_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    player_out_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    player_in_name = Column(String)
    player_out_name = Column(String)
    is_wildcard = Column(Boolean, default=False)
    is_free_hit = Column(Boolean, default=False)
    is_costed = Column(Boolean, default=True)
    cost = Column(Integer, default=4)

    # Relationships
    manager = relationship("Manager", back_populates="transfers")
    gameweek_obj = relationship("Gameweek", back_populates="transfers")
    player_in = relationship("Player", foreign_keys=[player_in_id])
    player_out = relationship("Player", foreign_keys=[player_out_id])

    def __repr__(self):
        return f"<Transfer(manager={self.entry_id}, gw={self.gameweek}, out={self.player_out_name}, in={self.player_in_name})>"