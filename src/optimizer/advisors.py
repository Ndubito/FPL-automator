import statistics
from typing import List, Dict, Optional

from sqlalchemy import desc, text
from sqlalchemy.dialects.postgresql import Any
from sqlalchemy.orm import Session
from sqlalchemy.sql.operators import and_, or_

from data.database import SessionLocal
from models import ManagerPick, Fixture, PlayerGameweekStats, Player
from optimizer.data_utils import get_available_players, get_current_team
from optimizer.transfer_optimizer import TransferOptimizer


class CaptainAdvisor:
    """Provides captain and vice-captain recommendations"""
    POSITION_MAP = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

    def __init__(self):
        self.position_weights = {
            '4': {1.2}, #FWD
            '3': {1.1},  #MID
            '2': {0.9}, #DEF
            '1': {0.3} #GK
        }

        # Add form weight factors
        self.form_weights = {
            'recent_points': 0.4,
            'season_points': 0.2,
            'fixture_difficulty': 0.2,
            'home_advantage': 0.1,
            'historical': 0.1
        }


    def suggest_captain(self, team: List[Dict], gameweek: int, session: Session) -> Dict:
        """
        Suggest captain based on multiple factors:
        - Expected points
        - Fixture difficulty
        - Home/away status
        - Recent form
        - Historical performance vs opponent
        """
        captain_scores = []

        for player in team:
            score = self._calculate_captain_score(player, gameweek, session)
            captain_scores.append({
                'player': player,
                'score': score,
                'reasons': self._get_captain_reasons(player, gameweek, session)
            })

        # Sort by score descending
        captain_scores.sort(key=lambda x: x['score'], reverse=True)

        return {
            'captain': captain_scores[0],
            'vice_captain': captain_scores[1],
            'alternatives': captain_scores[2:5]
        }

    def _calculate_captain_score(self, player: dict, gameweek: int, session: Session) -> float:
        """Calculate comprehensive captain score"""

        weekly_stats = (
            session.query(PlayerGameweekStats)
            .filter_by(player_id=player['id'], gameweek=gameweek)
            .first()
        )

        if not weekly_stats:
            return 0.0  # no stats yet for that gameweek

        base_score = weekly_stats.expected_points or 0.0

        # Position weight
        position_multiplier = self.position_weights.get(player['position'], 1.0)

        # Fixture difficulty (lower difficulty = higher score)
        fixture_score = self._get_fixture_score(player['team_id'], gameweek, session)

        # Form trend (recent 5 games)
        form_score = self._get_form_trend(player['id'], session)

        # Home advantage
        home_bonus = self._get_home_advantage(player['team_id'], gameweek, session)

        # Historical performance vs opponent
        history_bonus = self._get_historical_performance(player['id'], gameweek, session)

        total_score = (
                base_score * position_multiplier *
                (1 + fixture_score + form_score + home_bonus + history_bonus)
        )

        return round(total_score, 2)

    def _get_fixture_score(self, team_id: int, gameweek: int, session: Session) -> float:
        """Get fixture difficulty score (0.0 to 0.3 bonus)"""
        try:
            fixture = session.query(Fixture).filter_by(
                gameweek=gameweek
            ).filter(
                (Fixture.home_team_id == team_id) | (Fixture.away_team_id == team_id)
            ).first()

            if not fixture:
                return 0.0

            # Assume fixture has difficulty rating (1-5, where 1 is easiest)
            opponent_strength = getattr(fixture, 'difficulty', 3)
            return (6 - opponent_strength) * 0.06  # 0.0 to 0.3 range

        except Exception:
            return 0.0

    def _get_form_trend(self, player_id: int, session: Session) -> float:
        """Get recent form trend (-0.2 to 0.2)"""
        try:
            # Get last 5 gameweek performances
            recent_stats = session.query(PlayerGameweekStats).filter(
                PlayerGameweekStats.player_id == player_id
            ).order_by(desc(PlayerGameweekStats.gameweek)).limit(5).all()

            if len(recent_stats) < 3:  # Need at least 3 games for trend
                return 0.0

            # Extract points from recent games (reverse to get chronological order)
            recent_points = [stat.points for stat in reversed(recent_stats)]

            # Calculate weighted average trend
            trend_score = self._calculate_trend_score(recent_points)

            # Normalize to -0.2 to 0.2 range
            return max(-0.2, min(0.2, trend_score))

        except Exception as e:
            print(f"Error calculating form trend for player {player_id}: {e}")
            return 0.0

    def _calculate_trend_score(self, points_sequence: List[int]) -> float:
        """
        Calculate trend score from sequence of points
        Positive = improving form, Negative = declining form
        """
        if len(points_sequence) < 3:
            return 0.0

        # Method 1: Linear regression slope
        slope = self._calculate_linear_slope(points_sequence)

        # Method 2: Weighted recent performance
        weights = [1, 1.2, 1.4, 1.6, 2.0]  # More weight to recent games
        if len(weights) > len(points_sequence):
            weights = weights[-len(points_sequence):]

        weighted_avg = sum(p * w for p, w in zip(points_sequence, weights)) / sum(weights)
        overall_avg = statistics.mean(points_sequence)

        # Combine methods
        trend_indicator = (slope * 0.7) + ((weighted_avg - overall_avg) * 0.3)

        # Scale to appropriate range
        return trend_indicator * 0.05  # Adjust scaling factor as needed

    def _calculate_linear_slope(self, points_sequence: List[int]) -> float:
        """Calculate linear regression slope for trend analysis"""
        n = len(points_sequence)
        if n < 2:
            return 0.0

        x_values = list(range(n))
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(points_sequence)

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, points_sequence))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            return 0.0

        return numerator / denominator



    def _get_home_advantage(self, team_id: int, gameweek: int, session: Session) -> float:
        """Get home advantage bonus (0.0 or 0.1)"""
        try:
            fixture = session.query(Fixture).filter_by(
                gameweek=gameweek, home_team_id=team_id
            ).first()
            return 0.1 if fixture else 0.0
        except Exception:
            return 0.0

    def _get_historical_performance(self, player_id: int, gameweek: int, session: Session) -> float:
        """Get historical performance vs opponent (0.0 to 0.15)"""
        # This would analyze past performances against the same opponent
        try:
            # Get the upcoming fixture to find opponent
            current_fixture = self._get_player_fixture(player_id, gameweek, session)
            if not current_fixture:
                return 0.0

            # Determine opponent team
            player_team_id = self._get_player_team_id(player_id, session)
            if not player_team_id:
                return 0.0

            if current_fixture.home_team_id == player_team_id:
                opponent_id = current_fixture.away_team_id
                is_home = True
            else:
                opponent_id = current_fixture.home_team_id
                is_home = False

            # Get historical performances against this opponent
            historical_performances = self._get_performances_vs_opponent(
                player_id, opponent_id, gameweek, session
            )

            if not historical_performances:
                return 0.0

            # Calculate performance bonus
            performance_bonus = self._calculate_historical_bonus(
                historical_performances, is_home
            )

            # Return value between 0.0 and 0.15
            return max(0.0, min(0.15, performance_bonus))

        except Exception as e:
            print(f"Error calculating historical performance for player {player_id}: {e}")
            return 0.0

    def _calculate_historical_bonus(self, performances: List[Dict], is_home: bool) -> float:
        """
        Calculate bonus based on historical performances
        Considers both overall performance and home/away context
        """
        if not performances:
            return 0.0

        # Separate home and away performances
        home_performances = [p for p in performances if p['was_home']]
        away_performances = [p for p in performances if not p['was_home']]

        # Calculate average points
        overall_avg = statistics.mean([p['points'] for p in performances])

        # Context-specific average
        if is_home and home_performances:
            context_avg = statistics.mean([p['points'] for p in home_performances])
            context_weight = 0.7
        elif not is_home and away_performances:
            context_avg = statistics.mean([p['points'] for p in away_performances])
            context_weight = 0.7
        else:
            context_avg = overall_avg
            context_weight = 0.5

        # Weighted average
        weighted_avg = (context_avg * context_weight) + (overall_avg * (1 - context_weight))

        # Calculate bonus based on performance level
        if weighted_avg >= 8:
            base_bonus = 0.15
        elif weighted_avg >= 6:
            base_bonus = 0.10
        elif weighted_avg >= 4:
            base_bonus = 0.05
        else:
            base_bonus = 0.0

        # Adjust for consistency
        if len(performances) >= 3:
            points_list = [p['points'] for p in performances]
            consistency_bonus = self._calculate_consistency_bonus(points_list)
            base_bonus += consistency_bonus

        # Adjust for recency (more recent performances weighted higher)
        recency_bonus = self._calculate_recency_bonus(performances)
        base_bonus += recency_bonus

        return base_bonus

    def _calculate_consistency_bonus(self, points_list: List[int]) -> float:
        """
        Calculate bonus for consistent performances
        Lower variance = higher bonus
        """
        if len(points_list) < 2:
            return 0.0

        try:
            avg_points = statistics.mean(points_list)
            variance = statistics.variance(points_list)

            # High average with low variance gets bonus
            if avg_points >= 6 and variance <= 4:
                return 0.02
            elif avg_points >= 4 and variance <= 6:
                return 0.01
            else:
                return 0.0

        except Exception:
            return 0.0

    def _calculate_recency_bonus(self, performances: List[Dict]) -> float:
        """
        Calculate bonus based on recency of good performances
        More recent good performances get higher bonus
        """
        if not performances:
            return 0.0

        # Sort by gameweek (most recent first)
        sorted_performances = sorted(performances, key=lambda x: x['gameweek'], reverse=True)

        # Weight recent performances more heavily
        weighted_score = 0
        total_weight = 0

        for i, perf in enumerate(sorted_performances[:5]):  # Consider last 5 meetings
            weight = 1.0 / (i + 1)  # Decreasing weight for older games
            weighted_score += perf['points'] * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        weighted_avg = weighted_score / total_weight

        # Convert to bonus (0.0 to 0.03)
        if weighted_avg >= 8:
            return 0.03
        elif weighted_avg >= 6:
            return 0.02
        elif weighted_avg >= 4:
            return 0.01
        else:
            return 0.0

    def _get_performances_vs_opponent(self, player_id: int, opponent_id: int,
                                      current_gameweek: int, session: Session,
                                      seasons_back: int = 2) -> List[Dict]:
        """
        Get historical performances against specific opponent
        Limited to last N seasons to keep data relevant
        """
        try:
            # Calculate gameweek cutoff (approximately 2 seasons = 76 gameweeks)
            gameweek_cutoff = max(1, current_gameweek - (seasons_back * 38))

            # Get all fixtures where player's team faced opponent
            player_team_id = self._get_player_team_id(player_id, session)
            if not player_team_id:
                return []

            # Find historical fixtures
            historical_fixtures = session.query(Fixture).filter(
                Fixture.gameweek >= gameweek_cutoff,
                Fixture.gameweek < current_gameweek,
                or_(
                    and_(
                        Fixture.home_team_id == player_team_id,
                        Fixture.away_team_id == opponent_id
                    ),
                    and_(
                        Fixture.away_team_id == player_team_id,
                        Fixture.home_team_id == opponent_id
                    )
                )
            ).all()

            # Get player stats for these fixtures
            performances = []
            for fixture in historical_fixtures:
                stats = session.query(PlayerGameweekStats).filter(
                    and_(
                        PlayerGameweekStats.player_id == player_id,
                        PlayerGameweekStats.gameweek == fixture.gameweek
                    )
                ).first()

                if stats:
                    was_home = fixture.home_team_id == player_team_id
                    performances.append({
                        'gameweek': fixture.gameweek,
                        'points': stats.points,
                        'was_home': was_home,
                        'goals': getattr(stats, 'goals_scored', 0),
                        'assists': getattr(stats, 'assists', 0),
                        'minutes': getattr(stats, 'minutes_played', 0),
                        'clean_sheet': getattr(stats, 'clean_sheets', 0)
                    })

            return performances

        except Exception as e:
            print(f"Error getting performances vs opponent: {e}")
            return []

    def _get_player_fixture(self, player_id: int, gameweek: int, session: Session) -> Optional[Fixture]:
        """Get the fixture for a player in a specific gameweek"""
        try:
            # Get player's team
            player_team_id = self._get_player_team_id(player_id, session)
            if not player_team_id:
                return None

            # Find fixture for this team in this gameweek
            fixture = session.query(Fixture).filter(
                and_(
                    Fixture.gameweek == gameweek,
                    (Fixture.home_team_id == player_team_id) |
                    (Fixture.away_team_id == player_team_id)
                )
            ).first()

            return fixture

        except Exception:
            return None



    def _get_player_team_id(self, player_id: int, session: Session) -> Optional[int]:
        """Get the current team ID for a player"""
        try:
            player = session.query(Player).filter(Player.id == player_id).first()
            return player.team_id if player else None
        except Exception:
            return None



    def _get_captain_reasons(self, player: Dict, gameweek: int, session: Session) -> List[str]:
        """Generate human-readable reasons for captain choice"""
        reasons = []

        if player['expected_points'] > 8:
            reasons.append(f"High expected points ({player['expected_points']})")

        if self._get_home_advantage(player['team_id'], gameweek, session) > 0:
            reasons.append("Playing at home")

        fixture_score = self._get_fixture_score(player['team_id'], gameweek, session)
        if fixture_score > 0.15:
            reasons.append("Favorable fixture")

        if player['position'] in ['FWD', 'MID']:
            reasons.append(f"Good attacking returns potential ({player['position']})")

        return reasons


