import random
from game.constants import CHANCE_CARDS, COMMUNITY_CHEST_CARDS

class Deck:
    def __init__(self, cards):
        self.cards = list(cards)
        random.shuffle(self.cards)
        self.index = 0

    def draw(self):
        card = self.cards[self.index]
        self.index = (self.index + 1) % len(self.cards)
        return card

def make_decks():
    return Deck(CHANCE_CARDS), Deck(COMMUNITY_CHEST_CARDS)