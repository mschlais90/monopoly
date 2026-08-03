"""
Flask API server for the Monopoly web client.

Run:  python web/server.py          (from the project root)
  or: cd web && python server.py    (also works, path is adjusted)
"""

import os
import sys
import uuid
import json
import tempfile

_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_dir)
if _root not in sys.path:
    sys.path.insert(0, _root)

from flask import Flask, jsonify, request, send_from_directory

from game.engine import GameEngine
from game.constants import (BOARD_SPACES, COLOR_GROUPS, COLOR_HEX,
                            PLAYER_COLORS, PLAYER_COLOR_NAMES)
from game.save_load import _strategy_name
from strategies.random_strat import RandomStrategy
from strategies.conservative import ConservativeStrategy
from strategies.aggressive import AggressiveStrategy
from strategies.balanced import BalancedStrategy
from strategies.hyper_aggressive import HyperAggressiveStrategy
from strategies.base import BaseStrategy


class WebHumanStrategy(BaseStrategy):
    """Human player over HTTP - decisions are deferred to the client."""
    name = "Human"

    def __init__(self):
        super().__init__()

    def should_buy(self, player, prop, engine):
        return None

    def should_build(self, player, prop, engine):
        return False

    def should_unmortgage(self, player, prop, engine):
        return False

    def should_pay_jail_fine(self, player, engine):
        return None

    def should_use_goojf(self, player, engine):
        return None


STRATEGY_MAP = {
    "Random": RandomStrategy,
    "Conservative": ConservativeStrategy,
    "Aggressive": AggressiveStrategy,
    "Balanced": BalancedStrategy,
    "HyperAggressive": HyperAggressiveStrategy,
    "Human": WebHumanStrategy,
}

sessions = {}

app = Flask(__name__, static_folder="static")


def _current_player(engine):
    """The player whose turn is actually next.

    `engine.current_idx` can point at a bankrupt player — nothing rewinds it when
    someone busts, and `process_turn` only skips bankrupt players once it runs.
    Resolving the index the same way here keeps the server from mistaking a human
    turn for an AI turn (which would silently drop their jail/buy prompts).
    """
    n = len(engine.all_players)
    idx = engine.current_idx % n
    for _ in range(n):
        if not engine.all_players[idx].bankrupt:
            break
        idx = (idx + 1) % n
    return engine.all_players[idx]


def _trade_pending(engine, proposal):
    from game.trade import trade_balance
    recipient_net, _ = trade_balance(proposal, engine)
    return {
        "type": "trade",
        "proposer": proposal.proposer.name,
        "recipient": proposal.recipient.name,
        "offered_props": [{"name": p.name, "price": p.price} for p in proposal.offered_props],
        "offered_cash": proposal.offered_cash,
        "requested_props": [{"name": p.name, "price": p.price} for p in proposal.requested_props],
        "requested_cash": proposal.requested_cash,
        "recipient_net": recipient_net,
    }


def _pending_payload(engine):
    """Next decision the browser owes us, or None.

    Buys are queued (rolling doubles can land on two unowned properties in one
    turn), so this is called again after each answer until the queue drains.
    """
    if engine.pending_human_jail:
        player = engine.pending_human_jail
        return {
            "type": "jail",
            "player": player.name,
            "cash": player.money,
            "jail_turns": player.jail_turns,
            "goojf": player.get_out_of_jail_free,
        }

    # Drop queued buys for properties that were taken in the meantime.
    while engine.pending_human_buys and engine.pending_human_buys[0][1].owner is not None:
        engine.pending_human_buys.pop(0)
    if engine.pending_human_buys:
        player, prop = engine.pending_human_buys[0]
        return {
            "type": "buy",
            "property": prop.name,
            "price": prop.price,
            "pos": prop.pos,
            "cash": player.money,
            "remaining": len(engine.pending_human_buys),
        }

    while engine.pending_human_trades and (
            engine.pending_human_trades[0].recipient.bankrupt
            or engine.pending_human_trades[0].proposer.bankrupt):
        engine.pending_human_trades.pop(0)
    if engine.pending_human_trades:
        return _trade_pending(engine, engine.pending_human_trades[0])

    return None


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/strategies")
def list_strategies():
    return jsonify(list(STRATEGY_MAP.keys()))


