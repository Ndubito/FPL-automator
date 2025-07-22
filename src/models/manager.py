from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from data.database import Base

class Manager(Base):
    __tablename__ = "managers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    current_gw = Column(Integer)
    total_points = Column(Integer, default=0)
    overall_rank = Column(Integer)

    # Relationships
    picks = relationship("ManagerPick", back_populates="manager")
    transfers = relationship("Transfer", back_populates="manager")

    def __repr__(self):
        return f"<Manager {self.name} - GW {self.current_gw} - {self.total_points} pts>"