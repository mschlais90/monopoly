import tkinter as tk
from tkinter import ttk, messagebox
from game.constants import PLAYER_COLORS, PLAYER_COLOR_NAMES, STARTING_MONEY_DEFAULT
from strategies.random_strat import RandomStrategy
from strategies.conservative import ConservativeStrategy
from strategies.aggressive import AggressiveStrategy
from strategies.balanced import BalancedStrategy
from strategies.human import HumanStrategy
from strategies.hyper_aggressive import HyperAggressiveStrategy

STRATEGIES = {
    'Random':           RandomStrategy,
    'Conservative':     ConservativeStrategy,
    'Aggressive':       AggressiveStrategy,
    'Balanced':         BalancedStrategy,
    'Hyper-Aggressive': HyperAggressiveStrategy,
    'Human':            HumanStrategy,
}

class SetupFrame(tk.Frame):
    def __init__(self, parent, on_start, settings=None, **kwargs):
        super().__init__(parent, bg='#1a1a2e', **kwargs)
        self.on_start = on_start
        self.settings = settings
        self.num_players_var = tk.IntVar(value=2)
        self.starting_money_var = tk.StringVar(value=str(STARTING_MONEY_DEFAULT))
        self.player_rows = []
        self._build()

    def _build(self):
        # Header
        tk.Label(self, text='MONOPOLY', font=('Georgia', 36, 'bold italic'),
                 fg='#FFD700', bg='#1a1a2e').pack(pady=(40, 4))
        tk.Label(self, text='S I M U L A T O R', font=('Arial', 14, 'bold'),
                 fg='#e0e0e0', bg='#1a1a2e').pack(pady=(0, 30))

        card = tk.Frame(self, bg='#16213e', bd=0, relief='flat')
        card.pack(padx=60, pady=10, fill='x')
        card.pack_propagate(True)

        # Player count
        pc_frame = tk.Frame(card, bg='#16213e')
        pc_frame.pack(fill='x', padx=20, pady=10)
        tk.Label(pc_frame, text='Number of Players:', font=('Arial', 12),
                 fg='#e0e0e0', bg='#16213e', width=18, anchor='e').pack(side='left')
        for n in (2, 3, 4):
            rb = tk.Radiobutton(pc_frame, text=str(n), variable=self.num_players_var,
                                value=n, command=self._update_rows,
                                bg='#16213e', fg='#e0e0e0', selectcolor='#0f3460',
                                font=('Arial', 12, 'bold'), activebackground='#16213e')
            rb.pack(side='left', padx=10)

        # Divider
        tk.Frame(card, height=1, bg='#0f3460').pack(fill='x', padx=20)

        # Player rows container
        self.rows_frame = tk.Frame(card, bg='#16213e')
        self.rows_frame.pack(fill='x', padx=20, pady=10)

        defaults = ['Random', 'Conservative', 'Aggressive', 'Balanced']
        for i in range(4):
            color = PLAYER_COLORS[i]
            name_var = tk.StringVar(value=f'Player {i+1}')
            strat_var = tk.StringVar(value=defaults[i])
            row = tk.Frame(self.rows_frame, bg='#16213e', pady=4)
            row.pack(fill='x')

            # Color swatch
            swatch = tk.Label(row, text='  ', bg=color, width=2)
            swatch.pack(side='left', padx=(0, 6))

            tk.Label(row, text=f'Player {i+1}:', font=('Arial', 10),
                     fg='#e0e0e0', bg='#16213e', width=8, anchor='w').pack(side='left')

            name_entry = tk.Entry(row, textvariable=name_var, font=('Arial', 10),
                                  bg='#0f3460', fg='white', insertbackground='white',
                                  bd=1, relief='flat', width=16)
            name_entry.pack(side='left', padx=(0, 10))

            strat_cb = ttk.Combobox(row, textvariable=strat_var,
                                     values=list(STRATEGIES.keys()),
                                     state='readonly', width=14,
                                     font=('Arial', 10))
            strat_cb.pack(side='left')

            self.player_rows.append({'frame': row, 'name': name_var, 'strat': strat_var})

        # Starting money
        tk.Frame(card, height=1, bg='#0f3460').pack(fill='x', padx=20, pady=(10, 0))
        money_frame = tk.Frame(card, bg='#16213e')
        money_frame.pack(fill='x', padx=20, pady=10)
        tk.Label(money_frame, text='Starting Money: $', font=('Arial', 12),
                 fg='#e0e0e0', bg='#16213e').pack(side='left')
        money_entry = tk.Entry(money_frame, textvariable=self.starting_money_var,
                               font=('Arial', 12), bg='#0f3460', fg='white',
                               insertbackground='white', bd=1, relief='flat', width=8)
        money_entry.pack(side='left')

        # Start button
        btn_row = tk.Frame(self, bg='#1a1a2e')
        btn_row.pack(pady=30)
        tk.Button(btn_row, text='START GAME', command=self._start,
                  font=('Arial', 14, 'bold'), bg='#c62828', fg='white',
                  activebackground='#b71c1c', activeforeground='white',
                  relief='flat', padx=30, pady=10, cursor='hand2').pack(side='left', padx=10)
        tk.Button(btn_row, text='Settings', command=self._open_settings,
                  font=('Arial', 11), bg='#6C3483', fg='white',
                  relief='flat', padx=16, pady=10, cursor='hand2').pack(side='left', padx=10)

        self._update_rows()

    def _update_rows(self):
        n = self.num_players_var.get()
        for i, row_data in enumerate(self.player_rows):
            if i < n:
                row_data['frame'].pack(fill='x')
            else:
                row_data['frame'].pack_forget()

    def _open_settings(self):
        from ui.settings_dialog import SettingsDialog
        if self.settings:
            SettingsDialog(self.winfo_toplevel(), self.settings)

    def _start(self):
        try:
            money = int(self.starting_money_var.get())
            if money < 100:
                raise ValueError("Minimum $100")
        except ValueError as e:
            messagebox.showerror('Invalid Input', f'Starting money: {e}')
            return

        n = self.num_players_var.get()
        configs = []
        for i in range(n):
            rd = self.player_rows[i]
            name = rd['name'].get().strip() or f'Player {i+1}'
            strat_cls = STRATEGIES[rd['strat'].get()]
            configs.append({
                'name': name,
                'strategy': strat_cls(),
                'color': PLAYER_COLORS[i],
            })
        self.on_start(configs, money)