@app.route("/api/constants")
def get_constants():
    return jsonify({
        "board_spaces": BOARD_SPACES,
        "color_groups": COLOR_GROUPS,
        "color_hex": COLOR_HEX,
        "player_colors": PLAYER_COLORS,
        "player_color_names": PLAYER_COLOR_NAMES,
    })


@app.route("/api/new_game", methods=["POST"])
def new_game():
    body = request.json
    player_configs = []
    for i, pc in enumerate(body["players"]):
        cls = STRATEGY_MAP.get(pc["strategy"])
        if cls is None:
            return jsonify({"error": f"Unknown strategy: {pc['strategy']}"}), 400
        strat = cls()
        player_configs.append({
            "name": pc["name"],
            "strategy": strat,
            "color": pc.get("color", PLAYER_COLORS[i % len(PLAYER_COLORS)]),
        })
    starting_money = body.get("starting_money", 1500)
    engine = GameEngine(player_configs, starting_money)
    sid = uuid.uuid4().hex[:12]
    sessions[sid] = {"engine": engine}
    return jsonify({"session_id": sid, "state": _full_state(engine)})


def _full_state(engine):
    players = []
    for p in engine.all_players:
        players.append({
            "name": p.name,
            "color": p.color,
            "money": p.money,
            "position": p.position,
            "in_jail": p.in_jail,
            "jail_turns": p.jail_turns,
            "goojf": p.get_out_of_jail_free,
            "bankrupt": p.bankrupt,
            "strategy": _strategy_name(p.strategy) if not isinstance(p.strategy, WebHumanStrategy) else "Human",
            "net_worth": p.net_worth(),
            "properties": [
                {
                    "pos": prop.pos,
                    "name": prop.name,
                    "type": prop.type,
                    "color": getattr(prop, "color", None),
                    "price": prop.price,
                    "mortgaged": prop.mortgaged,
                    "houses": prop.houses,
                    "house_cost": prop.house_cost,
                    "mortgage_value": prop.mortgage_value,
                    "unmortgage_cost": prop.unmortgage_cost,
                }
                for prop in p.properties
            ],
        })

    board = {}
    for pos, prop in engine.board_properties.items():
        board[str(pos)] = {
            "name": prop.name,
            "owner": prop.owner.name if prop.owner else None,
            "mortgaged": prop.mortgaged,
            "houses": prop.houses,
            "price": prop.price,
        }

    return {
        "turn": engine.turn_number,
        "current_player": _current_player(engine).name,
        "game_over": engine.game_over,
        "winner": engine.winner.name if engine.winner else None,
        "free_parking_pot": engine.free_parking_pot,
        "players": players,
        "board": board,
    }


@app.route("/api/next_turn", methods=["POST"])
def next_turn():
    sid = request.json.get("session_id")
    sess = sessions.get(sid)
    if not sess:
        return jsonify({"error": "Invalid session"}), 404
    engine = sess["engine"]
    if engine.game_over:
        return jsonify({"state": _full_state(engine), "log": [], "pending": None})

    # Deferred prompts are armed unconditionally: `process_turn` skips bankrupt
    # players, so even a turn that looks like an AI's can land on the human.
    engine.turn_log = []
    engine.defer_human_prompts = True
    engine.pending_human_buys = []
    engine.pending_human_trades = []
    engine.pending_human_jail = None
    engine.process_turn()
    engine.defer_human_prompts = False

    return jsonify({
        "state": _full_state(engine),
        "log": engine.turn_log,
        "pending": _pending_payload(engine),
    })


