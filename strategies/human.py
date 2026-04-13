import tkinter as tk
from tkinter import messagebox, simpledialog
from strategies.base import BaseStrategy

class HumanStrategy(BaseStrategy):
    name = "Human"

    def should_buy(self, player, prop, engine):
        return messagebox.askyesno(
            "Buy Property?",
            f"{player.name}, buy {prop.name} for ${prop.price}?\nYour cash: ${player.money}",
            icon="question"
        )

    def should_build(self, player, prop, engine):
        # Human players build manually via the Property Management window.
        return False

    def should_unmortgage(self, player, prop, engine):
        # Human players unmortgage via the Property Management window.
        return False

    def should_pay_jail_fine(self, player, engine):
        return messagebox.askyesno(
            "Pay Jail Fine?",
            f"{player.name}, pay $50 to get out of jail?\nYour cash: ${player.money}",
            icon="question"
        )

    def should_use_goojf(self, player, engine):
        return messagebox.askyesno(
            "Use Get Out of Jail Free?",
            f"{player.name}, use your Get Out of Jail Free card?",
            icon="question"
        )

    def evaluate_trade(self, player, proposal, engine):
        from game.trade import trade_balance
        p = proposal.proposer
        op = "\n    ".join(pr.name for pr in proposal.offered_props) or "(nothing)"
        rp = "\n    ".join(pr.name for pr in proposal.requested_props) or "(nothing)"
        r_net, _ = trade_balance(proposal, engine)
        if r_net >= 0:
            value_line = f"You would gain approximately ${int(r_net):,} in strategic value."
        else:
            value_line = f"You would lose approximately ${int(-r_net):,} in strategic value."
        msg = (
            f"{p.name} is offering you a trade:\n\n"
            f"  {p.name} gives you:\n"
            f"    {op}\n"
            f"    Cash: ${proposal.offered_cash:,}\n\n"
            f"  You ({player.name}) give:\n"
            f"    {rp}\n"
            f"    Cash: ${proposal.requested_cash:,}\n\n"
            f"{value_line}\n\n"
            f"Accept this trade?"
        )
        return messagebox.askyesno(f"Trade Offer from {p.name}", msg, icon="question")