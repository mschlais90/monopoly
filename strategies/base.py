from abc import ABC, abstractmethod
from game.constants import COLOR_GROUPS

class BaseStrategy(ABC):
    name = "Base"

    def __init__(self):
        self.player = None

    @abstractmethod
    def should_buy(self, player, prop, engine):
        pass

    @abstractmethod
    def should_build(self, player, prop, engine):
        pass

    def should_unmortgage(self, player, prop, engine):
        return player.money >= prop.unmortgage_cost + 200

    def should_pay_jail_fine(self, player, engine):
        return player.money >= 200

    def should_use_goojf(self, player, engine):
        return True

    def should_mortgage_to_buy(self, player, prop, engine):
        """Return True to allow proactive mortgaging before a purchase."""
        return False

    def should_mortgage_to_build(self, player, prop, engine):
        """Return True to allow proactive mortgaging before building a house."""
        return False

    def select_to_mortgage(self, player, amount_needed, engine):
        """Return ordered list of properties to mortgage to reach amount_needed.
        Default: mortgage lowest-value unmortgaged properties that have no houses."""
        candidates = [p for p in player.properties
                      if not p.mortgaged and p.houses == 0]
        candidates.sort(key=lambda p: p.mortgage_value)
        result = []
        total = player.money
        for c in candidates:
            if total >= amount_needed:
                break
            result.append(c)
            total += c.mortgage_value
        return result

    # ── Trade hooks ──────────────────────────────────────────────────────────

    def evaluate_trade(self, player, proposal, engine):
        """Return True if player (as recipient) should accept this trade."""
        return False  # default: AI ignores trades unless overridden

    def find_trade_opportunity(self, player, engine):
        """Return a TradeProposal to initiate, or None. Called at end of turn."""
        return None

    # ── Shared trade helpers ──────────────────────────────────────────────────

    def _trade_ratio(self, player, proposal, engine):
        """Ratio of what recipient receives vs gives (>1 = good for recipient)."""
        from game.trade import trade_balance
        recipient_net, _ = trade_balance(proposal, engine)
        give_val = (proposal.requested_cash +
                    sum(p.price for p in proposal.requested_props)) or 1
        return (give_val + recipient_net) / give_val

    def _find_monopoly_trade(self, player, engine, offer_premium=0.0):
        """Look for a trade that would complete a color group for player.
        offer_premium: fraction above fair value we're willing to pay (e.g. 0.10 = 10% extra).
        Returns TradeProposal or None."""
        from game.trade import TradeProposal, strategic_value
        bp = engine.board_properties

        for color, positions in COLOR_GROUPS.items():
            props = [bp[p] for p in positions]
            mine = [p for p in props if p.owner == player and not p.mortgaged and p.houses == 0]
            needed = [p for p in props
                      if p.owner not in (None, player)
                      and not p.owner.bankrupt
                      and p.houses == 0]
            if not mine or not needed:
                continue

            for want in needed:
                target = want.owner
                want_val = strategic_value(want, player, [want], engine)

                # Try to find an offering of equivalent value
                offer_budget = want_val * (1.0 + offer_premium)
                # Prefer to offer single properties not in own near-monopoly groups
                candidates = sorted(
                    [p for p in player.properties
                     if p != want and not p.mortgaged and p.houses == 0
                     and p not in props],  # don't offer from the same group
                    key=lambda p: abs(p.price - want.price)
                )
                for offered in candidates:
                    cash_top_up = max(0, int(want_val - offered.price))
                    total_offered = offered.price + cash_top_up
                    if total_offered <= offer_budget and player.money >= cash_top_up:
                        return TradeProposal(
                            proposer=player,
                            recipient=target,
                            offered_props=[offered],
                            offered_cash=cash_top_up,
                            requested_props=[want],
                            requested_cash=0,
                        )
                # Cash-only offer if we have enough
                if player.money >= want_val * (1.0 + offer_premium):
                    return TradeProposal(
                        proposer=player,
                        recipient=target,
                        offered_props=[],
                        offered_cash=int(want_val * (1.0 + offer_premium)),
                        requested_props=[want],
                        requested_cash=0,
                    )
        return None