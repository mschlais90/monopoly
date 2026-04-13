import re
import tkinter as tk
from tkinter import ttk

ACTION_TYPES = [
    'All', 'Turn Header', 'Movement', 'Purchase',
    'Rent', 'Cards', 'Jail', 'Building', 'Bankruptcy', 'Other'
]

class ActionLog(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg='#1a1a2e', **kwargs)
        self._messages = []          # (text, player, action_type)
        self._current_turn_player = None
        self._player_filter = tk.StringVar(value='All')
        self._type_filter = tk.StringVar(value='All')
        self._build()

    def _build(self):
        header = tk.Label(self, text='ACTION LOG', bg='#16213e', fg='#e0e0e0',
                          font=('Consolas', 10, 'bold'), pady=4)
        header.pack(fill='x')

        # Filter bar
        filter_bar = tk.Frame(self, bg='#0f3460', pady=3)
        filter_bar.pack(fill='x')

        tk.Label(filter_bar, text='Player:', bg='#0f3460', fg='#ccc',
                 font=('Arial', 8)).pack(side='left', padx=(6, 2))
        self._player_cb = ttk.Combobox(filter_bar, textvariable=self._player_filter,
                                        values=['All'], state='readonly', width=10,
                                        font=('Arial', 8))
        self._player_cb.pack(side='left', padx=(0, 8))

        tk.Label(filter_bar, text='Type:', bg='#0f3460', fg='#ccc',
                 font=('Arial', 8)).pack(side='left', padx=(0, 2))
        self._type_cb = ttk.Combobox(filter_bar, textvariable=self._type_filter,
                                      values=ACTION_TYPES, state='readonly', width=12,
                                      font=('Arial', 8))
        self._type_cb.pack(side='left', padx=(0, 6))

        clear_btn = tk.Button(filter_bar, text='Clear', command=self.clear,
                               bg='#555', fg='white', font=('Arial', 7),
                               relief='flat', padx=4, pady=0, cursor='hand2')
        clear_btn.pack(side='right', padx=6)

        self._player_filter.trace_add('write', self._on_filter_change)
        self._type_filter.trace_add('write', self._on_filter_change)

        # Text area
        frame = tk.Frame(self, bg='#1a1a2e')
        frame.pack(fill='both', expand=True)

        self.text = tk.Text(frame, bg='#0f0f1a', fg='#e0e0e0',
                            font=('Consolas', 9), wrap='word',
                            state='disabled', bd=0, insertbackground='white')
        sb = tk.Scrollbar(frame, command=self.text.yview)
        self.text.config(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.text.pack(side='left', fill='both', expand=True)

        self.text.tag_config('turn_header', foreground='#FFD700', font=('Consolas', 9, 'bold'))
        self.text.tag_config('buy',         foreground='#4CAF50')
        self.text.tag_config('rent',        foreground='#FF7043')
        self.text.tag_config('card',        foreground='#42A5F5')
        self.text.tag_config('jail',        foreground='#FF5252')
        self.text.tag_config('bankrupt',    foreground='#E040FB', font=('Consolas', 9, 'bold'))
        self.text.tag_config('build',       foreground='#66BB6A')
        self.text.tag_config('normal',      foreground='#e0e0e0')

    def set_players(self, player_names):
        self._player_cb['values'] = ['All'] + list(player_names)
        self._player_filter.set('All')

    def append_many(self, messages):
        new_visible = []
        for msg in messages:
            self._extract_turn_player(msg)
            player = self._current_turn_player or 'System'
            atype = self._classify_type(msg)
            self._messages.append((msg, player, atype))
            if self._passes_filter(player, atype):
                new_visible.append((msg, self._pick_tag(msg)))

        if new_visible:
            self.text.config(state='normal')
            for msg, tag in new_visible:
                self.text.insert('end', msg + '\n', tag)
            self.text.see('end')
            self.text.config(state='disabled')

    def append(self, message):
        self.append_many([message])

    def clear(self):
        self._messages.clear()
        self._current_turn_player = None
        self.text.config(state='normal')
        self.text.delete('1.0', 'end')
        self.text.config(state='disabled')

    def _extract_turn_player(self, msg):
        m = re.match(r'=== Turn \d+: (.+?) \(', msg)
        if m:
            self._current_turn_player = m.group(1)

    def _classify_type(self, msg):
        m = msg.lower()
        if '===' in msg:                                    return 'Turn Header'
        if 'rolled' in m or 'moves to' in m or 'passed go' in m or 'escaped jail' in m:
                                                            return 'Movement'
        if 'bought' in m or 'passed on' in m or 'unowned' in m or 'buy' in m:
                                                            return 'Purchase'
        if 'rent' in m or 'owes' in m:                     return 'Rent'
        if 'chance' in m or 'comm. chest' in m or 'collected' in m or 'advanced to' in m:
                                                            return 'Cards'
        if 'jail' in m:                                     return 'Jail'
        if ('built' in m or 'house' in m or 'hotel' in m
                or 'mortgag' in m or 'unmortgag' in m):    return 'Building'
        if 'bankrupt' in m:                                 return 'Bankruptcy'
        return 'Other'

    def _passes_filter(self, player, atype):
        pf = self._player_filter.get()
        tf = self._type_filter.get()
        if pf not in ('All', '') and player != pf:
            return False
        if tf not in ('All', '') and atype != tf:
            return False
        return True

    def _pick_tag(self, msg):
        m = msg.lower()
        if '===' in msg:           return 'turn_header'
        if 'bought' in m:          return 'buy'
        if 'rent' in m or 'owes' in m: return 'rent'
        if 'chance' in m or 'chest' in m: return 'card'
        if 'jail' in m:            return 'jail'
        if 'bankrupt' in m:        return 'bankrupt'
        if 'built' in m or 'house' in m or 'hotel' in m: return 'build'
        return 'normal'

    def _on_filter_change(self, *_):
        self.text.config(state='normal')
        self.text.delete('1.0', 'end')
        for msg, player, atype in self._messages:
            if self._passes_filter(player, atype):
                self.text.insert('end', msg + '\n', self._pick_tag(msg))
        self.text.see('end')
        self.text.config(state='disabled')