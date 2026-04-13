from strategies.base import BaseStrategy
from game.constants import COLOR_GROUPS


class HyperAggressiveStrategy(BaseStrategy):
    name = "Hyper-Aggressive"

    def should_buy(self, player, prop, engine):
        return True

    def should_build(self, player, prop, engine):
        return True

    def should_mortgage_to_buy(self, player, prop, engine):
        return True

    def should_mortgage_to_build(self, player, prop, engine):
        return True

    def should_unmortgage(self, player, prop, engine):
        if prop.type == "property":
            group = COLOR_GROUPS.get(prop.color, [])
            if all(engine.board_properties[p].owner == player for p in group):
                return player.money >= prop.unmortgage_cost + prop.house_cost
        return player.money >= prop.unmortgage_cost + 100

    def should_pay_jail_fine(self, player, engine):
        return True

    def should_use_goojf(self, player, engine):
        return True

    def select_to_mortgage(self, player, amount_needed, engine):
        """Prioritise mortgaging: non-monopoly properties (cheap first),
        then lone railroads/utilities, then bare monopoly land (expensive last).
        Never mortgages properties with houses."""
        def score(prop):
            if prop.type == "railroad":
                rr_cnt = len(player.owned_railroads())
                # Lone railroad: low value, mortgage first
                return (1, -prop.mortgage_value) if rr_cnt == 1 else (3, -prop.mortgage_value)
            if prop.type == "utility":
                return (2, -prop.mortgage_value)
            if prop.type == "property":
                group = COLOR_GROUPS.get(prop.color, [])
                owns_group = all(
                    engine.board_properties[p].owner == player for p in group
                )
                if owns_group:
                    return (4, prop.mortgage_value)   # monopoly land: mortgage last, cheap first
                return (1, prop.mortgage_value)       # non-monopoly: mortgage first, cheap first
            return (5, 0)

        candidates = [p for p in player.properties
                      if not p.mortgaged and p.houses == 0]
        candidates.sort(key=score)
        result = []
        total = player.money
        for c in candidates:
            if total >= amount_needed:
                break
            result.append(c)
            total += c.mortgage_value
        return result

    def evaluate_trade(self, player, proposal, engine):
        # Accept anything with 18%+ of trade value margin
        return self._trade_ratio(player, proposal, engine) >= 0.82

    def find_trade_opportunity(self, player, engine):
        # Will pay up to 15% premium - most aggressive trader
        return self._find_monopoly_trade(player, engine, offer_premium=0.15)
