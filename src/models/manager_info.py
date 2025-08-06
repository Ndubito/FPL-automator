from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from data.database import Base


class ManagerInfo(Base):
    __tablename__ = 'manager_info'

    id = Column(Integer, primary_key=True)
    current_gameweek = Column(Integer)
    wildcard_used = Column(Boolean, default=False)
    bench_boost_used = Column(Boolean, default=False)
    triple_captain_used = Column(Boolean, default=False)
    free_hit_used = Column(Boolean, default=False)