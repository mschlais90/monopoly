from game.constants import COLOR_GROUPS


class TradeProposal:
    def __init__(self, proposer, recipient,
                 offered_props, offered_cash,
                 requested_props, requested_cash):
        self.proposer = proposer
        self.recipient = recipient
        self.offered_props = list(offered_props)      # what proposer gives
        self.offered_cash = int(offered_cash)
        self.requested_props = list(requested_props)  # what proposer wants back
        self.requested_cash = int(requested_cash)

    def __repr__(self):
        op = [p.name for p in self.offered_props]
        rp = [p.name for p in self.requested_props]
        return (f"Trade({self.proposer.name} offers {op}+${self.offered_cash} "
                f"for {rp}+${self.requested_cash} from {self.recipient.name})")


def strategic_value(prop, for_player, extra_props_receiving, engine, giving=False):
    """Estimate the strategic value of a property.

    When giving=False (default), value the prop as if for_player is acquiring it
    (together with extra_props_receiving).
    When giving=True, value the prop based on what for_player currently has
    (i.e. how much it's worth to them right now, including this prop).
    """
    base = prop.price
    if prop.type == "property":
        group = COLOR_GROUPS.get(prop.color, [])
        currently_own = {pos for pos in group
                         if engine.board_properties[pos].owner == for_player}
        if giving:
            frac = len(currently_own) / len(group)
        else:
            receiving_positions = {p.pos for p in extra_props_receiving
                                   if p.type == "property"}
            will_own_after = currently_own | receiving_positions
            frac = len(will_own_after) / len(group)
        if frac >= 1.0:
            return base * 2.5   # completes/breaks monopoly
        elif frac >= 0.67:
            return base * 1.4
        elif frac >= 0.34:
            return base * 1.15
    elif prop.type == "railroad":
        owned = sum(1 for p in for_player.properties
                    if p.type == "railroad" and p != prop)
        if giving:
            after = min(owned + 1, 4)  # count including this prop
        else:
            extra = sum(1 for p in extra_props_receiving if p.type == "railroad")
            after = min(owned + extra + 1, 4)
        mult = {1: 1.0, 2: 1.5, 3: 2.1, 4: 3.0}[after]
        return base * mult
    elif prop.type == "utility":
        owned = sum(1 for p in for_player.properties
                    if p.type == "utility" and p != prop)
        if giving:
            after = owned + 1  # count including this prop
        else:
            extra = sum(1 for p in extra_props_receiving if p.type == "utility")
            after = owned + extra + 1
        return base * (1.8 if after >= 2 else 1.0)
    return base


def trade_balance(proposal, engine):
    """Return (recipient_net_gain, proposer_net_gain).
    Positive means that side benefits."""
    p, r = proposal.proposer, proposal.recipient

    # Recipient: receives offered_props + offered_cash, gives requested_props + requested_cash
    r_receive = proposal.offered_cash + sum(
        strategic_value(prop, r, proposal.offered_props, engine)
        for prop in proposal.offered_props
    )
    r_give = proposal.requested_cash + sum(
        strategic_value(prop, r, [], engine, giving=True)
        for prop in proposal.requested_props
    )
    recipient_net = r_receive - r_give

    # Proposer: receives requested_props + requested_cash, gives offered_props + offered_cash
    p_receive = proposal.requested_cash + sum(
        strategic_value(prop, p, proposal.requested_props, engine)
        for prop in proposal.requested_props
    )
    p_give = proposal.offered_cash + sum(
        strategic_value(prop, p, [], engine, giving=True)
        for prop in proposal.offered_props
    )
    proposer_net = p_receive - p_give

    return recipient_net, proposer_net
