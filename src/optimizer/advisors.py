from optimizer.run_transfer_optimizer import get_available_players, get_current_team
from optimizer.transfer_optimizer import TransferOptimizer
from data.database import SessionLocal
from models import Player, ManagerPick, Fixture
from sqlalchemy.orm import Session
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import statistics


class CaptainAdvisor:
    """Provides captain and vice-captain recommendations"""

    def __init__(self):
        self.position_weights = {
            'FWD': {'easy': 1.3, 'medium': 1.2, 'hard': 1.1},
            'MID': {'easy': 1.2, 'medium': 1.1, 'hard': 1.0},
            'DEF': {'easy': 1.1, 'medium': 0.9, 'hard': 0.7},
            'GK': {'easy': 0.5, 'medium': 0.3, 'hard': 0.2}
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

    def _calculate_captain_score(self, player: Dict, gameweek: int, session: Session) -> float:
        """Calculate comprehensive captain score"""
        base_score = player['expected_points']

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
            # Get last 5 gameweek scores
            # This would need a PlayerGameweekStats table
            return 0.0  # Placeholder
        except Exception:
            return 0.0

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
        return 0.0  # Placeholder

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
        return 0  # Placeholder

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
        return 0  # Placeholder

    def _player_has_double_gameweek(self, team_id: int, gameweek: int, session: Session) -> bool:
        """Check if player's team has double gameweek"""
        return False  # Placeholder

    def _count_no_fixtures(self, team: List[Dict], gameweek: int, session: Session) -> int:
        """Count players with no fixture this gameweek"""
        return 0  # Placeholder

    def _get_fixture_score(self, team_id: int, gameweek: int, session: Session) -> float:
        """Get fixture difficulty score"""
        return 0.0  # Placeholder


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

    def _calculate_fixture_run(self, team_id: int, gameweek: int, session: Session, gameweeks: int = 6) -> float:
        """Calculate fixture difficulty for next N gameweeks"""
        # This would analyze upcoming fixtures
        return 0.0  # Placeholder

    def _generate_transfer_summary(self, priority: List, value: List, longterm: List) -> str:
        """Generate human-readable transfer summary"""
        summary_parts = []

        if priority:
            summary_parts.append(f"{len(priority)} urgent transfer(s) needed")

        if value:
            summary_parts.append(f"{len(value)} good value opportunities")

        if longterm:
            summary_parts.append(f"{len(longterm)} season keeper options")

        if not summary_parts:
            return "No immediate transfers recommended"

        return "; ".join(summary_parts)


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