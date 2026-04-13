from strategies.base import BaseStrategy
from game.constants import COLOR_GROUPS

PRIORITY_COLORS = {"orange", "red", "light_blue", "pink"}

class BalancedStrategy(BaseStrategy):
    name = "Balanced"
    CASH_BUFFER = 300

    def should_buy(self, player, prop, engine):
        if player.money - prop.price < self.CASH_BUFFER:
            return False
        if prop.type in ("railroad",):
            return True
        if prop.type == "utility":
            ut_owned = sum(1 for p in player.properties if p.type == "utility")
            return ut_owned == 1  # only buy second utility
        if prop.type == "property":
            if prop.color in PRIORITY_COLORS:
                return True
            return self._completes_group(player, prop, engine)
        return True

    def should_build(self, player, prop, engine):
        if player.money - prop.house_cost < self.CASH_BUFFER:
            return False
        # Build to hotels on priority colors, 3 houses on others
        if prop.color in PRIORITY_COLORS:
            return prop.houses < 5
        return prop.houses < 3

    def should_unmortgage(self, player, prop, engine):
        return player.money >= prop.unmortgage_cost + self.CASH_BUFFER

    def should_pay_jail_fine(self, player, engine):
        # Stay in jail in late game if lots of development
        total_dev = sum(pr.houses for p in engine.active_players for pr in p.properties)
        if total_dev > 20 and player.money >= self.CASH_BUFFER:
            return False
        return player.money >= self.CASH_BUFFER + 50

    def evaluate_trade(self, player, proposal, engine):
        # Accept at break-even or better (within 2%)
        return self._trade_ratio(player, proposal, engine) >= 0.98

    def find_trade_opportunity(self, player, engine):
        # Willing to pay a modest premium for priority groups
        return self._find_monopoly_trade(player, engine, offer_premium=0.05)

    def _completes_group(self, player, prop, engine):
        if prop.type != "property":
            return False
        group = COLOR_GROUPS.get(prop.color, [])
        owned = sum(1 for pos in group
                    if pos in engine.board_properties and
                    engine.board_properties[pos].owner == player)
        return owned == len(group) - 1