class ChipAdvisor:
    """Provides advice on when to use FPL chips"""

    def __init__(self):
        self.chips = {
            'wildcard': {'uses_per_season': 2, 'description': 'Unlimited free transfers'},
            'bench_boost': {'uses_per_season': 1, 'description': 'Points from bench players count'},
            'triple_captain': {'uses_per_season': 1, 'description': 'Captain gets 3x points instead of 2x'},
            'free_hit': {'uses_per_season': 1, 'description': 'Make unlimited transfers for one GW only'}
        }

    def analyze_chip_usage(self, current_team: List[Dict], gameweek: int,
                           chips_used: Dict[str, bool], session: Session) -> Dict:
        """
        Analyze optimal chip usage timing

        Args:
            chips_used: Dict like {'wildcard': True, 'bench_boost': False, ...}
        """
        recommendations = {}

        # Wildcard analysis
        if not chips_used.get('wildcard', False):
            recommendations['wildcard'] = self._analyze_wildcard(current_team, gameweek, session)

        # Bench Boost analysis
        if not chips_used.get('bench_boost', False):
            recommendations['bench_boost'] = self._analyze_bench_boost(current_team, gameweek, session)

        # Triple Captain analysis
        if not chips_used.get('triple_captain', False):
            recommendations['triple_captain'] = self._analyze_triple_captain(current_team, gameweek, session)

        # Free Hit analysis
        if not chips_used.get('free_hit', False):
            recommendations['free_hit'] = self._analyze_free_hit(current_team, gameweek, session)

        return recommendations

    def _analyze_wildcard(self, current_team: List[Dict], gameweek: int, session: Session) -> Dict:
        """Analyze when to use wildcard"""
        # Count injured/suspended players
        unavailable_count = sum(1 for p in current_team if p.get('status') != 'a')

        # Count players with bad fixtures (next 5 GWs)
        bad_fixture_count = self._count_bad_fixtures(current_team, gameweek, session, gameweeks=5)

        # Calculate team value efficiency
        value_efficiency = self._calculate_team_value_efficiency(current_team)

        urgency_score = (unavailable_count * 2) + bad_fixture_count + (1 - value_efficiency) * 5

        recommendation = {
            'urgency': 'High' if urgency_score > 6 else 'Medium' if urgency_score > 3 else 'Low',
            'score': round(urgency_score, 1),
            'reasons': [],
            'best_timing': self._suggest_wildcard_timing(gameweek, session)
        }

        if unavailable_count > 2:
            recommendation['reasons'].append(f"{unavailable_count} players unavailable")
        if bad_fixture_count > 5:
            recommendation['reasons'].append(f"{bad_fixture_count} players with difficult fixtures")
        if value_efficiency < 0.8:
            recommendation['reasons'].append("Team value could be optimized")

        return recommendation

    def _analyze_bench_boost(self, current_team: List[Dict], gameweek: int, session: Session) -> Dict:
        """Analyze when to use bench boost"""
        bench_players = [p for p in current_team if p.get('is_bench', False)]

        # Calculate expected bench points
        bench_expected = sum(p['expected_points'] for p in bench_players)

        # Look for double gameweeks
        double_gameweek_count = self._count_double_gameweeks(current_team, gameweek, session)

        # Check fixture difficulty for bench
        bench_fixture_score = sum(
            self._get_fixture_score(p['team_id'], gameweek, session)
            for p in bench_players
        )

        recommendation = {
            'expected_points': round(bench_expected, 1),
            'urgency': 'High' if bench_expected > 15 else 'Medium' if bench_expected > 10 else 'Low',
            'reasons': [],
            'best_timing': self._suggest_bench_boost_timing(gameweek, session)
        }

        if double_gameweek_count > 2:
            recommendation['reasons'].append(f"{double_gameweek_count} bench players have double gameweek")
        if bench_expected > 12:
            recommendation['reasons'].append(f"Strong bench with {bench_expected:.1f} expected points")
        if bench_fixture_score > 0.5:
            recommendation['reasons'].append("Bench players have favorable fixtures")

        return recommendation

    def _analyze_triple_captain(self, current_team: List[Dict], gameweek: int, session: Session) -> Dict:
        """Analyze when to use triple captain"""
        # Find best captain candidate
        captain_advisor = CaptainAdvisor()
        captain_suggestion = captain_advisor.suggest_captain(current_team, gameweek, session)

        best_captain = captain_suggestion['captain']
        captain_expected = best_captain['score']

        # Look for double gameweeks
        has_double_gameweek = self._player_has_double_gameweek(
            best_captain['player']['team_id'], gameweek, session
        )

        # Calculate potential extra points (captain gets 3x instead of 2x)
        extra_points = captain_expected  # One additional multiplier

        recommendation = {
            'best_candidate': best_captain['player']['name'],
            'expected_extra_points': round(extra_points, 1),
            'urgency': 'High' if extra_points > 8 else 'Medium' if extra_points > 5 else 'Low',
            'reasons': best_captain['reasons'],
            'best_timing': self._suggest_triple_captain_timing(gameweek, session)
        }

        if has_double_gameweek:
            recommendation['reasons'].append("Player has double gameweek")
            recommendation['urgency'] = 'High'

        return recommendation

    def _analyze_free_hit(self, current_team: List[Dict], gameweek: int, session: Session) -> Dict:
        """Analyze when to use free hit"""
        # Count players with no fixture this gameweek
        no_fixture_count = self._count_no_fixtures(current_team, gameweek, session)

        # Look for blank gameweeks
        is_blank_gameweek = no_fixture_count > 6

        recommendation = {
            'players_without_fixture': no_fixture_count,
            'urgency': 'High' if is_blank_gameweek else 'Low',
            'reasons': [],
            'best_timing': self._suggest_free_hit_timing(gameweek, session)
        }

        if is_blank_gameweek:
            recommendation['reasons'].append(f"{no_fixture_count} players have no fixture")

        return recommendation

    # Helper methods (simplified implementations)
    def _count_bad_fixtures(self, team: List[Dict], gameweek: int, session: Session, gameweeks: int = 5) -> int:
        """Count players with difficult fixtures in next N gameweeks"""
        bad_count = 0
        for player in team:
            team_id = player['team_id']
            fixtures = self._get_team_fixtures(team_id, gameweek, gameweek + gameweeks - 1, session)
            # Count "bad" fixtures
            if sum(1 for f in fixtures if self._get_fixture_score_from_fixture(f, team_id) > 3) >= (gameweeks // 2):
                bad_count += 1
        return bad_count

    def _calculate_team_value_efficiency(self, team: List[Dict]) -> float:
        """Calculate how efficiently team budget is used (0.0 to 1.0)"""
        total_price = sum(p['price'] for p in team)
        total_expected = sum(p['expected_points'] for p in team)
        return min(1.0, total_expected / (total_price * 0.5))  # Rough efficiency metric

    def _suggest_wildcard_timing(self, current_gw: int, session: Session) -> str:
        """Suggest best timing for wildcard"""
        return f"Consider for GW {current_gw + 2} after international break"

    def _suggest_bench_boost_timing(self, current_gw: int, session: Session) -> str:
        """Suggest best timing for bench boost"""
        return f"Look for double gameweek around GW {current_gw + 5}"

    def _suggest_triple_captain_timing(self, current_gw: int, session: Session) -> str:
        """Suggest best timing for triple captain"""
        return f"Save for double gameweek or easy home fixture"

    def _suggest_free_hit_timing(self, current_gw: int, session: Session) -> str:
        """Suggest best timing for free hit"""
        return f"Use during blank gameweeks (typically GW {current_gw + 10}+)"

    def _count_double_gameweeks(self, team: List[Dict], gameweek: int, session: Session) -> int:
        """Count players with double gameweeks"""
        count = 0
        for player in team:
            fixtures = self._get_team_fixtures(player['team_id'], gameweek, gameweek, session)
            if len(fixtures) > 1:  # More than one match in the same GW
                count += 1
        return count

    def _player_has_double_gameweek(self, team_id: int, gameweek: int, session: Session) -> bool:
        """Check if player's team has double gameweek"""
        fixtures = self._get_team_fixtures(team_id, gameweek, gameweek, session)
        return len(fixtures) > 1

    def _count_no_fixtures(self, team: List[Dict], gameweek: int, session: Session) -> int:
        """Count players with no fixture this gameweek"""
        no_fixture_count = 0
        for player in team:
            fixtures = self._get_team_fixtures(player['team_id'], gameweek, gameweek, session)
            if not fixtures:  # Empty list means no match that GW
                no_fixture_count += 1
        return no_fixture_count

    def _get_fixture_score(self, team_id: int, gameweek: int, session: Session) -> float:
        """Get fixture difficulty score"""
        fixtures = self._get_team_fixtures(team_id, gameweek, gameweek, session)
        if not fixtures:
            return 0.0
        scores = [self._get_fixture_score_from_fixture(f, team_id) for f in fixtures]
        return sum(scores) / len(scores)

    def _get_fixture_score_from_fixture(self, fixture: Any, team_id: int) -> int:
        """
        Return difficulty score (1–5) for a fixture from the perspective of the given team.
        Works with SQLAlchemy Row objects or dicts.
        """
        if isinstance(fixture, dict):
            if fixture['home_team_id'] == team_id:
                return fixture['difficulty_home']
            else:
                return fixture['difficulty_away']
        else:  # SQLAlchemy Row or tuple
            if fixture.home_team_id == team_id:
                return fixture.difficulty_home
            else:
                return fixture.difficulty_away

    from typing import List, Dict, Any
    from sqlalchemy.orm import Session

    def _get_team_fixtures(self, team_id: int, start_gw: int, end_gw: int, session: Session) -> List[Dict[str, Any]]:
        """
        Fetch fixtures for a team between two GWs from the DB or API.
        Returns a list of dicts.
        """
        query = text("""
                     SELECT gameweek, home_team_id, away_team_id, difficulty_home, difficulty_away
                     FROM fixtures
                     WHERE gameweek BETWEEN :start_gw AND :end_gw
                       AND (home_team_id = :team_id OR away_team_id = :team_id)
                     """)

        result = session.execute(query, {
            "start_gw": start_gw,
            "end_gw": end_gw,
            "team_id": team_id
        })

        # Convert to list of dicts
        fixtures: List[Dict[str, Any]] = [dict(row._mapping) for row in result]
        return fixtures


class TransferAdvisor:
    """Enhanced transfer recommendations"""

    def __init__(self):
        self.transfer_optimizer = TransferOptimizer()

    def get_transfer_recommendations(self, current_team: List[Dict],
                                     available_players: List[Dict],
                                     budget: float, gameweek: int,
                                     session: Session) -> Dict:
        """
        Get comprehensive transfer recommendations with priority levels
        """

        # Priority transfers (injuries, suspensions)
        priority_transfers = self._identify_priority_transfers(current_team, session)

        # Value transfers (price rises, good fixtures)
        value_transfers = self._identify_value_transfers(
            current_team, available_players, gameweek, session
        )

        # Long-term transfers (season keepers)
        longterm_transfers = self._identify_longterm_transfers(
            current_team, available_players, session
        )

        # Run optimization
        try:
            optimal_result = self.transfer_optimizer.optimize_transfers(
                current_team, available_players, budget
            )
        except Exception as e:
            optimal_result = {'transfers_in': [], 'transfers_out': []}

        return {
            'priority_transfers': priority_transfers,
            'value_transfers': value_transfers,
            'longterm_transfers': longterm_transfers,
            'optimal_transfers': {
                'in': optimal_result.get('transfers_in', []),
                'out': optimal_result.get('transfers_out', [])
            },
            'summary': self._generate_transfer_summary(
                priority_transfers, value_transfers, longterm_transfers
            )
        }

    def _identify_priority_transfers(self, current_team: List[Dict], session: Session) -> List[Dict]:
        """Identify urgent transfers (injuries, suspensions, etc.)"""
        priority = []

        for player in current_team:
            reasons = []
            urgency = 0

            # Check availability status
            if player.get('status') == 'i':  # Injured
                reasons.append("Injured")
                urgency += 3
            elif player.get('status') == 's':  # Suspended
                reasons.append("Suspended")
                urgency += 3
            elif player.get('status') == 'd':  # Doubtful
                reasons.append("Doubtful to play")
                urgency += 1

            # Check price drops
            if player.get('price_change', 0) < -0.2:
                reasons.append("Falling in price")
                urgency += 1

            if urgency > 0:
                priority.append({
                    'player': player,
                    'urgency': urgency,
                    'reasons': reasons
                })

        return sorted(priority, key=lambda x: x['urgency'], reverse=True)

    def _identify_value_transfers(self, current_team: List[Dict],
                                  available_players: List[Dict],
                                  gameweek: int, session: Session) -> List[Dict]:
        """Identify good value transfer opportunities"""
        value_transfers = []

        # Find players with good upcoming fixtures and rising prices
        for player in available_players:
            if player['id'] in [p['id'] for p in current_team]:
                continue

            value_score = 0
            reasons = []

            # Price rises
            if player.get('price_change', 0) > 0.1:
                reasons.append("Rising in price")
                value_score += 2

            # Good fixtures
            fixture_score = self._calculate_fixture_run(player['team_id'], gameweek, session)
            if fixture_score > 0.3:
                reasons.append("Excellent fixture run")
                value_score += 3
            elif fixture_score > 0.15:
                reasons.append("Good upcoming fixtures")
                value_score += 1

            # High expected points
            if player['expected_points'] > 7:
                reasons.append(f"High expected points ({player['expected_points']})")
                value_score += 2

            # Form
            if player.get('form', 0) > 6:
                reasons.append("Excellent recent form")
                value_score += 1

            if value_score > 2:
                value_transfers.append({
                    'player': player,
                    'value_score': value_score,
                    'reasons': reasons
                })

        return sorted(value_transfers, key=lambda x: x['value_score'], reverse=True)[:10]

    def _identify_longterm_transfers(self, current_team: List[Dict],
                                     available_players: List[Dict],
                                     session: Session) -> List[Dict]:
        """Identify season keeper transfers"""
        longterm = []

        for player in available_players:
            if player['id'] in [p['id'] for p in current_team]:
                continue

            # Season keeper criteria
            longterm_score = 0
            reasons = []

            # Consistent high scorer
            if player['expected_points'] > 8:
                reasons.append("Consistent high scorer")
                longterm_score += 3

            # Good value for money
            points_per_million = player['expected_points'] / player['price']
            if points_per_million > 1.5:
                reasons.append(f"Excellent value ({points_per_million:.1f} pts/£m)")
                longterm_score += 2

            # Key player for team
            if player.get('penalties', False):
                reasons.append("Takes penalties")
                longterm_score += 1

            if longterm_score > 3:
                longterm.append({
                    'player': player,
                    'longterm_score': longterm_score,
                    'reasons': reasons
                })

        return sorted(longterm, key=lambda x: x['longterm_score'], reverse=True)[:5]

    def _calculate_fixture_run(self, team_id: int, start_gw: int, session: Session, gameweeks: int = 6) -> float:
        """Calculate an average fixture difficulty score for the next N gameweeks"""
        end_gw = start_gw + gameweeks
        fixtures = session.query(Fixture).filter(
            Fixture.gameweek >= start_gw,
            Fixture.gameweek < end_gw,
            or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id)
        ).all()

        if not fixtures:
            return 0.0  # No upcoming fixtures

        difficulty_sum = 0
        for f in fixtures:
            if f.home_team_id == team_id:
                difficulty_sum += f.difficulty_home
            else:
                difficulty_sum += f.difficulty_away

        return difficulty_sum / len(fixtures)

    def _generate_transfer_summary(self, priority: List, value: List, longterm: List) -> str:
        """Generate human-readable transfer summary"""
        summary_parts = []

        if priority:
            players = ", ".join([p['player']['name'] for p in priority])
            summary_parts.append(f"Urgent transfers needed: {players}")

        if value:
            players = ", ".join([p['player']['name'] for p in value])
            summary_parts.append(f"Good value opportunities: {players}")

        if longterm:
            players = ", ".join([p['player']['name'] for p in longterm])
            summary_parts.append(f"Season keeper options: {players}")

        if not summary_parts:
            return "No immediate transfers recommended"

        return "; ".join(summary_parts)

        print("VALUE TRANSFERS SAMPLE:", value[:1])


