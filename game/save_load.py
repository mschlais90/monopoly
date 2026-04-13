"""
Save / load game state to/from a JSON file.

Public API
----------
save_game(engine, filepath)      -> None
load_engine(filepath)            -> GameEngine   (raises on error)
"""

import json

# ── Strategy registry ────────────────────────────────────────────────────────

def _strategy_map():
    from strategies.random_strat    import RandomStrategy
    from strategies.conservative    import ConservativeStrategy
    from strategies.aggressive      import AggressiveStrategy
    from strategies.balanced        import BalancedStrategy
    from strategies.hyper_aggressive import HyperAggressiveStrategy
    from strategies.human           import HumanStrategy
    return {
        "Random":          RandomStrategy,
        "Conservative":    ConservativeStrategy,
        "Aggressive":      AggressiveStrategy,
        "Balanced":        BalancedStrategy,
        "HyperAggressive": HyperAggressiveStrategy,
        "Human":           HumanStrategy,
    }

def _strategy_name(strategy):
    cls = type(strategy).__name__
    aliases = {
        "RandomStrategy":        "Random",
        "ConservativeStrategy":  "Conservative",
        "AggressiveStrategy":    "Aggressive",
        "BalancedStrategy":      "Balanced",
        "HyperAggressiveStrategy": "HyperAggressive",
        "HumanStrategy":         "Human",
    }
    return aliases.get(cls, cls)


# ── Save ─────────────────────────────────────────────────────────────────────

def save_game(engine, filepath):
    """Serialise engine state to a JSON file."""

    players_data = []
    for p in engine.all_players:
        players_data.append({
            "name":                p.name,
            "color":               p.color,
            "strategy":            _strategy_name(p.strategy),
            "money":               p.money,
            "position":            p.position,
            "in_jail":             p.in_jail,
            "jail_turns":          p.jail_turns,
            "get_out_of_jail_free": p.get_out_of_jail_free,
            "bankrupt":            p.bankrupt,
            "doubles_streak":      p.doubles_streak,
            "turn_count":          p.turn_count,
            "properties":          [prop.pos for prop in p.properties],
        })

    board_data = {}
    for pos, prop in engine.board_properties.items():
        board_data[str(pos)] = {
            "owner":     prop.owner.name if prop.owner else None,
            "mortgaged": prop.mortgaged,
            "houses":    prop.houses,
        }

    data = {
        "version":           1,
        "turn_number":       engine.turn_number,
        "current_idx":       engine.current_idx,
        "game_over":         engine.game_over,
        "free_parking_pot":  engine.free_parking_pot,
        "declined_trades":   engine._declined_trades,
        "players":           players_data,
        "board":             board_data,
        "chance_deck":       {"cards": engine.chance_deck.cards,
                              "index": engine.chance_deck.index},
        "community_chest_deck": {"cards": engine.community_chest_deck.cards,
                                  "index": engine.community_chest_deck.index},
    }

    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


# ── Load ─────────────────────────────────────────────────────────────────────

def load_engine(filepath):
    """Deserialise a JSON save file and return a fully restored GameEngine."""
    from game.engine import GameEngine
    from game.player import Player
    from game.cards  import Deck

    with open(filepath, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    smap = _strategy_map()

    # ── Reconstruct players (without properties yet) ──────────────────────
    player_lookup = {}
    player_cfgs   = []
    for pd in data["players"]:
        strategy_cls = smap.get(pd["strategy"])
        if strategy_cls is None:
            raise ValueError(f"Unknown strategy: {pd['strategy']!r}")
        strategy = strategy_cls()
        cfg = {"name": pd["name"], "strategy": strategy, "color": pd["color"]}
        player_cfgs.append(cfg)

    # Build engine (this also initialises board_properties from BOARD_SPACES)
    engine = GameEngine(player_cfgs, starting_money=0)

    # ── Restore player state ──────────────────────────────────────────────
    for p, pd in zip(engine.all_players, data["players"]):
        player_lookup[pd["name"]] = p
        p.money               = pd["money"]
        p.position            = pd["position"]
        p.in_jail             = pd["in_jail"]
        p.jail_turns          = pd["jail_turns"]
        p.get_out_of_jail_free = pd["get_out_of_jail_free"]
        p.bankrupt            = pd["bankrupt"]
        p.doubles_streak      = pd["doubles_streak"]
        p.turn_count          = pd["turn_count"]

    # ── Restore board property state ──────────────────────────────────────
    for pos_str, bdata in data["board"].items():
        pos  = int(pos_str)
        prop = engine.board_properties.get(pos)
        if prop is None:
            continue
        owner_name = bdata["owner"]
        prop.owner     = player_lookup[owner_name] if owner_name else None
        prop.mortgaged = bdata["mortgaged"]
        prop.houses    = bdata["houses"]

    # ── Rebuild each player's properties list ─────────────────────────────
    for p, pd in zip(engine.all_players, data["players"]):
        p.properties = []
        for pos in pd["properties"]:
            prop = engine.board_properties.get(pos)
            if prop:
                p.properties.append(prop)

    # ── Restore engine-level state ────────────────────────────────────────
    engine.turn_number      = data["turn_number"]
    engine.current_idx      = data["current_idx"]
    engine.game_over        = data["game_over"]
    engine.free_parking_pot = data["free_parking_pot"]
    engine._declined_trades = {k: v for k, v in data["declined_trades"].items()}

    # ── Restore deck state ────────────────────────────────────────────────
    cd = data["chance_deck"]
    engine.chance_deck.cards = cd["cards"]
    engine.chance_deck.index = cd["index"]

    cc = data["community_chest_deck"]
    engine.community_chest_deck.cards = cc["cards"]
    engine.community_chest_deck.index = cc["index"]

    return engine
