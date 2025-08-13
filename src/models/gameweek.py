from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from data.database import Base

class Gameweek(Base):
    __tablename__ = 'gameweeks'
    __table_args__ = {'extend_existing': True}  # Add this line


    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    deadline_time = Column(DateTime, nullable=False)
    average_entry_score = Column(Integer)
    highest_score = Column(Integer)
    is_current = Column(Boolean, default=False)
    is_next = Column(Boolean, default=False)
    is_finished = Column(Boolean, default=False)

    # Relationships
    manager_picks = relationship("ManagerPick", back_populates="gameweek_obj")
    transfers = relationship("Transfer", back_populates="gameweek_obj")
    player_stats = relationship("PlayerGameweekStats", back_populates="gameweek_obj")

    def __repr__(self):
        return f"<Gameweek {self.id}: {self.name}>"