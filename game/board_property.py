class BoardProperty:
    def __init__(self, space_data):
        self.pos = space_data["pos"]
        self.name = space_data["name"]
        self.type = space_data["type"]
        self.price = space_data.get("price", 0)
        self.owner = None
        self.mortgaged = False
        self.houses = 0  # 0-4 houses; 5 = hotel
        if self.type == "property":
            self.color = space_data["color"]
            self.rent_table = space_data["rent"]
            self.house_cost = space_data["house_cost"]
        else:
            self.color = None
            self.rent_table = None
            self.house_cost = 0

    @property
    def mortgage_value(self):
        return self.price // 2

    @property
    def unmortgage_cost(self):
        return int(self.mortgage_value * 1.1)

    def get_rent(self, dice_total=0, owner_railroads=0, owner_utilities=0,
                 is_monopoly=False, double_rr=False):
        if self.mortgaged:
            return 0
        if self.type == "property":
            if self.houses >= 1:
                idx = self.houses + 1
                return self.rent_table[min(idx, 6)]
            elif is_monopoly:
                return self.rent_table[1]
            else:
                return self.rent_table[0]
        elif self.type == "railroad":
            base = {1: 25, 2: 50, 3: 100, 4: 200}.get(owner_railroads, 25)
            return base * 2 if double_rr else base
        elif self.type == "utility":
            mult = 10 if owner_utilities == 2 else 4
            return mult * dice_total
        return 0