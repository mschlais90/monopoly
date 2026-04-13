import tkinter as tk
import re
import math
from tkinter import ttk, messagebox
from game.engine import GameEngine
from ui.board_canvas import BoardCanvas
from ui.player_panel import PlayerPanel
from ui.action_log import ActionLog
from ui.trade_dialog import TradeDialog
from ui.properties_dialog import PropertiesDialog

SPEED_DELAYS = {1: 2000, 2: 1000, 3: 500, 4: 200, 5: 50}

class GameFrame(tk.Frame):
    def __init__(self, parent, player_configs, starting_money, on_menu,
                 settings=None, **kwargs):
        super().__init__(parent, bg='#2c3e50', **kwargs)
        self.on_menu = on_menu
        self.settings = settings
        self.engine = GameEngine(player_configs, starting_money)
        self._auto_running = False
        self._speed = 3
        self._after_id = None
        self._animating = False
        self._last_dice = None          # (d1, d2) from most recent roll
        self._build()
        self._refresh_ui()

    def _build(self):
        # Top bar
        top_bar = tk.Frame(self, bg='#1a252f', pady=4)
        top_bar.pack(fill='x')
        tk.Label(top_bar, text='MONOPOLY SIMULATOR',
                 font=('Georgia', 14, 'bold italic'), fg='#FFD700',
                 bg='#1a252f').pack(side='left', padx=10)
        self.turn_label = tk.Label(top_bar, text='Turn: 0', font=('Arial', 11),
                                    fg='#e0e0e0', bg='#1a252f')
        self.turn_label.pack(side='left', padx=20)
        self.current_player_label = tk.Label(top_bar, text='', font=('Arial', 11, 'bold'),
                                              fg='#4CAF50', bg='#1a252f')
        self.current_player_label.pack(side='left')
        tk.Button(top_bar, text='Menu', command=self._back_to_menu,
                  bg='#555', fg='white', font=('Arial', 9), relief='flat',
                  cursor='hand2').pack(side='right', padx=4)
        tk.Button(top_bar, text='Settings', command=self._open_settings,
                  bg='#6C3483', fg='white', font=('Arial', 9), relief='flat',
                  cursor='hand2').pack(side='right', padx=4)

        # Main content
        content = tk.Frame(self, bg='#2c3e50')
        content.pack(fill='both', expand=True)

        # Left column: board + unowned properties panel
        left_col = tk.Frame(content, bg='#2c3e50')
        left_col.pack(side='left', fill='y')

        board_frame = tk.Frame(left_col, bg='#2c3e50')
        board_frame.pack(padx=8, pady=(8, 4))
        self.board = BoardCanvas(board_frame)
        self.board.pack()

        self._build_unowned_panel(left_col)

        # Right panel
        right = tk.Frame(content, bg='#2c3e50', padx=6)
        right.pack(side='left', fill='both', expand=True)

        # Player panels (2x2 grid)
        pp_frame = tk.Frame(right, bg='#2c3e50')
        self.player_panels_frame = pp_frame
        pp_frame.pack(fill='x', pady=(4, 4))
        self.player_panels = []
        for i, p in enumerate(self.engine.all_players):
            panel = PlayerPanel(pp_frame, p)
            panel.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky='nsew')
            self.player_panels.append(panel)
        pp_frame.columnconfigure(0, weight=1)
        pp_frame.columnconfigure(1, weight=1)

        # Action log
        self.action_log = ActionLog(right)
        self.action_log.pack(fill='both', expand=True, pady=(0, 4))
        self.action_log.set_players([p.name for p in self.engine.all_players])

        # Bottom controls
        ctrl = tk.Frame(self, bg='#1a252f', pady=6)
        ctrl.pack(fill='x')

        self.next_btn = tk.Button(ctrl, text='Next Turn', command=self._next_turn,
                                   font=('Arial', 11, 'bold'), bg='#27AE60', fg='white',
                                   activebackground='#229954', relief='flat',
                                   padx=16, pady=6, cursor='hand2')
        self.next_btn.pack(side='left', padx=(10, 6))

        self.auto_btn = tk.Button(ctrl, text='Auto Run', command=self._toggle_auto,
                                   font=('Arial', 11, 'bold'), bg='#2980B9', fg='white',
                                   activebackground='#2471A3', relief='flat',
                                   padx=16, pady=6, cursor='hand2')
        self.auto_btn.pack(side='left', padx=6)

        tk.Label(ctrl, text='Speed:', font=('Arial', 10), fg='#e0e0e0',
                 bg='#1a252f').pack(side='left', padx=(16, 4))
        self.speed_var = tk.IntVar(value=self._speed)
        speed_scale = tk.Scale(ctrl, from_=1, to=5, orient='horizontal',
                                variable=self.speed_var, command=self._set_speed,
                                bg='#1a252f', fg='white', highlightthickness=0,
                                length=120, troughcolor='#2c3e50', sliderrelief='flat')
        speed_scale.pack(side='left')

        speed_labels = tk.Label(ctrl, text='Slow  →  Fast', font=('Arial', 8),
                                 fg='#aaa', bg='#1a252f')
        speed_labels.pack(side='left', padx=4)



        tk.Button(ctrl, text='Properties', command=self._open_properties,
                  font=('Arial', 11, 'bold'), bg='#6C3483', fg='white',
                  activebackground='#5B2C6F', relief='flat',
                  padx=14, pady=6, cursor='hand2').pack(side='left', padx=6)

        self.trade_btn = tk.Button(ctrl, text='Trade', command=self._open_trade,
                                    font=('Arial', 11, 'bold'), bg='#8E44AD', fg='white',
                                    activebackground='#7D3C98', relief='flat',
                                    padx=16, pady=6, cursor='hand2')
        self.trade_btn.pack(side='left', padx=6)

        tk.Button(ctrl, text='New Game', command=self._back_to_menu,
                  font=('Arial', 10), bg='#7f8c8d', fg='white',
                  relief='flat', padx=12, pady=6, cursor='hand2').pack(side='right', padx=6)
        tk.Button(ctrl, text='Save Game', command=self._save_game,
                  font=('Arial', 10), bg='#1a6b3c', fg='white',
                  relief='flat', padx=12, pady=6, cursor='hand2').pack(side='right', padx=6)
        tk.Button(ctrl, text='Load Game', command=self._load_game,
                  font=('Arial', 10), bg='#154e6e', fg='white',
                  relief='flat', padx=12, pady=6, cursor='hand2').pack(side='right', padx=6)

    def _build_unowned_panel(self, parent):
        from game.constants import BOARD_SPACES, COLOR_HEX
        outer = tk.Frame(parent, bg='#1a1a2e', padx=8, pady=4)
        outer.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        hdr = tk.Frame(outer, bg='#16213e')
        hdr.pack(fill='x')
        tk.Label(hdr, text='UNOWNED PROPERTIES', bg='#16213e', fg='#e0e0e0',
                 font=('Consolas', 9, 'bold'), pady=3).pack(side='left', padx=6)
        self._unowned_count_label = tk.Label(hdr, text='', bg='#16213e',
                                              fg='#aaaaaa', font=('Consolas', 9))
        self._unowned_count_label.pack(side='right', padx=6)

        inner = tk.Frame(outer, bg='#1a1a2e')
        inner.pack(fill='both', expand=True)

        self._unowned_text = tk.Text(inner, bg='#0f0f1a', fg='#e0e0e0',
                                      font=('Consolas', 8), wrap='none',
                                      state='disabled', bd=0, height=8)
        sb_y = tk.Scrollbar(inner, orient='vertical', command=self._unowned_text.yview)
        sb_x = tk.Scrollbar(inner, orient='horizontal', command=self._unowned_text.xview)
        self._unowned_text.config(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.pack(side='right', fill='y')
        sb_x.pack(side='bottom', fill='x')
        self._unowned_text.pack(side='left', fill='both', expand=True)

        # One tag per color group + types
        for color, hex_val in COLOR_HEX.items():
            self._unowned_text.tag_config(color, foreground=hex_val)
        self._unowned_text.tag_config('railroad', foreground='#bbbbbb')
        self._unowned_text.tag_config('utility',  foreground='#aaddff')
        self._unowned_text.tag_config('dim',       foreground='#555555')

    def _refresh_unowned(self):
        from game.constants import BOARD_SPACES, COLOR_HEX
        bp = self.engine.board_properties
        unowned = [sp for sp in BOARD_SPACES
                   if sp['pos'] in bp and bp[sp['pos']].owner is None]

        self._unowned_count_label.config(text=f'({len(unowned)} remaining)')
        self._unowned_text.config(state='normal')
        self._unowned_text.delete('1.0', 'end')

        if not unowned:
            self._unowned_text.insert('end', '  All properties are owned.', 'dim')
        else:
            for sp in unowned:
                prop = bp[sp['pos']]
                if prop.type == 'property':
                    tag = prop.color
                    symbol = '■ '
                elif prop.type == 'railroad':
                    tag = 'railroad'
                    symbol = '🚂 '
                else:
                    tag = 'utility'
                    symbol = '⚡ '
                line = f'{symbol}{sp["name"]:<28}  ${sp["price"]:>4}\n'
                self._unowned_text.insert('end', line, tag)

        self._unowned_text.config(state='disabled')

    def _next_turn(self):
        if self.engine.game_over or self._animating:
            if self.engine.game_over:
                self._show_winner()
            return
        pre = {p.name: p.position for p in self.engine.all_players if not p.bankrupt}
        self.engine.turn_log = []
        self.engine.defer_human_prompts = True
        self.engine.pending_human_buys  = []
        self.engine.pending_human_trades = []
        self.engine.process_turn()
        self.engine.defer_human_prompts = False
        self._update_dice()
        self.action_log.append_many(self.engine.turn_log)

        def after_anim():
            self._process_pending_human_actions()
            self._refresh_ui()
            if self.engine.game_over:
                self._show_winner()

        if self.settings and self.settings.animate_movement:
            self._start_animation(pre, after_anim)
        else:
            after_anim()

    def _toggle_auto(self):
        if self._auto_running:
            self._stop_auto()
        else:
            self._start_auto()

    def _start_auto(self):
        self._auto_running = True
        self.auto_btn.config(text='Pause', bg='#E74C3C')
        self.next_btn.config(state='disabled')
        self._run_auto()

    def _stop_auto(self):
        self._auto_running = False
        self.auto_btn.config(text='Auto Run', bg='#2980B9')
        self.next_btn.config(state='normal')
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _run_auto(self):
        if not self._auto_running:
            return
        if self.engine.game_over:
            self._stop_auto()
            self._show_winner()
            return
        pre = {p.name: p.position for p in self.engine.all_players if not p.bankrupt}
        self.engine.turn_log = []
        # AI-only turns: no deferral needed. Human turns in auto mode: still defer
        self.engine.defer_human_prompts = True
        self.engine.pending_human_buys  = []
        self.engine.pending_human_trades = []
        self.engine.process_turn()
        self.engine.defer_human_prompts = False
        self._update_dice()
        self.action_log.append_many(self.engine.turn_log)
        delay = SPEED_DELAYS.get(self._speed, 500)
        animate = (self.settings and self.settings.animate_movement
                   and self._speed <= 3)

        def after_anim():
            self._process_pending_human_actions()
            self._refresh_ui()
            if self._auto_running:
                self._after_id = self.after(delay, self._run_auto)

        if animate:
            self._start_animation(pre, after_anim)
        else:
            after_anim()

    def _save_game(self):
        from tkinter import filedialog
        from game.save_load import save_game
        was_running = self._auto_running
        if was_running:
            self._stop_auto()
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Monopoly save", "*.json"), ("All files", "*.*")],
            title="Save Game",
        )
        if path:
            try:
                save_game(self.engine, path)
                messagebox.showinfo("Saved", f"Game saved to:\n{path}")
            except Exception as exc:
                messagebox.showerror("Save Failed", str(exc))
        if was_running:
            self._start_auto()

    def _load_game(self):
        from tkinter import filedialog
        from game.save_load import load_engine
        was_running = self._auto_running
        if was_running:
            self._stop_auto()
        path = filedialog.askopenfilename(
            filetypes=[("Monopoly save", "*.json"), ("All files", "*.*")],
            title="Load Game",
        )
        if not path:
            if was_running:
                self._start_auto()
            return
        try:
            new_engine = load_engine(path)
        except Exception as exc:
            messagebox.showerror("Load Failed", str(exc))
            if was_running:
                self._start_auto()
            return

        # Swap engine and rebuild UI panels
        self.engine = new_engine
        self._last_dice = None
        self._animating = False

        # Rebuild player panels (player count/colors may differ)
        for panel in self.player_panels:
            panel.destroy()
        self.player_panels = []
        pp_frame = self.player_panels_frame
        for i, player in enumerate(self.engine.all_players):
            panel = PlayerPanel(pp_frame, player)
            panel.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky='nsew')
            self.player_panels.append(panel)

        self.action_log.set_players([p.name for p in self.engine.all_players])
        self._refresh_ui()
        messagebox.showinfo("Loaded", f"Game loaded from:\n{path}")

    def _open_settings(self):
        from ui.settings_dialog import SettingsDialog
        if self.settings:
            SettingsDialog(self.winfo_toplevel(), self.settings)

    def _update_dice(self):
        """Extract the most recent dice roll from the turn log."""
        for msg in reversed(self.engine.turn_log):
            m = re.search(r'Rolled (\d+)\+(\d+)=', msg)
            if m:
                self._last_dice = (int(m.group(1)), int(m.group(2)))
                return

    # ── Animation ─────────────────────────────────────────────────────────────

    @staticmethod
    def _ease_delays(n_steps, total_ms=2000):
        """Ease-in-out delays: slow start, fast middle, slow end."""
        if n_steps <= 0:
            return []
        if n_steps == 1:
            return [min(total_ms, 400)]
        eps = 0.15
        speeds = [math.sin(math.pi * i / (n_steps - 1)) + eps
                  for i in range(n_steps)]
        max_s = max(speeds)
        raw = [max_s / s for s in speeds]
        total_raw = sum(raw)
        return [max(20, int(d / total_raw * total_ms)) for d in raw]

    def _start_animation(self, pre_positions, callback):
        moved = []
        for player in self.engine.all_players:
            if player.bankrupt:
                continue
            old = pre_positions.get(player.name, player.position)
            new = player.position
            if old != new:
                moved.append((player, old, new))

        if not moved:
            callback()
            return

        player, old_pos, new_pos = moved[0]

        # Go-to-jail teleport: skip path animation
        if new_pos == 10 and old_pos == 30:
            callback()
            return

        path = []
        pos = old_pos
        while pos != new_pos:
            pos = (pos + 1) % 40
            path.append(pos)
            if len(path) > 40:
                break

        if not path:
            callback()
            return

        delays = self._ease_delays(len(path))
        static = {p.name: p.position
                  for p in self.engine.all_players
                  if not p.bankrupt and p is not player}
        dice = self._last_dice if (self.settings and self.settings.show_dice) else None

        self._animating = True
        self.next_btn.config(state='disabled')
        self._anim_state = {
            'player': player, 'path': path, 'static': static,
            'delays': delays, 'callback': callback, 'dice': dice,
        }
        self._anim_step(0)

    def _anim_step(self, idx):
        st = self._anim_state
        if idx >= len(st['path']):
            self._animating = False
            self.next_btn.config(state='normal')
            st['callback']()
            return
        overrides = dict(st['static'])
        overrides[st['player'].name] = st['path'][idx]
        self.board.draw_board(self.engine, pos_overrides=overrides,
                              dice=st['dice'])
        self._after_id = self.after(st['delays'][idx],
                                    lambda: self._anim_step(idx + 1))

    # ── Deferred human actions (shown after animation) ────────────────────────

    def _process_pending_human_actions(self):
        new_log = []

        # Buy decisions
        for player, prop in list(self.engine.pending_human_buys):
            if prop.owner is not None:
                continue  # property taken in the meantime
            old = self.engine.turn_log[:]
            self.engine.turn_log = []
            if player.strategy.should_buy(player, prop, self.engine):
                if player.money >= prop.price:
                    prop.owner = player
                    player.properties.append(prop)
                    player.pay(prop.price)
                    self.engine._log(
                        f"  {player.name} bought {prop.name} for ${prop.price:,}.")
                else:
                    self.engine._log(
                        f"  {player.name} cannot afford {prop.name}.")
            else:
                self.engine._log(
                    f"  {player.name} passed on {prop.name}.")
            new_log.extend(self.engine.turn_log)
            self.engine.turn_log = old
        self.engine.pending_human_buys = []

        # Trade decisions
        for proposal in list(self.engine.pending_human_trades):
            if proposal.recipient.bankrupt or proposal.proposer.bankrupt:
                continue
            old = self.engine.turn_log[:]
            self.engine.turn_log = []
            accepted = proposal.recipient.strategy.evaluate_trade(
                proposal.recipient, proposal, self.engine)
            if accepted:
                self.engine.execute_trade(proposal)
            else:
                self.engine._log(
                    f"  [TRADE DECLINED] {proposal.recipient.name} declined "
                    f"{proposal.proposer.name}'s offer.")
                self.engine._declined_trades[
                    self.engine._trade_key(proposal)] = self.engine.turn_number
            new_log.extend(self.engine.turn_log)
            self.engine.turn_log = old
        self.engine.pending_human_trades = []

        if new_log:
            self.action_log.append_many(new_log)

    def _open_properties(self):
        was_running = self._auto_running
        if was_running:
            self._stop_auto()
        dlg = PropertiesDialog(self, self.engine, refresh_callback=self._refresh_ui)
        self.wait_window(dlg)
        self._refresh_ui()
        if was_running:
            self._start_auto()

    def _open_trade(self):
        was_running = self._auto_running
        if was_running:
            self._stop_auto()
        current_idx = self.engine.current_idx % len(self.engine.all_players)
        proposer = self.engine.all_players[current_idx]
        dlg = TradeDialog(self, self.engine, proposer=proposer)
        self.wait_window(dlg)
        if dlg.result:
            self.action_log.append_many(self.engine.turn_log[-10:])
            self._refresh_ui()
        if was_running:
            self._start_auto()

    def _set_speed(self, val):
        self._speed = int(float(val))

    def _refresh_ui(self):
        state = self.engine.get_state()
        self.turn_label.config(text=f'Turn: {state["turn"]}')
        current = state['current_player']
        if current and not self.engine.game_over:
            active = self.engine.active_players
            idx = self.engine.current_idx % len(self.engine.all_players)
            cp = self.engine.all_players[idx]
            self.current_player_label.config(
                text=f'Next: {cp.name}', fg=cp.color)
        elif self.engine.game_over:
            w = state['winner']
            self.current_player_label.config(
                text=f'WINNER: {w.name}!' if w else 'Game Over',
                fg='#FFD700')

        dice = self._last_dice if (self.settings and self.settings.show_dice) else None
        self.board.draw_board(self.engine, dice=dice)
        for panel in self.player_panels:
            panel.update()
        self._refresh_unowned()

    def _show_winner(self):
        w = self.engine.winner
        if w:
            nw = w.net_worth()
            msg = (f'{w.name} wins with net worth ${nw:,}!\n\n'
                   f'Total turns: {self.engine.turn_number}')
        else:
            msg = 'Game over!'
        if messagebox.showinfo('Game Over', msg, parent=self):
            pass

    def _back_to_menu(self):
        self._stop_auto()
        self.on_menu()