@app.route("/api/decide", methods=["POST"])
def decide():
    body = request.json
    sid = body.get("session_id")
    sess = sessions.get(sid)
    if not sess:
        return jsonify({"error": "Invalid session"}), 404
    engine = sess["engine"]
    dtype = body.get("type")
    choice = body.get("choice")
    extra_log = []

    def leave_jail_and_move(player):
        """Roll, move, and queue whatever the landing asks the player to decide."""
        from game.dice import roll
        d1, d2 = roll()
        total = d1 + d2
        extra_log.append(f"  Rolled {d1}+{d2}={total}" + (" (Doubles!)" if d1 == d2 else ""))
        engine.turn_log = []
        engine.defer_human_prompts = True
        engine.pending_human_buys = []
        engine.pending_human_trades = []
        engine._move_player(player, total)
        if not player.bankrupt:
            engine._apply_landing(player, total)
        engine.defer_human_prompts = False
        extra_log.extend(engine.turn_log)
        engine.turn_log = []

    if dtype == "jail":
        player = engine.pending_human_jail
        engine.pending_human_jail = None
        if player:
            from game.constants import JAIL_FINE
            from game.dice import roll
            if choice == "goojf" and player.get_out_of_jail_free > 0:
                player.get_out_of_jail_free -= 1
                player.in_jail = False
                player.jail_turns = 0
                extra_log.append(f"  {player.name} used a Get Out of Jail Free card!")
                leave_jail_and_move(player)
            elif choice and choice != "goojf":  # pay fine
                engine._charge_bank(player, JAIL_FINE)
                if not player.bankrupt:
                    player.in_jail = False
                    player.jail_turns = 0
                    extra_log.append(f"  {player.name} paid ${JAIL_FINE} to get out of jail.")
                    leave_jail_and_move(player)
            else:  # roll for doubles
                d1, d2 = roll()
                doubles = (d1 == d2)
                total = d1 + d2
                extra_log.append(f"  Jail roll: {d1}+{d2}={total}")
                if doubles:
                    player.in_jail = False
                    player.jail_turns = 0
                    extra_log.append(f"  Doubles! {player.name} escapes jail and moves {total} spaces.")
                    engine.turn_log = []
                    engine.defer_human_prompts = True
                    engine.pending_human_buys = []
                    engine.pending_human_trades = []
                    engine._move_player(player, total)
                    if not player.bankrupt:
                        engine._apply_landing(player, total)
                    engine.defer_human_prompts = False
                    extra_log.extend(engine.turn_log)
                    engine.turn_log = []
                else:
                    player.jail_turns += 1
                    extra_log.append(f"  No doubles. {player.name} stays in jail (turn {player.jail_turns}/3).")
    elif dtype == "buy":
        if engine.pending_human_buys:
            player, prop = engine.pending_human_buys.pop(0)
            if choice and prop.owner is None and player.money >= prop.price:
                prop.owner = player
                player.properties.append(prop)
                player.pay(prop.price)
                extra_log.append(f"  {player.name} bought {prop.name} for ${prop.price}.")
            else:
                extra_log.append(f"  {player.name} passed on {prop.name}.")
    elif dtype == "trade":
        if engine.pending_human_trades:
            proposal = engine.pending_human_trades.pop(0)
            if choice:
                engine.execute_trade(proposal)
                extra_log.extend(engine.turn_log)
                engine.turn_log = []
            else:
                engine._declined_trades[engine._trade_key(proposal)] = engine.turn_number

    # A single turn can queue several decisions (doubles landing on two unowned
    # properties, say), so hand back the next one instead of discarding the rest.
    return jsonify({
        "state": _full_state(engine),
        "log": extra_log,
        "pending": _pending_payload(engine),
    })



