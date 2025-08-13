# Import all models to ensure they are registered with SQLAlchemy
from .team import Team
from .player import Player
from .manager import Manager
from .gameweek import Gameweek
from .manager_pick import ManagerPick
from .transfer import Transfer
from .player_gameweek_stats import PlayerGameweekStats
from .fixture import Fixture

# Make models available when importing from models
__all__ = [
    'Team',
    'Player',
    'Manager',
    'Gameweek',
    'ManagerPick',
    'Transfer',
    'PlayerGameweekStats',
    'Fixture',
]

