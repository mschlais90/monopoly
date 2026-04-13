import random
from game.constants import (BOARD_SPACES, COLOR_GROUPS, RAILROADS, UTILITIES,
                             GO_SALARY, JAIL_POSITION, JAIL_FINE, MAX_TURNS)
from game.board_property import BoardProperty
from game.player import Player
from game.dice import roll
from game.cards import make_decks


class GameEngine:
    def __init__(self, player_configs, starting_money=1500):
        self.board_spaces = BOARD_SPACES
        self.board_properties = {}
        for sp in BOARD_SPACES:
            if sp["type"] in ("property", "railroad", "utility"):
                self.board_properties[sp["pos"]] = BoardProperty(sp)

        self.chance_deck, self.community_chest_deck = make_decks()

        self.all_players = []
        for cfg in player_configs:
            p = Player(cfg["name"], cfg["strategy"], cfg["color"], starting_money)
            cfg["strategy"].player = p
            self.all_players.append(p)

        self.current_idx = 0
        self.turn_number = 0
        self.game_over = False
        self.winner = None
        self.log = []
        self.turn_log = []
        self._declined_trades = {}  # trade_key -> turn_number when declined
        self.free_parking_pot = 0
        self.defer_human_prompts = False   # set True by UI during animation
        self.pending_human_buys = []       # (player, prop) deferred buy decisions
        self.pending_human_trades = []     # TradeProposal deferred trade decisions

    @property
    def active_players(self):
        return [p for p in self.all_players if not p.bankrupt]

    def _log(self, msg):
        self.log.append(msg)
        self.turn_log.append(msg)

    def process_turn(self):
        if self.game_over:
            return False
        if len(self.active_players) <= 1:
            self._check_game_over()
            return not self.game_over

        # Skip bankrupt players
        attempts = 0
        while self.all_players[self.current_idx].bankrupt:
            self.current_idx = (self.current_idx + 1) % len(self.all_players)
            attempts += 1
            if attempts > len(self.all_players):
                self._check_game_over()
                return not self.game_over

        player = self.all_players[self.current_idx]
        self.turn_number += 1
        player.turn_count += 1
        self.turn_log = []
        self._log(f"=== Turn {self.turn_number}: {player.name} (${player.money}) ===")

        if player.in_jail:
            got_out, roll_used, roll_total = self._handle_jail_turn(player)
            if not got_out:
                self.current_idx = (self.current_idx + 1) % len(self.all_players)
                self._check_game_over()
                return not self.game_over
            elif roll_used:
                self._move_player(player, roll_total)
                if not player.bankrupt:
                    self._apply_landing(player, roll_total)
                if not player.bankrupt:
                    self._build_and_unmortgage(player)
                self.current_idx = (self.current_idx + 1) % len(self.all_players)
                self._check_game_over()
                return not self.game_over

        player.doubles_streak = 0
        for _ in range(3):  # max 3 rolls per turn (for doubles)
            d1, d2 = roll()
            doubles = (d1 == d2)
            total = d1 + d2
            self._log(f"  Rolled {d1}+{d2}={total}" + (" (Doubles!)" if doubles else ""))

            if doubles:
                player.doubles_streak += 1
                if player.doubles_streak >= 3:
                    self._log(f"  Three doubles! {player.name} goes to jail.")
                    self._send_to_jail(player)
                    break
            else:
                player.doubles_streak = 0

            self._move_player(player, total)
            if not player.bankrupt:
                self._apply_landing(player, total)

            if player.bankrupt or player.in_jail:
                break
            if not doubles:
                break
            self._log(f"  {player.name} rolls again for doubles!")

        if not player.bankrupt:
            self._build_and_unmortgage(player)
            self._trade_phase(player)

        self.current_idx = (self.current_idx + 1) % len(self.all_players)
        self._check_game_over()
        return not self.game_over

    def _handle_jail_turn(self, player):
        strategy = player.strategy
        # Use GOOJF card?
        if player.get_out_of_jail_free > 0 and strategy.should_use_goojf(player, self):
            player.get_out_of_jail_free -= 1
            player.in_jail = False
            player.jail_turns = 0
            self._log(f"  {player.name} used a Get Out of Jail Free card!")
            return True, False, 0

        # Pay fine?
        if player.money >= JAIL_FINE and strategy.should_pay_jail_fine(player, self):
            self._charge_bank(player, JAIL_FINE)
            player.in_jail = False
            player.jail_turns = 0
            self._log(f"  {player.name} paid ${JAIL_FINE} to get out of jail.")
            return True, False, 0

        # Forced on 3rd turn
        if player.jail_turns >= 2:
            self._charge_bank(player, JAIL_FINE)
            player.in_jail = False
            player.jail_turns = 0
            self._log(f"  {player.name} forced to pay ${JAIL_FINE} after 3 turns in jail.")
            return True, False, 0

        # Roll for doubles
        d1, d2 = roll()
        doubles = (d1 == d2)
        total = d1 + d2
        self._log(f"  Jail roll: {d1}+{d2}={total}")
        if doubles:
            player.in_jail = False
            player.jail_turns = 0
            self._log(f"  Doubles! {player.name} escapes jail and moves {total} spaces.")
            return True, True, total
        else:
            player.jail_turns += 1
            self._log(f"  No doubles. {player.name} stays in jail (turn {player.jail_turns}/3).")
            return False, False, 0

    def _move_player(self, player, steps):
        old_pos = player.position
        player.position = (player.position + steps) % 40
        if old_pos + steps >= 40:  # crossed or landed on Go
            player.receive(GO_SALARY)
            self._log(f"  Passed Go! {player.name} collects ${GO_SALARY}.")
        space_name = BOARD_SPACES[player.position]["name"]
        self._log(f"  {player.name} moves to [{player.position}] {space_name}.")

    def _apply_landing(self, player, dice_total):
        pos = player.position
        space = BOARD_SPACES[pos]
        stype = space["type"]

        if stype == "go":
            pass  # already collected when passing
        elif stype in ("property", "railroad", "utility"):
            prop = self.board_properties[pos]
            if prop.owner is None:
                self._offer_purchase(player, prop)
            elif prop.owner == player:
                self._log(f"  {player.name} owns {prop.name}.")
            else:
                self._collect_rent(player, prop, dice_total)
        elif stype == "tax":
            amt = space["amount"]
            self._log(f"  {player.name} pays {space['name']}: ${amt}.")
            self._charge_bank(player, amt, to_pot=True)
        elif stype == "chance":
            card = self.chance_deck.draw()
            self._log(f"  [CHANCE] {card['text']}")
            self._apply_card(player, card, dice_total)
        elif stype == "community_chest":
            card = self.community_chest_deck.draw()
            self._log(f"  [COMM. CHEST] {card['text']}")
            self._apply_card(player, card, dice_total)
        elif stype == "jail":
            self._log(f"  Just visiting jail.")
        elif stype == "go_to_jail":
            self._send_to_jail(player)
        elif stype == "free_parking":
            if self.free_parking_pot > 0:
                player.receive(self.free_parking_pot)
                self._log(f"  {player.name} collects ${self.free_parking_pot:,} from Free Parking!")
                self.free_parking_pot = 0
            else:
                self._log(f"  Free Parking. Pot is empty.")

    def _apply_card(self, player, card, dice_total):
        action = card["action"]
        if action == "advance_to":
            target = card["target"]
            self._card_advance(player, target, dice_total)
        elif action == "nearest_railroad":
            target = self._find_nearest(player.position, RAILROADS)
            old_pos = player.position
            player.position = target
            if target <= old_pos:
                player.receive(GO_SALARY)
                self._log(f"  Passed Go! Collected ${GO_SALARY}.")
            prop = self.board_properties[target]
            self._log(f"  Moved to nearest Railroad: {prop.name}.")
            if prop.owner and prop.owner != player:
                rr_cnt = len(prop.owner.owned_railroads())
                rent = prop.get_rent(owner_railroads=rr_cnt, double_rr=True)
                self._log(f"  Paying double RR rent: ${rent}.")
                self._transfer(player, prop.owner, rent)
            elif prop.owner is None:
                self._offer_purchase(player, prop)
        elif action == "nearest_utility":
            target = self._find_nearest(player.position, UTILITIES)
            old_pos = player.position
            player.position = target
            if target <= old_pos:
                player.receive(GO_SALARY)
                self._log(f"  Passed Go! Collected ${GO_SALARY}.")
            prop = self.board_properties[target]
            self._log(f"  Moved to nearest Utility: {prop.name}.")
            if prop.owner and prop.owner != player:
                d1, d2 = roll()
                new_total = d1 + d2
                rent = 10 * new_total
                self._log(f"  Rolled {d1}+{d2}={new_total} for utility. Paying 10x=${rent}.")
                self._transfer(player, prop.owner, rent)
            elif prop.owner is None:
                self._offer_purchase(player, prop)
        elif action == "collect":
            amt = card["amount"]
            player.receive(amt)
            self._log(f"  {player.name} collected ${amt}.")
        elif action == "pay":
            amt = card["amount"]
            self._charge_bank(player, amt, to_pot=True)
        elif action == "get_out_of_jail_free":
            player.get_out_of_jail_free += 1
            self._log(f"  {player.name} got a Get Out of Jail Free card.")
        elif action == "go_back":
            amt = card["amount"]
            player.position = (player.position - amt) % 40
            self._log(f"  {player.name} moved back {amt} to {BOARD_SPACES[player.position]['name']}.")
            self._apply_landing(player, dice_total)
        elif action == "go_to_jail":
            self._send_to_jail(player)
        elif action == "repairs":
            hc = card["house_cost"]
            htc = card["hotel_cost"]
            total_cost = sum(
                (htc if p.houses == 5 else p.houses * hc)
                for p in player.properties if p.type == "property"
            )
            self._log(f"  Repairs cost: ${total_cost}.")
            if total_cost > 0:
                self._charge_bank(player, total_cost, to_pot=True)
        elif action == "pay_each_player":
            amt = card["amount"]
            others = [p for p in self.active_players if p != player]
            for other in others:
                self._transfer(player, other, amt)
                if player.bankrupt:
                    break
        elif action == "collect_from_each":
            amt = card["amount"]
            others = [p for p in self.active_players if p != player]
            for other in others:
                self._transfer(other, player, amt)

    def _card_advance(self, player, target, dice_total):
        old_pos = player.position
        player.position = target
        # Passed Go if target <= old_pos (and it's not a backward move to a lower number
        # that doesn't pass Go - we check for forward travel past 39)
        if target < old_pos and target != 30:
            player.receive(GO_SALARY)
            self._log(f"  Passed Go! Collected ${GO_SALARY}.")
        space_name = BOARD_SPACES[target]["name"]
        self._log(f"  Advanced to [{target}] {space_name}.")
        self._apply_landing(player, dice_total)

    def _collect_rent(self, payer, prop, dice_total):
        owner = prop.owner
        is_mono = self._is_monopoly(owner, prop)
        rr_cnt = len(owner.owned_railroads())
        ut_cnt = len(owner.owned_utilities())
        rent = prop.get_rent(dice_total=dice_total, owner_railroads=rr_cnt,
                              owner_utilities=ut_cnt, is_monopoly=is_mono)
        label = f"hotel" if prop.houses == 5 else (f"{prop.houses} house(s)" if prop.houses > 0 else "base")
        self._log(f"  {payer.name} owes ${rent} rent to {owner.name} for {prop.name} ({label}).")
        self._transfer(payer, owner, rent)

    def _offer_purchase(self, player, prop):
        self._log(f"  {prop.name} is unowned (${prop.price}). {player.name} has ${player.money}.")
        from strategies.human import HumanStrategy
        if self.defer_human_prompts and isinstance(player.strategy, HumanStrategy):
            if player.money >= prop.price:
                self.pending_human_buys.append((player, prop))
                self._log(f"  [Buy decision pending for {player.name}...]")
            return
        if not player.strategy.should_buy(player, prop, self):
            self._log(f"  {player.name} passed on {prop.name}.")
            return
        # Raise cash via mortgaging if needed and strategy allows
        if player.money < prop.price and player.strategy.should_mortgage_to_buy(player, prop, self):
            self._proactive_mortgage(player, prop.price)
        if player.money >= prop.price:
            prop.owner = player
            player.properties.append(prop)
            player.pay(prop.price)
            self._log(f"  {player.name} bought {prop.name} for ${prop.price}.")
        else:
            self._log(f"  {player.name} cannot afford {prop.name} (${player.money}/${prop.price}).")

    def _send_to_jail(self, player):
        player.position = JAIL_POSITION
        player.in_jail = True
        player.jail_turns = 0
        player.doubles_streak = 0
        self._log(f"  {player.name} is sent to jail!")

    def _charge_bank(self, player, amount, to_pot=False):
        # _raise_cash uses player.receive() directly — mortgage/house-sale proceeds
        # go to the player only and never interact with the pot.
        if player.money < amount:
            self._raise_cash(player, amount)

        if player.money >= amount:
            player.pay(amount)
            # Only the actual charged amount (tax / card fine) goes to the pot,
            # never the cash raised internally through mortgaging or selling houses.
            if to_pot:
                self.free_parking_pot += amount
                self._log(f"  ${amount} added to Free Parking pot (now ${self.free_parking_pot:,}).")
        else:
            self._log(f"  {player.name} cannot pay ${amount}. BANKRUPT to bank!")
            self._bankrupt(player, None)

    def _transfer(self, payer, receiver, amount):
        if payer.money >= amount:
            payer.pay(amount)
            receiver.receive(amount)
        else:
            if self._raise_cash(payer, amount):
                payer.pay(amount)
                receiver.receive(amount)
            else:
                self._log(f"  {payer.name} cannot pay ${amount} to {receiver.name}. BANKRUPT!")
                self._bankrupt(payer, receiver)

    def _raise_cash(self, player, amount_needed):
        props_with_houses = sorted(
            [p for p in player.properties if p.type == "property" and p.houses > 0],
            key=lambda p: p.house_cost, reverse=True
        )
        for prop in props_with_houses:
            while prop.houses > 0 and player.money < amount_needed:
                prop.houses -= 1
                val = prop.house_cost // 2
                player.receive(val)
                self._log(f"  {player.name} sold house on {prop.name} for ${val}.")

        if player.money >= amount_needed:
            return True

        unmortgaged = sorted(
            [p for p in player.properties if not p.mortgaged],
            key=lambda p: p.mortgage_value
        )
        for prop in unmortgaged:
            if player.money >= amount_needed:
                break
            prop.mortgaged = True
            player.receive(prop.mortgage_value)
            self._log(f"  {player.name} mortgaged {prop.name} for ${prop.mortgage_value}.")

        return player.money >= amount_needed

    def _bankrupt(self, player, creditor):
        if player.bankrupt:
            return
        player.bankrupt = True
        if creditor and not creditor.bankrupt:
            creditor.receive(player.money)
            for prop in list(player.properties):
                prop.owner = creditor
                creditor.properties.append(prop)
            player.properties.clear()
            player.money = 0
            self._log(f"  ** {player.name} is BANKRUPT! Assets transferred to {creditor.name}. **")
        else:
            for prop in list(player.properties):
                prop.owner = None
                prop.mortgaged = False
                prop.houses = 0
            player.properties.clear()
            player.money = 0
            self._log(f"  ** {player.name} is BANKRUPT! Properties returned to bank. **")

    def _build_and_unmortgage(self, player):
        self._building_phase(player)
        self._unmortgage_phase(player)

    def _building_phase(self, player):
        for color, positions in COLOR_GROUPS.items():
            props = [self.board_properties[p] for p in positions]
            if not all(p.owner == player and not p.mortgaged for p in props):
                continue
            changed = True
            while changed:
                changed = False
                min_h = min(p.houses for p in props)
                if min_h >= 5:
                    break
                for prop in sorted(props, key=lambda p: p.houses):
                    if prop.houses == min_h and prop.houses < 5:
                        cost = prop.house_cost
                        if player.strategy.should_build(player, prop, self):
                            if (player.money < cost and
                                    player.strategy.should_mortgage_to_build(player, prop, self)):
                                self._proactive_mortgage(player, cost)
                            if player.money >= cost:
                                player.pay(cost)
                                prop.houses += 1
                                label = "hotel" if prop.houses == 5 else f"{prop.houses}H"
                                self._log(f"  {player.name} built on {prop.name} ({label}) for ${cost}.")
                                changed = True
                            else:
                                break
                        else:
                            break
                    if player.bankrupt:
                        return

    def _unmortgage_phase(self, player):
        for prop in list(player.properties):
            if prop.mortgaged:
                cost = prop.unmortgage_cost
                if player.money >= cost and player.strategy.should_unmortgage(player, prop, self):
                    player.pay(cost)
                    prop.mortgaged = False
                    self._log(f"  {player.name} unmortgaged {prop.name} for ${cost}.")

    def _proactive_mortgage(self, player, amount_needed):
        """Ask the strategy which properties to mortgage, then mortgage them."""
        to_mortgage = player.strategy.select_to_mortgage(player, amount_needed, self)
        for prop in to_mortgage:
            if player.money >= amount_needed:
                break
            if not prop.mortgaged and prop.houses == 0:
                prop.mortgaged = True
                player.receive(prop.mortgage_value)
                self._log(f"  {player.name} mortgaged {prop.name} for ${prop.mortgage_value}.")

    def _find_nearest(self, pos, targets):
        for i in range(1, 41):
            candidate = (pos + i) % 40
            if candidate in targets:
                return candidate
        return targets[0]

    def _is_monopoly(self, player, prop):
        if prop.type != "property":
            return False
        group = COLOR_GROUPS.get(prop.color, [])
        return all(self.board_properties[p].owner == player for p in group)

    def execute_trade(self, proposal):
        """Execute a confirmed trade between two players."""
        p, r = proposal.proposer, proposal.recipient
        for prop in list(proposal.offered_props):
            if prop in p.properties:
                p.properties.remove(prop)
            r.properties.append(prop)
            prop.owner = r
        for prop in list(proposal.requested_props):
            if prop in r.properties:
                r.properties.remove(prop)
            p.properties.append(prop)
            prop.owner = p
        p.pay(proposal.offered_cash)
        r.receive(proposal.offered_cash)
        r.pay(proposal.requested_cash)
        p.receive(proposal.requested_cash)
        op = ', '.join(pr.name for pr in proposal.offered_props) or 'nothing'
        rp = ', '.join(pr.name for pr in proposal.requested_props) or 'nothing'
        msg = (f"  [TRADE] {p.name} gives {op}+${proposal.offered_cash} "
               f"| {r.name} gives {rp}+${proposal.requested_cash}")
        self._log(msg)

    def _trade_key(self, proposal):
        """Stable key identifying a specific trade offer for cooldown tracking."""
        return (
            proposal.proposer.name,
            proposal.recipient.name,
            frozenset(p.pos for p in proposal.offered_props),
            frozenset(p.pos for p in proposal.requested_props),
        )

    def _trade_phase(self, player):
        """AI player looks for a trade opportunity and proposes it to the other party."""
        if player.bankrupt or len(self.active_players) < 2:
            return
        proposal = player.strategy.find_trade_opportunity(player, self)
        if proposal is None:
            return
        recipient = proposal.recipient
        if recipient.bankrupt:
            return

        # Cooldown check: skip if this exact trade was declined within 10 full rounds
        key = self._trade_key(proposal)
        cooldown = 10 * len(self.active_players)
        if self.turn_number - self._declined_trades.get(key, -cooldown) < cooldown:
            return

        # Defer to UI if animation is pending and recipient is human
        from strategies.human import HumanStrategy
        if self.defer_human_prompts and isinstance(recipient.strategy, HumanStrategy):
            self.pending_human_trades.append(proposal)
            self._log(f"  [Trade decision pending for {recipient.name}...]")
            return

        # Recipient evaluates
        accepted = recipient.strategy.evaluate_trade(recipient, proposal, self)
        if accepted:
            self.execute_trade(proposal)
        else:
            op = ', '.join(p.name for p in proposal.offered_props) or f'${proposal.offered_cash}'
            rp = ', '.join(p.name for p in proposal.requested_props) or f'${proposal.requested_cash}'
            self._log(f"  [TRADE DECLINED] {recipient.name} declined "
                      f"{player.name}'s offer of {op} for {rp}.")
            self._declined_trades[key] = self.turn_number

    def _check_game_over(self):
        active = self.active_players
        if len(active) <= 1 or self.turn_number >= MAX_TURNS:
            self.game_over = True
            if active:
                self.winner = max(active, key=lambda p: p.net_worth())
            self._log(f"  *** GAME OVER! Winner: {self.winner.name if self.winner else 'None'} ***")

    def get_state(self):
        return {
            "turn": self.turn_number,
            "game_over": self.game_over,
            "winner": self.winner,
            "players": self.all_players,
            "active_players": self.active_players,
            "board_properties": self.board_properties,
            "current_player": self.all_players[self.current_idx] if self.all_players else None,
        }