@app.route("/api/propose_trade", methods=["POST"])
def propose_trade():
    body = request.json
    sid = body.get("session_id")
    sess = sessions.get(sid)
    if not sess:
        return jsonify({"error": "Invalid session"}), 404
    engine = sess["engine"]
    
    from game.trade import TradeProposal
    
    proposer_name = body.get("proposer_name")
    recipient_name = body.get("recipient_name")
    offered_positions = body.get("offered_prop_positions", [])
    offered_cash = body.get("offered_cash", 0)
    requested_positions = body.get("requested_prop_positions", [])
    requested_cash = body.get("requested_cash", 0)
    
    proposer = next((p for p in engine.all_players if p.name == proposer_name), None)
    recipient = next((p for p in engine.all_players if p.name == recipient_name), None)

    if not proposer or not recipient:
        return jsonify({"error": "Invalid players"}), 400

    offered_props = [engine.board_properties[pos] for pos in offered_positions if pos in engine.board_properties and engine.board_properties[pos].owner == proposer]
    requested_props = [engine.board_properties[pos] for pos in requested_positions if pos in engine.board_properties and engine.board_properties[pos].owner == recipient]
    
    proposal = TradeProposal(proposer, recipient, offered_props, offered_cash, requested_props, requested_cash)
    
    # Check cooldown
    key = engine._trade_key(proposal)
    if key in engine._declined_trades:
        last_declined = engine._declined_trades[key]
        if engine.turn_number - last_declined < 10:
            return jsonify({
                "error": f"Trade on cooldown ({10 - (engine.turn_number - last_declined)} turns remaining)",
                "state": _full_state(engine),
                "log": []
            })
    
    # Log the proposal
    engine._log_trade_proposal(proposal)
    extra_log = list(engine.turn_log)
    engine.turn_log = []

    # If recipient is human, defer the decision to the browser
    if isinstance(recipient.strategy, WebHumanStrategy):
        engine.pending_human_trades = [proposal]
        return jsonify({
            "state": _full_state(engine),
            "log": extra_log,
            "pending": _trade_pending(engine, proposal),
        })

    # AI recipient evaluates
    accepted = recipient.strategy.evaluate_trade(recipient, proposal, engine)

    if accepted:
        engine.execute_trade(proposal)
        extra_log.extend(engine.turn_log)
        engine.turn_log = []
    else:
        engine._declined_trades[key] = engine.turn_number

    return jsonify({
        "state": _full_state(engine),
        "log": extra_log,
        "pending": None,
    })
@app.route("/api/mortgage", methods=["POST"])
def mortgage_property():
    body = request.json
    sess = sessions.get(body["session_id"])
    if not sess:
        return jsonify({"error": "Invalid session"}), 404
    engine = sess["engine"]
    player = next((p for p in engine.all_players if p.name == body["player"]), None)
    prop = engine.board_properties.get(body["pos"])
    if not player or not prop or prop.owner != player:
        return jsonify({"error": "Invalid property"}), 400
    if prop.mortgaged or prop.houses > 0:
        return jsonify({"error": "Cannot mortgage"}), 400
    if prop.type == "property":
        group = COLOR_GROUPS.get(prop.color, [])
        if any(engine.board_properties[p].houses > 0
               for p in group if engine.board_properties[p].owner == player):
            return jsonify({"error": "Sell houses in group first"}), 400

    prop.mortgaged = True
    player.receive(prop.mortgage_value)
    return jsonify({"state": _full_state(engine),
                    "log": [f"  {player.name} mortgaged {prop.name} for ${prop.mortgage_value}."]})


@app.route("/api/unmortgage", methods=["POST"])
def unmortgage_property():
    body = request.json
    sess = sessions.get(body["session_id"])
    if not sess:
        return jsonify({"error": "Invalid session"}), 404
    engine = sess["engine"]
    player = next((p for p in engine.all_players if p.name == body["player"]), None)
    prop = engine.board_properties.get(body["pos"])
    if not player or not prop or prop.owner != player:
        return jsonify({"error": "Invalid property"}), 400
    if not prop.mortgaged:
        return jsonify({"error": "Not mortgaged"}), 400
    cost = prop.unmortgage_cost
    if player.money < cost:
        return jsonify({"error": "Insufficient funds"}), 400
    player.pay(cost)
    prop.mortgaged = False
    return jsonify({"state": _full_state(engine),
                    "log": [f"  {player.name} unmortgaged {prop.name} for ${cost}."]})