# Updated main function with all advisors
def run_complete_advisor():
    """Run the complete FPL advisory system"""
    with SessionLocal() as session:
        latest_pick = session.query(ManagerPick).order_by(ManagerPick.gameweek.desc()).first()
        if not latest_pick:
            print("No manager picks found.")
            return

        gw = latest_pick.gameweek
        available_players = get_available_players(session)
        current_team = get_current_team(session, gw)

        # Initialize advisors
        captain_advisor = CaptainAdvisor()
        chip_advisor = ChipAdvisor()
        transfer_advisor = TransferAdvisor()

        print(f"\n🏆 FPL Advisory Report - Gameweek {gw}\n")
        print("=" * 50)

        # 1. Captain Recommendations
        print("\n👑 CAPTAIN RECOMMENDATIONS")
        captain_rec = captain_advisor.suggest_captain(current_team, gw, session)

        captain = captain_rec['captain']
        vice = captain_rec['vice_captain']

        print(f"🅲 Captain: {captain['player']['name']} ({captain['player']['position']}) - {captain['score']} pts")
        print(f"   Reasons: {', '.join(captain['reasons'])}")
        print(f"🆅 Vice-Captain: {vice['player']['name']} ({vice['player']['position']}) - {vice['score']} pts")

        print("\n📋 Alternatives:")
        for i, alt in enumerate(captain_rec['alternatives'][:3], 3):
            print(f"{i}. {alt['player']['name']} - {alt['score']} pts")

        # 2. Transfer Recommendations
        print(f"\n🔄 TRANSFER RECOMMENDATIONS")
        transfer_rec = transfer_advisor.get_transfer_recommendations(
            current_team, available_players, 100.0, gw, session
        )

        print(f"Summary: {transfer_rec['summary']}")

        if transfer_rec['priority_transfers']:
            print("\n🚨 PRIORITY TRANSFERS:")
            for pt in transfer_rec['priority_transfers'][:3]:
                print(f"  OUT: {pt['player']['name']} - {', '.join(pt['reasons'])}")

        if transfer_rec['value_transfers']:
            print("\n💎 VALUE OPPORTUNITIES:")
            for vt in transfer_rec['value_transfers'][:3]:
                print(f"  IN: {vt['player']['name']} (£{vt['player']['price']}m) - {', '.join(vt['reasons'])}")

        # 3. Chip Usage Advice
        print(f"\n🃏 CHIP USAGE ADVICE")
        chips_used = {'wildcard': False, 'bench_boost': False, 'triple_captain': False, 'free_hit': False}
        chip_rec = chip_advisor.analyze_chip_usage(current_team, gw, chips_used, session)

        for chip_name, advice in chip_rec.items():
            chip_display = chip_name.replace('_', ' ').title()
            print(f"\n{chip_display}: {advice['urgency']} Priority")
            if advice.get('reasons'):
                print(f"  Reasons: {', '.join(advice['reasons'])}")
            if advice.get('best_timing'):
                print(f"  Timing: {advice['best_timing']}")

        print("\n" + "=" * 50)
        print("✅ Advisory report complete!")


if __name__ == "__main__":
    run_complete_advisor()
