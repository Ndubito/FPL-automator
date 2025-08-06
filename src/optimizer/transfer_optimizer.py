import pulp
from collections import defaultdict
from typing import List, Dict, Tuple
from models import ManagerPick
from data.database import SessionLocal
from optimizer.run_transfer_optimizer import get_available_players, get_current_team


class TransferOptimizer:
    def __init__(self, transfer_cost: float = 4.0, free_transfers: int = 1):
        self.transfer_cost = transfer_cost
        self.free_transfers = free_transfers

    def optimize_transfers(self, current_team: List[Dict], available_players: List[Dict],
                           budget: float, gameweeks_ahead: int = 1) -> Dict:
        """
        Optimizes transfers considering transfer costs and multiple gameweeks

        Returns:
        - Dict with 'selected_team', 'transfers_in', 'transfers_out', 'cost'
        """

        # Create optimization problem
        prob = pulp.LpProblem("FPL_Transfer_Optimization", pulp.LpMaximize)

        # Decision variables
        player_vars = {
            p['id']: pulp.LpVariable(f"select_{p['id']}", cat='Binary')
            for p in available_players
        }

        transfer_in_vars = {
            p['id']: pulp.LpVariable(f"transfer_in_{p['id']}", cat='Binary')
            for p in available_players
        }

        transfer_out_vars = {
            p['id']: pulp.LpVariable(f"transfer_out_{p['id']}", cat='Binary')
            for p in current_team
        }

        # Current team player IDs
        current_ids = {p['id'] for p in current_team}

        # OBJECTIVE: Maximize expected points minus transfer costs
        total_transfers = pulp.lpSum([transfer_in_vars[p['id']] for p in available_players])
        transfer_cost_penalty = pulp.lpSum([
            (total_transfers - self.free_transfers) * self.transfer_cost
        ])

        prob += pulp.lpSum([
            player_vars[p['id']] * p['expected_points'] * gameweeks_ahead
            for p in available_players
        ]) - transfer_cost_penalty, "TotalValue"

        # CONSTRAINT: Link selection with transfers
        for p in available_players:
            if p['id'] in current_ids:
                # Current player: selected = (not transferred out)
                prob += (player_vars[p['id']] + transfer_out_vars[p['id']]) == 1
                prob += transfer_in_vars[p['id']] == 0  # Can't transfer in current players
            else:
                # New player: selected = transferred in
                prob += player_vars[p['id']] == transfer_in_vars[p['id']]

        # CONSTRAINT: Equal transfers in and out
        prob += (pulp.lpSum([transfer_in_vars[p['id']] for p in available_players]) ==
                 pulp.lpSum([transfer_out_vars[p['id']] for p in current_team]))

        # CONSTRAINT: Budget (including transfer costs)
        current_team_value = sum(p['price'] for p in current_team)

        # Calculate selling prices (typically 50% of price rise)
        money_from_sales = pulp.lpSum([
            transfer_out_vars[p['id']] * self._get_selling_price(p)
            for p in current_team
        ])

        money_for_purchases = pulp.lpSum([
            transfer_in_vars[p['id']] * p['price']
            for p in available_players
        ])

        prob += (money_for_purchases - money_from_sales +
                 transfer_cost_penalty) <= budget, "Budget"

        # CONSTRAINT: Squad composition (15 players total)
        prob += pulp.lpSum([player_vars[p['id']] for p in available_players]) == 15

        # CONSTRAINT: Position requirements
        positions = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
        for pos, count in positions.items():
            pos_players = [p for p in available_players if p['position'] == pos]
            prob += pulp.lpSum([player_vars[p['id']] for p in pos_players]) == count

        # CONSTRAINT: Max 3 players per team
        team_groups = defaultdict(list)
        for p in available_players:
            team_groups[p['team_id']].append(p)

        for team_id, group in team_groups.items():
            prob += pulp.lpSum([player_vars[p['id']] for p in group]) <= 3

        # Solve
        prob.solve()

        if prob.status != pulp.LpStatusOptimal:
            raise Exception("Optimization failed to find optimal solution")

        # Extract results
        selected_team = [p for p in available_players if pulp.value(player_vars[p['id']]) == 1]
        transfers_in = [p for p in available_players if pulp.value(transfer_in_vars[p['id']]) == 1]
        transfers_out = [p for p in current_team if pulp.value(transfer_out_vars[p['id']]) == 1]

        total_transfer_cost = max(0, len(transfers_in) - self.free_transfers) * self.transfer_cost

        return {
            'selected_team': selected_team,
            'transfers_in': transfers_in,
            'transfers_out': transfers_out,
            'transfer_cost': total_transfer_cost,
            'total_expected_points': sum(p['expected_points'] for p in selected_team),
            'remaining_budget': budget - total_transfer_cost
        }

    def _get_selling_price(self, player: Dict) -> float:
        """Calculate selling price considering price changes"""
        # Simplified - in reality you'd track purchase price vs current price
        return player['price']  # Assume no price change for now

    def optimize_wildcard(self, available_players: List[Dict], budget: float) -> List[Dict]:
        """Optimize team selection when using wildcard (no transfer costs)"""
        prob = pulp.LpProblem("FPL_Wildcard_Optimization", pulp.LpMaximize)

        player_vars = {
            p['id']: pulp.LpVariable(f"player_{p['id']}", cat='Binary')
            for p in available_players
        }

        # Objective: Maximize expected points
        prob += pulp.lpSum([
            player_vars[p['id']] * p['expected_points']
            for p in available_players
        ])

        # Standard FPL constraints
        prob += pulp.lpSum([
            player_vars[p['id']] * p['price'] for p in available_players
        ]) <= budget

        prob += pulp.lpSum([player_vars[p['id']] for p in available_players]) == 15

        positions = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
        for pos, count in positions.items():
            pos_players = [p for p in available_players if p['position'] == pos]
            prob += pulp.lpSum([player_vars[p['id']] for p in pos_players]) == count

        team_groups = defaultdict(list)
        for p in available_players:
            team_groups[p['team_id']].append(p)

        for team_id, group in team_groups.items():
            prob += pulp.lpSum([player_vars[p['id']] for p in group]) <= 3

        prob.solve()

        return [p for p in available_players if pulp.value(player_vars[p['id']]) == 1]


