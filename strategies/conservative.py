from strategies.base import BaseStrategy
from game.constants import COLOR_GROUPS

class ConservativeStrategy(BaseStrategy):
    name = "Conservative"
    CASH_BUFFER = 400

    def should_buy(self, player, prop, engine):
        if player.money - prop.price < self.CASH_BUFFER:
            return False
        # Prefer cheap properties
        return prop.price <= 200 or self._completes_group(player, prop, engine)

    def should_build(self, player, prop, engine):
        if player.money - prop.house_cost < self.CASH_BUFFER:
            return False
        # Only build up to 3 houses
        return prop.houses < 3

    def should_unmortgage(self, player, prop, engine):
        return player.money >= prop.unmortgage_cost + self.CASH_BUFFER

    def should_pay_jail_fine(self, player, engine):
        active = engine.active_players
        total_hotels = sum(
            1 for p2 in active for pr in p2.properties
            if pr.type == "property" and pr.houses >= 4
        )
        # Prefer to stay in jail if many hotels on board (late game protection)
        if total_hotels > 6:
            return False
        return player.money >= self.CASH_BUFFER + 50

    def evaluate_trade(self, player, proposal, engine):
        # Only accept clearly beneficial trades (15%+ gain)
        return self._trade_ratio(player, proposal, engine) >= 1.15

    def find_trade_opportunity(self, player, engine):
        # Only propose when the deal is near-fair (0% premium max)
        return self._find_monopoly_trade(player, engine, offer_premium=0.0)

    def _completes_group(self, player, prop, engine):
        if prop.type != "property":
            return False
        group = COLOR_GROUPS.get(prop.color, [])
        owned_in_group = sum(
            1 for pos in group
            if pos in engine.board_properties and engine.board_properties[pos].owner == player
        )
        return owned_in_group == len(group) - 1