@app.route("/api/buy_house", methods=["POST"])
def buy_house():
    body = request.json
    sess = sessions.get(body["session_id"])
    if not sess:
        return jsonify({"error": "Invalid session"}), 404
    engine = sess["engine"]
    player = next((p for p in engine.all_players if p.name == body["player"]), None)
    prop = engine.board_properties.get(body["pos"])
    if not player or not prop or prop.owner != player:
        return jsonify({"error": "Invalid property"}), 400
    if prop.type != "property" or prop.mortgaged or prop.houses >= 5:
        return jsonify({"error": "Cannot build here"}), 400
    bp = engine.board_properties
    group = COLOR_GROUPS.get(prop.color, [])
    if not all(bp[p].owner == player for p in group):
        return jsonify({"error": "Need full color group"}), 400
    if any(bp[p].mortgaged for p in group):
        return jsonify({"error": "Unmortgage group first"}), 400
    min_h = min(bp[p].houses for p in group)
    if prop.houses > min_h:
        return jsonify({"error": "Even building rule"}), 400
    if player.money < prop.house_cost:
        return jsonify({"error": "Insufficient funds"}), 400

    player.pay(prop.house_cost)
    prop.houses += 1
    label = "hotel" if prop.houses == 5 else f"{prop.houses} house(s)"
    return jsonify({"state": _full_state(engine),
                    "log": [f"  {player.name} built on {prop.name} ({label}) for ${prop.house_cost}."]})


@app.route("/api/save", methods=["POST"])
def save():
    from game.save_load import save_game
    sid = request.json.get("session_id")
    sess = sessions.get(sid)
    if not sess:
        return jsonify({"error": "Invalid session"}), 404
    engine = sess["engine"]
    tmp = tempfile.mktemp(suffix=".json")
    try:
        save_game(engine, tmp)
        with open(tmp, "r", encoding="utf-8") as f:
            data = json.load(f)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    return jsonify(data)


@app.route("/api/load", methods=["POST"])
def load():
    from game.save_load import load_engine as _load
    from game import save_load
    body = request.json
    save_data = body.get("save_data")
    if not save_data:
        return jsonify({"error": "No save data"}), 400

    tmp = tempfile.mktemp(suffix=".json")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(save_data, f)
        orig_map = save_load._strategy_map
        def patched_map():
            m = orig_map()
            m["Human"] = WebHumanStrategy
            m["WebHumanStrategy"] = WebHumanStrategy
            return m
        save_load._strategy_map = patched_map
        try:
            engine = _load(tmp)
        finally:
            save_load._strategy_map = orig_map
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

    sid = uuid.uuid4().hex[:12]
    sessions[sid] = {"engine": engine}
    return jsonify({"session_id": sid, "state": _full_state(engine)})


@app.route("/api/auto_turns", methods=["POST"])
def auto_turns():
    body = request.json
    sid = body["session_id"]
    count = min(body.get("count", 1), 100)
    sess = sessions.get(sid)
    if not sess:
        return jsonify({"error": "Invalid session"}), 404
    engine = sess["engine"]
    all_logs = []

    pending = None
    for _ in range(count):
        if engine.game_over:
            break
        if isinstance(_current_player(engine).strategy, WebHumanStrategy):
            break
        engine.turn_log = []
        engine.defer_human_prompts = True
        engine.pending_human_buys = []
        engine.pending_human_trades = []
        engine.pending_human_jail = None
        engine.process_turn()
        engine.defer_human_prompts = False
        all_logs.extend(engine.turn_log)

        pending = _pending_payload(engine)
        if pending:
            break

    human_next = False
    if not engine.game_over:
        human_next = isinstance(_current_player(engine).strategy, WebHumanStrategy)

    return jsonify({
        "state": _full_state(engine),
        "log": all_logs,
        "human_next": human_next,
        "pending": pending,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"Starting Monopoly Web Server on port {port}...")
    if port == 5000:
        print("Open http://127.0.0.1:5000 in your browser")
    app.run(host="0.0.0.0", port=port, debug=debug)





