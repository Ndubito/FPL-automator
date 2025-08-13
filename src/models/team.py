from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from data.database import Base

class Team(Base):
    __tablename__ = 'teams'
    __table_args__ = {'extend_existing': True}  # Add this line


    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    short_name = Column(String, nullable=False)
    code = Column(Integer, unique=True, nullable=True)
    strength = Column(Integer, nullable=True)
    strength_attack_home = Column(Integer, nullable=True)
    strength_attack_away = Column(Integer, nullable=True)
    strength_defence_home = Column(Integer, nullable=True)
    strength_defence_away = Column(Integer, nullable=True)

    # Relationships - using string references to avoid circular imports
    players = relationship("Player", back_populates="team")

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}', short_name='{self.short_name}')>"
