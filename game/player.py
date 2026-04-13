class Player:
    def __init__(self, name, strategy, color, starting_money=1500):
        self.name = name
        self.strategy = strategy
        self.color = color
        self.money = starting_money
        self.position = 0
        self.properties = []
        self.in_jail = False
        self.jail_turns = 0
        self.get_out_of_jail_free = 0
        self.bankrupt = False
        self.doubles_streak = 0
        self.turn_count = 0

    def pay(self, amount):
        self.money -= amount

    def receive(self, amount):
        self.money += amount

    def net_worth(self):
        worth = self.money
        for p in self.properties:
            if p.mortgaged:
                worth += p.mortgage_value
            else:
                worth += p.price
                if p.type == "property" and p.houses > 0:
                    sell_back = p.house_cost // 2
                    worth += p.houses * sell_back
        return worth

    def owned_railroads(self):
        return [p for p in self.properties if p.type == "railroad" and not p.mortgaged]

    def owned_utilities(self):
        return [p for p in self.properties if p.type == "utility" and not p.mortgaged]

    def __repr__(self):
        return f"Player({self.name}, ${self.money})"