# Enhanced main function
def run_enhanced_optimizer():
    with SessionLocal() as session:
        latest_pick = session.query(ManagerPick).order_by(ManagerPick.gameweek.desc()).first()
        if not latest_pick:
            print("No manager picks found.")
            return

        gw = latest_pick.gameweek
        available_players = get_available_players(session)
        current_team = get_current_team(session, gw)

        optimizer = TransferOptimizer(transfer_cost=4.0, free_transfers=1)

        try:
            result = optimizer.optimize_transfers(
                current_team=current_team,
                available_players=available_players,
                budget=100.0,  # Available budget for transfers
                gameweeks_ahead=3  # Look ahead multiple gameweeks
            )

            print(f"\n📊 Transfer Recommendations (GW {gw}):")
            print(f"💰 Transfer Cost: £{result['transfer_cost']}m")
            print(f"📈 Expected Points: {result['total_expected_points']:.1f}")
            print(f"💵 Remaining Budget: £{result['remaining_budget']}m\n")

            if result['transfers_out']:
                print("🔴 TRANSFERS OUT:")
                for p in result['transfers_out']:
                    print(f"  ← {p['name']} ({p['position']}) - £{p['price']}m")

            if result['transfers_in']:
                print("\n🟢 TRANSFERS IN:")
                for p in result['transfers_in']:
                    print(f"  → {p['name']} ({p['position']}) - £{p['price']}m - {p['expected_points']:.1f} pts")

            if not result['transfers_in']:
                print("✅ No transfers recommended - current team is optimal!")

        except Exception as e:
            print(f"❌ Optimization failed: {e}")
            # Fallback to wildcard optimization
            print("🃏 Trying wildcard optimization instead...")
            wildcard_team = optimizer.optimize_wildcard(available_players, 100.0)
            print("\n🃏 Wildcard Team Suggestion:")
            for p in sorted(wildcard_team, key=lambda x: x['position']):
                print(f"  {p['name']} - {p['position']} - £{p['price']}m - {p['expected_points']:.1f} pts")


if __name__ == "__main__":
    run_enhanced_optimizer()