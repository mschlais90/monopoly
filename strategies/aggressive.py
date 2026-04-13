from strategies.base import BaseStrategy

class AggressiveStrategy(BaseStrategy):
    name = "Aggressive"

    def should_buy(self, player, prop, engine):
        return player.money >= prop.price + 50

    def should_build(self, player, prop, engine):
        return player.money >= prop.house_cost + 50

    def should_unmortgage(self, player, prop, engine):
        return player.money >= prop.unmortgage_cost + 50

    def should_pay_jail_fine(self, player, engine):
        return player.money >= 100

    def evaluate_trade(self, player, proposal, engine):
        # Accept neutral or slightly unfavourable trades (down to 12% loss)
        return self._trade_ratio(player, proposal, engine) >= 0.88

    def find_trade_opportunity(self, player, engine):
        # Will pay up to 8% premium to complete a monopoly
        return self._find_monopoly_trade(player, engine, offer_premium=0.08)