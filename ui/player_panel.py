import tkinter as tk
from game.constants import COLOR_HEX

class PlayerPanel(tk.Frame):
    def __init__(self, parent, player, **kwargs):
        super().__init__(parent, bd=2, relief='ridge', **kwargs)
        self.player = player
        self._build()

    def _build(self):
        p = self.player
        self.config(bg=p.color)

        header = tk.Frame(self, bg=p.color)
        header.pack(fill='x', padx=2, pady=(2, 0))

        # Status dot
        self.status_dot = tk.Canvas(header, width=12, height=12, bg=p.color,
                                    highlightthickness=0)
        self.status_dot.pack(side='left', padx=(4, 2), pady=4)
        self.status_dot.create_oval(1, 1, 11, 11, fill='#2ECC71', outline='white')

        self.name_label = tk.Label(header, text=p.name, bg=p.color, fg='white',
                                   font=('Arial', 11, 'bold'))
        self.name_label.pack(side='left')

        self.strategy_label = tk.Label(header, text=f'[{p.strategy.name}]',
                                       bg=p.color, fg='#dddddd',
                                       font=('Arial', 8))
        self.strategy_label.pack(side='right', padx=4)

        inner = tk.Frame(self, bg='#f8f8f8')
        inner.pack(fill='both', expand=True, padx=2, pady=2)

        info_frame = tk.Frame(inner, bg='#f8f8f8')
        info_frame.pack(fill='x', padx=6, pady=2)

        self.pos_label = tk.Label(info_frame, text='Position: Go', bg='#f8f8f8',
                                  font=('Arial', 8), anchor='w')
        self.pos_label.pack(side='left', fill='x', expand=True)

        money_frame = tk.Frame(inner, bg='#f8f8f8')
        money_frame.pack(fill='x', padx=6)

        self.cash_label = tk.Label(money_frame, text='Cash: $1500',
                                   bg='#f8f8f8', font=('Arial', 9, 'bold'),
                                   fg='#27AE60', anchor='w')
        self.cash_label.pack(side='left')

        self.networth_label = tk.Label(money_frame, text='Net: $1500',
                                       bg='#f8f8f8', font=('Arial', 8),
                                       fg='#555', anchor='e')
        self.networth_label.pack(side='right')

        prop_header = tk.Label(inner, text='Properties:', bg='#f8f8f8',
                               font=('Arial', 8, 'bold'), anchor='w')
        prop_header.pack(fill='x', padx=6)

        self.prop_text = tk.Text(inner, height=4, font=('Arial', 7),
                                 bg='#f8f8f8', bd=0, wrap='word',
                                 state='disabled')
        self.prop_text.pack(fill='both', expand=True, padx=6, pady=(0, 4))

    def update(self):
        from game.constants import BOARD_SPACES
        p = self.player
        if p.bankrupt:
            self.status_dot.itemconfig(1, fill='#E74C3C')
            self.name_label.config(fg='#ffaaaa')
            self.cash_label.config(text='BANKRUPT', fg='#E74C3C')
            self.networth_label.config(text='')
            self.pos_label.config(text='Out of game')
            self.prop_text.config(state='normal')
            self.prop_text.delete('1.0', 'end')
            self.prop_text.config(state='disabled')
            return

        space = BOARD_SPACES[p.position]
        jail_str = ' [JAIL]' if p.in_jail else ''
        self.pos_label.config(text=f'[{p.position}] {space["name"]}{jail_str}')
        self.cash_label.config(text=f'Cash: ${p.money:,}')
        nw = p.net_worth()
        self.networth_label.config(text=f'Net: ${nw:,}')

        self.prop_text.config(state='normal')
        self.prop_text.delete('1.0', 'end')
        if p.properties:
            lines = []
            for prop in sorted(p.properties, key=lambda x: x.pos):
                m_str = '[M]' if prop.mortgaged else ''
                h_str = ''
                if prop.type == 'property' and prop.houses > 0:
                    h_str = f' [{prop.houses}H]' if prop.houses < 5 else ' [HTL]'
                color_dot = ''
                if prop.type == 'property':
                    color_name = prop.color.replace('_', ' ').title()
                    color_dot = f'({color_name}) '
                lines.append(f'{m_str}{prop.name} {h_str}')
            self.prop_text.insert('end', '\n'.join(lines))
        else:
            self.prop_text.insert('end', 'No properties')
        self.prop_text.config(state='disabled')