import tkinter as tk
from game.constants import BOARD_SPACES, COLOR_GROUPS, COLOR_HEX, PLAYER_COLORS, SQUARE_ABBREV

BOARD_SIZE = 700
CORNER = 100

def get_cell_size():
    return (BOARD_SIZE - 2 * CORNER) / 9

def square_rect(pos):
    cell = get_cell_size()
    if pos == 0:
        return (BOARD_SIZE - CORNER, BOARD_SIZE - CORNER, BOARD_SIZE, BOARD_SIZE)
    elif 1 <= pos <= 9:
        x1 = BOARD_SIZE - CORNER - pos * cell
        return (x1, BOARD_SIZE - CORNER, x1 + cell, BOARD_SIZE)
    elif pos == 10:
        return (0, BOARD_SIZE - CORNER, CORNER, BOARD_SIZE)
    elif 11 <= pos <= 19:
        n = pos - 10
        y2 = BOARD_SIZE - CORNER - (n - 1) * cell
        y1 = y2 - cell
        return (0, y1, CORNER, y2)
    elif pos == 20:
        return (0, 0, CORNER, CORNER)
    elif 21 <= pos <= 29:
        n = pos - 21
        x1 = CORNER + n * cell
        return (x1, 0, x1 + cell, CORNER)
    elif pos == 30:
        return (BOARD_SIZE - CORNER, 0, BOARD_SIZE, CORNER)
    elif 31 <= pos <= 39:
        n = pos - 31
        y1 = CORNER + n * cell
        return (BOARD_SIZE - CORNER, y1, BOARD_SIZE, y1 + cell)
    return (0, 0, 0, 0)


def color_band_rect(pos, x1, y1, x2, y2, band=14):
    if 1 <= pos <= 9:
        return (x1, y1, x2, y1 + band)
    elif 11 <= pos <= 19:
        return (x2 - band, y1, x2, y2)
    elif 21 <= pos <= 29:
        return (x1, y2 - band, x2, y2)
    elif 31 <= pos <= 39:
        return (x1, y1, x1 + band, y2)
    return None


class BoardCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=BOARD_SIZE, height=BOARD_SIZE,
                         bg='#d4edda', highlightthickness=2,
                         highlightbackground='#155724', **kwargs)
        self.space_color_map = self._build_space_color_map()

    def _build_space_color_map(self):
        m = {}
        for sp in BOARD_SPACES:
            pos = sp['pos']
            if sp['type'] == 'property':
                m[pos] = COLOR_HEX[sp['color']]
        return m

    def draw_board(self, engine=None, pos_overrides=None, dice=None):
        self.delete('all')
        self._draw_squares(engine)
        self._draw_center_label(engine, dice)
        if engine:
            self._draw_houses(engine)
            self._draw_tokens(engine, pos_overrides or {})

    def _draw_squares(self, engine=None):
        for sp in BOARD_SPACES:
            pos = sp['pos']
            x1, y1, x2, y2 = square_rect(pos)
            stype = sp['type']

            # Background
            bg = '#FFFDE7'
            if stype == 'go':
                bg = '#C8E6C9'
            elif stype in ('jail',):
                bg = '#FFECB3'
            elif stype == 'go_to_jail':
                bg = '#FFCCBC'
            elif stype == 'free_parking':
                bg = '#E8F5E9'
            elif stype == 'tax':
                bg = '#FCE4EC'
            elif stype in ('chance',):
                bg = '#FFF9C4'
            elif stype == 'community_chest':
                bg = '#E3F2FD'
            elif stype in ('railroad', 'utility'):
                bg = '#F5F5F5'

            self.create_rectangle(x1, y1, x2, y2, fill=bg, outline='#333333', width=1)

            # Color band for properties
            if pos in self.space_color_map:
                br = color_band_rect(pos, x1, y1, x2, y2)
                if br:
                    bx1, by1, bx2, by2 = br
                    self.create_rectangle(bx1, by1, bx2, by2,
                                          fill=self.space_color_map[pos],
                                          outline='', width=0)

            # Text label
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            label = SQUARE_ABBREV.get(pos, sp['name'])
            angle = 0
            if 11 <= pos <= 19:
                angle = 90
            elif 31 <= pos <= 39:
                angle = 270

            # Adjust center for color band offset
            if 1 <= pos <= 9:
                cy = (y1 + 14 + y2) / 2
            elif 11 <= pos <= 19:
                cx = (x1 + x2 - 14) / 2
            elif 21 <= pos <= 29:
                cy = (y1 + y2 - 14) / 2
            elif 31 <= pos <= 39:
                cx = (x1 + 14 + x2) / 2

            # For Free Parking, overlay pot amount below the label
            if pos == 20 and engine and engine.free_parking_pot > 0:
                label = f"FREE\nPARKING\n${engine.free_parking_pot:,}"
                self.create_text(cx, cy, text=label, font=('Arial', 6, 'bold'),
                                 justify='center', fill='#1B5E20')
            else:
                self.create_text(cx, cy, text=label, font=('Arial', 6), angle=angle,
                                 justify='center', fill='#222222')

            # Price for properties
            if stype in ('property', 'railroad', 'utility'):
                price = sp.get('price', 0)
                if price:
                    if 1 <= pos <= 9:
                        self.create_text(cx, y2 - 6, text=f'${price}', font=('Arial', 5), fill='#444')
                    elif 11 <= pos <= 19:
                        self.create_text(x1 + 6, cy, text=f'${price}', font=('Arial', 5),
                                        angle=90, fill='#444')
                    elif 21 <= pos <= 29:
                        self.create_text(cx, y1 + 6, text=f'${price}', font=('Arial', 5), fill='#444')
                    elif 31 <= pos <= 39:
                        self.create_text(x2 - 6, cy, text=f'${price}', font=('Arial', 5),
                                        angle=270, fill='#444')

    def _draw_center_label(self, engine=None, dice=None):
        cx, cy = BOARD_SIZE / 2, BOARD_SIZE / 2
        self.create_rectangle(CORNER, CORNER, BOARD_SIZE - CORNER, BOARD_SIZE - CORNER,
                               fill='#e8f5e9', outline='#2e7d32', width=2)
        if dice:
            # Shift title upward to make room for dice
            self.create_text(cx, cy - 60, text='MONOPOLY',
                             font=('Georgia', 22, 'bold italic'), fill='#c62828')
            self.create_text(cx, cy - 28, text='SIMULATOR',
                             font=('Arial', 12, 'bold'), fill='#1b5e20')
            d1, d2 = dice
            die_size = 44
            self._draw_die(cx - die_size - 6, cy + 14, d1, die_size)
            self._draw_die(cx + 6,             cy + 14, d2, die_size)
            doubles_str = '  Doubles!' if d1 == d2 else ''
            self.create_text(cx, cy + 72,
                             text=f'{d1}  +  {d2}  =  {d1 + d2}{doubles_str}',
                             font=('Arial', 11, 'bold'), fill='#1b5e20')
        else:
            self.create_text(cx, cy - 30, text='MONOPOLY',
                             font=('Georgia', 22, 'bold italic'), fill='#c62828')
            self.create_text(cx, cy + 10, text='SIMULATOR',
                             font=('Arial', 12, 'bold'), fill='#1b5e20')

    def _draw_die(self, cx, cy, value, size=44):
        """Draw a die face centered at (cx, cy) on the board canvas."""
        half = size / 2
        self.create_rectangle(cx - half, cy - half, cx + half, cy + half,
                               fill='white', outline='#333', width=2)
        r = max(3, int(size / 10))
        spread = 0.30 * size
        dot_positions = {
            1: [(0, 0)],
            2: [(-spread, -spread), (spread, spread)],
            3: [(-spread, -spread), (0, 0), (spread, spread)],
            4: [(-spread, -spread), (spread, -spread),
                (-spread,  spread), (spread,  spread)],
            5: [(-spread, -spread), (spread, -spread), (0, 0),
                (-spread,  spread), (spread,  spread)],
            6: [(-spread, -0.38*size), (spread, -0.38*size),
                (-spread,  0),         (spread,  0),
                (-spread,  0.38*size), (spread,  0.38*size)],
        }
        for dx, dy in dot_positions.get(value, []):
            px, py = cx + dx, cy + dy
            self.create_oval(px - r, py - r, px + r, py + r, fill='#222', outline='')

    def _draw_houses(self, engine):
        cell = get_cell_size()
        band = 14
        for pos, prop in engine.board_properties.items():
            if prop.houses == 0:
                continue
            x1, y1, x2, y2 = square_rect(pos)
            color = '#4CAF50' if prop.houses < 5 else '#F44336'
            count = 1 if prop.houses == 5 else prop.houses
            # Draw in the color band area
            if 1 <= pos <= 9:
                for i in range(count):
                    hx = x1 + 3 + i * 8
                    self.create_rectangle(hx, y1 + 2, hx + 6, y1 + band - 2,
                                          fill=color, outline='#fff', width=1)
            elif 11 <= pos <= 19:
                for i in range(count):
                    hy = y1 + 3 + i * 8
                    self.create_rectangle(x2 - band + 2, hy, x2 - 2, hy + 6,
                                          fill=color, outline='#fff', width=1)
            elif 21 <= pos <= 29:
                for i in range(count):
                    hx = x1 + 3 + i * 8
                    self.create_rectangle(hx, y2 - band + 2, hx + 6, y2 - 2,
                                          fill=color, outline='#fff', width=1)
            elif 31 <= pos <= 39:
                for i in range(count):
                    hy = y1 + 3 + i * 8
                    self.create_rectangle(x1 + 2, hy, x1 + band - 2, hy + 6,
                                          fill=color, outline='#fff', width=1)

    def _draw_tokens(self, engine, pos_overrides=None):
        pos_overrides = pos_overrides or {}
        r = 10  # token radius (increased from 7)
        offsets = [(12, 12), (28, 12), (12, 28), (28, 28)]

        pos_groups = {}
        for player in engine.all_players:
            if player.bankrupt:
                continue
            pos = pos_overrides.get(player.name, player.position)
            pos_groups.setdefault(pos, []).append(player)

        for pos, group in pos_groups.items():
            x1, y1, x2, y2 = square_rect(pos)
            base_x = (x1 + x2) / 2 - 20
            base_y = (y1 + y2) / 2 - 14
            for idx, player in enumerate(group):
                if idx >= 4:
                    break
                ox, oy = offsets[idx]
                tx = base_x + ox
                ty = base_y + oy
                self.create_oval(tx - r, ty - r, tx + r, ty + r,
                                 fill=player.color, outline='white', width=2)
                self.create_text(tx, ty, text=player.name[0].upper(),
                                 font=('Arial', 8, 'bold'), fill='white')