import random
from strategies.base import BaseStrategy

class RandomStrategy(BaseStrategy):
    name = "Random"

    def should_buy(self, player, prop, engine):
        return player.money >= prop.price and random.random() < 0.7

    def should_build(self, player, prop, engine):
        return player.money >= prop.house_cost + 100 and random.random() < 0.5

    def should_pay_jail_fine(self, player, engine):
        return random.random() < 0.5 and player.money >= 100

    def evaluate_trade(self, player, proposal, engine):
        ratio = self._trade_ratio(player, proposal, engine)
        if ratio >= 0.90:
            return random.random() < 0.75
        if ratio >= 0.75:
            return random.random() < 0.35
        return False

    def find_trade_opportunity(self, player, engine):
        if random.random() < 0.4:
            return self._find_monopoly_trade(player, engine, offer_premium=0.05)
        return None